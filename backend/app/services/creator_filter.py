"""
Stage 2/3 helpers — creator assembly, deterministic signals, Gate 1 rule-based filters,
2x2 sub-style guard and competitor Layers 2 & 3 (Spec 4.1, 4.2, 5.1).
"""
import re
from collections import Counter, defaultdict
from statistics import median, mean
from typing import Any, Dict, List, Optional, Tuple

from app.models import (
    BrandDNA,
    Competitor,
    CompetitorFlag,
    CreatorSignals,
    KOLProfile,
    VideoMetric,
)
from app.services.apify_service import item_to_video

# --- Spec 4.1 Gate 1 vocabularies -------------------------------------------------
# Merchant words excluded ONLY when the bio has no creator work signal (spec rule).
SPEC_MERCHANT_PATTERNS = [
    r"\bofficial\b", r"\bstore\b", r"\bshop\b",
    "สั่งซื้อจิ้มลิงก์", "ตัวแทนจำหน่าย", "ราคาส่ง", "มีบริการเก็บเงินปลายทาง", "เปิดบิล",
]
# Unmistakable factory / wholesale / company markers: always merchants (carried over from the
# previous merchant-flood fix for custom-production brands).
FACTORY_PATTERNS = [
    "โรงงาน", "รับผลิต", "รับสกรีน", "ร้านสกรีน", "ขายส่ง", "บริษัท", "หจก.", "บจก.", r"co\.,?\s*ltd",
]
# Creator "open for work" signals (Spec: ติดต่องาน, For work, DM, Line @).
WORK_READY_PATTERNS = [
    "ติดต่องาน", "ติดต่อรีวิว", "รับงาน", "งานติดต่อ", r"for\s*work", r"\bwork\s*:", r"\bdm\b", r"\binbox\b",
    r"line\s*@", r"line\s*:", r"line\s*id", r"ไลน์\s*@", r"ไลน์\s*:", r"\bcontact\b", r"[\w.+-]+@[\w-]+\.\w+",
]

BOT_BASKET_RATIO = 0.85
BOT_MEDIAN_COMMENTS = 1
BOT_MEDIAN_VIEWS = 300

LIFESTYLE_MAX_BASKET = 0.15
EVERYDAY_MAX_BASKET = 0.40


def _has(patterns: List[str], text: str) -> Optional[str]:
    for p in patterns:
        if re.search(p, text, re.IGNORECASE):
            return p.replace("\\b", "").replace("\\s*", " ")
    return None


def follower_tier(followers: int) -> str:
    if followers < 10_000:
        return "Nano"
    if followers < 100_000:
        return "Micro"
    if followers < 500_000:
        return "Mid-Tier"
    return "Macro"


def is_work_ready(bio: str) -> bool:
    return _has(WORK_READY_PATTERNS, bio or "") is not None


def _ratio_median(pairs: List[Tuple[float, float]]) -> float:
    vals = [n / d for n, d in pairs if d > 0]
    return float(median(vals)) if vals else 0.0


def compute_signals(videos: List[VideoMetric]) -> CreatorSignals:
    if not videos:
        return CreatorSignals()
    views = [v.views for v in videos]
    return CreatorSignals(
        basket_ratio=round(sum(1 for v in videos if v.has_yellow_basket) / len(videos), 3),
        median_views=float(median(views)),
        mean_views=float(mean(views)),
        median_comments=float(median([v.comments for v in videos])),
        save_rate=round(_ratio_median([(v.collect_count, v.views) for v in videos]), 5),
        comment_to_like=round(_ratio_median([(v.comments, v.likes) for v in videos]), 5),
        share_to_like=round(_ratio_median([(v.shares, v.likes) for v in videos]), 5),
        avg_caption_length=round(mean([len(v.caption) for v in videos]), 1),
        kol_query_hits=sum(1 for v in videos if v.query_origin == "KOL_QUERY"),
        koc_query_hits=sum(1 for v in videos if v.query_origin == "KOC_QUERY"),
    )


