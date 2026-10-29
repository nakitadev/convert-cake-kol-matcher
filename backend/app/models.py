"""
Data models for the Convert Cake TikTok KOL/KOC Discovery & Matching Engine.

Implements the 4-stage pipeline from `system_specification_tiktok_kol_matching_engine.md`:
  1. Brand DNA & Conversion Model Classification
  2. Adaptive Scene Translation & TikTok Discovery (KOL_QUERY / KOC_QUERY)
  3. Two-Stage Filtering, 2x2 KOL/KOC Classification & Dynamic Scoring (40 / 35 / 25)
  4. Role-Adaptive Pitch Hooks & 3-Layer Grounded Competitor Detection
"""
from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Spec enums
# ---------------------------------------------------------------------------
ConversionModel = Literal[
    "ECOMMERCE_PRODUCT",
    "APP_DIGITAL_SERVICE",
    "HIGH_TICKET_LEADGEN",
    "LIFESTYLE_EXPERIENCE",
]

FunnelRole = Literal["KOL", "KOC"]

SubStyle = Literal[
    "KOL - Expert / Guru",
    "KOL - Lifestyle / Aesthetic",
    "KOC - Hard-Sell Reviewer",
    "KOC - Everyday User / Vlog",
]

QueryOrigin = Literal["KOL_QUERY", "KOC_QUERY", "NATURAL_QUERY"]
QuerySpecificity = Literal["direct", "adjacent"]

SUB_STYLE_ROLE: Dict[str, str] = {
    "KOL - Expert / Guru": "KOL",
    "KOL - Lifestyle / Aesthetic": "KOL",
    "KOC - Hard-Sell Reviewer": "KOC",
    "KOC - Everyday User / Vlog": "KOC",
}

# Spec 2.2 — Recommended KOL : KOC media mix per conversion model (percent KOL / KOC)
CONVERSION_MODEL_MIX: Dict[str, Dict[str, int]] = {
    "ECOMMERCE_PRODUCT": {"kol": 30, "koc": 70},
    "APP_DIGITAL_SERVICE": {"kol": 60, "koc": 40},
    "HIGH_TICKET_LEADGEN": {"kol": 70, "koc": 30},
    "LIFESTYLE_EXPERIENCE": {"kol": 60, "koc": 40},
}


# ---------------------------------------------------------------------------
# Stage 1 — Brand DNA
# ---------------------------------------------------------------------------
class BrandAnalyzeRequest(BaseModel):
    brand_name: Optional[str] = Field(default=None, description="Brand name if known")
    website_url: Optional[str] = Field(default=None, description="Client website URL")
    facebook_url: Optional[str] = Field(default=None, description="Client Facebook Page URL")
    custom_notes: Optional[str] = Field(default=None, description="Optional agency brief notes")
    manual_competitors: Optional[List[str]] = Field(
        default_factory=list, description="Optional competitor override from the marketing team"
    )
    force_refresh: bool = Field(default=False, description="Bypass demo cache and force live external scrape")


class SearchQuery(BaseModel):
    query: str = Field(..., description="Natural Thai TikTok search phrase (2-4 words, <= 18 letters)")
    side: Optional[QueryOrigin] = Field(default="NATURAL_QUERY", description="Natural query or origin tag")
    specificity: Optional[QuerySpecificity] = Field(
        default="direct", description="direct or adjacent syntax rule"
    )
    syntax_rule: Optional[str] = Field(default=None, description="Abstract syntax rule used")


class Competitor(BaseModel):
    brand: str = Field(..., description="Canonical competitor brand name")
    aliases: List[str] = Field(default_factory=list, description="English + Thai transliteration aliases")
    source: Literal["google_search_grounded", "llm_knowledge", "manual", "tiktok_cooccurrence"] = Field(
        ..., description="Detection layer that surfaced this competitor"
    )
    mentions: int = Field(default=0, description="Co-occurrence count in scraped TikTok clips (Layer 2)")


class KolKocMix(BaseModel):
    kol: int = Field(..., ge=0, le=100)
    koc: int = Field(..., ge=0, le=100)


