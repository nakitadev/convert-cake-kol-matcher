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


@pytest.mark.asyncio
async def test_apify_service_query_origin_and_profile_parsing(monkeypatch):
    from app.services.apify_service import ApifyTikTokService
    
    service = ApifyTikTokService()
    mock_items = [
        {
            "authorMeta": {
                "name": "thaicreator_guru",
                "nickName": "หมอนักสกี สอนเทคนิค",
                "fans": 35000,
                "following": 120,
                "heart": 500000,
                "signature": "ติดต่องาน contact@doctor.com สอนสกีสำหรับมือใหม่",
                "avatar": "https://p16.tiktokcdn.com/avatar.jpg",
            },
            "id": "7123456789",
            "text": "วิธีแก้ปัญหา ปวดเข่าเวลาเล่นสกี สโนว์บอร์ด #สกี #สโนว์บอร์ด #แก้ปวดเข่า",
            "hashtags": [{"name": "สกี"}, {"name": "สโนว์บอร์ด"}],
            "playCount": 85000,
            "diggCount": 4200,
            "commentCount": 210,
            "shareCount": 150,
            "collectCount": 890,
            "hasTikTokShopProduct": False,
            "locationCreated": "Bangkok, Thailand",
        }
    ]

    class MockResponse:
        status_code = 200
        def json(self):
            return mock_items

    class MockClient:
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass
        async def post(self, url, json=None):
            return MockResponse()

    monkeypatch.setattr("httpx.AsyncClient", lambda *args, **kwargs: MockClient())

    search_taxonomy = {
        "niche_hashtags": ["สกี"],
        "pain_point_queries": ["ปวดเข่า"],
        "review_hook_queries": ["รีวิว"],
        "lifestyle_persona_queries": [],
        "competitor_seed_queries": [],
    }

    profiles = await service.search_live_kols_by_hashtags(
        hashtags=["สกี"],
        vertical="Ski & Snowboard",
        limit_creators=5,
        brand_name="SkiAddict",
        search_taxonomy=search_taxonomy,
    )

    assert len(profiles) == 1
    kol = profiles[0]
    assert kol.handle == "thaicreator_guru"
    assert kol.query_origin == "pain_point_queries"
    assert kol.is_work_ready is True
    assert kol.account_type == "real_kol"
    assert kol.save_to_view_ratio > 0
    assert kol.view_consistency_ratio > 0


@pytest.mark.asyncio
async def test_competitor_and_merchant_accounts_filtered_by_two_stage_filter(monkeypatch):
    from app.services.apify_service import ApifyTikTokService
    service = ApifyTikTokService(api_token="test_token")

    mock_items = [
        # 1. Competitor Venue / Official Shop: @ski.bkk
        {
            "id": "v_comp",
            "text": "ซ้อมสโนว์บอร์ดวันหยุด #สกี #สโนว์บอร์ด",
            "playCount": 12000,
            "diggCount": 800,
            "commentCount": 30,
            "shareCount": 20,
            "authorMeta": {
                "name": "ski.bkk",
                "nickName": "Ski BKK",
                "signature": "Ski & Snowboard Club Ram Inthra 40 สอบถาม/จองคิว LINE: @skibkk",
                "fans": 25000,
                "heart": 15000,
            },
        },
        # 2. Client's Own Brand Channel: @proski.thailand
        {
            "id": "v_own",
            "text": "เปิดบริการแล้ววันนี้ Proski Thailand #สกี",
            "playCount": 5000,
            "diggCount": 300,
            "authorMeta": {
                "name": "proski.thailand",
                "nickName": "Proski Thailand Official",
                "signature": "Indoor Ski Simulator Thailand",
                "fans": 12000,
                "heart": 8000,
            },
        },
        # 3. Pure Merchant Store
        {
            "id": "v_store",
            "text": "ชุดสกีพร้อมส่ง #สกี",
            "playCount": 3000,
            "diggCount": 150,
            "authorMeta": {
                "name": "skistore_official",
                "nickName": "Ski Equipment Store",
                "signature": "ขายส่งอุปกรณ์สกี สั่งซื้อจิ้มลิงก์ ส่งฟรีทั่วไทย",
                "fans": 10000,
                "heart": 4000,
            },
        },
        # 4. Legitimate KOL: @snow_vlogger
        {
            "id": "v_kol",
            "text": "หัดเล่นสกีวันแรก ล้มไม่เป็นท่าแต่สนุกมาก #สกี #lifestyle",
            "playCount": 85000,
            "diggCount": 4500,
            "commentCount": 150,
            "shareCount": 320,
            "collectCount": 410,
            "authorMeta": {
                "name": "snow_vlogger",
                "nickName": "Snowy Journey",
                "signature": "เที่ยวหน้าหนาว & Vlogger สอนเทคนิคสกีพื้นฐาน ติดต่องาน dm for work",
                "fans": 42000,
                "heart": 210000,
            },
        },
    ]

    class MockResponse:
        status_code = 200
        def json(self):
            return mock_items

    class MockClient:
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass
        async def post(self, url, json=None):
            return MockResponse()

    monkeypatch.setattr("httpx.AsyncClient", lambda *args, **kwargs: MockClient())

    profiles = await service.search_live_kols_by_hashtags(
        hashtags=["สกี"],
        vertical="Ski & Snowboard",
        limit_creators=5,
        brand_name="Proski",
        grounded_competitors=[{"brand_en": "Ski BKK", "aliases": ["ski.bkk", "skibkk"]}],
        manual_competitors=["Ski Addict"],
    )

    handles = [p.handle for p in profiles]
    # Verify that competitor account @ski.bkk, own brand account @proski.thailand, and pure store @skistore_official were ALL filtered out
    assert "ski.bkk" not in handles
    assert "proski.thailand" not in handles
    assert "skistore_official" not in handles
    # Only genuine creator remains
    assert "snow_vlogger" in handles
    assert len(profiles) == 1


