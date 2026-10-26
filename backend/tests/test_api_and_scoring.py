import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import BrandAnalyzeRequest, BrandDNA, MatchRequest
from app.services.brand_analyzer import get_brand_analyzer
from app.services.kol_repository import get_kol_repository
from app.services.scoring_engine import get_scoring_engine
from app.workflow.graph import run_full_matching

client = TestClient(app)


def test_root_and_health():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


def test_brand_presets_loaded():
    resp = client.get("/api/presets")
    assert resp.status_code == 200
    presets = resp.json()
    assert len(presets) >= 3
    preset_ids = [p["id"] for p in presets]
    assert "srichand-skincare" in preset_ids
    assert "baantongkee-specialty-cafe" in preset_ids


@pytest.mark.asyncio
async def test_brand_analyzer_preset():
    analyzer = get_brand_analyzer()
    req = BrandAnalyzeRequest(preset_id="srichand-skincare")
    dna = await analyzer.analyze(req)
    assert dna.brand_name.startswith("Srichand")
    assert dna.vertical == "Beauty & Skincare"
    assert "สกินแคร์ผิวแพ้ง่าย" in dna.thai_keywords
    assert dna.average_price_thb > 0


def test_kol_repository_loading():
    repo = get_kol_repository()
    kols = repo.get_all()
    assert len(kols) >= 20
    # Verify each KOL has direct TikTok profile link
    for kol in kols:
        assert kol.tiktok_url.startswith("https://www.tiktok.com/@")
        assert kol.handle in kol.tiktok_url
        assert len(kol.recent_videos) >= 2


def test_anti_spam_yellow_basket_penalty():
    repo = get_kol_repository()
    scoring = get_scoring_engine()
    analyzer = get_brand_analyzer()

    srichand = analyzer.get_presets()[0]
    kols = repo.get_all()

    # Find a spam trap account
    trap_kol = next((k for k in kols if k.is_affiliate_spam_trap), None)
    assert trap_kol is not None, "Seed dataset must include at least one affiliate spam trap"

    total_score, breakdown, why_text, hooks = scoring.evaluate_kol(trap_kol, srichand)
    assert breakdown.affiliate_spam_penalty_applied is True
    assert breakdown.affiliate_spam_penalty_points >= 40.0
    assert "Penalized by Affiliate Spam Filter" in breakdown.affiliate_spam_reason
    assert "[PENALIZED]" in why_text


def test_legit_kol_scoring_and_signals():
    repo = get_kol_repository()
    scoring = get_scoring_engine()
    analyzer = get_brand_analyzer()

    srichand = analyzer.get_presets()[0]
    kols = repo.get_all()

    # Find a legitimate beauty KOL
    fah_kol = next((k for k in kols if k.handle == "fah.skindiary"), None)
    assert fah_kol is not None

    total_score, breakdown, why_text, hooks = scoring.evaluate_kol(fah_kol, srichand)
    assert breakdown.affiliate_spam_penalty_applied is False
    assert total_score >= 70.0
    assert breakdown.relevance_weighted > 0
    assert breakdown.engagement_weighted > 0
    assert breakdown.audience_weighted > 0
    assert breakdown.confidence_level in ["High", "Medium"]
    assert len(breakdown.evidence_list) >= 2
    assert len(hooks) >= 1
    assert "ศรีจันทร์" in hooks[0] or "สกินแคร์" in hooks[0] or "ผิวมัน" in hooks[0] or len(hooks) > 0


@pytest.mark.asyncio
async def test_langgraph_full_workflow():
    analyzer = get_brand_analyzer()
    srichand = analyzer.get_presets()[0]

    response = await run_full_matching(
        brand_dna=srichand,
        top_k=5,
        include_traps=True,
    )

    assert response.brand_dna.brand_name == srichand.brand_name
    assert len(response.ranked_kols) == 5
    # Top rank should be ordered descending
    scores = [item.total_match_score for item in response.ranked_kols]
    assert scores == sorted(scores, reverse=True)
    # Spam traps separated
    assert len(response.penalized_spam_kols) >= 1
    assert len(response.workflow_trace) >= 4


def test_fastapi_analyze_and_match_endpoints():
    # 1. Test Analyze
    analyze_res = client.post("/api/analyze-brand", json={"preset_id": "srichand-skincare"})
    assert analyze_res.status_code == 200
    brand_dna = analyze_res.json()
    assert brand_dna["vertical"] == "Beauty & Skincare"

    # 2. Test Match with Human-Reviewed DNA
    match_res = client.post(
        "/api/match-kols",
        json={
            "brand_dna": brand_dna,
            "top_k": 6,
            "include_penalized_traps": True,
        }
    )
    assert match_res.status_code == 200
    data = match_res.json()
    assert len(data["ranked_kols"]) == 6
    assert "total_candidates_evaluated" in data
    assert len(data["penalized_spam_kols"]) >= 1

    # 3. Test Auto Match (1-Click)
    auto_res = client.post(
        "/api/auto-match",
        json={
            "preset_id": "baantongkee-specialty-cafe",
            "top_k": 4,
        }
    )
    assert auto_res.status_code == 200
    auto_data = auto_res.json()
    assert auto_data["brand_dna"]["vertical"] == "Cafe / F&B & Lifestyle"
    assert len(auto_data["ranked_kols"]) == 4
