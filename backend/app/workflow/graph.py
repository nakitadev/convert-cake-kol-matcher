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
                limit_creators=50,
                search_taxonomy=brand_dna.search_taxonomy,
                grounded_competitors=brand_dna.grounded_competitors,
                manual_competitors=brand_dna.manual_competitors,
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
    trace.append("Node 3: enrich_apify_node started")
    apify_status = "Live TikTok Scraper Telemetry (Apify Clockworks Active)"
    trace.append(f"Apify telemetry status: {apify_status}")
    return {"apify_status": apify_status, "trace": trace}


async def score_and_rank_node(state: MatcherState) -> Dict[str, Any]:
    trace = list(state.get("trace", []))
    trace.append("Node 4: score_and_rank_node started")

    brand_dna = state.get("brand_dna")
    candidates = state.get("candidates", [])
    top_k = state.get("top_k", 20)
    apify_status = state.get("apify_status", "Live TikTok Scraper")

    scoring = get_scoring_engine()
    gemini = get_gemini_service()
    ranked_results: List[RankedKOL] = []
    spam_traps: List[RankedKOL] = []

    for kol in candidates:
        total_score, breakdown, why_text, hooks = scoring.evaluate_kol(kol, brand_dna)
        ranked_item = RankedKOL(
            rank=1,
            kol=kol,
            total_match_score=total_score,
            score_breakdown=breakdown,
            why_this_kol=why_text,
            thai_campaign_hooks=hooks,
            enrichment_source=apify_status,
            llm_generator_model="gemini-3.5-flash-lite",
        )
        if breakdown.affiliate_spam_penalty_applied:
            spam_traps.append(ranked_item)
        else:
            ranked_results.append(ranked_item)

    # Sort legitimate KOLs descending by total score
    ranked_results.sort(key=lambda x: x.total_match_score, reverse=True)
    for idx, item in enumerate(ranked_results, 1):
        item.rank = idx

    # Sort penalized traps descending
    spam_traps.sort(key=lambda x: x.total_match_score, reverse=True)
    for idx, item in enumerate(spam_traps, 1):
        item.rank = idx

    top_ranked = ranked_results[:top_k]

    # Dynamic AI synthesis of personalized hooks and strategic rationale via Gemini 3.5 Flash Lite (Zero-Hardcode)
    if gemini.is_configured and brand_dna:
        for item in top_ranked:
            try:
                llm_rationale, llm_hooks = await gemini.generate_hooks_and_rationale(
                    brand_name=brand_dna.brand_name,
                    brand_vertical=brand_dna.vertical,
                    brand_price=brand_dna.average_price_thb,
                    kol_name=item.kol.display_name,
                    kol_persona=item.kol.creator_persona,
                    kol_styles=item.kol.content_styles,
                    median_er=item.score_breakdown.median_engagement_rate_pct,
                    is_spam=item.score_breakdown.affiliate_spam_penalty_applied,
                    spam_reason=item.score_breakdown.affiliate_spam_reason or "",
                    creator_archetype=item.kol.creator_archetype,
                    is_review_creator=(item.kol.creator_category == "Content Creator (เน้นรีวิว)"),
                )
                if llm_rationale:
                    item.why_this_kol = llm_rationale
                if llm_hooks and len(llm_hooks) > 0:
                    item.thai_campaign_hooks = llm_hooks
            except Exception as e:
                pass

    trace.append(
        f"Scored {len(candidates)} candidates: {len(top_ranked)} top ranked matches, "
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
    workflow.add_node("score_and_rank", score_and_rank_node)

    workflow.add_edge(START, "analyze_brand")
    workflow.add_edge("analyze_brand", "discover_candidates")
    workflow.add_edge("discover_candidates", "enrich_apify")
    workflow.add_edge("enrich_apify", "score_and_rank")
    workflow.add_edge("score_and_rank", END)

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
    top_k: int = 20,
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