class BrandDNA(BaseModel):
    id: Optional[str] = Field(default=None, description="Brand DNA identifier")
    brand_name: str = Field(..., description="Brand name")
    website_url: str = Field(default="", description="Website URL")
    facebook_url: str = Field(default="", description="Facebook Page URL")
    vertical: str = Field(..., description="Primary industry vertical")
    sub_category: str = Field(default="", description="Specific product / service category")
    brand_summary: str = Field(..., description="Concise value proposition summary")
    target_audience: str = Field(..., description="Primary Thai target audience")
    target_age_range: str = Field(default="")
    brand_tone: List[str] = Field(default_factory=list, description="Thai tone-of-voice traits")
    customer_pain_points: List[str] = Field(
        default_factory=list, description="Real Thai customer questions / pain points (Facebook comments)"
    )
    price_positioning: str = Field(default="", description="Price tier positioning")
    average_price_thb: int = Field(default=0)

    # Spec 2.2 — Conversion model & media mix
    conversion_model: ConversionModel = Field(..., description="One of the 4 Brand Conversion Models")
    conversion_model_reason: str = Field(default="", description="Why the brand fits this conversion model")
    kol_koc_mix: KolKocMix = Field(..., description="Recommended KOL : KOC media mix")

    # Spec 3 — Scene translation queries (separate KOL / KOC sets)
    search_queries: List[SearchQuery] = Field(default_factory=list)
    niche_keywords: List[str] = Field(
        default_factory=list, description="Sub-niche keywords used for keyword-match scoring"
    )

    # Spec 5.1 — Competitors
    manual_competitors: List[str] = Field(default_factory=list)
    competitors: List[Competitor] = Field(default_factory=list)

    scraped_sources: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Stage 2/3 — Creators
# ---------------------------------------------------------------------------
class VideoMetric(BaseModel):
    video_id: str
    url: str = Field(default="", description="TikTok web video URL")
    caption: str = Field(default="")
    hashtags: List[str] = Field(default_factory=list)
    views: int = Field(..., ge=0)
    likes: int = Field(..., ge=0)
    comments: int = Field(..., ge=0)
    shares: int = Field(..., ge=0)
    collect_count: int = Field(default=0, ge=0, description="Saves / bookmarks")
    has_yellow_basket: bool = Field(default=False, description="TikTok Shop product attached")
    query_origin: Optional[QueryOrigin] = Field(default=None, description="Search side that surfaced this clip")
    search_query: Optional[str] = Field(default=None)


class CompetitorFlag(BaseModel):
    type: Literal["conflict", "comparison"]
    label: str = Field(..., description="UI label e.g. '⚠️ Competitor Conflict: X' or '🎯 Comparison Opportunity'")
    brands: List[str] = Field(default_factory=list)
    video_id: Optional[str] = None


class CreatorSignals(BaseModel):
    """Deterministic signals computed from the creator's recent clips."""
    basket_ratio: float = 0.0
    median_views: float = 0.0
    mean_views: float = 0.0
    median_comments: float = 0.0
    save_rate: float = Field(default=0.0, description="Median collectCount / playCount")
    comment_to_like: float = Field(default=0.0, description="Median commentCount / diggCount")
    share_to_like: float = Field(default=0.0, description="Median shareCount / diggCount")
    avg_caption_length: float = 0.0
    kol_query_hits: int = 0
    koc_query_hits: int = 0


class KOLProfile(BaseModel):
    id: str
    handle: str
    display_name: str
    tiktok_url: str
    avatar_url: Optional[str] = None
    bio: str = ""
    follower_count: int = Field(..., ge=0)
    following_count: int = Field(default=0, ge=0)
    total_likes: int = Field(default=0, ge=0)
    tier: Literal["Nano", "Micro", "Mid-Tier", "Macro"] = Field(..., description="Spec 4.2 follower tier")
    recent_videos: List[VideoMetric] = Field(default_factory=list)

    query_origin: QueryOrigin = Field(default="NATURAL_QUERY", description="Primary search side that discovered this creator")
    is_work_ready: bool = Field(default=False, description="Bio has ติดต่องาน / For work / DM / Line @")
    signals: CreatorSignals = Field(default_factory=CreatorSignals)

    # Gate 2 / 2x2 classification
    funnel_role: Optional[FunnelRole] = None
    sub_style: Optional[SubStyle] = None
    llm_relevance_score: float = Field(default=0.0, description="0-1 relevance from LLM Relevance Gate")
    why_it_fits: str = Field(default="", description="One-sentence LLM rationale")
    pitch_hook: str = Field(default="", description="Role-adaptive 3-second opening hook")

    # Tier-2 audience proxy (Top-K only)
    real_comments: List[str] = Field(default_factory=list, description="Real scraped comments (Top-K)")
    comment_intent_ratio: Optional[float] = Field(default=None, description="Share of buyer-intent comments")

    competitor_flags: List[CompetitorFlag] = Field(default_factory=list)


