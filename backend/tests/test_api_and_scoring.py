"""
Convert Cake TikTok KOL/KOC Discovery & Matching Engine — Test Suite.

Verifies the 4-stage pipeline against system_specification_tiktok_kol_matching_engine.md:
  1. Stage 1: Brand DNA & 4 Conversion Models + Scene Translation (2-3 words, <= 18 letters, 60/40 funnel)
  2. Stage 2: TikTok Discovery (Country: TH, KOL_QUERY vs KOC_QUERY origin tagging) & Competitor Layer 2
  3. Stage 3: Two-Stage Filtering (Gate 1: Merchant & Smart Bot Filter; Gate 2: Batch LLM Relevance Gate; 2x2 Matrix & Guard)
  4. Stage 4: Dynamic Scoring (40/35/25), Balanced Top-K Media Mix Portfolio & Role-Adaptive 3-Sec Hooks
  5. FastAPI Endpoints & Healthcheck
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import (
    BrandAnalyzeRequest,
    BrandDNA,
    Competitor,
    CreatorSignals,
    KOLProfile,
    KolKocMix,
    SearchQuery,
    VideoMetric,
    CONVERSION_MODEL_MIX,
)
from app.services.brand_analyzer import get_brand_analyzer
from app.services.scoring_engine import get_scoring_engine
from app.services.gemini_service import get_gemini_service
from app.services import query_translation as qt
from app.services.creator_filter import (
    group_items_by_creator,
    build_profile,
    brand_account_reason,
    merchant_reason,
    affiliate_bot_reason,
    guard_sub_style,
    competitor_flags,
    frequent_terms,
)

client = TestClient(app)


# ---------------------------------------------------------------------------
# 1. API Health & Root
# ---------------------------------------------------------------------------
def test_root_and_health():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"

    root_resp = client.get("/")
    assert root_resp.status_code == 200
    assert "Convert Cake" in root_resp.json()["name"]


# ---------------------------------------------------------------------------
# 2. Stage 1: Brand DNA & Conversion Models
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_brand_analyzer_live_extraction():
    analyzer = get_brand_analyzer()
    req = BrandAnalyzeRequest(
        brand_name="Her Hyness Clean Skincare",
        custom_notes="Clean dermatological skincare for sensitive skin in Bangkok, average price 790 THB, sold on TikTok Shop",
    )
    dna = await analyzer.analyze(req)
    assert "Her Hyness" in dna.brand_name
    assert dna.conversion_model in CONVERSION_MODEL_MIX
    assert dna.kol_koc_mix.kol + dna.kol_koc_mix.koc == 100
    assert len(dna.search_queries) >= 4
    # Check that both KOL_QUERY and KOC_QUERY exist
    assert any(q.side == "KOL_QUERY" for q in dna.search_queries)
    assert any(q.side == "KOC_QUERY" for q in dna.search_queries)
    assert len(dna.competitors) >= 1
    assert dna.id.startswith("live-")


def test_conversion_model_mix_values():
    assert CONVERSION_MODEL_MIX["ECOMMERCE_PRODUCT"] == {"kol": 30, "koc": 70}
    assert CONVERSION_MODEL_MIX["APP_DIGITAL_SERVICE"] == {"kol": 60, "koc": 40}
    assert CONVERSION_MODEL_MIX["HIGH_TICKET_LEADGEN"] == {"kol": 70, "koc": 30}
    assert CONVERSION_MODEL_MIX["LIFESTYLE_EXPERIENCE"] == {"kol": 60, "koc": 40}


# ---------------------------------------------------------------------------
# 3. Stage 2: Scene Translation Syntax Guardrails (Spec 3.2)
# ---------------------------------------------------------------------------
def test_scene_translation_syntax_rules():
    # Rule 1: Short & Native (<= 18 Thai letters, 2-3 words)
    valid_q1 = "วิธีลดสิวผด"
    ok, reason = qt.validate_query(valid_q1)
    assert ok is True

    valid_q2 = "รีวิว ครีมแต้มสิว"
    ok, _ = qt.validate_query(valid_q2)
    assert ok is True

    # Too many words (> 3 words)
    too_long_words = "วิธี ใช้ ครีม แต้ม สิว ตัวดัง"
    ok, reason = qt.validate_query(too_long_words)
    assert ok is False
    assert "words" in reason

    # Rule 3: Anti-Merchant Guardrail (ห้ามมี ราคาส่ง, ขายถูก, โปรโมชั่น, ตัวแทนจำหน่าย)
    merchant_q = "สกินแคร์ ราคาส่ง"
    ok, reason = qt.validate_query(merchant_q)
    assert ok is False
    assert "anti-merchant" in reason


def test_scene_translation_60_40_funnel():
    queries = [
        SearchQuery(query="สกินแคร์ลดสิว", side="KOL_QUERY", specificity="direct"),
        SearchQuery(query="ส่วนผสมเซรั่ม", side="KOL_QUERY", specificity="direct"),
        SearchQuery(query="เทียบสเปกครีม", side="KOL_QUERY", specificity="direct"),
        SearchQuery(query="รูทีนคนนอนดึก", side="KOL_QUERY", specificity="adjacent"),
        SearchQuery(query="แต่งหน้าไปเรียน", side="KOL_QUERY", specificity="adjacent"),
    ]
    picked = qt.select_funnel(queries, side="KOL_QUERY", per_side=5)
    assert len(picked) == 5
    direct_count = sum(1 for q in picked if q.specificity == "direct")
    adjacent_count = sum(1 for q in picked if q.specificity == "adjacent")
    assert direct_count == 3  # 60%
    assert adjacent_count == 2  # 40%


# ---------------------------------------------------------------------------
# 4. Stage 3: Two-Stage Filtering (Gate 1 & Gate 2) (Spec 4.1)
# ---------------------------------------------------------------------------
def test_gate1_merchant_exclusion():
    # 1. Commercial factory account with no work-ready signal -> must be excluded
    factory_kol = KOLProfile(
        id="factory_1",
        handle="screen_factory_th",
        display_name="โรงงานสกรีนเสื้อ ด่วน",
        tiktok_url="https://www.tiktok.com/@screen_factory_th",
        bio="รับสกรีนเสื้อยืด ไม่มีขั้นต่ำ ราคาส่ง สั่งผลิตจิ้มลิงก์",
        follower_count=20000,
        total_likes=10000,
        tier="Micro",
        query_origin="KOC_QUERY",
        is_work_ready=False,
    )
    reason = merchant_reason(factory_kol)
    assert reason is not None
    assert "Factory" in reason or "Merchant" in reason


def test_gate1_smart_affiliate_bot_filter():
    # 2. Smart bot: basket > 85% AND is_work_ready == False AND median comments <= 1
    bot_kol = KOLProfile(
        id="bot_1",
        handle="cheap_repost_bot",
        display_name="พิกัดของใช้ถูก",
        tiktok_url="https://www.tiktok.com/@cheap_repost_bot",
        bio="จิ้มตะกร้าเหลืองเลยจ้า",
        follower_count=45000,
        total_likes=1200,
        tier="Micro",
        query_origin="KOC_QUERY",
        is_work_ready=False,
        signals=CreatorSignals(
            basket_ratio=0.95,
            median_comments=0.0,
            median_views=250.0,
        ),
    )
    bot_reason = affiliate_bot_reason(bot_kol)
    assert bot_reason is not None
    assert "Affiliate Spam Bot" in bot_reason


def test_gate1_top_review_creator_not_excluded():
    # KOC Hard-Sell Reviewer with 100% basket but high engagement & work-ready bio -> MUST PASS Gate 1
    top_reviewer = KOLProfile(
        id="koc_review_star",
        handle="review_with_ploy",
        display_name="Ploy ป้ายยาพาช้อป",
        tiktok_url="https://www.tiktok.com/@review_with_ploy",
        bio="รีวิวของใช้จริงทุกชิ้น ป้ายยาของดี ตะกร้า TikTok Shop ติดต่องาน line @ployreview",
        follower_count=85000,
        total_likes=650000,
        tier="Micro",
        query_origin="KOC_QUERY",
        is_work_ready=True,  # Open for work!
        signals=CreatorSignals(
            basket_ratio=1.0,  # 100% basket!
            median_comments=45.0,  # Real active comments!
            median_views=35000.0,
            comment_to_like=0.035,
        ),
    )
    # Check Gate 1 filters
    assert merchant_reason(top_reviewer) is None
    assert affiliate_bot_reason(top_reviewer) is None


def test_2x2_substyle_lifestyle_guardrail():
    # Spec 4.2: 'KOL - Lifestyle / Aesthetic' cannot have basket ratio >= 15%
    signals_low_basket = CreatorSignals(basket_ratio=0.05)
    assert guard_sub_style("KOL - Lifestyle / Aesthetic", signals_low_basket) == "KOL - Lifestyle / Aesthetic"

    signals_high_basket = CreatorSignals(basket_ratio=0.60)
    guarded = guard_sub_style("KOL - Lifestyle / Aesthetic", signals_high_basket)
    assert guarded != "KOL - Lifestyle / Aesthetic"
    assert guarded in ("KOC - Hard-Sell Reviewer", "KOC - Everyday User / Vlog")


# ---------------------------------------------------------------------------
# 5. Competitor Layers (Spec 5.1)
# ---------------------------------------------------------------------------
def test_competitor_flags_conflict_vs_comparison():
    competitors = [
        Competitor(brand="La Roche-Posay", aliases=["La Roche-Posay", "ลาโรช"], source="google_search_grounded"),
        Competitor(brand="CeraVe", aliases=["CeraVe", "เซราวี"], source="google_search_grounded"),
    ]

    # Video with 1 competitor -> Conflict
    p_conflict = KOLProfile(
        id="p1",
        handle="skincare_test1",
        display_name="Skincare Test",
        tiktok_url="https://www.tiktok.com/@skincare_test1",
        follower_count=50000,
        tier="Micro",
        query_origin="KOL_QUERY",
        is_work_ready=True,
        recent_videos=[
            VideoMetric(
                video_id="v1",
                url="https://tiktok.com/@skincare_test1/v1",
                caption="รีวิว ลาโรช แต้มสิวยุบไวมาก",
                views=10000,
                likes=500,
                comments=20,
                shares=10,
                has_yellow_basket=False,
            )
        ],
    )
    flags1 = competitor_flags(p_conflict, competitors)
    assert len(flags1) == 1
    assert flags1[0].type == "conflict"
    assert "Competitor Conflict: La Roche-Posay" in flags1[0].label

    # Video comparing both competitors -> Comparison Opportunity
    p_compare = KOLProfile(
        id="p2",
        handle="skincare_test2",
        display_name="Skincare Compare",
        tiktok_url="https://www.tiktok.com/@skincare_test2",
        follower_count=70000,
        tier="Micro",
        query_origin="KOL_QUERY",
        is_work_ready=True,
        recent_videos=[
            VideoMetric(
                video_id="v2",
                url="https://tiktok.com/@skincare_test2/v2",
                caption="เทียบกันชัดๆ ลาโรช vs เซราวี ตัวไหนเหมาะกับผิวแพ้ง่าย",
                views=25000,
                likes=1500,
                comments=60,
                shares=30,
                has_yellow_basket=False,
            )
        ],
    )
    flags2 = competitor_flags(p_compare, competitors)
    assert any(f.type == "comparison" for f in flags2)
    assert any("Comparison Opportunity" in f.label for f in flags2)


# ---------------------------------------------------------------------------
# 6. Stage 4: Dynamic Scoring Engine (Spec 4.3 - 40 / 35 / 25)
# ---------------------------------------------------------------------------
def test_dynamic_scoring_breakdown_legit_creator():
    scoring = get_scoring_engine()
    brand = BrandDNA(
        id="b_test",
        brand_name="Her Hyness",
        vertical="Beauty & Skincare",
        sub_category="Clean Skincare",
        brand_summary="Clean dermocosmetics skincare for acne-prone sensitive skin",
        target_audience="Young Thai beauty shoppers",
        brand_tone=["Authentic", "Modern"],
        price_positioning="Mid-Range",
        average_price_thb=690,
        conversion_model="ECOMMERCE_PRODUCT",
        kol_koc_mix=KolKocMix(kol=30, koc=70),
        niche_keywords=["สกินแคร์", "ผิวแพ้ง่าย", "สิว"],
        search_queries=[
            SearchQuery(query="สกินแคร์ผิวแพ้ง่าย", side="KOL_QUERY", specificity="direct"),
            SearchQuery(query="ป้ายยาสกินแคร์", side="KOC_QUERY", specificity="direct"),
        ],
    )

    kol = KOLProfile(
        id="koc_fah",
        handle="fah_skincare",
        display_name="Fah Skincare Review",
        tiktok_url="https://www.tiktok.com/@fah_skincare",
        bio="รีวิวสกินแคร์ผิวแพ้ง่าย ใช้จริงทุกตัว ติดต่องาน line @fahwork",
        follower_count=85000,
        tier="Micro",
        query_origin="KOC_QUERY",
        is_work_ready=True,
        funnel_role="KOC",
        sub_style="KOC - Hard-Sell Reviewer",
        llm_relevance_score=0.9,
        signals=CreatorSignals(
            basket_ratio=0.80,
            median_views=30000.0,
            mean_views=35000.0,
            median_comments=80.0,
            comment_to_like=0.03,
            share_to_like=0.02,
        ),
        recent_videos=[
            VideoMetric(
                video_id="v_1",
                url="https://tiktok.com/@fah/1",
                caption="รีวิวสกินแคร์สำหรับผิวแพ้ง่าย เป็นสิวต้องลอง",
                hashtags=["สกินแคร์", "ผิวแพ้ง่าย", "ของดีบอกต่อ"],
                views=30000,
                likes=2000,
                comments=90,
                shares=40,
                collect_count=120,
                has_yellow_basket=True,
            )
        ],
    )

    score, breakdown = scoring.evaluate_kol(kol, brand)

    # Check 3 Dimensions
    assert 0 <= breakdown.relevance_total <= 40
    assert 0 <= breakdown.engagement_total <= 35
    assert 0 <= breakdown.audience_total <= 25
    assert 50.0 <= score <= 100.0

    # Work-ready bonus applied
    assert kol.is_work_ready is True
    assert breakdown.subniche_workready_points >= 4.0

    # For ECOMMERCE_PRODUCT, KOC - Hard-Sell Reviewer receives full 5/5 affiliate health
    assert breakdown.affiliate_health_points == 5.0


def test_affiliate_health_luxury_penalty():
    scoring = get_scoring_engine()
    # Luxury / High-Ticket Lead Gen brand
    luxury_brand = BrandDNA(
        id="b_lux",
        brand_name="The Ritz Luxury Hotel",
        vertical="Hospitality",
        sub_category="5-Star Luxury Resort",
        brand_summary="Ultra-luxury retreat in Phuket",
        target_audience="Affluent travelers",
        price_positioning="Luxury",
        average_price_thb=15000,
        conversion_model="LIFESTYLE_EXPERIENCE",
        kol_koc_mix=KolKocMix(kol=70, koc=30),
        niche_keywords=["luxuryhotel", "phuketresort"],
        search_queries=[SearchQuery(query="พาส่องโรงแรมหรู", side="KOL_QUERY", specificity="direct")],
    )

    # Channel with > 70% yellow basket selling cheap goods -> must receive penalized affiliate health points
    spammy_lifestyle = KOLProfile(
        id="k_spammy",
        handle="random_lifestyle",
        display_name="Lifestyle Shop",
        tiktok_url="https://www.tiktok.com/@random_lifestyle",
        bio="รีวิวที่พักพร้อมปักตะกร้าของใช้",
        follower_count=60000,
        tier="Micro",
        query_origin="KOL_QUERY",
        funnel_role="KOL",
        sub_style="KOL - Lifestyle / Aesthetic",
        signals=CreatorSignals(basket_ratio=0.85, median_views=10000.0, mean_views=12000.0),
        recent_videos=[
            VideoMetric(
                video_id="vl",
                url="https://tiktok.com/@vl/1",
                caption="พาชมวิวสวยๆ",
                views=10000,
                likes=400,
                comments=10,
                shares=5,
                collect_count=15,
                has_yellow_basket=True,
            )
        ],
    )

    _, breakdown = scoring.evaluate_kol(spammy_lifestyle, luxury_brand)
    # Spec 4.3 #3: basket > 70% in LIFESTYLE_EXPERIENCE is penalized
    assert breakdown.affiliate_health_points < 3.0


# ---------------------------------------------------------------------------
# 7. End-to-End FastAPI Endpoints
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_fastapi_analyze_brand_endpoint(monkeypatch):
    """
    Tests the FastAPI /api/analyze-brand endpoint routing and serialization.
    """
    from httpx import AsyncClient, ASGITransport
    from app.services import brand_analyzer as ba_module

    mock_dna = BrandDNA(
        id="live-afteryou",
        brand_name="After You Dessert Cafe",
        vertical="Food & Beverage",
        sub_category="Dessert Cafe",
        brand_summary="Famous dessert cafe in Bangkok known for Shibuya Honey Toast",
        target_audience="Urban youth and sweet lovers",
        price_positioning="Mid-Range",
        average_price_thb=350,
        conversion_model="LIFESTYLE_EXPERIENCE",
        conversion_model_reason="Store visits and experiential dining",
        kol_koc_mix=KolKocMix(kol=70, koc=30),
        search_queries=[
            SearchQuery(query="พาส่องเมนูใหม่", side="KOL_QUERY", specificity="direct"),
            SearchQuery(query="คาเฟ่กรุงเทพ", side="KOL_QUERY", specificity="adjacent"),
            SearchQuery(query="พากินสยาม", side="KOC_QUERY", specificity="direct"),
            SearchQuery(query="คาเฟ่บรรยากาศดี", side="KOC_QUERY", specificity="adjacent"),
        ],
        niche_keywords=["HoneyToast", "CafeBkk"],
        competitors=[
            Competitor(brand="Karun Thai Tea", aliases=["Karun", "การันต์"], source="google_search_grounded")
        ],
    )

    class MockAnalyzer:
        async def analyze(self, req):
            return mock_dna

    monkeypatch.setattr("app.main.get_brand_analyzer", lambda: MockAnalyzer())
    monkeypatch.setattr(ba_module, "get_brand_analyzer", lambda: MockAnalyzer())

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/analyze-brand",
            json={
                "brand_name": "After You Dessert Cafe",
                "custom_notes": "Famous dessert cafe in Bangkok known for Shibuya Honey Toast and Kakigori, average ticket 250-400 THB",
            },
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "After You" in data["brand_name"]
    assert data["conversion_model"] == "LIFESTYLE_EXPERIENCE"
    assert data["kol_koc_mix"] == {"kol": 70, "koc": 30}
    assert len(data["search_queries"]) == 4


@pytest.mark.asyncio
async def test_end_to_end_matching_pipeline(monkeypatch):
    """
    Tests the complete 4-stage matching pipeline:
    BrandDNA -> Discovery -> Two-Stage Filter (Gate 1 & 2) -> Scoring (40/35/25) -> Top-K Media Mix Portfolio -> 3-Sec Hooks.
    """
    from app.services.apify_service import get_apify_service
    from app.workflow.graph import run_full_matching

    brand_dna = BrandDNA(
        id="b_e2e",
        brand_name="MizuMi",
        vertical="Beauty & Skincare",
        sub_category="Sunscreen & Acne Care",
        brand_summary="Thai clean dermocosmetics brand famous for sensitive-skin sunscreen",
        target_audience="Young Thai consumers with acne and sensitive skin",
        price_positioning="Mid-Range",
        average_price_thb=690,
        conversion_model="ECOMMERCE_PRODUCT",
        kol_koc_mix=KolKocMix(kol=30, koc=70),
        niche_keywords=["กันแดด", "ผิวแพ้ง่าย", "สิว"],
        search_queries=[
            SearchQuery(query="กันแดดผิวแพ้ง่าย", side="KOL_QUERY", specificity="direct"),
            SearchQuery(query="ป้ายยากันแดด", side="KOC_QUERY", specificity="direct"),
        ],
        competitors=[
            Competitor(brand="La Roche-Posay", aliases=["La Roche-Posay", "ลาโรช"], source="google_search_grounded")
        ],
    )

    mock_discover_items = [
        # 1. KOL Expert (KOL_QUERY)
        {
            "id": "v101",
            "text": "เจาะลึกส่วนผสมกันแดด สำหรับผิวแพ้ง่าย #กันแดด #ผิวแพ้ง่าย",
            "playCount": 45000,
            "diggCount": 3500,
            "commentCount": 120,
            "shareCount": 250,
            "collectCount": 800,
            "hasTikTokShopProduct": False,
            "_origin": "KOL_QUERY",
            "authorMeta": {
                "name": "dr_skin_guru",
                "nickName": "หมอสกินแคร์",
                "signature": "แพทย์ผิวหนัง ให้ความรู้สกินแคร์ ติดต่องาน line @drskin",
                "fans": 120000,
                "heart": 850000,
            },
        },
        # 2. KOC Hard-Sell Reviewer (KOC_QUERY, 100% basket, high engagement)
        {
            "id": "v102",
            "text": "ป้ายยากันแดดตัวเด็ด คุมมันไม่อุดตัน จิ้มตะกร้าเหลือง #ป้ายยา #กันแดด",
            "playCount": 55000,
            "diggCount": 4200,
            "commentCount": 180,
            "shareCount": 90,
            "collectCount": 300,
            "hasTikTokShopProduct": True,
            "_origin": "KOC_QUERY",
            "authorMeta": {
                "name": "ploy_paiya",
                "nickName": "Ploy ป้ายยาพาช้อป",
                "signature": "รีวิวของใช้จริงทุกชิ้น ป้ายยาของดี ตะกร้า TikTok Shop ติดต่องาน line @ploy",
                "fans": 95000,
                "heart": 700000,
            },
        },
        # 3. Excluded Merchant Shop (Gate 1 filter)
        {
            "id": "v103",
            "text": "โรงงานผลิตครีมกันแดด รับผลิตสร้างแบรนด์ ราคาส่ง สั่งผลิตจิ้มลิงก์",
            "playCount": 12000,
            "diggCount": 200,
            "commentCount": 5,
            "shareCount": 1,
            "collectCount": 3,
            "hasTikTokShopProduct": False,
            "_origin": "KOL_QUERY",
            "authorMeta": {
                "name": "oem_cream_factory",
                "nickName": "โรงงานผลิตครีม ราคาส่ง",
                "signature": "โรงงานรับผลิตครีมกันแดด OEM ไม่มีขั้นต่ำ",
                "fans": 15000,
                "heart": 5000,
            },
        },
    ]

    apify = get_apify_service()
    monkeypatch.setattr(apify, "api_token", "mock_apify_token_123")

    async def mock_discover(*args, **kwargs):
        return {"items": mock_discover_items, "errors": []}

    async def mock_scrape_profiles(*args, **kwargs):
        return {}

    monkeypatch.setattr(apify, "discover", mock_discover)
    monkeypatch.setattr(apify, "discover_batch", mock_discover)
    monkeypatch.setattr(apify, "scrape_profiles", mock_scrape_profiles)

    response = await run_full_matching(brand_dna=brand_dna, top_k=5)

    assert response.brand_dna.brand_name == "MizuMi"
    assert response.strategy.conversion_model == "ECOMMERCE_PRODUCT"
    assert len(response.ranked_kols) >= 2
    # Verify Gate 1 filtered out the OEM factory merchant
    assert any(ex.handle == "oem_cream_factory" for ex in response.excluded_creators)
    # Verify ranked creators have scores, breakdown, and pitch hooks
    for r in response.ranked_kols:
        assert 0.0 <= r.total_match_score <= 100.0
        assert r.score_breakdown.relevance_total > 0
        assert r.score_breakdown.engagement_total > 0
        assert r.score_breakdown.audience_total > 0

