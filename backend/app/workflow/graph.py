import asyncio
from typing import TypedDict, List, Optional, Dict, Any
from langgraph.graph import StateGraph, START, END

from app.models import (
    BrandAnalyzeRequest,
    BrandDNA,
    KOLProfile,
    RankedKOL,
    MatchResponse,
)
from app.services.brand_analyzer import get_brand_analyzer
from app.services.scoring_engine import get_scoring_engine
from app.services.apify_service import get_apify_service
from app.services.gemini_service import get_gemini_service


class MatcherState(TypedDict, total=False):
    brand_request: Optional[BrandAnalyzeRequest]
    brand_dna: Optional[BrandDNA]
    top_k: int
    include_traps: bool
    min_followers: Optional[int]
    max_followers: Optional[int]
    candidates: List[KOLProfile]
    apify_status: str
    ranked_kols: List[RankedKOL]
    penalized_spam_kols: List[RankedKOL]
    trace: List[str]


async def analyze_brand_node(state: MatcherState) -> Dict[str, Any]:
    trace = list(state.get("trace", []))
    trace.append("Node 1: analyze_brand_node started")

    if state.get("brand_dna"):
        trace.append("Using existing validated BrandDNA")
        return {"trace": trace}

    req = state.get("brand_request") or BrandAnalyzeRequest()
    if req.website_url:
        trace.append(f"Ingesting client website via Jina Reader: {req.website_url}")
    if req.facebook_url:
        trace.append(f"Scraping live Facebook Page via Apify Scraper: {req.facebook_url}")

    analyzer = get_brand_analyzer()
    brand_dna = await analyzer.analyze(req)

    trace.append(f"BrandDNA extracted for '{brand_dna.brand_name}' ({brand_dna.vertical} - {brand_dna.sub_category})")
    for src in brand_dna.scraped_sources:
        trace.append(f"Ingested source: {src}")

    return {"brand_dna": brand_dna, "trace": trace}


async def discover_candidates_node(state: MatcherState) -> Dict[str, Any]:
    trace = list(state.get("trace", []))
    trace.append("Node 2: discover_candidates_node started")

    brand_dna = state.get("brand_dna")
    if not brand_dna or not brand_dna.vertical:
        raise ValueError("BrandDNA vertical is required. Zero-Hardcode Policy forbids fallback defaults.")
    if not brand_dna.thai_keywords:
        raise ValueError("BrandDNA thai_keywords is required. Zero-Hardcode Policy forbids fallback defaults.")

    vertical = brand_dna.vertical
    keywords = [k.lstrip('#').strip() for k in brand_dna.thai_keywords if k and k.lstrip('#').strip()]
    if not keywords:
        raise ValueError("No valid Thai keywords found in BrandDNA. Zero-Hardcode Policy forbids fallback defaults.")

    apify = get_apify_service()
    candidates = []

    # Live TikTok Discovery via Apify Scraper (Zero-Mock with 5-Angle Taxonomy)
    if apify.is_configured:
        trace.append(f"Querying live TikTok creators via Apify (5-Angle Taxonomy & Hashtags: #{keywords[0]})")
        try:
            live_candidates = await apify.search_live_kols_by_hashtags(
                hashtags=keywords,
                vertical=vertical,
                limit_creators=30,
                search_taxonomy=brand_dna.search_taxonomy,
                grounded_competitors=brand_dna.grounded_competitors,
                manual_competitors=brand_dna.manual_competitors,
                brand_name=brand_dna.brand_name,
            )
            if live_candidates:
                candidates = live_candidates
                trace.append(
                    f"Discovered {len(candidates)} real live Thai TikTok creators via Apify Clockworks Actor "
                    f"(2-Stage Entity Filter applied, Work-Ready signals checked)"
                )
        except Exception as e:
            trace.append(f"Apify live search error: {e}")
            raise RuntimeError(f"Live Apify TikTok Discovery failed: {e}. Zero-Mock Policy enforces 100% live data.")

    if not candidates:
        trace.append("No live TikTok creators returned for given keywords")
        raise RuntimeError(f"Zero live TikTok creators matched for hashtags {keywords[:3]}. Pure live scraping returned 0 results.")

    return {"candidates": candidates, "trace": trace}


