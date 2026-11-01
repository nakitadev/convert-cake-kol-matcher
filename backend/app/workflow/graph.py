"""
LangGraph Workflow: 4-Stage Convert Cake TikTok KOL/KOC Matching Engine.

Spec 1 & 4.1:
  Stage 1: analyze_brand_node — Brand DNA, Conversion Model, Scene Translation, Competitor Layer 1 (Google Search Grounding)
  Stage 2: discover_candidates_node — TikTok Discovery via Apify (KOL_QUERY & KOC_QUERY, TH country code),
           Profile enrichment, Competitor Layer 2 (Co-occurrence Discovery)
  Stage 3: filter_and_classify_node — Two-Stage Filtering (Gate 1: Merchant & Bot Filter, Gate 2: Batch LLM Relevance Gate),
           2x2 Sub-Style Guard, Competitor Layer 3 (Sponsor Conflict & Comparison Opportunity)
  Stage 4: score_rank_hooks_node — Dynamic Scoring (40/35/25), Balanced Top-K Media Mix Portfolio,
           Tier-2 Comment Analysis, Two-Pass Stratified Quota Ranking
"""
import asyncio
import logging
from typing import TypedDict, List, Optional, Dict, Any

from langgraph.graph import StateGraph, START, END

from app.models import (
    BrandAnalyzeRequest,
    BrandDNA,
    Competitor,
    ExcludedCreator,
    FilterStats,
    KOLProfile,
    MatchResponse,
    RankedKOL,
    StrategySummary,
)
from app.services.brand_analyzer import get_brand_analyzer
from app.services.scoring_engine import get_scoring_engine
from app.services.apify_service import get_apify_service
from app.services.gemini_service import get_gemini_service
from app.services.creator_filter import (
    group_items_by_creator,
    build_profile,
    brand_account_reason,
    merchant_reason,
    affiliate_bot_reason,
    guard_sub_style,
    frequent_terms,
    competitor_flags,
)
from app.services.tracing import (
    get_langfuse_callback_handler,
    flush_langfuse_handler,
    get_trace_url_from_handler,
)

logger = logging.getLogger(__name__)


class MatcherState(TypedDict, total=False):
    brand_request: Optional[BrandAnalyzeRequest]
    brand_dna: Optional[BrandDNA]
    top_k: int
    raw_clips_count: int
    raw_creators: Dict[str, Dict[str, Any]]
    assembled_creators: List[KOLProfile]
    excluded_creators: List[ExcludedCreator]
    qualified_creators: List[KOLProfile]
    filter_stats: FilterStats
    strategy: StrategySummary
    ranked_kols: List[RankedKOL]
    warnings: List[str]
    trace: List[str]


# ---------------------------------------------------------------------------
# Node 1: Brand DNA & Conversion Model Classification
# ---------------------------------------------------------------------------
async def analyze_brand_node(state: MatcherState) -> Dict[str, Any]:
    trace = list(state.get("trace", []))
    trace.append("Stage 1: analyze_brand_node started")

    if state.get("brand_dna"):
        trace.append("Using existing validated BrandDNA")
        return {"trace": trace}

    req = state.get("brand_request") or BrandAnalyzeRequest()
    if req.website_url:
        trace.append(f"Ingesting website via Jina Reader: {req.website_url}")
    if req.facebook_url:
        trace.append(f"Scraping Facebook page: {req.facebook_url}")

    analyzer = get_brand_analyzer()
    brand_dna = await analyzer.analyze(req)

    trace.append(
        f"BrandDNA extracted: '{brand_dna.brand_name}' ({brand_dna.conversion_model} — "
        f"KOL {brand_dna.kol_koc_mix.kol}% : KOC {brand_dna.kol_koc_mix.koc}%)"
    )
    trace.append(
        f"Scene Translation generated {len(brand_dna.search_queries)} queries "
        f"({sum(1 for q in brand_dna.search_queries if q.side == 'KOL_QUERY')} KOL / "
        f"{sum(1 for q in brand_dna.search_queries if q.side == 'KOC_QUERY')} KOC)"
    )
    trace.append(f"Competitor Layer 1: {len(brand_dna.competitors)} Thai competitors catalogued")

    return {"brand_dna": brand_dna, "trace": trace}