def group_items_by_creator(items: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Group raw Apify search clips by author, keeping origin tags."""
    creators: Dict[str, Dict[str, Any]] = {}
    for it in items:
        meta = it.get("authorMeta") or {}
        handle = str(meta.get("name") or "").strip()
        if not handle:
            continue
        key = handle.lower()
        entry = creators.setdefault(key, {"meta": meta, "videos": {}})
        video = item_to_video(it, origin=it.get("_origin"))
        if video.video_id and video.video_id not in entry["videos"]:
            entry["videos"][video.video_id] = video
        # keep the richest author meta (profile scrapes carry follower counts)
        if (meta.get("fans") or 0) > (entry["meta"].get("fans") or 0):
            entry["meta"] = meta
    return creators


def build_profile(entry: Dict[str, Any], profile_items: Optional[List[Dict[str, Any]]] = None, max_videos: int = 10) -> KOLProfile:
    meta = dict(entry["meta"])
    search_videos: Dict[str, VideoMetric] = dict(entry["videos"])
    latest: List[VideoMetric] = []
    for it in profile_items or []:
        v = item_to_video(it)
        if v.video_id in search_videos:
            v.query_origin = search_videos[v.video_id].query_origin
        latest.append(v)
        pm = it.get("authorMeta") or {}
        if (pm.get("fans") or 0) > (meta.get("fans") or 0):
            meta.update({k: val for k, val in pm.items() if val})
    seen = {v.video_id for v in latest}
    videos = latest + [v for vid, v in search_videos.items() if vid not in seen]
    videos = videos[:max_videos]

    origins = Counter(v.query_origin for v in search_videos.values() if v.query_origin)
    if origins.get("KOL_QUERY", 0) > origins.get("KOC_QUERY", 0):
        origin = "KOL_QUERY"
    elif origins.get("KOC_QUERY", 0) > 0:
        origin = "KOC_QUERY"
    elif origins.get("NATURAL_QUERY", 0) > 0:
        origin = "NATURAL_QUERY"
    else:
        origin = origins.most_common(1)[0][0] if origins else "NATURAL_QUERY"

    handle = str(meta.get("name")).strip()
    bio = str(meta.get("signature") or "").strip()
    followers = int(meta.get("fans") or 0)
    signals = compute_signals(videos)
    signals.kol_query_hits = origins.get("KOL_QUERY", 0)
    signals.koc_query_hits = origins.get("KOC_QUERY", 0)
    return KOLProfile(
        id=f"tt_{handle.lower()}",
        handle=handle,
        display_name=str(meta.get("nickName") or handle).strip(),
        tiktok_url=f"https://www.tiktok.com/@{handle}",
        avatar_url=str(meta.get("avatar") or "") or None,
        bio=bio,
        follower_count=followers,
        following_count=int(meta.get("following") or 0),
        total_likes=int(meta.get("heart") or 0),
        tier=follower_tier(followers),
        recent_videos=videos,
        query_origin=origin,
        is_work_ready=is_work_ready(bio),
        signals=signals,
    )


# --- Gate 1 ---------------------------------------------------------------------
def _squash(s: str) -> str:
    return re.sub(r"[\s._\-]", "", (s or "").lower())


def brand_account_reason(profile: KOLProfile, brand: BrandDNA) -> Optional[str]:
    handle, display = _squash(profile.handle), _squash(profile.display_name)
    own = _squash(brand.brand_name)
    if len(own) >= 3 and (own in handle or own in display):
        return f"Client brand's own account ({brand.brand_name})"
    for comp in brand.competitors:
        for name in [comp.brand] + comp.aliases:
            c = _squash(name)
            if len(c) >= 4 and (c in handle or c in display):
                return f"Competitor official account ({comp.brand})"
    return None


def merchant_reason(profile: KOLProfile) -> Optional[str]:
    text = f"{profile.handle} {profile.display_name} {profile.bio}"
    hit = _has(FACTORY_PATTERNS, text)
    if hit:
        return f"Factory / wholesale / company account ('{hit}')"
    hit = _has(SPEC_MERCHANT_PATTERNS, f"{profile.display_name} {profile.bio}")
    if hit and not profile.is_work_ready:
        return f"Merchant / official store ('{hit}') with no creator work-ready signal"
    return None


def affiliate_bot_reason(profile: KOLProfile) -> Optional[str]:
    s = profile.signals
    ghost = s.median_comments <= BOT_MEDIAN_COMMENTS or s.median_views < BOT_MEDIAN_VIEWS
    if s.basket_ratio > BOT_BASKET_RATIO and not profile.is_work_ready and ghost:
        return (
            f"Affiliate Spam Bot: basket {s.basket_ratio:.0%} > 85%, no work-ready bio, "
            f"median comments {s.median_comments:.0f} / median views {s.median_views:.0f}"
        )
    return None


# --- 2x2 guard ------------------------------------------------------------------
def guard_sub_style(sub_style: str, signals: CreatorSignals) -> str:
    """Enforce the spec's basket-ratio signal for 'KOL - Lifestyle / Aesthetic' (< 15%)."""
    if sub_style == "KOL - Lifestyle / Aesthetic" and signals.basket_ratio >= LIFESTYLE_MAX_BASKET:
        return "KOC - Everyday User / Vlog" if signals.basket_ratio <= EVERYDAY_MAX_BASKET else "KOC - Hard-Sell Reviewer"
    return sub_style


# --- Competitor layers 2 & 3 ------------------------------------------------------
def frequent_terms(profiles: List[KOLProfile], brand: BrandDNA, top_n: int = 40, min_creators: int = 2) -> List[Dict[str, Any]]:
    """Layer 2 input — hashtags used by >= min_creators distinct creators."""
    per_term = defaultdict(set)
    own = _squash(brand.brand_name)
    for p in profiles:
        for v in p.recent_videos:
            for t in v.hashtags:
                term = t.strip().lower()
                if len(term) >= 3 and _squash(term) != own:
                    per_term[term].add(p.handle)
    ranked = sorted(((t, len(h)) for t, h in per_term.items() if len(h) >= min_creators), key=lambda x: -x[1])
    return [{"term": t, "creators": n} for t, n in ranked[:top_n]]


def _alias_regex(alias: str) -> Optional[re.Pattern]:
    a = alias.strip()
    if len(a) < 3:
        return None
    if re.fullmatch(r"[\x00-\x7F]+", a):
        return re.compile(r"(?<![a-z0-9])" + re.escape(a.lower()) + r"(?![a-z0-9])")
    return re.compile(re.escape(a.lower()))


def mentioned_competitors(text: str, competitors: List[Competitor]) -> List[str]:
    low = (text or "").lower()
    found = []
    for c in competitors:
        for alias in [c.brand] + c.aliases:
            rx = _alias_regex(alias)
            if rx and rx.search(low):
                found.append(c.brand)
                break
    return found


def competitor_flags(profile: KOLProfile, competitors: List[Competitor]) -> List[CompetitorFlag]:
    """Layer 3 — single-brand review = Conflict; multi-brand clip = Comparison Opportunity."""
    if not competitors:
        return []
    conflicts: Dict[str, str] = {}
    comparison: Optional[CompetitorFlag] = None
    for v in profile.recent_videos:
        brands = mentioned_competitors(f"{v.caption} {' '.join(v.hashtags)}", competitors)
        if len(brands) >= 2 and comparison is None:
            comparison = CompetitorFlag(type="comparison", label="🎯 Comparison Opportunity", brands=brands, video_id=v.video_id)
        elif len(brands) == 1:
            conflicts.setdefault(brands[0], v.video_id)
    flags = [
        CompetitorFlag(type="conflict", label=f"⚠️ Competitor Conflict: {b}", brands=[b], video_id=vid)
        for b, vid in conflicts.items()
    ]
    if comparison:
        flags.append(comparison)
    return flags
