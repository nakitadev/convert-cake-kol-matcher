from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.models import (
    BrandAnalyzeRequest,
    BrandDNA,
    MatchRequest,
    AutoMatchRequest,
    MatchResponse,
    KOLProfile,
)
from app.services.brand_analyzer import get_brand_analyzer
from app.services.kol_repository import get_kol_repository
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
            "/api/presets",
            "/api/analyze-brand",
            "/api/match-kols",
            "/api/auto-match",
            "/api/kols",
        ]
    }


@app.get("/api/health")
async def health():
    return {"status": "healthy", "service": "kol-matcher-backend"}


@app.get("/api/presets", response_model=List[BrandDNA])
async def list_presets():
    analyzer = get_brand_analyzer()
    return analyzer.get_presets()


@app.post("/api/analyze-brand", response_model=BrandDNA)
async def analyze_brand(req: BrandAnalyzeRequest):
    """
    Stage 1: Extract Brand DNA from client website/Facebook page or preset.
    Supports Human-in-the-Loop review & editing prior to Stage 2.
    """
    try:
        analyzer = get_brand_analyzer()
        brand_dna = await analyzer.analyze(req)
        return brand_dna
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze brand: {str(e)}")


@app.post("/api/match-kols", response_model=MatchResponse)
async def match_kols(req: MatchRequest):
    """
    Stage 2: Evaluate & rank Thai TikTok KOLs against confirmed Brand DNA
    using the 3-part Hybrid Scoring Engine (Relevance 45%, Engagement 35%, Multi-Signal Audience 20%).
    """
    try:
        response = await run_full_matching(
            brand_dna=req.brand_dna,
            top_k=req.top_k,
            include_traps=req.include_penalized_traps,
            min_followers=req.min_followers,
            max_followers=req.max_followers,
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"KOL matching failed: {str(e)}")


@app.post("/api/auto-match", response_model=MatchResponse)
async def auto_match(req: AutoMatchRequest):
    """
    1-Click End-to-End matching pipeline combining Stage 1 & Stage 2 in LangGraph.
    """
    try:
        brand_req = BrandAnalyzeRequest(
            brand_name=req.brand_name,
            website_url=req.website_url,
            facebook_url=req.facebook_url,
            preset_id=req.preset_id,
            custom_notes=req.custom_notes,
        )
        response = await run_full_matching(
            brand_request=brand_req,
            top_k=req.top_k,
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Auto matching failed: {str(e)}")


@app.get("/api/kols", response_model=List[KOLProfile])
async def list_kols(
    vertical: Optional[str] = Query(None),
    tier: Optional[str] = Query(None),
):
    repo = get_kol_repository()
    all_kols = repo.get_all()
    if vertical:
        all_kols = [k for k in all_kols if vertical.lower() in k.vertical.lower()]
    if tier:
        all_kols = [k for k in all_kols if tier.lower() in k.tier.lower()]
    return all_kols


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