# ---------------------------------------------------------------------------
# Node 2: Adaptive Scene Translation & TikTok Discovery
# ---------------------------------------------------------------------------
async def discover_candidates_node(state: MatcherState) -> Dict[str, Any]:
    trace = list(state.get("trace", []))
    trace.append("Stage 2: discover_candidates_node started (TikTok Discovery)")

    brand_dna = state.get("brand_dna")
    if not brand_dna:
        raise ValueError("BrandDNA is required for TikTok discovery.")

    natural_queries = [q.query for q in brand_dna.search_queries][:8]
    trace.append(f"Running Single-Job Apify TikTok search (Country: TH) across {len(natural_queries)} natural queries")

    apify = get_apify_service()
    warnings = list(state.get("warnings", []))
    raw_items: List[Dict[str, Any]] = []

    if apify.is_configured:
        try:
            res = await apify.discover_batch(queries=natural_queries, results_per_query=8)
            raw_items = res.get("items", [])
            for err in res.get("errors", []):
                warnings.append(str(err))
            trace.append(f"Apify single-job batch returned {len(raw_items)} raw clips")
        except Exception as e:
            trace.append(f"Apify discovery error: {e}")
            raise RuntimeError(f"Live TikTok discovery failed: {e}. Zero-Mock Policy enforces genuine data.")
    else:
        raise RuntimeError("APIFY_API_TOKEN is not configured. Live TikTok discovery requires Apify.")

    if not raw_items:
        raise RuntimeError("Zero live TikTok clips returned for search queries.")

    # Group clips by creator handle
    grouped = group_items_by_creator(raw_items)
    trace.append(f"Grouped clips into {len(grouped)} unique creator candidates")

    # Fast Profile enrichment: only enrich creators with < 3 videos from search, max 4 handles
    enriched_profiles: Dict[str, List[Dict[str, Any]]] = {}
    top_handles = [h for h, entry in grouped.items() if len(entry.get("videos", {})) < 3][:4]
    if apify.is_configured and top_handles:
        try:
            enriched_profiles = await apify.scrape_profiles(top_handles, per_profile=4)
            trace.append(f"Profile enrichment completed for {len(enriched_profiles)} creators")
        except Exception as e:
            trace.append(f"Profile enrichment note: {e}")
            warnings.append(f"Profile enrichment partial: {e}")

    # Build assembled KOLProfile objects
    assembled: List[KOLProfile] = []
    for h, entry in grouped.items():
        try:
            p = build_profile(entry, enriched_profiles.get(h.lower()), max_videos=8)
            assembled.append(p)
        except Exception as e:
            logger.debug(f"Failed to build profile for {h}: {e}")

    trace.append(f"Assembled {len(assembled)} candidate creator profiles with deterministic signals")

    # Competitor Layer 2: Bottom-Up TikTok Co-occurrence Discovery
    gemini = get_gemini_service()
    if gemini.is_configured and assembled:
        terms = frequent_terms(assembled, brand_dna, top_n=30, min_creators=2)
        if terms:
            try:
                co_comps = await gemini.identify_cooccurring_brands(
                    brand_name=brand_dna.brand_name,
                    sub_category=brand_dna.sub_category or brand_dna.vertical,
                    frequent_terms=terms,
                )
                if co_comps:
                    new_competitors = []
                    existing_brands = {c.brand.lower() for c in brand_dna.competitors}
                    for item in co_comps:
                        b_name = item.get("brand")
                        if b_name and b_name.lower() not in existing_brands:
                            new_competitors.append(
                                Competitor(
                                    brand=b_name,
                                    aliases=item.get("aliases", [b_name]),
                                    source="tiktok_cooccurrence",
                                    mentions=int(item.get("mentions", 0)),
                                )
                            )
                    if new_competitors:
                        brand_dna.competitors.extend(new_competitors)
                        trace.append(f"Competitor Layer 2: Discovered {len(new_competitors)} co-occurring competitor brands on TikTok")
            except Exception as e:
                trace.append(f"Competitor Layer 2 discovery warning: {e}")

    return {
        "raw_clips_count": len(raw_items),
        "raw_creators": grouped,
        "assembled_creators": assembled,
        "warnings": warnings,
        "trace": trace,
    }


