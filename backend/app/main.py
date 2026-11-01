import os
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv

# Load .env (supports backend/.env or root .env, container env vars take precedence)
env_path = Path(__file__).resolve().parent.parent / ".env"
root_env = Path(__file__).resolve().parents[2] / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path, override=False)
elif root_env.exists():
    load_dotenv(dotenv_path=root_env, override=False)
else:
    load_dotenv(override=False)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.models import (
    BrandAnalyzeRequest,
    BrandDNA,
    MatchRequest,
    AutoMatchRequest,
    MatchResponse,
)
from app.services.brand_analyzer import get_brand_analyzer
from app.workflow.graph import run_full_matching

app = FastAPI(
    title="Convert Cake — Thai TikTok KOL Matcher API",
    description="AI Automation Engine for Thai TikTok Influencer Matching & Ranking",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "name": "Convert Cake — Thai TikTok KOL Matcher API",
        "status": "operational",
        "version": "1.0.0",
        "market": "Thailand",
        "endpoints": [
            "/api/health",
            "/api/demo-presets",
            "/api/analyze-brand",
            "/api/match-kols",
            "/api/auto-match",
        ],
    }


@app.get("/api/health")
async def health():
    return {"status": "healthy", "service": "kol-matcher-backend"}


def get_dry_run_dataset() -> Dict[str, Any]:
    dataset_path = Path(__file__).resolve().parent / "data" / "dry_run_dataset.json"
    if dataset_path.exists():
        try:
            return json.loads(dataset_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def resolve_preset(dataset: Dict[str, Any], preset_id: Optional[str], brand_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
    if preset_id and preset_id in dataset:
        return dataset[preset_id]
    if brand_name:
        b_lower = brand_name.lower().strip()
        for k, v in dataset.items():
            cand_name = v.get("brand_name", "").lower().strip()
            if b_lower in cand_name or cand_name in b_lower:
                return v
    return dataset.get("skincare-beauty")


@app.get("/api/demo-presets")
async def demo_presets():
    """
    Presets endpoint for Dry Run simulation and benchmark demonstration.
    """
    dataset = get_dry_run_dataset()
    return [
        {
            "id": k,
            "brand_name": v.get("brand_name"),
            "industry": v.get("industry"),
            "icon": v.get("icon", "🏷️"),
            "badge": v.get("badge", "Benchmark"),
            "execution_duration_sec": v.get("execution_duration_sec", 60.0),
            "estimated_cost_usd": v.get("estimated_cost_usd", 0.28),
            "estimated_cost_thb": v.get("estimated_cost_thb", 9.80),
            "brand_dna": v.get("brand_dna", {}),
        }
        for k, v in dataset.items()
    ]


@app.post("/api/analyze-brand", response_model=BrandDNA)
async def analyze_brand(req: BrandAnalyzeRequest):
    """
    Stage 1: Extract Brand DNA from client website/Facebook page with Gemini 3.5 Flash Lite.
    Supports Human-in-the-Loop review & editing prior to Stage 2.
    """
    if req.dry_run:
        dataset = get_dry_run_dataset()
        preset = resolve_preset(dataset, req.preset_id, req.brand_name)
        if preset and "brand_dna" in preset:
            dna_dict = dict(preset["brand_dna"])
            if req.custom_notes:
                dna_dict["custom_notes"] = req.custom_notes
            if req.manual_competitors:
                dna_dict["manual_competitors"] = req.manual_competitors
            return BrandDNA(**dna_dict)

    try:
        analyzer = get_brand_analyzer()
        brand_dna = await analyzer.analyze(req)
        return brand_dna
    except Exception as e:
        err_msg = str(e)
        if any(keyword in err_msg for keyword in ["HTTP 402", "HTTP 403", "Quota Exhausted", "hard limit exceeded", "usage limit", "APIFY_API_TOKEN is not configured"]):
            raise HTTPException(status_code=402, detail=f"Apify Usage Quota Exhausted: {err_msg}")
        if any(keyword in err_msg for keyword in ["429", "ResourceExhausted", "RATE_LIMIT_EXCEEDED", "rate limit"]):
            raise HTTPException(status_code=429, detail=f"AI/LLM Rate Limit Exceeded (HTTP 429): {err_msg}")
        raise HTTPException(status_code=500, detail=f"Failed to analyze brand: {str(e)}")


@app.post("/api/match-kols", response_model=MatchResponse)
async def match_kols(req: MatchRequest):
    """
    Stage 2: Evaluate & rank live Thai TikTok creators against Brand DNA
    using the Archetype-Aware Dynamic Scoring Engine (Relevance 40%, Engagement 35%, Multi-Signal Audience 25%).
    """
    if req.dry_run:
        dataset = get_dry_run_dataset()
        preset = resolve_preset(dataset, req.preset_id, req.brand_dna.brand_name)
        if preset and "match_response" in preset:
            res_dict = dict(preset["match_response"])
            if req.top_k and "ranked_kols" in res_dict:
                res_dict["ranked_kols"] = res_dict["ranked_kols"][: req.top_k]
            return MatchResponse(**res_dict)

    try:
        response = await run_full_matching(
            brand_dna=req.brand_dna,
            top_k=req.top_k,
        )
        return response
    except Exception as e:
        err_msg = str(e)
        if any(keyword in err_msg for keyword in ["HTTP 402", "HTTP 403", "Quota Exhausted", "hard limit exceeded", "usage limit", "APIFY_API_TOKEN is not configured"]):
            raise HTTPException(status_code=402, detail=f"Apify Usage Quota Exhausted: {err_msg}")
        if any(keyword in err_msg for keyword in ["429", "ResourceExhausted", "RATE_LIMIT_EXCEEDED", "rate limit"]):
            raise HTTPException(status_code=429, detail=f"AI/LLM Rate Limit Exceeded (HTTP 429): {err_msg}")
        raise HTTPException(status_code=500, detail=f"KOL matching failed: {err_msg}")


@app.post("/api/auto-match", response_model=MatchResponse)
async def auto_match(req: AutoMatchRequest):
    """
    1-Click End-to-End matching pipeline combining Stage 1 & Stage 2 via LangGraph.
    """
    if req.dry_run:
        dataset = get_dry_run_dataset()
        preset = resolve_preset(dataset, req.preset_id, req.brand_name)
        if preset and "match_response" in preset:
            res_dict = dict(preset["match_response"])
            if req.top_k and "ranked_kols" in res_dict:
                res_dict["ranked_kols"] = res_dict["ranked_kols"][: req.top_k]
            return MatchResponse(**res_dict)

    try:
        brand_req = BrandAnalyzeRequest(
            brand_name=req.brand_name,
            website_url=req.website_url,
            facebook_url=req.facebook_url,
            custom_notes=req.custom_notes,
            manual_competitors=req.manual_competitors,
            force_refresh=req.force_refresh,
        )
        response = await run_full_matching(
            brand_request=brand_req,
            top_k=req.top_k,
        )
        return response
    except Exception as e:
        err_msg = str(e)
        if any(keyword in err_msg for keyword in ["HTTP 402", "HTTP 403", "Quota Exhausted", "hard limit exceeded", "usage limit", "APIFY_API_TOKEN is not configured"]):
            raise HTTPException(status_code=402, detail=f"Apify Usage Quota Exhausted: {err_msg}")
        if any(keyword in err_msg for keyword in ["429", "ResourceExhausted", "RATE_LIMIT_EXCEEDED", "rate limit"]):
            raise HTTPException(status_code=429, detail=f"AI/LLM Rate Limit Exceeded (HTTP 429): {err_msg}")
        raise HTTPException(status_code=500, detail=f"Auto matching failed: {err_msg}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
