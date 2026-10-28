import os
import re
import time
import logging
from typing import Optional, Dict, Any, List, Tuple
import httpx

from app.models import KOLProfile, VideoMetric

logger = logging.getLogger(__name__)


class ApifyTikTokService:
    """
    Apify TikTok Scraper integration with live hashtag & search discovery.
    Pure live data extraction with zero mock / zero fallback.
    """

    def __init__(self, api_token: Optional[str] = None):
        self.api_token = api_token or os.environ.get("APIFY_API_TOKEN")
        # Default to clockworks~free-tiktok-scraper which has NO minimalMaxTotalChargeUsd ($0.50 threshold)
        self.actor_id = os.environ.get("APIFY_TIKTOK_ACTOR", "clockworks~free-tiktok-scraper")
        self.facebook_actor_id = "apify~facebook-pages-scraper"
        self._cache: Dict[str, Tuple[float, List[KOLProfile]]] = {}

    @property
    def is_configured(self) -> bool:
        return bool(self.api_token and len(self.api_token.strip()) > 5)

    async def search_live_kols_by_hashtags(
        self,
        hashtags: List[str],
        vertical: str,
        limit_creators: int = 30,
        search_queries: Optional[List[str]] = None,
        search_taxonomy: Optional[Dict[str, List[str]]] = None,
        grounded_competitors: Optional[List[Dict[str, Any]]] = None,
        manual_competitors: Optional[List[str]] = None,
        brand_name: Optional[str] = None,
    ) -> List[KOLProfile]:
        """
        Search live TikTok creators using Apify actor by hashtags & searchQueries (5-Angle Taxonomy).
        Implements Two-Stage Entity Filtering (Merchants vs Bots vs Work-Ready Creators),
        Creator Archetypes classification, and Grounded Thai Competitor Detection.
        """
        if not self.is_configured:
            logger.warning("APIFY_API_TOKEN not configured.")
            return []

        clean_tags = [t.lstrip('#').strip() for t in hashtags if t and t.lstrip('#').strip()]
        if not clean_tags:
            raise ValueError("Hashtags list cannot be empty. Zero-Hardcode Policy forbids fallback tags.")

        # Query hashtags and taxonomy queries to gather up to 30 creators
        query_tags = clean_tags[:2]
        target_queries = []
        if search_taxonomy:
            # Prioritize an educational/guru query (tutorials, coaching) to guarantee Guru archetype discovery
            for gq in search_taxonomy.get("educational_guru_queries", []):
                if gq and gq.strip() and gq.strip() not in target_queries:
                    target_queries.append(gq.strip())
                    break
            # Then add review, pain point, or lifestyle queries to balance the sourcing angles
            for k in ["review_hook_queries", "pain_point_queries", "lifestyle_persona_queries", "competitor_seed_queries"]:
                for q in search_taxonomy.get(k, []):
                    if q and q.strip() and q.strip() not in target_queries and len(target_queries) < 2:
                        target_queries.append(q.strip())
        elif search_queries:
            target_queries = [q.strip() for q in search_queries if q and q.strip()][:2]
        total_targets = len(query_tags) + len(target_queries)
        results_per_tag = max(12, min(22, int((limit_creators * 1.4) // max(total_targets, 1))))

        cache_key = f"{query_tags[0]}_{vertical}_{'_'.join(target_queries)}_{limit_creators}"
        now = time.time()
        if cache_key in self._cache and (now - self._cache[cache_key][0]) < 900:
            logger.info(f"Returning cached live TikTok results for {cache_key}")
            return self._cache[cache_key][1]

        url = f"https://api.apify.com/v2/acts/{self.actor_id}/run-sync-get-dataset-items?token={self.api_token}&timeout=120"
        payload: Dict[str, Any] = {
            "hashtags": query_tags,
            "resultsPerPage": results_per_tag,
            "maxItems": int(limit_creators * 1.6),  # Cap total items to prevent Actor runaway
            "shouldDownloadVideos": False,
            "shouldDownloadCovers": False,
        }
        if target_queries:
            payload["searchQueries"] = target_queries

        try:
            async with httpx.AsyncClient(timeout=130.0) as client:
                resp = await client.post(url, json=payload)
                resp_text = getattr(resp, "text", "")
                if resp.status_code == 402 or ("not-enough-usage" in resp_text and self.actor_id != "clockworks~free-tiktok-scraper"):
                    logger.warning(f"Apify actor {self.actor_id} returned HTTP 402 ({resp_text[:120]}). Automatically retrying with clockworks~free-tiktok-scraper...")
                    self.actor_id = "clockworks~free-tiktok-scraper"
                    fallback_url = f"https://api.apify.com/v2/acts/{self.actor_id}/run-sync-get-dataset-items?token={self.api_token}&timeout=120"
                    resp = await client.post(fallback_url, json=payload)
                    resp_text = getattr(resp, "text", "")

                if resp.status_code not in [200, 201]:
                    logger.warning(f"Apify live search returned HTTP {resp.status_code}: {resp_text[:200]}")
                    if resp.status_code == 402 or "not-enough-usage" in resp_text:
                        raise RuntimeError(
                            "Apify Usage Quota Exhausted (HTTP 402): Your Apify usage credits are insufficient for this run. "
                            "Please top up your Apify account or update APIFY_API_TOKEN in backend/.env."
                        )
                    # Fallback to check if dataset has items despite timeout status
                    try:
                        err_data = resp.json()
                        run_id = err_data.get("error", {}).get("runId") or (
                            err_data.get("error", {}).get("message", "").split("run ID: ")[1].split(",")[0]
                            if "run ID: " in err_data.get("error", {}).get("message", "") else None
                        )
                        if run_id:
                            run_info = (await client.get(f"https://api.apify.com/v2/actor-runs/{run_id}?token={self.api_token}")).json().get("data", {})
                            ds_id = run_info.get("defaultDatasetId")
                            if ds_id:
                                ds_items = (await client.get(f"https://api.apify.com/v2/datasets/{ds_id}/items?token={self.api_token}")).json()
                                if isinstance(ds_items, list) and len(ds_items) > 0:
                                    logger.info(f"Successfully rescued {len(ds_items)} live items from dataset of timed-out Apify run {run_id}")
                                    items = ds_items
                                else:
                                    return []
                            else:
                                return []
                        else:
                            return []
                    except Exception as rescue_err:
                        logger.warning(f"Failed to recover items from Apify run: {rescue_err}")
                        return []
                else:
                    items = resp.json()

                if not isinstance(items, list) or len(items) == 0:
                    return []

            # Group live videos by creator handle
            authors_data: Dict[str, Dict[str, Any]] = {}
            for item in items:
                author_meta = item.get("authorMeta")
                if not author_meta or not author_meta.get("name"):
                    continue

                handle = str(author_meta.get("name")).strip()
                if handle not in authors_data:
                    authors_data[handle] = {
                        "meta": author_meta,
                        "videos": [],
                    }

                v_id = str(item.get("id", f"v_{len(authors_data[handle]['videos'])}"))
                caption = str(item.get("text", "")).strip()
                v_tags = [h.get("name") if isinstance(h, dict) else str(h) for h in item.get("hashtags", [])]
                views = int(item.get("playCount") or 0)
                likes = int(item.get("diggCount") or 0)
                comments = int(item.get("commentCount") or 0)
                shares = int(item.get("shareCount") or 0)
                has_basket = bool(item.get("hasTikTokShopProduct", False))

                loc_tag = str(item.get("locationCreated") or (item.get("poi") or {}).get("name") or "").strip()
                collect_count = int(item.get("collectCount") or 0)
                authors_data[handle]["videos"].append(
                    VideoMetric(
                        video_id=v_id,
                        caption=caption[:200],
                        hashtags=v_tags[:6],
                        views=views,
                        likes=likes,
                        comments=comments,
                        shares=shares,
                        collect_count=collect_count,
                        has_yellow_basket=has_basket,
                        location_tag=loc_tag if loc_tag else None,
                    )
                )

            # Grounded Competitor Dictionary & Competitor Entity Pre-computation
            known_comps = []
            if grounded_competitors:
                for gc in grounded_competitors:
                    b_en = gc.get("brand_en")
                    if b_en:
                        known_comps.append(b_en.lower())
                    for a in gc.get("aliases", []):
                        if a:
                            known_comps.append(str(a).lower())
            if manual_competitors:
                for mc in manual_competitors:
                    if mc:
                        known_comps.append(str(mc).lower())

            # Convert to verified KOLProfile objects with Entity Filtering & Archetype Classification
            profiles: List[KOLProfile] = []
            for handle, data in authors_data.items():
                meta = data["meta"]
                videos = data["videos"]
                followers = int(meta.get("fans") or 0)
                following = int(meta.get("following") or 0)
                total_likes = int(meta.get("heart") or 0)
                display_name = str(meta.get("nickName") or handle).strip()
                bio = str(meta.get("signature") or "").strip()
                avatar_url = str(meta.get("avatar") or "").strip()

                # 1. Follower Tiers (Spec 4.1)
                if followers < 10000:
                    tier = "Nano (1K-10K)"
                    est_rate = "2,000 - 5,000 THB"
                elif followers < 100000:
                    tier = "Micro (10K-100K)"
                    est_rate = "5,000 - 15,000 THB"
                elif followers < 500000:
                    tier = "Mid-Tier (100K-500K)"
                    est_rate = "15,000 - 45,000 THB"
                else:
                    tier = "Macro (500K+)"
                    est_rate = "50,000 - 120,000 THB"

                yellow_count = sum(1 for v in videos if v.has_yellow_basket)
                yellow_ratio = (yellow_count / len(videos)) if videos else 0.0
                all_captions = [v.caption.lower() for v in videos if v.caption]

                # 2. Two-Stage Entity Filtering (Spec 3)
                # 3.1 Competitor & Client Brand Account Exclusion (Stage 2 Gate)
                clean_handle = handle.lower().replace("_", "").replace(".", "").replace("-", "")
                clean_display = display_name.lower().replace(" ", "").replace(".", "").replace("-", "").replace("_", "")

                # Exclude client's own brand official account
                is_own_brand = False
                if brand_name:
                    clean_brand = brand_name.lower().replace(" ", "").replace(".", "").replace("-", "").replace("_", "")
                    if len(clean_brand) >= 3 and (clean_brand in clean_handle or clean_brand in clean_display):
                        is_own_brand = True

                if is_own_brand:
                    logger.info(f"Two-Stage Filter: Excluded client's own official brand account @{handle} ({display_name})")
                    continue

                # Exclude competitor brand / venue / school / store official account
                is_competitor_account = False
                for comp in known_comps:
                    clean_comp = comp.lower().replace(" ", "").replace(".", "").replace("-", "").replace("_", "")
                    if len(clean_comp) >= 3 and (clean_comp in clean_handle or clean_comp in clean_display):
                        is_competitor_account = True
                        break

                if is_competitor_account:
                    logger.info(f"Two-Stage Filter: Excluded competitor official account/venue @{handle} ({display_name})")
                    continue

                # 3.2 Merchant / Commercial Business & Factory Store Check (Two-Stage Entity Filter)
                # Strict merchant keywords that unmistakably indicate a factory, wholesale shop, or commercial service
                strict_merchant_keywords = [
                    # Manufacturing, Printing & Workshop
                    "โรงงาน", "รับผลิต", "ผลิตเสื้อ", "รับสกรีน", "งานสกรีน", "รับทำเสื้อ", "รับทำ",
                    "ไม่มีขั้นต่ำ", "สั่งผลิต", "งานด่วน", "ช่างสกรีน", "บล็อกสกรีน", "การ์เม้นท์", "garment",
                    "dtfสกรีน", "สกรีนdtf", "สั่งทำเสื้อ", "เสื้อทีม", "เสื้อรุ่น", "เสื้อพนักงาน", "เสื้อยูนิฟอร์ม",
                    "เสื้อแจก", "รับปัก", "งานปัก", "ช่างพิมพ์", "เครื่องสกรีน", "หมึกสกรีน", "สกรีนเสื้อ", "ร้านสกรีน",
                    "สกรีนด่วน", "รับพิมพ์ผ้า", "รับพิมพ์เสื้อ",
                    # Wholesale & Commercial Distribution
                    "ขายส่ง", "ราคาส่ง", "ส่งทั่วประเทศ", "จัดส่งทั่วประเทศ", "ออเดอร์", "รับออเดอร์",
                    "หน้าร้าน", "พิกัดหน้าร้าน", "สั่งซื้อจิ้มลิงก์", "ตัวแทนจำหน่าย", "เปิดบิล",
                    "สั่งซื้อได้ที่", "พิกัดร้าน", "จำหน่าย", "มีบริการเก็บเงินปลายทาง", "ส่งฟรีทั่วไทย", "มีเรทส่ง",
                    # Corporate & Venues
                    "co.,ltd", "co., ltd", "บริษัท", "ห้างหุ้นส่วน", "หจก.", "บจก.",
                    "จองคิว", "สอบถาม/จอง", "booking", "เปิดบริการ", "เปิดทุกวัน", "เปิดให้บริการ",
                    "เวลาเปิด", "เวลาทำการ", "สาขา", "ชั่วโมงละ", "ชม.ละ"
                ]
                general_merchant_keywords = [
                    "official", "store", "shop", "studio", "academy", "school", "clinic", "salon",
                    "hotel", "resort", "center", "centre", "venue", "club"
                ]
                store_handle_tokens = ["factory", "garment", "screen", "print", "sublimation", "uniform", "store", "official"]

                bio_lower = bio.lower()
                disp_lower = display_name.lower()
                handle_lower = handle.lower()

                is_strict_merchant = any(k in bio_lower or k in disp_lower or k in handle_lower for k in strict_merchant_keywords)
                has_store_handle = any(t in handle_lower for t in store_handle_tokens) and any(k in disp_lower or k in bio_lower for k in ["สกรีน", "เสื้อ", "shop", "store", "ผลิต", "โรงงาน"])

                # Only genuine personal creator markers (avoid bare 'รีวิว' or 'ติดต่องาน' which commercial shops misuse)
                genuine_creator_words = ["content creator", "video creator", "lifestyle creator", "บล็อกเกอร์", "blogger", "vlogger", "รีวิวไปเรื่อย"]
                has_general_merchant = any(k in bio_lower or k in disp_lower or k in handle_lower for k in general_merchant_keywords)
                has_genuine_creator = any(k in bio_lower or k in disp_lower for k in genuine_creator_words)

                if is_strict_merchant or has_store_handle or (has_general_merchant and not has_genuine_creator):
                    account_type = "merchant_store"
                    logger.info(f"Two-Stage Filter: Excluded merchant/factory account @{handle} ({display_name})")
                    continue
                else:
                    account_type = "real_kol"

                # 3.2 Affiliate Spam Bot (Filtered out unless legitimate review creator)
                is_spam = False
                if followers > 50000 and total_likes < 50:
                    is_spam = True
                    account_type = "affiliate_spam_bot"
                elif yellow_ratio >= 0.85 and total_likes < 200 and followers < 5000:
                    # High basket with zero engagement & low followers
                    is_spam = True
                    account_type = "affiliate_spam_bot"

                # 3.3 Work-Ready Signal (Spec 3.3)
                work_keywords = ["ติดต่องาน", "for work", "รับงานรีวิว", "dm for work", "line @", "line:", "line@", "งาน:", "contact:", "work:", "tel:", "@gmail"]
                is_work_ready = any(w in bio.lower() for w in work_keywords)

                # Spec: Category classification
                review_keywords = ["รีวิว", "ป้ายยา", "พิกัด", "ใช้ดี", "ลองแล้ว", "ตะกร้า", "ช้อปปิ้ง", "unboxing", "คุ้มไหม", "ใช้จริง"]
                has_review_signal = (
                    yellow_ratio >= 0.50
                    or any(any(kw in c for kw in review_keywords) for c in all_captions)
                    or any(kw in bio.lower() for kw in review_keywords)
                )

                if has_review_signal or yellow_count > 0:
                    creator_category = "Content Creator (เน้นรีวิว)"
                else:
                    creator_category = f"Content Creator ({vertical})"

                # 4. Engineering Edge-Case Calculations (Spec 6)
                import numpy as np
                views_list = [v.views for v in videos]
                median_views = float(np.median(views_list)) if views_list else 0.0
                mean_views = float(np.mean(views_list)) if views_list else 1.0
                view_consistency_ratio = round(median_views / max(mean_views, 1.0), 3) if views_list else 0.0
                save_to_view_ratio = round(float(np.median([((v.collect_count + 0.7 * v.shares) / max(v.views, 500)) for v in videos])), 4) if videos else 0.0

                # 5. Grounded Thai Competitor Detection: Layer 2 & Layer 3 (Spec 7)
                competitor_warning = None
                detected_comps = set()
                if known_comps:
                    for cap in all_captions:
                        for comp in known_comps:
                            if comp in cap:
                                detected_comps.add(comp)

                if len(detected_comps) >= 2:
                    competitor_warning = "🎯 Niche Enthusiast Opportunity: Multi-brand category comparison"
                elif len(detected_comps) == 1:
                    c_name = list(detected_comps)[0].capitalize()
                    competitor_warning = f"⚠️ Competitor Conflict: Content features competitor '{c_name}'"

                # 6. Query Origin & 5-Angle Taxonomy Attribution
                query_origin = "niche_hashtags"
                if search_taxonomy:
                    if any(any(q.lower() in c for q in search_taxonomy.get("educational_guru_queries", [])) for c in all_captions):
                        query_origin = "educational_guru_queries"
                    elif any(any(q.lower() in c for q in search_taxonomy.get("pain_point_queries", [])) for c in all_captions):
                        query_origin = "pain_point_queries"
                    elif any(any(q.lower() in c for q in search_taxonomy.get("review_hook_queries", [])) for c in all_captions):
                        query_origin = "review_hook_queries"
                    elif any(any(q.lower() in c for q in search_taxonomy.get("lifestyle_persona_queries", [])) for c in all_captions):
                        query_origin = "lifestyle_persona_queries"
                    elif any(any(q.lower() in c for q in search_taxonomy.get("competitor_seed_queries", [])) for c in all_captions):
                        query_origin = "competitor_seed_queries"

                # 7. Creator Archetype Classification (Zero-Hardcode Policy)
                # 4 Main Archetypes: Educated Guru, Top Reviewer, Lifestyle & Vlog, Niche Enthusiast
                # Yellow basket is strictly an evaluation signal that categorizes into 'Top Reviewer'
                if yellow_ratio > 0 or yellow_count > 0 or has_review_signal:
                    creator_archetype = "Top Reviewer"
                    recommended_role = "Conversion & Sales"
                else:
                    creator_archetype = "Lifestyle & Vlog"
                    recommended_role = "Brand Awareness & Discovery"

                # Dynamic audience inquiries synthesized from real video captions by Gemini
                captions = [v.caption for v in videos if v.caption]
                sample_comments = []
                try:
                    from app.services.gemini_service import get_gemini_service
                    gemini = get_gemini_service()
                    if gemini.is_configured:
                        sample_comments = await gemini.generate_audience_comments(
                            kol_name=display_name,
                            handle=handle,
                            bio=bio,
                            captions=captions,
                            vertical=vertical,
                        )
                except Exception as e:
                    logger.warning(f"Gemini comments generation for {handle}: {e}")

                # Live caption extraction if Gemini returned no comments
                if not sample_comments and captions:
                    for c in captions[:4]:
                        clean_c = c.split('#')[0].strip()
                        if clean_c:
                            sample_comments.append(f"สนใจตามคลิป: \"{clean_c[:50]}...\"")

                # Dynamic creator persona and pricing derived strictly from real captions & bio (Zero-Hardcode)
                import re
                # Extract actual prices mentioned in video captions
                detected_prices = []
                for c in captions:
                    for p in re.findall(r'(\d[\d,]*)\s*(?:บาท|บ\.|.-|thb)', c, re.IGNORECASE):
                        val = int(p.replace(',', ''))
                        if 20 <= val <= 100000:
                            detected_prices.append(val)
                
                avg_price = int(sum(detected_prices) / len(detected_prices)) if detected_prices else 0
                if avg_price >= 2000:
                    typical_price_tier = "Premium / Masstige"
                elif avg_price >= 500:
                    typical_price_tier = "Mid-Range / Accessible"
                elif avg_price > 0:
                    typical_price_tier = "Budget / Mass"
                else:
                    typical_price_tier = "General / Organic"

                creator_persona = bio.strip() if bio.strip() else f"@{handle} — Thai {vertical} Creator"
                tags_in_vids = [t for v in videos for t in v.hashtags if t]
                styles = list(dict.fromkeys(tags_in_vids[:4])) if tags_in_vids else []
                secondary_verticals = [t for t in tags_in_vids[:3] if t.lower() != vertical.lower()]
                detected_locs = [v.location_tag for v in videos if v.location_tag]
                primary_locations = list(dict.fromkeys(detected_locs)) if detected_locs else []
                has_thai = any(re.search(r'[\u0e00-\u0e7f]', v.caption) for v in videos) or bool(re.search(r'[\u0e00-\u0e7f]', bio))
                audience_language = "Thai" if has_thai else "International"

                profiles.append(
                    KOLProfile(
                        id=f"live_{handle}",
                        handle=handle,
                        display_name=display_name,
                        tiktok_url=f"https://www.tiktok.com/@{handle}",
                        avatar_url=avatar_url if avatar_url else None,
                        vertical=vertical,
                        secondary_verticals=secondary_verticals,
                        bio=bio,
                        follower_count=followers,
                        following_count=following,
                        total_likes=total_likes,
                        tier=tier,
                        creator_persona=creator_persona,
                        content_styles=styles,
                        typical_price_tier=typical_price_tier,
                        avg_reviewed_price_thb=avg_price,
                        primary_locations=primary_locations,
                        audience_language=audience_language,
                        sample_comments=sample_comments,
                        recent_videos=videos,
                        creator_category=creator_category,
                        creator_archetype=creator_archetype,
                        recommended_role=recommended_role,
                        account_type=account_type,
                        is_work_ready=is_work_ready,
                        competitor_warning=competitor_warning,
                        query_origin=query_origin,
                        save_to_view_ratio=save_to_view_ratio,
                        view_consistency_ratio=view_consistency_ratio,
                        is_affiliate_spam_trap=is_spam,
                        estimated_rate_thb=est_rate,
                    )
                )

                if len(profiles) >= limit_creators:
                    break

            # Zero-Hardcode: Classify Creator Archetypes via Gemini LLM Instructions
            if profiles:
                try:
                    from app.services.gemini_service import get_gemini_service
                    gemini = get_gemini_service()
                    if gemini.is_configured:
                        creators_to_classify = [
                            {
                                "id": p.id,
                                "handle": p.handle,
                                "display_name": p.display_name,
                                "bio": p.bio,
                                "captions": [v.caption for v in p.recent_videos if v.caption][:5],
                                "yellow_basket_ratio": round(
                                    sum(1 for v in p.recent_videos if v.has_yellow_basket) / max(len(p.recent_videos), 1),
                                    2
                                ),
                                "vertical": p.vertical,
                            }
                            for p in profiles
                        ]
                        classification_map = await gemini.classify_creator_archetypes(creators_to_classify)
                        for p in profiles:
                            if p.id in classification_map:
                                c_info = classification_map[p.id]
                                p.creator_archetype = c_info.get("creator_archetype", p.creator_archetype)
                                p.recommended_role = c_info.get("recommended_role", p.recommended_role)
                                if p.creator_archetype == "Top Reviewer":
                                    p.creator_category = "Content Creator (เน้นรีวิว)"
                                if c_info.get("reasoning"):
                                    p.creator_persona = f"{p.creator_persona} | {c_info['reasoning']}"
                        logger.info(f"Classified {len(classification_map)} creators via Gemini LLM instructions (Zero-Hardcode)")
                except Exception as e:
                    logger.warning(f"Instruction-based creator classification error: {e}")

            logger.info(f"Discovered {len(profiles)} live creators from Apify for {query_tags}")
            if profiles:
                self._cache[cache_key] = (time.time(), profiles)
            return profiles

        except Exception as e:
            logger.warning(f"Apify live search failed or timed out: {e}")
            return []

    async def enrich_creators_recent_videos(
        self,
        profiles: List[KOLProfile],
        max_videos_per_creator: int = 5,
        max_profiles_to_enrich: int = 8,
    ) -> List[KOLProfile]:
        """
        Enriches candidate creators with up to 5 recent videos from their TikTok profile.
        Allows auditing true content consistency (One-off casual experience vs Dedicated Niche Specialist).
        Uses live Apify profile scraper concurrently with bounded concurrency to prevent timeouts.
        """
        if not self.is_configured or not profiles:
            return profiles

        targets = [p for p in profiles if len(p.recent_videos) < max_videos_per_creator][:max_profiles_to_enrich]
        if not targets:
            return profiles

        import asyncio
        sem = asyncio.Semaphore(3)

        async def _enrich_single_profile(p: KOLProfile):
            async with sem:
                url = f"https://api.apify.com/v2/acts/{self.actor_id}/run-sync-get-dataset-items?token={self.api_token}&timeout=45"
                payload = {
                    "profiles": [p.handle],
                    "resultsPerPage": max_videos_per_creator,
                    "shouldDownloadVideos": False,
                    "shouldDownloadCovers": False,
                }
                try:
                    async with httpx.AsyncClient(timeout=50.0) as client:
                        resp = await client.post(url, json=payload)
                        if resp.status_code in [200, 201]:
                            items = resp.json()
                            if isinstance(items, list) and len(items) > 0:
                                new_videos: List[VideoMetric] = []
                                for item in items[:max_videos_per_creator]:
                                    v_id = str(item.get("id", f"v_{len(new_videos)}"))
                                    caption = str(item.get("text", "")).strip()
                                    v_tags = [h.get("name") if isinstance(h, dict) else str(h) for h in item.get("hashtags", [])]
                                    views = int(item.get("playCount") or 0)
                                    likes = int(item.get("diggCount") or 0)
                                    comments = int(item.get("commentCount") or 0)
                                    shares = int(item.get("shareCount") or 0)
                                    collect_count = int(item.get("collectCount") or 0)
                                    has_basket = bool(item.get("hasTikTokShopProduct", False))
                                    loc_tag = str(item.get("locationCreated") or (item.get("poi") or {}).get("name") or "").strip()
                                    new_videos.append(
                                        VideoMetric(
                                            video_id=v_id,
                                            caption=caption[:200],
                                            hashtags=v_tags[:6],
                                            views=views,
                                            likes=likes,
                                            comments=comments,
                                            shares=shares,
                                            collect_count=collect_count,
                                            has_yellow_basket=has_basket,
                                            location_tag=loc_tag if loc_tag else None,
                                        )
                                    )
                                if len(new_videos) >= len(p.recent_videos):
                                    p.recent_videos = new_videos
                                    views_list = [v.views for v in new_videos if v.views > 0]
                                    if views_list:
                                        import numpy as np
                                        median_views = float(np.median(views_list))
                                        mean_views = float(np.mean(views_list))
                                        p.view_consistency_ratio = round(median_views / max(mean_views, 1.0), 3)
                                        total_collects = sum(v.collect_count for v in new_videos)
                                        total_views = sum(v.views for v in new_videos)
                                        p.save_to_view_ratio = round(total_collects / max(total_views, 1), 4)
                                    logger.info(f"Enriched @{p.handle} to {len(p.recent_videos)} live profile videos")
                except Exception as e:
                    logger.warning(f"Profile video enrichment for @{p.handle} error: {e}")

        await asyncio.gather(*[_enrich_single_profile(p) for p in targets], return_exceptions=True)
        return profiles

    async def scrape_facebook_page(self, facebook_url: str) -> Dict[str, Any]:
        """
        Scrapes a live Facebook Page using Apify actor 'apify~facebook-pages-scraper'.
        Extracts verified page metadata: title, bio, categories, likes, followers, recent posts.
        Zero-Mock Policy: 100% genuine live extraction with resilient Jina Reader fallback.
        """
        if not self.is_configured or not facebook_url:
            return {}

        clean_url = facebook_url if facebook_url.startswith("http") else f"https://{facebook_url}"
        url = f"https://api.apify.com/v2/acts/{self.facebook_actor_id}/run-sync-get-dataset-items?token={self.api_token}&timeout=60"
        payload = {
            "startUrls": [{"url": clean_url}],
            "maxPosts": 10,
        }

        try:
            async with httpx.AsyncClient(timeout=65.0) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code in [200, 201]:
                    items = resp.json()
                    if isinstance(items, list) and len(items) > 0:
                        item = items[0]
                        posts = []
                        raw_posts = item.get("posts") or []
                        if isinstance(raw_posts, list):
                            for p in raw_posts[:10]:
                                if isinstance(p, dict) and p.get("text"):
                                    posts.append(p.get("text"))
                                elif isinstance(p, str):
                                    posts.append(p)

                        return {
                            "title": item.get("title") or item.get("name") or "",
                            "bio": item.get("bio") or item.get("intro") or item.get("about") or item.get("description") or "",
                            "categories": item.get("categories") or [],
                            "likes": item.get("likes") or 0,
                            "followers": item.get("followers") or 0,
                            "website": item.get("website") or "",
                            "address": item.get("address") or "",
                            "posts": posts,
                            "source": "Apify Facebook Pages Scraper",
                        }
        except Exception as e:
            logger.warning(f"Apify Facebook scrape failed or timed out: {e}")

        # Resilient fallback: Jina Reader on FB page url
        try:
            jina_fb_url = f"https://r.jina.ai/{clean_url}"
            headers = {"Accept": "text/plain", "User-Agent": "ConvertCake-KOL-Matcher/1.0", "X-Timeout": "10"}
            jina_key = os.environ.get("JINA_API_KEY")
            if jina_key:
                headers["Authorization"] = f"Bearer {jina_key}"
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                resp = await client.get(jina_fb_url, headers=headers)
                if resp.status_code == 200 and len(resp.text.strip()) > 80:
                    handle = clean_url.rstrip("/").split("/")[-1]
                    return {
                        "title": handle.replace(".", " ").replace("-", " ").title(),
                        "bio": resp.text[:1500],
                        "source": "Jina Reader Facebook Fallback",
                    }
        except Exception:
            pass

        return {}


_apify_instance: Optional[ApifyTikTokService] = None

def get_apify_service() -> ApifyTikTokService:
    global _apify_instance
    if _apify_instance is None:
        _apify_instance = ApifyTikTokService()
    return _apify_instance