# ---------------------------------------------------------------------------
# Node 3: Two-Stage Filtering & 2x2 KOL/KOC Classification
# ---------------------------------------------------------------------------
async def filter_and_classify_node(state: MatcherState) -> Dict[str, Any]:
    trace = list(state.get("trace", []))
    trace.append("Stage 3: filter_and_classify_node started (Two-Stage Filtering & 2x2 Matrix)")

    brand_dna = state.get("brand_dna")
    assembled = state.get("assembled_creators", [])
    excluded: List[ExcludedCreator] = []
    gate1_passed: List[KOLProfile] = []

    # --- Gate 1: Rule-Based Merchant & Smart Spam Bot Filter (Spec 4.1) ---
    removed_brand = 0
    removed_merch = 0
    removed_bots = 0

    for p in assembled:
        brand_reason = brand_account_reason(p, brand_dna)
        if brand_reason:
            removed_brand += 1
            excluded.append(
                ExcludedCreator(
                    handle=p.handle,
                    display_name=p.display_name,
                    tiktok_url=p.tiktok_url,
                    follower_count=p.follower_count,
                    bio=p.bio,
                    stage="gate1_brand_account",
                    reason=brand_reason,
                )
            )
            continue

        merch_reason = merchant_reason(p)
        if merch_reason:
            removed_merch += 1
            excluded.append(
                ExcludedCreator(
                    handle=p.handle,
                    display_name=p.display_name,
                    tiktok_url=p.tiktok_url,
                    follower_count=p.follower_count,
                    bio=p.bio,
                    stage="gate1_merchant",
                    reason=merch_reason,
                )
            )
            continue

        bot_reason = affiliate_bot_reason(p)
        if bot_reason:
            removed_bots += 1
            excluded.append(
                ExcludedCreator(
                    handle=p.handle,
                    display_name=p.display_name,
                    tiktok_url=p.tiktok_url,
                    follower_count=p.follower_count,
                    bio=p.bio,
                    stage="gate1_affiliate_bot",
                    reason=bot_reason,
                )
            )
            continue

        gate1_passed.append(p)

    trace.append(
        f"Gate 1 Filter: {len(gate1_passed)} passed, {len(excluded)} excluded "
        f"({removed_brand} brand accounts, {removed_merch} merchants, {removed_bots} affiliate bots)"
    )

    # --- Gate 2: Batch LLM Relevance Gate & 2x2 Matrix Classification (Spec 4.1 & 4.2) ---
    gemini = get_gemini_service()
    qualified: List[KOLProfile] = []
    removed_irrelevant = 0

    if gemini.is_configured and gate1_passed:
        creator_summaries = [
            {
                "id": p.id,
                "handle": p.handle,
                "display_name": p.display_name,
                "bio": p.bio,
                "captions": [v.caption for v in p.recent_videos[:3] if v.caption],
                "query_origin": p.query_origin,
                "basket_ratio": p.signals.basket_ratio,
                "save_rate": p.signals.save_rate,
                "comment_to_like": p.signals.comment_to_like,
                "avg_caption_length": p.signals.avg_caption_length,
            }
            for p in gate1_passed
        ]

        try:
            rel_map = await gemini.relevance_gate(
                brand=brand_dna.model_dump(),
                creators=creator_summaries,
            )
            for p in gate1_passed:
                info = rel_map.get(p.id) or {}
                is_rel = info.get("is_relevant_creator", True)
                if not is_rel:
                    removed_irrelevant += 1
                    excluded.append(
                        ExcludedCreator(
                            handle=p.handle,
                            display_name=p.display_name,
                            tiktok_url=p.tiktok_url,
                            follower_count=p.follower_count,
                            bio=p.bio,
                            stage="gate2_irrelevant",
                            reason=info.get("why_it_fits") or "Content irrelevant / meme / homonym",
                        )
                    )
                else:
                    p.llm_relevance_score = float(info.get("relevance_score") or 0.8)
                    raw_sub_style = str(
                        info.get("sub_style")
                        or ("KOL - Expert / Guru" if p.query_origin == "KOL_QUERY" else "KOC - Hard-Sell Reviewer")
                    )
                    # Enforce 2x2 guardrail (e.g. Lifestyle cannot have yellow basket >= 15%)
                    p.sub_style = guard_sub_style(raw_sub_style, p.signals)
                    role = info.get("main_role")
                    p.funnel_role = role if role in ("KOL", "KOC") else ("KOL" if p.sub_style.startswith("KOL") else "KOC")
                    p.why_it_fits = str(info.get("why_it_fits") or f"Matches {brand_dna.sub_category} audience")

                    # Competitor Layer 3: Sponsor Conflict & Multi-Brand Comparison
                    p.competitor_flags = competitor_flags(p, brand_dna.competitors)
                    qualified.append(p)

            trace.append(f"Gate 2 Batch LLM Relevance Gate: {len(qualified)} qualified ({removed_irrelevant} irrelevant channels excluded)")
        except Exception as e:
            trace.append(f"Gate 2 LLM Relevance Gate error ({e}) — falling back to deterministic classification")
            for p in gate1_passed:
                p.sub_style = "KOL - Expert / Guru" if p.query_origin == "KOL_QUERY" else "KOC - Hard-Sell Reviewer"
                p.funnel_role = "KOL" if p.sub_style.startswith("KOL") else "KOC"
                p.llm_relevance_score = 0.75
                p.why_it_fits = f"Fits {brand_dna.vertical} target audience."
                p.competitor_flags = competitor_flags(p, brand_dna.competitors)
                qualified.append(p)
    else:
        qualified = gate1_passed

    stats = FilterStats(
        raw_clips=state.get("raw_clips_count", 0),
        unique_creators=len(assembled),
        removed_brand_accounts=removed_brand,
        removed_merchants=removed_merch,
        removed_affiliate_bots=removed_bots,
        removed_irrelevant=removed_irrelevant,
        scored=len(qualified),
    )

    return {
        "excluded_creators": excluded,
        "qualified_creators": qualified,
        "filter_stats": stats,
        "trace": trace,
    }