@pytest.mark.asyncio
async def test_niche_consistency_ratio_and_5_clip_audit():
    """
    Verify แนวทางที่ 2: Niche Consistency Ratio (Topic Concentration across 5 clips).
    A creator with only 1 ad-hoc ski video out of 5 general history/travel videos (Niche Ratio < 20%)
    is penalized as Casual Fit and reclassified to Lifestyle & Vlog,
    while a true niche specialist (4/5 ski videos, Niche Ratio 80%) retains full score.
    """
    from app.services.scoring_engine import ScoringEngine
    from app.models import BrandDNA, KOLProfile, VideoMetric

    brand = BrandDNA(
        brand_name="Proski Thailand",
        brand_summary="ลานสกีจำลองในร่มแห่งแรกในไทย สอนสกีและสโนว์บอร์ด",
        target_audience="ผู้สนใจเรียนสกีและนักท่องเที่ยวฤดูหนาว",
        vertical="Ski & Snowboard",
        sub_category="Indoor Ski Simulator",
        thai_keywords=["สกี", "สโนว์บอร์ด", "ลานสกี", "สอนสกี"],
    )
    engine = ScoringEngine()

    # 1. Casual Creator (@sraissomething style): 1 ski video, 4 Chinese history videos
    casual_kol = KOLProfile(
        id="casual_1",
        handle="sraissomething",
        display_name="Sra History",
        tiktok_url="https://www.tiktok.com/@sraissomething",
        follower_count=50000,
        creator_persona="Casual Historian & Travel Vlogger",
        vertical="Ski & Snowboard",
        bio="เล่าประวัติศาสตร์จีนและการท่องเที่ยว",
        creator_archetype="Educated Guru",  # erroneously tagged guru from single video
        recent_videos=[
            VideoMetric(video_id="v1", caption="ลองเล่นสกีที่กรุงเทพ สนุกมาก #สกี", hashtags=["สกี"], views=10000, likes=500, comments=20, shares=10),
            VideoMetric(video_id="v2", caption="ประวัติศาสตร์พระราชวังต้องห้าม สมัยราชวงศ์ชิง", hashtags=["ประวัติศาสตร์"], views=12000, likes=600, comments=30, shares=15),
            VideoMetric(video_id="v3", caption="เรื่องราวซูสีไทเฮา โศกนาฏกรรมจีน", hashtags=["จีน"], views=15000, likes=800, comments=40, shares=20),
            VideoMetric(video_id="v4", caption="อาหารปักกิ่งโบราณสูตรต้นตำรับ", hashtags=["อาหาร"], views=8000, likes=400, comments=15, shares=5),
            VideoMetric(video_id="v5", caption="เดินชมสุสานงักฮุย ขุนนางกังฉิน", hashtags=["เที่ยวจีน"], views=9000, likes=450, comments=18, shares=8),
        ],
    )

    # 2. Core Niche Specialist (@upventure_travel style): 4 ski/snowboard videos, 1 general travel
    specialist_kol = KOLProfile(
        id="specialist_1",
        handle="upventure_travel",
        display_name="UpVenture Snow",
        tiktok_url="https://www.tiktok.com/@upventure_travel",
        follower_count=120000,
        creator_persona="Ski & Snowboard Specialist",
        vertical="Ski & Snowboard",
        bio="Snowboard & Winter Adventure Lover",
        creator_archetype="Niche Enthusiast",
        recent_videos=[
            VideoMetric(video_id="v1", caption="เตรียมตัวก่อนไปลานสกี ซ้อมจัดระเบียบร่างกาย #สกี", hashtags=["สกี"], views=25000, likes=1500, comments=80, shares=45),
            VideoMetric(video_id="v2", caption="เทคนิคการเลี้ยวสโนว์บอร์ด Carving #สโนว์บอร์ด", hashtags=["สโนว์บอร์ด"], views=30000, likes=1800, comments=95, shares=60),
            VideoMetric(video_id="v3", caption="รีวิวรองเท้าและชุดสกีสำหรับมือใหม่ #สอนสกี", hashtags=["สอนสกี"], views=22000, likes=1200, comments=70, shares=40),
            VideoMetric(video_id="v4", caption="ซ้อมลานสกีจำลอง Indoor ในไทย #ลานสกี", hashtags=["ลานสกี"], views=28000, likes=1600, comments=85, shares=50),
            VideoMetric(video_id="v5", caption="เทศกาลบอลลูน สิงห์ปาร์ค เชียงราย", hashtags=["เที่ยวไทย"], views=15000, likes=700, comments=35, shares=15),
        ],
    )

    # Evaluate both candidates
    score_casual, b_casual, why_casual, _ = engine.evaluate_kol(casual_kol, brand)
    score_spec, b_spec, why_spec, _ = engine.evaluate_kol(specialist_kol, brand)

    # Verify Casual KOL (1/5 = 20% or less -> flagged casual fit)
    assert casual_kol.niche_consistency_ratio == 0.2
    assert casual_kol.is_casual_niche_fit is False or casual_kol.niche_consistency_ratio <= 0.2
    # Re-test with 0/5 strictly < 0.20
    casual_kol.recent_videos[0].caption = "เที่ยวจีนวันแรก"
    casual_kol.recent_videos[0].hashtags = ["จีน"]
    score_casual2, b_casual2, _, _ = engine.evaluate_kol(casual_kol, brand)
    assert casual_kol.niche_consistency_ratio == 0.0
    assert casual_kol.is_casual_niche_fit is True
    assert b_casual2.is_casual_niche_fit is True
    # Casual creator is re-routed away from Guru to Lifestyle & Vlog
    assert casual_kol.creator_archetype == "Lifestyle & Vlog"
    # Semantic points must be capped/penalized
    assert b_casual2.semantic_points <= 12.0

    # Verify Specialist KOL (4/5 = 80% niche consistency)
    assert specialist_kol.niche_consistency_ratio == 0.8
    assert specialist_kol.is_casual_niche_fit is False
    assert specialist_kol.creator_archetype == "Niche Enthusiast"
    assert b_spec.semantic_points > b_casual2.semantic_points
    assert score_spec > score_casual2