async def enrich_apify_node(state: MatcherState) -> Dict[str, Any]:
    trace = list(state.get("trace", []))
    trace.append("Node 3: enrich_apify_node started (5-Clip Multi-Video Audit & 4 Archetypes)")
    candidates = state.get("candidates", [])

    apify = get_apify_service()
    if apify.is_configured and candidates:
        try:
            # Enrich top candidate creators with up to 5 profile videos to audit true content consistency
            await apify.enrich_creators_recent_videos(candidates, max_videos_per_creator=5, max_profiles_to_enrich=8)
            trace.append("Audited up to 5 recent TikTok videos per creator to evaluate Niche Consistency")
        except Exception as e:
            trace.append(f"Profile 5-video enrichment note: {e}")

    # Zero-Hardcode: Classify creators via Gemini Instructions into the 4 Core Archetypes with 5-clip captions
    gemini = get_gemini_service()
    if gemini.is_configured and candidates:
        try:
            creators_to_classify = [
                {
                    "id": p.id,
                    "handle": p.handle,
                    "display_name": p.display_name,
                    "bio": p.bio,
                    "captions": [v.caption for v in p.recent_videos if v.caption][:5],
                    "yellow_basket_ratio": round(
                        sum(1 for v in p.recent_videos if v.has_yellow_basket) / max(len(p.recent_videos), 1),
                        2
                    ),
                    "vertical": p.vertical,
                }
                for p in candidates
            ]
            classification_map = await gemini.classify_creator_archetypes(creators_to_classify)
            for p in candidates:
                if p.id in classification_map:
                    c_info = classification_map[p.id]
                    p.creator_archetype = c_info.get("creator_archetype", p.creator_archetype)
                    p.recommended_role = c_info.get("recommended_role", p.recommended_role)
                    if p.creator_archetype == "Top Reviewer":
                        p.creator_category = "Content Creator (เน้นรีวิว)"
                    if c_info.get("reasoning"):
                        p.creator_persona = f"{p.creator_persona} | {c_info['reasoning']}"
            trace.append(f"Classified {len(classification_map)} creators across 4 Archetypes with 5-clip context")
        except Exception as e:
            trace.append(f"Gemini instruction classification warning: {e}")

    apify_status = "Live TikTok Scraper Telemetry (Apify Clockworks Active)"
    trace.append(f"Apify telemetry status: {apify_status}")
    return {"apify_status": apify_status, "candidates": candidates, "trace": trace}