# ---------------------------------------------------------------------------
# Node 4: Dynamic Scoring, Media Mix Top-K & Stratified Portfolio Ranking
# ---------------------------------------------------------------------------
async def score_rank_hooks_node(state: MatcherState) -> Dict[str, Any]:
    trace = list(state.get("trace", []))
    trace.append("Stage 4: score_rank_hooks_node started (Scoring, Top-K Media Mix & Stratified Ranking)")

    brand_dna = state.get("brand_dna")
    qualified = state.get("qualified_creators", [])
    top_k = state.get("top_k", 10)
    scoring = get_scoring_engine()
    gemini = get_gemini_service()
    apify = get_apify_service()

    if not qualified:
        trace.append("Warning: No creators survived filtering.")
        return {
            "ranked_kols": [],
            "strategy": StrategySummary(
                conversion_model=brand_dna.conversion_model,
                conversion_model_reason=brand_dna.conversion_model_reason,
                recommended_mix=brand_dna.kol_koc_mix,
                achieved_mix={"KOL": 0, "KOC": 0},
            ),
            "trace": trace,
        }

    # 1. Batch Embeddings & Scoring (40 / 35 / 25 pts)
    eval_results = await scoring.evaluate_kols_batch(qualified, brand_dna)
    candidates_ranked: List[RankedKOL] = []
    for kol, (score, breakdown) in zip(qualified, eval_results):
        candidates_ranked.append(
            RankedKOL(
                rank=1,
                kol=kol,
                total_match_score=score,
                score_breakdown=breakdown,
            )
        )

    # Sort descending by score
    candidates_ranked.sort(key=lambda x: x.total_match_score, reverse=True)

    # 2. Balanced Top-K Selection based on Recommended Media Mix (Spec 2.2 & 4.2)
    # E.g., ECOMMERCE_PRODUCT recommends 30% KOL : 70% KOC
    kol_target_ratio = brand_dna.kol_koc_mix.kol / 100.0
    desired_kol = max(1, round(top_k * kol_target_ratio))
    desired_koc = max(1, top_k - desired_kol)

    sub_styles = [
        "KOL - Expert / Guru",
        "KOL - Lifestyle / Aesthetic",
        "KOC - Hard-Sell Reviewer",
        "KOC - Everyday User / Vlog",
    ]

    selected_ids = set()
    selected: List[RankedKOL] = []

    # Pass A: Guarantee at least 1 representation per sub-style if available
    for style in sub_styles:
        matching = [r for r in candidates_ranked if r.kol.sub_style == style and r.kol.id not in selected_ids]
        if matching:
            best = matching[0]
            selected.append(best)
            selected_ids.add(best.kol.id)

    # Pass B: Fill KOL & KOC quotas
    current_kol = sum(1 for r in selected if r.kol.funnel_role == "KOL")
    current_koc = sum(1 for r in selected if r.kol.funnel_role == "KOC")

    for r in candidates_ranked:
        if r.kol.id in selected_ids:
            continue
        if r.kol.funnel_role == "KOL" and current_kol < desired_kol:
            selected.append(r)
            selected_ids.add(r.kol.id)
            current_kol += 1
        elif r.kol.funnel_role == "KOC" and current_koc < desired_koc:
            selected.append(r)
            selected_ids.add(r.kol.id)
            current_koc += 1
        if len(selected) >= top_k:
            break

    # Pass C: Fill remaining slots if either side had fewer candidates
    if len(selected) < top_k:
        for r in candidates_ranked:
            if r.kol.id not in selected_ids:
                selected.append(r)
                selected_ids.add(r.kol.id)
                if len(selected) >= top_k:
                    break

    # 3. Tier-2 Targeted Comment Analysis for Top-K Creators (Spec 4.3 #3)
    if apify.is_configured:
        video_urls_to_scrape = []
        creator_video_map = {}
        for r in selected:
            # Pick the video with the most comments or yellow basket
            vids = r.kol.recent_videos
            if vids:
                best_vid = max(vids, key=lambda v: (v.has_yellow_basket, v.comments, v.views))
                if best_vid.url:
                    video_urls_to_scrape.append(best_vid.url)
                    creator_video_map[best_vid.url] = r.kol

        if video_urls_to_scrape:
            try:
                # Scrape up to 3 candidate clips with 20s timeout; fallback to Tier-1 Fast Proxy if slow
                comments_map = await asyncio.wait_for(
                    apify.scrape_comments(video_urls_to_scrape[:3], per_post=20),
                    timeout=20.0,
                )
                if comments_map:
                    trace.append(f"Tier-2 Comment Analysis: Scraped live comments for {len(comments_map)} Top-K clips")
                    for url, cmts in comments_map.items():
                        kol_obj = creator_video_map.get(url)
                        if kol_obj:
                            kol_obj.real_comments = cmts
                    # Re-score Top-K with Tier-2 comment intent
                    for r in selected:
                        if r.kol.real_comments:
                            new_score, new_breakdown = scoring.evaluate_kol(r.kol, brand_dna)
                            r.total_match_score = new_score
                            r.score_breakdown = new_breakdown
            except Exception as e:
                trace.append(f"Tier-2 comment analysis note: {e} — using Tier-1 Fast Proxy")

    # Re-sort final portfolio descending by total match score and assign rank 1..N
    selected.sort(key=lambda x: x.total_match_score, reverse=True)
    for idx, r in enumerate(selected, start=1):
        r.rank = idx

    # Build Strategy Summary
    achieved_kol = sum(1 for r in selected if r.kol.funnel_role == "KOL")
    achieved_koc = sum(1 for r in selected if r.kol.funnel_role == "KOC")
    strategy = StrategySummary(
        conversion_model=brand_dna.conversion_model,
        conversion_model_reason=brand_dna.conversion_model_reason,
        recommended_mix=brand_dna.kol_koc_mix,
        achieved_mix={"KOL": achieved_kol, "KOC": achieved_koc},
    )

    trace.append(
        f"Final Portfolio: {len(selected)} Top-K creators (Achieved Mix: {achieved_kol} KOL : {achieved_koc} KOC, "
        f"Target Mix: {brand_dna.kol_koc_mix.kol}% : {brand_dna.kol_koc_mix.koc}%)"
    )

    return {
        "ranked_kols": selected,
        "strategy": strategy,
        "trace": trace,
    }


