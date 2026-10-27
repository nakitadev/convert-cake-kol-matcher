import asyncio
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


def test_100_percent_yellow_basket_allowed_for_review_creator():
    scoring = get_scoring_engine()
    brand = BrandDNA(
        id="b1",
        brand_name="MizuMi",
        vertical="Beauty & Skincare",
        sub_category="Sunscreen & Acne Care",
        brand_summary="Thai dermocosmetics sunscreen",
        target_audience="Acne skin users in Thailand",
        average_price_thb=690,
        thai_keywords=["กันแดด", "สิว"],
    )
    review_kol = KOLProfile(
        id="live_review_star",
        handle="review.expert",
        display_name="Review Expert Thailand",
        tiktok_url="https://www.tiktok.com/@review.expert",
        vertical="Beauty & Skincare",
        bio="รีวิวสกินแคร์ใช้จริง ป้ายยาของดีในต๊อกๆ",
        follower_count=85000,
        tier="Micro (50K-250K)",
        creator_persona="Skincare Reviewer",
        creator_category="Content Creator (เน้นรีวิว)",
        sample_comments=["ใช้ตามแล้วดีจริง", "พิกัดตะกร้าอยู่ตรงไหนคะ"],
        recent_videos=[
            VideoMetric(
                video_id=f"v_{i}",
                caption=f"รีวิวกันแดดสำหรับคนเป็นสิว คลิปที่ {i}",
                hashtags=["รีวิวบิวตี้", "ของดีบอกต่อ"],
                views=25000,
                likes=1200,
                comments=45,
                shares=15,
                has_yellow_basket=True,  # 100% yellow basket across all videos!
            )
            for i in range(5)
        ],
        is_affiliate_spam_trap=False,
    )

    score, breakdown, why, hooks = scoring.evaluate_kol(review_kol, brand)
    # Spec: 100% yellow basket must NOT be penalized and should be categorized as review creator
    assert breakdown.yellow_basket_ratio == 1.0
    assert breakdown.affiliate_spam_penalty_applied is False
    assert "[PENALIZED]" not in why
    assert "Content Creator (เน้นรีวิว)" in why
    assert "ตะกร้าเหลือง 100%" in why
    assert any("ตะกร้าเหลือง" in h for h in hooks)


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


@pytest.mark.asyncio
async def test_zero_hardcode_discovery_policy():
    from app.workflow.graph import discover_candidates_node
    import pytest

    # Zero-Hardcode: missing brand_dna or vertical must fail with ValueError, NOT fall back to 'Beauty & Skincare'
    with pytest.raises(ValueError, match="BrandDNA vertical is required"):
        await discover_candidates_node({"brand_dna": None})

    bad_dna = BrandDNA(
        id="test",
        brand_name="Test",
        vertical="",
        brand_summary="test",
        target_audience="test",
        thai_keywords=[],
    )
    with pytest.raises(ValueError, match="BrandDNA vertical is required"):
        await discover_candidates_node({"brand_dna": bad_dna})


@pytest.mark.asyncio
async def test_creator_archetype_instruction_classification():
    """
    Tests that creator classification uses LLM instruction differentiating
    Educated Guru (knowledge-sharing/techniques) from Lifestyle & Vlog (travel/daily life)
    and Top Reviewer (unboxing/comparison/buying advice) without hardcoded keywords.
    """
    gemini = get_gemini_service()
    if not gemini.is_configured:
        pytest.skip("GEMINI_API_KEY not configured")

    creators = [
        {
            "id": "guru_1",
            "handle": "ski_instructor_th",
            "display_name": "ครูอาร์ท สอนสกี",
            "bio": "สอนสกีและสโนว์บอร์ดระดับมืออาชีพ อธิบายหลักการเบรกและการควบคุมบอร์ด",
            "captions": ["3 ท่าฝึกซ้อมปรับสรีระร่างกายก่อนขึ้นลานหิมะจริง", "เทคนิคการถ่ายน้ำหนักขอบสกีเพื่อการเลี้ยวที่ปลอดภัย"],
            "yellow_basket_ratio": 0.0,
            "vertical": "Sports & Outdoors",
        },
        {
            "id": "travel_1",
            "handle": "japan_trip_vlogger",
            "display_name": "แพรว พาหลงทาง",
            "bio": "Vlogger ท่องเที่ยวญี่ปุ่น กิน เที่ยว พักผ่อน ชิลๆ กับธรรมชาติสวยๆ",
            "captions": ["ไปเที่ยวลานสกีญี่ปุ่นวิวหิมะสวยตาแตกมากทุกคน แวะกินไอติมต่อ", "เช่าชุดเที่ยวเมืองหิมะ ถ่ายรูปมุมไหนก็ปัง #เที่ยวญี่ปุ่น"],
            "yellow_basket_ratio": 0.0,
            "vertical": "Travel & Lifestyle",
        },
        {
            "id": "reviewer_1",
            "handle": "honest_review_th",
            "display_name": "รีวิวตามจริง",
            "bio": "ซื้อเองรีวิวเอง ชี้เป้าของน่าใช้ พิกัดตะกร้าเหลือง",
            "captions": ["เทียบแว่นกันแดด 3 รุ่น คุ้มไหมที่จะซื้อ มีพิกัดในตะกร้า", "เปิดกล่องลองของใหม่ ซื้อจากต๊อกต๊อกช็อป"],
            "yellow_basket_ratio": 0.8,
            "vertical": "Product Review",
        },
    ]
    res = await gemini.classify_creator_archetypes(creators)
    assert "guru_1" in res
    assert res["guru_1"]["creator_archetype"] == "Educated Guru"
    assert res["guru_1"]["recommended_role"] == "Trust & Credibility"

    assert "travel_1" in res
    assert res["travel_1"]["creator_archetype"] == "Lifestyle & Vlog"
    assert res["travel_1"]["recommended_role"] == "Brand Awareness & Discovery"

    assert "reviewer_1" in res
    assert res["reviewer_1"]["creator_archetype"] == "Top Reviewer"
    assert res["reviewer_1"]["recommended_role"] == "Conversion & Sales"


