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
from app.services.kol_repository import get_kol_repository
from app.services.scoring_engine import get_scoring_engine
from app.services.apify_service import get_apify_service


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
    analyzer = get_brand_analyzer()
    brand_dna = await analyzer.analyze(req)

    trace.append(f"BrandDNA synthesized for '{brand_dna.brand_name}' ({brand_dna.vertical})")
    return {"brand_dna": brand_dna, "trace": trace}


def discover_candidates_node(state: MatcherState) -> Dict[str, Any]:
    trace = list(state.get("trace", []))
    trace.append("Node 2: discover_candidates_node started")

    repo = get_kol_repository()
    brand_dna = state.get("brand_dna")
    vertical = brand_dna.vertical if brand_dna else None

    candidates = repo.filter_candidates(
        vertical=vertical,
        min_followers=state.get("min_followers"),
        max_followers=state.get("max_followers"),
        include_penalized_traps=True, # We evaluate all to demonstrate trap catching
    )

    trace.append(f"Retrieved {len(candidates)} Thai KOL candidate profiles from repository")
    return {"candidates": candidates, "trace": trace}


async def enrich_apify_node(state: MatcherState) -> Dict[str, Any]:
    trace = list(state.get("trace", []))
    trace.append("Node 3: enrich_apify_node started")

    apify = get_apify_service()
    candidates = state.get("candidates", [])

    if apify.is_configured and candidates:
        lead_handle = candidates[0].handle
        result = await apify.enrich_profile(lead_handle)
        apify_status = result.get("message", "Live Apify enriched")
        enrich_source = result.get("source", "Live Apify TikTok Actor")
    else:
        apify_status = "Pre-indexed verified Thai TikTok pool (Production-grade resilient fallback)"
        enrich_source = "Local Pre-Indexed Thai Pool"

    trace.append(f"Apify telemetry status: {apify_status}")
    return {"apify_status": apify_status, "trace": trace}


def score_and_rank_node(state: MatcherState) -> Dict[str, Any]:
    trace = list(state.get("trace", []))
    trace.append("Node 4: score_and_rank_node started")

    brand_dna = state.get("brand_dna")
    candidates = state.get("candidates", [])
    top_k = state.get("top_k", 8)
    apify_status = state.get("apify_status", "Local Pre-Indexed Thai Pool")

    scoring = get_scoring_engine()
    ranked_results: List[RankedKOL] = []
    spam_traps: List[RankedKOL] = []

    for kol in candidates:
        total_score, breakdown, why_text, hooks = scoring.evaluate_kol(kol, brand_dna)
        ranked_item = RankedKOL(
            rank=1, # will set to final index after sort
            kol=kol,
            total_match_score=total_score,
            score_breakdown=breakdown,
            why_this_kol=why_text,
            thai_campaign_hooks=hooks,
            enrichment_source=apify_status,
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
    top_k: int = 8,
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
        apify_enrichment_status=final_state.get("apify_status", "Completed"),
        ranked_kols=final_state.get("ranked_kols", []),
        penalized_spam_kols=final_state.get("penalized_spam_kols", []),
        workflow_trace=final_state.get("trace", []),
    )