# ---------------------------------------------------------------------------
# Graph Compilation
# ---------------------------------------------------------------------------
def build_kol_matcher_graph():
    workflow = StateGraph(MatcherState)

    workflow.add_node("analyze_brand", analyze_brand_node)
    workflow.add_node("discover_candidates", discover_candidates_node)
    workflow.add_node("filter_and_classify", filter_and_classify_node)
    workflow.add_node("score_rank_hooks", score_rank_hooks_node)

    workflow.add_edge(START, "analyze_brand")
    workflow.add_edge("analyze_brand", "discover_candidates")
    workflow.add_edge("discover_candidates", "filter_and_classify")
    workflow.add_edge("filter_and_classify", "score_rank_hooks")
    workflow.add_edge("score_rank_hooks", END)

    return workflow.compile()


_graph_instance = None


def get_matcher_graph():
    global _graph_instance
    if _graph_instance is None:
        _graph_instance = build_kol_matcher_graph()
    return _graph_instance


async def run_full_matching(
    brand_request: Optional[BrandAnalyzeRequest] = None,
    brand_dna: Optional[BrandDNA] = None,
    top_k: int = 10,
) -> MatchResponse:
    graph = get_matcher_graph()
    initial_state: MatcherState = {
        "brand_request": brand_request,
        "brand_dna": brand_dna,
        "top_k": top_k,
        "trace": [],
        "warnings": [],
    }

    # Optional Langfuse Tracing
    lf_handler = get_langfuse_callback_handler()
    config: Dict[str, Any] = {}
    if lf_handler:
        brand_label = (
            (brand_dna.brand_name if brand_dna else None)
            or (brand_request.brand_name if brand_request else None)
            or "Thai_KOL_Matcher"
        )
        config["callbacks"] = [lf_handler]
        config["run_name"] = f"kol_matching_{brand_label}"
        config["tags"] = ["convert-cake", "kol-matcher"]
        config["metadata"] = {
            "brand_name": brand_label,
            "top_k": top_k,
        }
        logger.info("Langfuse tracing enabled for workflow: %s", config["run_name"])

    try:
        final_state = await graph.ainvoke(initial_state, config=config if config else None)
    finally:
        flush_langfuse_handler(lf_handler)

    brand_result = final_state.get("brand_dna")
    strategy_result = final_state.get("strategy") or StrategySummary(
        conversion_model=brand_result.conversion_model if brand_result else "ECOMMERCE_PRODUCT",
        recommended_mix=brand_result.kol_koc_mix if brand_result else {"kol": 50, "koc": 50},
        achieved_mix={},
    )
    filter_stats = final_state.get("filter_stats") or FilterStats()

    workflow_trace = final_state.get("trace", [])
    trace_url = get_trace_url_from_handler(lf_handler)
    if trace_url:
        workflow_trace.append(f"Langfuse Trace: {trace_url}")
    elif lf_handler and getattr(lf_handler, "last_trace_id", None):
        workflow_trace.append(f"Langfuse Trace ID: {lf_handler.last_trace_id}")

    return MatchResponse(
        brand_dna=brand_result,
        strategy=strategy_result,
        filter_stats=filter_stats,
        ranked_kols=final_state.get("ranked_kols", []),
        excluded_creators=final_state.get("excluded_creators", []),
        warnings=final_state.get("warnings", []),
        workflow_trace=workflow_trace,
        langfuse_trace_url=trace_url,
    )