def test_full_spec_40_35_25_and_archetypes():
    scoring = get_scoring_engine()
    brand = BrandDNA(
        id="live-skincare",
        brand_name="MizuMi Skincare",
        vertical="Beauty & Skincare",
        sub_category="Sunscreen & Acne",
        brand_summary="Thai derm skincare for sensitive skin",
        target_audience="Acne prone teens and working adults",
        thai_keywords=["กันแดด", "สิว", "รีวิว"],
        grounded_competitors=[{"brand_en": "Biore", "aliases": ["บิโอเร", "บีโอเร"]}],
        manual_competitors=["Canmake"],
    )

    # 1. Educated Guru profile
    guru_kol = KOLProfile(
        id="guru_derm",
        handle="dr_skin_guru",
        display_name="Dr. Skin Guru",
        tiktok_url="https://www.tiktok.com/@dr_skin_guru",
        vertical="Beauty & Skincare",
        bio="เภสัชกรสอนเลือกสารกันแดด ติดต่องาน: work@gmail.com",
        follower_count=120000,
        tier="Mid-Tier (100K-500K)",
        creator_persona="Educated Guru",
        creator_archetype="Educated Guru",
        recommended_role="Trust & Credibility",
        is_work_ready=True,
        save_to_view_ratio=0.045,
        view_consistency_ratio=0.85,
        sample_comments=["สารตัวนี้ดีมาก", "พิกัดซื้อที่ไหนคะ", "ผิวแพ้ง่ายใช้ได้ไหม"],
        recent_videos=[
            VideoMetric(
                video_id="v1",
                caption="วิธีเลือกกันแดดสำหรับคนเป็นสิว ผิวแพ้ง่าย #สาระ",
                views=80000,
                likes=6000,
                comments=240,
                shares=500,
                collect_count=900,
                has_yellow_basket=False,
            )
        ],
    )

    score, breakdown, why, hooks = scoring.evaluate_kol(guru_kol, brand)
    # Check 40/35/25 breakdown constraints
    assert breakdown.relevance_weighted <= 40.0
    assert breakdown.engagement_weighted <= 35.0
    assert breakdown.audience_weighted <= 25.0
    assert score == round(breakdown.relevance_weighted + breakdown.engagement_weighted + breakdown.audience_weighted, 1)
    assert breakdown.save_to_view_points >= 8.0
    assert "[Archetype: Educated Guru (Trust & Credibility)]" in why
    assert "Open for Sponsor" in why
    assert len(hooks) == 3

    # 2. Competitor Conflict Check
    comp_kol = KOLProfile(
        id="comp_kol",
        handle="comp_reviewer",
        display_name="Beauty Fan",
        tiktok_url="https://www.tiktok.com/@comp_reviewer",
        vertical="Beauty & Skincare",
        bio="รีวิวเครื่องสำอาง",
        follower_count=20000,
        tier="Micro (10K-100K)",
        creator_persona="Top Reviewer",
        creator_archetype="Top Reviewer",
        competitor_warning="⚠️ Competitor Conflict: Content features competitor 'Biore'",
        sample_comments=["ใช้ตาม"],
        recent_videos=[
            VideoMetric(
                video_id="v2",
                caption="เปรียบเทียบกันแดด biore กับแบรนด์อื่น",
                views=10000,
                likes=500,
                comments=20,
                shares=10,
                has_yellow_basket=True,
            )
        ],
    )
    c_score, c_breakdown, c_why, _ = scoring.evaluate_kol(comp_kol, brand)
    assert "⚠️ Competitor Conflict" in c_why