async def evaluate_and_rank_node(state: MatcherState) -> Dict[str, Any]:
    trace = list(state.get("trace", []))
    trace.append("Node 4: Creator Fit & Archetype Matching (Multi-Signal Evaluation & Ranking)")

    brand_dna = state.get("brand_dna")
    candidates = state.get("candidates", [])
    top_k = state.get("top_k", 10)
    apify_status = state.get("apify_status", "Live TikTok Scraper")

    scoring = get_scoring_engine()
    gemini = get_gemini_service()
    ranked_results: List[RankedKOL] = []
    spam_traps: List[RankedKOL] = []

    # Batch Embeddings & Scoring for all candidates (30 KOLs) asynchronously
    eval_results = await scoring.evaluate_kols_batch(candidates, brand_dna)
    for kol, (total_score, breakdown, why_text, _) in zip(candidates, eval_results):
        ranked_item = RankedKOL(
            rank=1,
            kol=kol,
            total_match_score=total_score,
            score_breakdown=breakdown,
            why_this_kol=why_text,
            thai_campaign_hooks=[],
            enrichment_source=apify_status,
            llm_generator_model="gemini-3.5-flash-lite",
        )
        if breakdown.affiliate_spam_penalty_applied:
            spam_traps.append(ranked_item)
        else:
            ranked_results.append(ranked_item)

    # Sort legitimate KOLs descending by total score
    ranked_results.sort(key=lambda x: x.total_match_score, reverse=True)

    # Sort penalized traps descending
    spam_traps.sort(key=lambda x: x.total_match_score, reverse=True)
    for idx, item in enumerate(spam_traps, 1):
        item.rank = idx

    # Balanced Top-K Selection (Archetype Quota Ranking):
    # Guarantees representation across all 4 Core Creator Archetypes:
    # 1. Educated Guru (Trust & Technical Coaching)
    # 2. Top Reviewer (Product Review & Conversion)
    # 3. Lifestyle & Vlog (Broad Reach & Lifestyle Integration)
    # 4. Niche Enthusiast (Core Community & Deep Passion)
    core_archetypes = ["Educated Guru", "Top Reviewer", "Lifestyle & Vlog", "Niche Enthusiast"]
    selected_ids = set()
    balanced_selection = []

    # 1. First Pass: Guarantee top 2 creators per archetype if available in evaluated candidates
    quota_per_archetype = 2
    for archetype in core_archetypes:
        archetype_candidates = [
            r for r in ranked_results
            if r.kol.creator_archetype == archetype and r.kol.id not in selected_ids
        ]
        archetype_candidates.sort(key=lambda x: x.total_match_score, reverse=True)
        for c in archetype_candidates[:quota_per_archetype]:
            balanced_selection.append(c)
            selected_ids.add(c.kol.id)

    # 2. Second Pass: Fill remaining slots up to max(top_k, len(balanced_selection))
    # using highest-scoring overall candidates to maintain elite score quality
    remaining_candidates = [r for r in ranked_results if r.kol.id not in selected_ids]
    remaining_candidates.sort(key=lambda x: x.total_match_score, reverse=True)

    target_total = max(top_k, len(balanced_selection))
    slots_needed = target_total - len(balanced_selection)
    if slots_needed > 0:
        for c in remaining_candidates[:slots_needed]:
            balanced_selection.append(c)
            selected_ids.add(c.kol.id)

    if len(balanced_selection) < top_k and remaining_candidates:
        for c in remaining_candidates:
            if c.kol.id not in selected_ids and len(balanced_selection) < top_k:
                balanced_selection.append(c)
                selected_ids.add(c.kol.id)

    # Re-sort final balanced portfolio descending by total match score and assign rank 1..N
    balanced_selection.sort(key=lambda x: x.total_match_score, reverse=True)
    for idx, item in enumerate(balanced_selection, 1):
        item.rank = idx

    top_ranked = balanced_selection

    archetype_counts = {
        arch: sum(1 for r in top_ranked if r.kol.creator_archetype == arch)
        for arch in core_archetypes
    }
    trace.append(
        f"Scored {len(candidates)} candidates: {len(top_ranked)} top ranked matches across all 4 archetypes {archetype_counts}, "
        f"{len(spam_traps)} affiliate spam accounts identified and penalized."
    )

    return {
        "ranked_kols": top_ranked,
        "penalized_spam_kols": spam_traps,
        "trace": trace,
    }


def build_kol_matcher_graph():
    workflow = StateGraph(MatcherState)

    workflow.add_node("analyze_brand", analyze_brand_node)
    workflow.add_node("discover_candidates", discover_candidates_node)
    workflow.add_node("enrich_apify", enrich_apify_node)
    workflow.add_node("evaluate_and_rank", evaluate_and_rank_node)

    workflow.add_edge(START, "analyze_brand")
    workflow.add_edge("analyze_brand", "discover_candidates")
    workflow.add_edge("discover_candidates", "enrich_apify")
    workflow.add_edge("enrich_apify", "evaluate_and_rank")
    workflow.add_edge("evaluate_and_rank", END)

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
    include_traps: bool = True,
    min_followers: Optional[int] = None,
    max_followers: Optional[int] = None,
) -> MatchResponse:
    graph = get_matcher_graph()
    initial_state: MatcherState = {
        "brand_request": brand_request,
        "brand_dna": brand_dna,
        "top_k": top_k,
        "include_traps": include_traps,
        "min_followers": min_followers,
        "max_followers": max_followers,
        "trace": [],
    }

    final_state = await graph.ainvoke(initial_state)

    return MatchResponse(
        brand_dna=final_state["brand_dna"],
        total_candidates_evaluated=len(final_state.get("candidates", [])),
        apify_enrichment_status=final_state.get("apify_status", "Live TikTok Scraper"),
        ranked_kols=final_state.get("ranked_kols", []),
        penalized_spam_kols=final_state.get("penalized_spam_kols", []),
        workflow_trace=final_state.get("trace", []),
    )
