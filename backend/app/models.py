from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field


class BrandAnalyzeRequest(BaseModel):
    brand_name: Optional[str] = Field(default=None, description="Brand name if known")
    website_url: Optional[str] = Field(default=None, description="Client website URL")
    facebook_url: Optional[str] = Field(default=None, description="Client Facebook Page URL")
    custom_notes: Optional[str] = Field(default=None, description="Optional agency brief notes")
    manual_competitors: Optional[List[str]] = Field(default_factory=list, description="Optional manual competitor names provided by agency")


class BrandDNA(BaseModel):
    id: Optional[str] = Field(default=None, description="Brand DNA identifier")
    brand_name: str = Field(..., description="Brand name")
    website_url: str = Field(default="", description="Website URL")
    facebook_url: str = Field(default="", description="Facebook Page URL")
    vertical: str = Field(..., description="Primary industry vertical extracted dynamically from brand data")
    sub_category: str = Field(default="", description="Specific product or service category")
    brand_summary: str = Field(..., description="Concise summary of the brand value proposition and products")
    target_audience: str = Field(..., description="Primary target demographic & psychographic in Thailand")
    target_age_range: str = Field(default="", description="Target age range")
    target_locations: List[str] = Field(default_factory=list, description="Target geographic regions in Thailand")
    brand_tone: List[str] = Field(default_factory=list, description="Brand tone and personality traits")
    content_style_preferences: List[str] = Field(default_factory=list, description="Desired TikTok content formats")
    price_positioning: Literal["Budget / Mass", "Mid-Range / Accessible", "Premium / Masstige", "Luxury / High-End", "Dynamic"] = Field(
        default="Dynamic", description="Product price tier positioning"
    )
    average_price_thb: int = Field(default=0, description="Representative product price in THB")
    thai_keywords: List[str] = Field(default_factory=list, description="Thai search keywords & hashtags for TikTok discovery")
    scraped_sources: List[str] = Field(default_factory=list, description="Sources used to construct Brand DNA")
    manual_competitors: List[str] = Field(default_factory=list, description="Manual competitor brand names")
    search_taxonomy: Dict[str, List[str]] = Field(
        default_factory=lambda: {
            "niche_hashtags": [],
            "pain_point_queries": [],
            "review_hook_queries": [],
            "lifestyle_persona_queries": [],
            "competitor_seed_queries": [],
        },
        description="5-angle search taxonomy for TikTok discovery",
    )
    grounded_competitors: List[Dict[str, Any]] = Field(
        default_factory=list, description="Search-grounded Thai competitor dictionary with bilingual aliases"
    )


class VideoMetric(BaseModel):
    video_id: str = Field(..., description="TikTok video ID")
    caption: str = Field(..., description="Thai/English video caption")
    hashtags: List[str] = Field(default_factory=list, description="Video hashtags without #")
    views: int = Field(..., ge=0)
    likes: int = Field(..., ge=0)
    comments: int = Field(..., ge=0)
    shares: int = Field(..., ge=0)
    collect_count: int = Field(default=0, ge=0, description="Number of saves/bookmarks")
    has_yellow_basket: bool = Field(default=False, description="Whether video has TikTok Shop affiliate link")
    reviewed_item_price_thb: Optional[int] = Field(default=None, description="Estimated price in THB of product featured")
    location_tag: Optional[str] = Field(default=None, description="Thai check-in or location tag")


class KOLProfile(BaseModel):
    id: str = Field(..., description="KOL identifier")
    handle: str = Field(..., description="TikTok handle without @")
    display_name: str = Field(..., description="Creator display name")
    tiktok_url: str = Field(..., description="Direct TikTok profile link")
    avatar_url: Optional[str] = Field(default=None, description="Avatar image URL")
    vertical: str = Field(..., description="Primary content vertical")
    secondary_verticals: List[str] = Field(default_factory=list)
    bio: str = Field(default="", description="TikTok bio")
    follower_count: int = Field(..., ge=0)
    following_count: int = Field(default=0, ge=0)
    total_likes: int = Field(default=0, ge=0)
    tier: str = Field(default="Micro (10K-100K)")
    creator_persona: str = Field(..., description="Creator archetype & visual aesthetic")
    content_styles: List[str] = Field(default_factory=list, description="Typical content formats")
    typical_price_tier: str = Field(default="Dynamic")
    avg_reviewed_price_thb: int = Field(default=0, description="Average price in THB of products typically featured")
    primary_locations: List[str] = Field(default_factory=list, description="Frequent Thai locations/check-ins")
    audience_language: str = Field(default="Thai", description="Primary language of creator & commenters")
    sample_comments: List[str] = Field(default_factory=list, description="Live Thai comments / inquiries from recent videos")
    recent_videos: List[VideoMetric] = Field(default_factory=list, description="Recent video metrics from TikTok")
    creator_category: str = Field(default="Content Creator (ทั่วไป)", description="หมวดหมู่ครีเอเตอร์ เช่น Content Creator (เน้นรีวิว), Lifestyle, ฯลฯ")
    creator_archetype: Literal["Educated Guru", "Top Reviewer", "Lifestyle & Vlog", "Niche Enthusiast", "General Creator"] = Field(
        default="General Creator", description="4 Main Creator Archetypes from spec"
    )
    recommended_role: str = Field(default="Brand Awareness", description="Recommended campaign role (Trust, Sales, Awareness, Reach)")
    account_type: Literal["merchant_store", "affiliate_spam_bot", "real_kol"] = Field(
        default="real_kol", description="Entity classification stage: merchant, spam bot, or real KOL"
    )
    is_work_ready: bool = Field(default=False, description="Work-Ready KOL signal: has Line @, for work, email in bio")
    competitor_warning: Optional[str] = Field(default=None, description="⚠️ Competitor Conflict or 🎯 Niche Enthusiast Opportunity")
    query_origin: Optional[str] = Field(default=None, description="Taxonomy query angle that discovered this creator")
    save_to_view_ratio: float = Field(default=0.0, description="Save-to-view utility ratio")
    view_consistency_ratio: float = Field(default=0.0, description="Median views / mean views ratio")
    is_affiliate_spam_trap: bool = Field(default=False, description="Whether creator is classified as fake affiliate bot/spam trap")
    estimated_rate_thb: str = Field(default="", description="Estimated campaign rate per video in THB")