@pytest.mark.asyncio
async def test_batch_embeddings_and_evaluate_kols_batch():
    """
    Verify async batch embeddings and evaluation for candidate KOLs.
    Tests evaluate_kols_batch and get_embeddings_batch with concurrent execution.
    """
    scoring = get_scoring_engine()
    brand = BrandDNA(
        id="test-batch-brand",
        brand_name="SkinLab",
        website_url="https://skinlab.co.th",
        facebook_url="",
        vertical="Beauty & Skincare",
        sub_category="Facial Serum",
        brand_summary="เซรั่มบำรุงผิวหน้า",
        target_audience="ผู้หญิง 20-35 ปี",
        target_age_range="20-35",
        target_locations=["Bangkok"],
        brand_tone=["Professional"],
        content_style_preferences=["Review"],
        price_positioning="Mid-Range / Accessible",
        average_price_thb=690,
        thai_keywords=["เซรั่ม", "หน้าใส", "ผิวชุ่มชื้น"],
        scraped_sources=["Web"],
        manual_competitors=[],
        search_taxonomy={},
        grounded_competitors=[],
    )

    kols = [
        KOLProfile(
            id=f"batch_kol_{i}",
            handle=f"creator_{i}",
            display_name=f"Creator {i}",
            tiktok_url=f"https://www.tiktok.com/@creator_{i}",
            vertical="Beauty & Skincare",
            bio="รีวิวสกินแคร์และเซรั่มหน้าใส",
            follower_count=50000 + i * 1000,
            tier="Micro (10K-100K)",
            creator_persona="Educated Guru",
            creator_archetype="Educated Guru",
            is_work_ready=True,
            sample_comments=["เซรั่มดีมาก"],
            recent_videos=[
                VideoMetric(
                    video_id=f"v_{i}",
                    caption="รีวิวเซรั่มกู้หน้าใส ผิวชุ่มชื้น",
                    views=20000,
                    likes=1200,
                    comments=50,
                    shares=30,
                    collect_count=80,
                    has_yellow_basket=False,
                )
            ],
        )
        for i in range(5)
    ]

    results = await scoring.evaluate_kols_batch(kols, brand)
    assert len(results) == 5
    for score, breakdown, why, hooks in results:
        assert 0.0 <= score <= 100.0
        assert breakdown.relevance_weighted > 0
        assert breakdown.engagement_weighted > 0
        assert breakdown.audience_weighted > 0
        assert len(why) > 0


@pytest.mark.asyncio
async def test_parallel_brand_scrape_concurrent(monkeypatch):
    """
    Verify that BrandAnalyzer concurrently scrapes website and Facebook page in parallel via asyncio.gather.
    """
    from app.services.brand_analyzer import BrandAnalyzer
    from app.services.apify_service import ApifyTikTokService
    import time

    analyzer = BrandAnalyzer()

    async def mock_scrape_website(url: str):
        await asyncio.sleep(0.1)
        return ("Website content for brand test", "Brand Website Title")

    async def mock_scrape_fb(url: str):
        await asyncio.sleep(0.1)
        return {
            "title": "Brand FB Title",
            "bio": "Brand FB Bio",
            "categories": ["Skincare"],
            "likes": 5000,
            "followers": 10000,
            "posts": ["Post 1", "Post 2"],
        }

    monkeypatch.setattr(analyzer, "_scrape_website", mock_scrape_website)
    monkeypatch.setattr(ApifyTikTokService, "is_configured", property(lambda self: True))
    monkeypatch.setattr(ApifyTikTokService, "scrape_facebook_page", lambda self, url: mock_scrape_fb(url))

    # Mock Gemini brand DNA generation
    from app.services.gemini_service import GeminiService
    async def mock_generate_dna(*args, **kwargs):
        return {
            "brand_name": "TestParallelBrand",
            "vertical": "Beauty & Skincare",
            "sub_category": "Serum",
            "thai_keywords": ["เซรั่ม", "ผิวใส"],
            "target_audience": "All",
            "price_positioning": "Budget / Mass",
            "average_price_thb": 490,
        }
    monkeypatch.setattr(GeminiService, "is_configured", property(lambda self: True))
    monkeypatch.setattr(GeminiService, "generate_brand_dna", mock_generate_dna)

    req = BrandAnalyzeRequest(
        brand_name="TestParallelBrand",
        website_url="https://testbrand.com",
        facebook_url="https://facebook.com/testbrand",
    )

    t0 = time.time()
    dna = await analyzer.analyze(req)
    duration = time.time() - t0

    # If run sequentially, 0.1s + 0.1s = ~0.2s+. In parallel, ~0.10 - 0.15s.
    assert dna.brand_name == "TestParallelBrand"
    assert "Live Website via Jina Reader" in dna.scraped_sources[0]
    assert any("Live Facebook" in s for s in dna.scraped_sources)
    assert duration < 0.28