class ExcludedCreator(BaseModel):
    handle: str
    display_name: str
    tiktok_url: str
    follower_count: int = 0
    bio: str = ""
    stage: Literal["gate1_merchant", "gate1_affiliate_bot", "gate1_brand_account", "gate2_irrelevant"]
    reason: str


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------
class SignalBreakdown(BaseModel):
    # 1. Brand & Funnel Relevance (40 คะแนน)
    relevance_total: float = Field(..., description="0-40")
    semantic_llm_points: float = Field(..., description="0-30 cosine + LLM fit")
    cosine_similarity: float = Field(default=0.0, description="Raw cosine similarity -1..1")
    subniche_workready_points: float = Field(..., description="0-10 keyword match + work-ready bonus")
    matched_keywords: List[str] = Field(default_factory=list)

    # 2. Engagement Quality & Content Utility (35 คะแนน)
    engagement_total: float = Field(..., description="0-35")
    median_er_points: float = Field(..., description="0-15")
    median_engagement_rate: float = Field(default=0.0, description="Median ER (fraction) on clips >= 500 views")
    eligible_clips: int = Field(default=0, description="Clips with playCount >= 500")
    utility_points: float = Field(..., description="0-10 save & share utility")
    utility_score: float = Field(default=0.0, description="Median (collect + 0.7*share) / max(play, 500)")
    consistency_points: float = Field(..., description="0-10 view consistency")
    view_consistency_ratio: float = Field(default=0.0)

    # 3. Audience Proxy & Commercial Viability (25 คะแนน)
    audience_total: float = Field(..., description="0-25")
    thai_authenticity_points: float = Field(..., description="0-10")
    thai_ratio: float = Field(default=0.0)
    buyer_intent_points: float = Field(..., description="0-10")
    buyer_intent_tier: Literal["tier1_fast_proxy", "tier2_comment_analysis"] = "tier1_fast_proxy"
    affiliate_health_points: float = Field(..., description="0-5 brand-adaptive affiliate health")

    evidence: List[str] = Field(default_factory=list)


class RankedKOL(BaseModel):
    rank: int = Field(..., ge=1)
    kol: KOLProfile
    total_match_score: float = Field(..., description="0-100")
    score_breakdown: SignalBreakdown
    pitch_hook: str = Field(default="", description="3-second Thai opening hook tailored to sub-style")


# ---------------------------------------------------------------------------
# API requests / responses
# ---------------------------------------------------------------------------
class MatchRequest(BaseModel):
    brand_dna: BrandDNA
    top_k: int = Field(default=10, ge=1, le=50)
    force_refresh: bool = Field(default=False, description="Bypass demo cache and force live external fetch")


class AutoMatchRequest(BaseModel):
    brand_name: Optional[str] = None
    website_url: Optional[str] = None
    facebook_url: Optional[str] = None
    custom_notes: Optional[str] = None
    manual_competitors: Optional[List[str]] = Field(default_factory=list)
    top_k: int = Field(default=10, ge=1, le=50)
    force_refresh: bool = Field(default=False, description="Bypass demo cache and force live external fetch")


class StrategySummary(BaseModel):
    conversion_model: ConversionModel
    conversion_model_reason: str = ""
    recommended_mix: KolKocMix
    achieved_mix: Dict[str, int] = Field(default_factory=dict, description="Counts of KOL / KOC in final list")


class FilterStats(BaseModel):
    raw_clips: int = 0
    unique_creators: int = 0
    removed_brand_accounts: int = 0
    removed_merchants: int = 0
    removed_affiliate_bots: int = 0
    removed_irrelevant: int = 0
    scored: int = 0


class MatchResponse(BaseModel):
    brand_dna: BrandDNA
    strategy: StrategySummary
    filter_stats: FilterStats
    ranked_kols: List[RankedKOL]
    excluded_creators: List[ExcludedCreator] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list, description="Non-fatal live API issues surfaced to UI")
    workflow_trace: List[str] = Field(default_factory=list)