class SignalBreakdown(BaseModel):
    relevance_score_raw: float = Field(..., description="0-100 raw relevance score")
    relevance_weighted: float = Field(..., description="0-40 weighted relevance points (Spec: 40 pts)")
    semantic_similarity: float = Field(..., description="0-1 dense vector similarity")
    semantic_points: float = Field(default=0.0, description="0-28 semantic relevance points")
    niche_keyword_points: float = Field(default=0.0, description="0-12 keyword & work-ready points")
    matched_keywords: List[str] = Field(default_factory=list, description="Matched Thai/English keywords & hashtags")
    embedding_model: str = Field(default="gemini-embedding-2", description="Model used for dense vector semantic matching")

    engagement_score_raw: float = Field(..., description="0-100 raw engagement score after penalty")
    engagement_weighted: float = Field(..., description="0-35 weighted engagement points (Spec: 35 pts)")
    median_engagement_rate_pct: float = Field(..., description="Median((Likes + Comments + Shares + Saves) / Views) * 100")
    median_er_points: float = Field(default=0.0, description="0-15 median ER points")
    save_to_view_points: float = Field(default=0.0, description="0-10 save-to-view utility points")
    view_consistency_points: float = Field(default=0.0, description="0-10 view consistency points")
    views_to_followers_ratio: float = Field(default=0.0, description="Median views divided by follower count")
    yellow_basket_ratio: float = Field(default=0.0, description="Fraction of recent videos with TikTok Shop affiliate links")
    affiliate_spam_penalty_applied: bool = Field(default=False, description="True if penalized by the Affiliate Spam / Yellow-Basket filter")
    affiliate_spam_penalty_points: float = Field(default=0.0, description="Raw engagement points deducted for affiliate spam")
    affiliate_spam_reason: Optional[str] = Field(default=None, description="Explanation if affiliate spam penalty was triggered")

    audience_score_raw: float = Field(..., description="0-100 raw multi-signal audience score")
    audience_weighted: float = Field(..., description="0-25 weighted audience points (Spec: 25 pts)")
    thai_authenticity_points: float = Field(default=0.0, description="0-10 Thai audience authenticity points")
    buyer_intent_points: float = Field(default=0.0, description="0-10 Buyer intent proxy points")
    affiliate_saturation_points: float = Field(default=0.0, description="0-5 Affiliate saturation health points")

    # Compatibility signals for 4-signal breakdown display
    persona_signal_score: float = Field(default=20.0, description="Creator persona & visual style")
    price_proxy_signal_score: float = Field(default=20.0, description="Product price-point proxy")
    geo_language_signal_score: float = Field(default=20.0, description="Thai geo/language & check-ins")
    comment_sentiment_signal_score: float = Field(default=20.0, description="Commenters sample")
    confidence_level: Literal["High", "Medium", "Low"] = Field(default="High", description="Confidence level in public audience inference")
    evidence_list: List[str] = Field(default_factory=list, description="Concrete evidence statements")


class RankedKOL(BaseModel):
    rank: int = Field(..., ge=1)
    kol: KOLProfile
    total_match_score: float = Field(..., description="Final 0-100 composite match score")
    score_breakdown: SignalBreakdown
    why_this_kol: str = Field(..., description="Agency-grade strategic rationale explaining fit or penalty")
    thai_campaign_hooks: List[str] = Field(default_factory=list, description="Custom Thai TikTok campaign hook ideas tailored to archetype")
    enrichment_source: str = Field(default="Live Apify TikTok Scraper", description="Data telemetry source")
    llm_generator_model: str = Field(default="gemini-3.5-flash-lite", description="Gemini LLM model used for synthesis")


class MatchRequest(BaseModel):
    brand_dna: BrandDNA
    top_k: int = Field(default=8, ge=1, le=36, description="Number of top ranked KOLs to return")
    include_penalized_traps: bool = Field(default=True, description="Whether to include affiliate spam accounts for transparency")
    min_followers: Optional[int] = Field(default=None, description="Optional minimum follower filter")
    max_followers: Optional[int] = Field(default=None, description="Optional maximum follower filter")


class AutoMatchRequest(BaseModel):
    brand_name: Optional[str] = None
    website_url: Optional[str] = None
    facebook_url: Optional[str] = None
    custom_notes: Optional[str] = None
    manual_competitors: Optional[List[str]] = Field(default_factory=list)
    top_k: int = Field(default=8, ge=1, le=36)


class MatchResponse(BaseModel):
    brand_dna: BrandDNA
    total_candidates_evaluated: int
    apify_enrichment_status: str
    ranked_kols: List[RankedKOL]
    penalized_spam_kols: List[RankedKOL] = Field(default_factory=list, description="Affiliate spam accounts penalized")
    workflow_trace: List[str] = Field(default_factory=list, description="LangGraph node execution trace")
