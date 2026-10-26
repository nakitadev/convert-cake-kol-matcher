import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import (
    BrandAnalyzeRequest,
    BrandDNA,
    KOLProfile,
    VideoMetric,
    MatchRequest,
)
from app.services.brand_analyzer import get_brand_analyzer
from app.services.scoring_engine import get_scoring_engine
from app.services.gemini_service import get_gemini_service

client = TestClient(app)


def test_root_and_health():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"

    root_resp = client.get("/")
    assert root_resp.status_code == 200
    assert "Convert Cake" in root_resp.json()["name"]


@pytest.mark.asyncio
async def test_brand_analyzer_pure_live():
    analyzer = get_brand_analyzer()
    req = BrandAnalyzeRequest(
        brand_name="Her Hyness Clean Skincare",
        custom_notes="Clean dermatological skincare for sensitive skin in Bangkok, budget 400-800 THB",
    )
    dna = await analyzer.analyze(req)
    assert "Her Hyness" in dna.brand_name
    assert len(dna.thai_keywords) >= 1
    assert dna.average_price_thb > 0
    assert dna.id.startswith("live-")


def test_scoring_engine_legit_creator():
    scoring = get_scoring_engine()
    brand = BrandDNA(
        id="live-testbrand",
        brand_name="Her Hyness",
        vertical="Beauty & Skincare",
        sub_category="Clean Skincare",
        brand_summary="Clean skincare for acne-prone skin",
        target_audience="Young Thai beauty shoppers",
        target_locations=["Bangkok", "Thailand"],
        brand_tone=["Trustworthy", "Modern"],
        content_style_preferences=["Review", "Vlog"],
        price_positioning="Mid-Range / Accessible",
        average_price_thb=690,
        thai_keywords=["รีวิวบิวตี้", "สกินแคร์", "ผิวแพ้ง่าย"],
    )

    kol = KOLProfile(
        id="live_fah_beauty",
        handle="fah_beauty",
        display_name="Fah Skincare",
        tiktok_url="https://www.tiktok.com/@fah_beauty",
        vertical="Beauty & Skincare",
        secondary_verticals=["Lifestyle"],
        bio="รีวิวสกินแคร์ผิวแพ้ง่าย ใช้จริงทุกตัว",
        follower_count=85000,
        total_likes=900000,
        tier="Micro (10K-100K)",
        creator_persona="Authentic Skincare Reviewer",
        content_styles=["Review", "Vlog"],
        typical_price_tier="Mid-Range / Accessible",
        avg_reviewed_price_thb=550,
        primary_locations=["Bangkok", "Thailand"],
        sample_comments=["ใช้ตามแล้วดีมาก", "ขอพิกัดหน่อยค่ะ", "ราคาเท่าไหร่คะ"],
        recent_videos=[
            VideoMetric(
                video_id="v1",
                caption="รีวิวสกินแคร์กู้ผิวโทรมใน 7 วัน",
                hashtags=["รีวิวบิวตี้", "สกินแคร์"],
                views=45000,
                likes=3200,
                comments=150,
                shares=80,
                has_yellow_basket=False,
                location_tag="Bangkok, Thailand",
            )
        ],
        is_affiliate_spam_trap=False,
    )

    score, breakdown, why, hooks = scoring.evaluate_kol(kol, brand)
    assert score >= 60.0
    assert breakdown.affiliate_spam_penalty_applied is False
    assert breakdown.confidence_level in ["High", "Medium"]
    assert len(hooks) == 3
    assert "Her Hyness" in hooks[0]
    assert "[PENALIZED]" not in why


def test_anti_spam_yellow_basket_penalty():
    scoring = get_scoring_engine()
    brand = BrandDNA(
        id="live-testbrand",
        brand_name="Test Brand",
        vertical="Beauty & Skincare",
        brand_summary="Testing anti spam",
        target_audience="Thai consumers",
        thai_keywords=["รีวิว"],
    )

    # Spam account: 100% yellow basket, low retention
    spam_kol = KOLProfile(
        id="live_spam_farm",
        handle="cheap_shop_repost",
        display_name="Affiliate Repost Farm",
        tiktok_url="https://www.tiktok.com/@cheap_shop_repost",
        vertical="Beauty & Skincare",
        bio="คลิกลิงก์ตะกร้าเหลืองเลย",
        follower_count=50000,
        tier="Micro (10K-100K)",
        creator_persona="Affiliate Bot",
        sample_comments=[],
        recent_videos=[
            VideoMetric(
                video_id="v1",
                caption="กดตะกร้าเหลืองด่วน",
                hashtags=["ของดีบอกต่อ"],
                views=1000,
                likes=10,
                comments=0,
                shares=0,
                has_yellow_basket=True,
            )
        ],
        is_affiliate_spam_trap=True,
    )

    score, breakdown, why, hooks = scoring.evaluate_kol(spam_kol, brand)
    assert breakdown.affiliate_spam_penalty_applied is True
    assert breakdown.affiliate_spam_penalty_points == 55.0
    assert "[PENALIZED]" in why
    assert hooks == ["(N/A — Account flagged as affiliate spam)"]


def test_gemini_service_cosine_math():
    gemini = get_gemini_service()
    v1 = [1.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    v3 = [0.0, 1.0, 0.0]
    assert gemini.cosine_similarity(v1, v2) == 1.0
    assert gemini.cosine_similarity(v1, v3) == 0.5


def test_fastapi_analyze_endpoint():
    res = client.post(
        "/api/analyze-brand",
        json={
            "brand_name": "After You",
            "custom_notes": "Bangkok dessert cafe Kakigori Shibuya toast",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert "After You" in data["brand_name"]
    assert "thai_keywords" in data