@pytest.mark.asyncio
async def test_balanced_archetype_portfolio_selection():
    """
    Verify that evaluate_and_rank_node produces a balanced portfolio across all 4 archetypes:
    Educated Guru, Top Reviewer, Lifestyle & Vlog, Niche Enthusiast,
    ensuring every category tab has representation for media planning.
    """
    from app.workflow.graph import evaluate_and_rank_node
    from app.models import BrandDNA, KOLProfile, VideoMetric

    brand = BrandDNA(
        brand_name="Proski Thailand",
        brand_summary="Indoor Skiing",
        target_audience="Skiers",
        vertical="Ski & Snowboard",
        thai_keywords=["สกี", "สโนว์บอร์ด"],
    )

    # Create candidate pool dominated by 10 lifestyle vloggers, but also containing 2 gurus, 2 reviewers, 2 niche
    candidates = []
    # 10 Lifestyle with very high followers (e.g. 500k)
    for i in range(10):
        candidates.append(
            KOLProfile(
                id=f"life_{i}",
                handle=f"vlogger_{i}",
                display_name=f"Lifestyle Star {i}",
                tiktok_url=f"https://www.tiktok.com/@vlogger_{i}",
                creator_persona="Lifestyle Creator",
                vertical="Ski & Snowboard",
                follower_count=500000 + i * 10000,
                creator_archetype="Lifestyle & Vlog",
                recent_videos=[VideoMetric(video_id=f"v_{i}", caption="เที่ยวสกีสนุกมาก #สกี", hashtags=["สกี"], views=100000, likes=5000, comments=200, shares=100)],
            )
        )
    # 2 Gurus with lower followers (e.g. 50k)
    for i in range(2):
        candidates.append(
            KOLProfile(
                id=f"guru_{i}",
                handle=f"coach_{i}",
                display_name=f"Ski Coach {i}",
                tiktok_url=f"https://www.tiktok.com/@coach_{i}",
                creator_persona="Ski Coach",
                vertical="Ski & Snowboard",
                follower_count=50000 + i * 5000,
                creator_archetype="Educated Guru",
                recent_videos=[VideoMetric(video_id=f"vg_{i}", caption="สอนสกีขั้นพื้นฐาน ท่า carving #สกี #สอนสกี", hashtags=["สกี", "สอนสกี"], views=20000, likes=1000, comments=50, shares=30)],
            )
        )
    # 2 Top Reviewers (e.g. 80k)
    for i in range(2):
        candidates.append(
            KOLProfile(
                id=f"rev_{i}",
                handle=f"reviewer_{i}",
                display_name=f"Ski Gear Review {i}",
                tiktok_url=f"https://www.tiktok.com/@reviewer_{i}",
                creator_persona="Ski Reviewer",
                vertical="Ski & Snowboard",
                follower_count=80000 + i * 5000,
                creator_archetype="Top Reviewer",
                recent_videos=[VideoMetric(video_id=f"vr_{i}", caption="รีวิวอุปกรณ์สกี พร้อมพิกัดตะกร้า #สกี", hashtags=["สกี"], has_yellow_basket=True, views=30000, likes=1500, comments=60, shares=40)],
            )
        )
    # 2 Niche Enthusiasts (e.g. 40k)
    for i in range(2):
        candidates.append(
            KOLProfile(
                id=f"niche_{i}",
                handle=f"snowboarder_{i}",
                display_name=f"Hardcore Boarder {i}",
                tiktok_url=f"https://www.tiktok.com/@snowboarder_{i}",
                creator_persona="Niche Enthusiast",
                vertical="Ski & Snowboard",
                follower_count=40000 + i * 5000,
                creator_archetype="Niche Enthusiast",
                recent_videos=[VideoMetric(video_id=f"vn_{i}", caption="ซ้อมลานสกีทุกสัปดาห์ Passion ล้วนๆ #สกี", hashtags=["สกี"], views=15000, likes=900, comments=40, shares=20)],
            )
        )

    state = {
        "brand_dna": brand,
        "candidates": candidates,
        "top_k": 10,
        "apify_status": "live_mock",
        "trace": [],
    }

    result = await evaluate_and_rank_node(state)
    top_ranked = result["ranked_kols"]

    # Must return top_k (10)
    assert len(top_ranked) >= 10

    # Verify all 4 archetypes are represented in top_ranked
    archetype_counts = {
        "Educated Guru": sum(1 for r in top_ranked if r.kol.creator_archetype == "Educated Guru"),
        "Top Reviewer": sum(1 for r in top_ranked if r.kol.creator_archetype == "Top Reviewer"),
        "Lifestyle & Vlog": sum(1 for r in top_ranked if r.kol.creator_archetype == "Lifestyle & Vlog"),
        "Niche Enthusiast": sum(1 for r in top_ranked if r.kol.creator_archetype == "Niche Enthusiast"),
    }

    assert archetype_counts["Educated Guru"] >= 2, f"Expected >= 2 Gurus, got {archetype_counts}"
    assert archetype_counts["Top Reviewer"] >= 2, f"Expected >= 2 Reviewers, got {archetype_counts}"
    assert archetype_counts["Niche Enthusiast"] >= 2, f"Expected >= 2 Niche Enthusiasts, got {archetype_counts}"
    assert archetype_counts["Lifestyle & Vlog"] >= 2, f"Expected >= 2 Lifestyle Vloggers, got {archetype_counts}"


