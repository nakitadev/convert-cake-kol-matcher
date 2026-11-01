"""
Apify integration (live data only).

- TikTok search via `clockworks~tiktok-scraper` locked to `proxyCountryCode: "TH"` (Spec 3.2 #4).
  KOL and KOC query sets run as separate actor runs so every clip carries a reliable
  `KOL_QUERY` / `KOC_QUERY` origin tag.
- Batch profile enrichment (latest clips per creator) in ONE actor run.
- Tier-2 comment scraping for Top-K creators via `clockworks~tiktok-comments-scraper`.
- Facebook page info + recent posts + real customer comments (Spec 2.1).
"""
import os
import time
import asyncio
import logging
from typing import Optional, Dict, Any, List, Tuple

import httpx

from app.models import VideoMetric
from app.services.scraper_cache import (
    get_scraper_cache,
    TTL_FACEBOOK,
    TTL_TIKTOK_SEARCH,
    TTL_TIKTOK_PROFILE,
    TTL_TIKTOK_COMMENTS,
)

logger = logging.getLogger(__name__)

APIFY_BASE = "https://api.apify.com/v2"
FREE_TIKTOK_ACTOR = "clockworks~free-tiktok-scraper"


class ApifyQuotaError(RuntimeError):
    pass


def item_to_video(item: Dict[str, Any], origin: Optional[str] = None, query: Optional[str] = None) -> VideoMetric:
    tags = []
    for h in item.get("hashtags") or []:
        name = h.get("name") if isinstance(h, dict) else str(h)
        if name:
            tags.append(str(name).lstrip("#").strip())
    return VideoMetric(
        video_id=str(item.get("id") or ""),
        url=str(item.get("webVideoUrl") or ""),
        caption=str(item.get("text") or "").strip()[:500],
        hashtags=[t for t in tags if t][:15],
        views=int(item.get("playCount") or 0),
        likes=int(item.get("diggCount") or 0),
        comments=int(item.get("commentCount") or 0),
        shares=int(item.get("shareCount") or 0),
        collect_count=int(item.get("collectCount") or 0),
        has_yellow_basket=bool(item.get("hasTikTokShopProduct") or item.get("isECVideo") or item.get("productList")),
        query_origin=origin,
        search_query=query or item.get("searchQuery"),
    )


class ApifyTikTokService:
    def __init__(self, api_token: Optional[str] = None):
        self.api_token = api_token or os.environ.get("APIFY_API_TOKEN")
        self.actor_id = os.environ.get("APIFY_TIKTOK_ACTOR", "clockworks~tiktok-scraper")
        self.comments_actor_id = os.environ.get("APIFY_TIKTOK_COMMENTS_ACTOR", "clockworks~tiktok-comments-scraper")
        self.fb_pages_actor = "apify~facebook-pages-scraper"
        self.fb_posts_actor = "apify~facebook-posts-scraper"
        self.fb_comments_actor = "apify~facebook-comments-scraper"
        self._cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}

    @property
    def is_configured(self) -> bool:
        return bool(self.api_token and len(self.api_token.strip()) > 5)

    # ------------------------------------------------------------------
    async def _run_actor(self, actor: str, payload: Dict[str, Any], timeout_s: int = 90) -> List[Dict[str, Any]]:
        if not self.is_configured:
            raise RuntimeError("APIFY_API_TOKEN is not configured.")
        url = f"{APIFY_BASE}/acts/{actor}/run-sync-get-dataset-items?token={self.api_token}&timeout={timeout_s}"
        async with httpx.AsyncClient(timeout=timeout_s + 10) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code in (200, 201):
                data = resp.json()
                return data if isinstance(data, list) else []
            text = resp.text[:300]
            if resp.status_code == 402 or "not-enough-usage" in text:
                raise ApifyQuotaError(f"Apify Usage Quota Exhausted (HTTP 402) on {actor}: {text}")
            # Auto-recovery: sync call timed out but the run may have produced a dataset.
            try:
                err = resp.json().get("error", {})
                msg = err.get("message", "")
                run_id = err.get("runId") or (msg.split("run ID: ")[1].split(",")[0].strip() if "run ID: " in msg else None)
                if run_id:
                    run = (await client.get(f"{APIFY_BASE}/actor-runs/{run_id}?token={self.api_token}")).json().get("data", {})
                    ds = run.get("defaultDatasetId")
                    if ds:
                        items = (await client.get(f"{APIFY_BASE}/datasets/{ds}/items?token={self.api_token}")).json()
                        if isinstance(items, list) and items:
                            logger.info(f"Recovered {len(items)} items from timed-out run {run_id}")
                            return items
            except Exception as rescue_err:
                logger.warning(f"Apify dataset recovery failed: {rescue_err}")
            raise RuntimeError(f"Apify actor {actor} returned HTTP {resp.status_code}: {text}")

    async def _run_tiktok(self, payload: Dict[str, Any], timeout_s: int = 90) -> List[Dict[str, Any]]:
        try:
            return await self._run_actor(self.actor_id, payload, timeout_s)
        except ApifyQuotaError:
            if self.actor_id == FREE_TIKTOK_ACTOR:
                raise
            logger.warning(f"{self.actor_id} quota error — retrying with {FREE_TIKTOK_ACTOR}")
            self.actor_id = FREE_TIKTOK_ACTOR
            return await self._run_actor(self.actor_id, payload, timeout_s)

    # ------------------------------------------------------------------
    # Stage 2 — discovery
    # ------------------------------------------------------------------
    async def search_side(self, queries: List[str], origin: str, results_per_query: int) -> List[Dict[str, Any]]:
        if not queries:
            return []
        payload = {
            "searchQueries": queries,
            "resultsPerPage": results_per_query,
            "maxItems": results_per_query * len(queries),
            "proxyCountryCode": "TH",
            "shouldDownloadVideos": False,
            "shouldDownloadCovers": False,
            "shouldDownloadSubtitles": False,
        }
        items = await self._run_tiktok(payload, timeout_s=60)
        for it in items:
            it["_origin"] = origin
        return items

    async def discover_batch(self, queries: List[str], results_per_query: int = 8) -> Dict[str, Any]:
        """Run all natural search queries in a SINGLE Apify actor job (Spec 6.1) with SQLite + in-memory caching."""
        if not queries:
            return {"items": [], "errors": []}
        clean_queries = list(dict.fromkeys([q.strip() for q in queries if q.strip()]))
        cache = get_scraper_cache()
        sqlite_key = cache.hash_key("tiktok_search", sorted(clean_queries), results_per_query)
        cached_sqlite = cache.get(sqlite_key)
        if cached_sqlite and isinstance(cached_sqlite, dict):
            logger.info("ScraperCache HIT for TikTok search (%d queries)", len(clean_queries))
            return cached_sqlite

        cache_key = f"batch_{'_'.join(sorted(clean_queries))}_{results_per_query}"
        now = time.time()
        if cache_key in self._cache and (now - self._cache[cache_key][0]) < 900:
            logger.info("Returning in-memory cached live TikTok discovery batch results")
            return self._cache[cache_key][1]

        payload = {
            "searchQueries": clean_queries,
            "resultsPerPage": results_per_query,
            "maxItems": results_per_query * len(clean_queries),
            "proxyCountryCode": "TH",
            "shouldDownloadVideos": False,
            "shouldDownloadCovers": False,
            "shouldDownloadSubtitles": False,
        }
        items = await self._run_tiktok(payload, timeout_s=90)
        for it in items:
            if "_origin" not in it:
                it["_origin"] = "NATURAL_QUERY"
        result = {"items": items, "errors": []}
        if items:
            self._cache[cache_key] = (now, result)
            cache.set(
                sqlite_key,
                result,
                cache_type="tiktok_search",
                ttl_seconds=TTL_TIKTOK_SEARCH,
                url_or_query=", ".join(clean_queries)[:400],
            )
        return result

    async def discover(self, kol_queries: List[str], koc_queries: List[str], results_per_query: int = 8) -> Dict[str, Any]:
        """Run queries in a single Apify job (Spec 6.1) with backward compatibility for split lists."""
        all_queries = list(dict.fromkeys(kol_queries + koc_queries))
        return await self.discover_batch(all_queries, results_per_query)

    async def scrape_profiles(self, handles: List[str], per_profile: int = 4) -> Dict[str, List[Dict[str, Any]]]:
        """Fetch the latest clips for candidate creators in a single actor run (backed by SQLite cache)."""
        if not handles:
            return {}
        target_handles = [h.strip().lower().lstrip("@") for h in handles[:8] if h.strip()]
        cache = get_scraper_cache()
        sqlite_key = cache.hash_key("tiktok_profiles", sorted(target_handles), per_profile)
        cached_sqlite = cache.get(sqlite_key)
        if cached_sqlite and isinstance(cached_sqlite, dict):
            logger.info("ScraperCache HIT for TikTok profiles (%d handles)", len(target_handles))
            return cached_sqlite

        payload = {
            "profiles": target_handles,
            "resultsPerPage": per_profile,
            "profileScrapeSections": ["videos"],
            "profileSorting": "latest",
            "proxyCountryCode": "TH",
            "shouldDownloadVideos": False,
            "shouldDownloadCovers": False,
        }
        try:
            items = await self._run_tiktok(payload, timeout_s=120)
        except Exception as e:
            logger.warning("scrape_profiles timed out or failed: %s", e)
            items = []
        out: Dict[str, List[Dict[str, Any]]] = {}
        for it in items:
            name = str((it.get("authorMeta") or {}).get("name") or "").strip().lower()
            if name:
                out.setdefault(name, []).append(it)

        if out:
            cache.set(
                sqlite_key,
                out,
                cache_type="tiktok_profiles",
                ttl_seconds=TTL_TIKTOK_PROFILE,
                url_or_query=", ".join(target_handles)[:400],
            )
        return out

    # ------------------------------------------------------------------
    # Stage 3 — Tier-2 comment analysis
    # ------------------------------------------------------------------
    async def scrape_comments(self, video_urls: List[str], per_post: int = 25) -> Dict[str, List[str]]:
        urls = [u for u in video_urls[:4] if u]
        if not urls:
            return {}
        cache = get_scraper_cache()
        sqlite_key = cache.hash_key("tiktok_comments", sorted(urls), per_post)
        cached_sqlite = cache.get(sqlite_key)
        if cached_sqlite and isinstance(cached_sqlite, dict):
            logger.info("ScraperCache HIT for TikTok comments (%d urls)", len(urls))
            return cached_sqlite

        payload = {"postURLs": urls, "commentsPerPost": per_post, "maxRepliesPerComment": 0}
        items = await self._run_actor(self.comments_actor_id, payload, timeout_s=45)
        out: Dict[str, List[str]] = {}
        for it in items:
            text = str(it.get("text") or "").strip()
            src = str(it.get("videoWebUrl") or it.get("postUrl") or it.get("submittedVideoUrl") or "")
            if text and src:
                out.setdefault(src, []).append(text)
        if out:
            cache.set(
                sqlite_key,
                out,
                cache_type="tiktok_comments",
                ttl_seconds=TTL_TIKTOK_COMMENTS,
                url_or_query=", ".join(urls)[:400],
            )
        return out

    # ------------------------------------------------------------------
    # Stage 1 — Facebook page, posts & real customer comments
    # ------------------------------------------------------------------
    async def scrape_facebook_page(self, facebook_url: str) -> Dict[str, Any]:
        clean = facebook_url if facebook_url.startswith("http") else f"https://{facebook_url}"
        cache = get_scraper_cache()
        sqlite_key = cache.hash_key("facebook", clean)
        cached_sqlite = cache.get(sqlite_key)
        if cached_sqlite and isinstance(cached_sqlite, dict):
            logger.info("ScraperCache HIT for Facebook page: %s", clean)
            return cached_sqlite

        page_res, posts_res = await asyncio.gather(
            self._run_actor(self.fb_pages_actor, {"startUrls": [{"url": clean}]}, timeout_s=90),
            self._run_actor(self.fb_posts_actor, {"startUrls": [{"url": clean}], "resultsLimit": 10}, timeout_s=90),
            return_exceptions=True,
        )
        result: Dict[str, Any] = {"source": "Apify Facebook scrapers", "posts": [], "comments": []}
        if isinstance(page_res, list) and page_res:
            p = page_res[0]
            result.update({
                "title": p.get("title") or p.get("name") or "",
                "bio": p.get("intro") or p.get("about") or p.get("description") or "",
                "categories": p.get("categories") or [],
                "followers": p.get("followers") or 0,
            })
        post_urls = []
        if isinstance(posts_res, list):
            for post in posts_res:
                if post.get("text"):
                    result["posts"].append(str(post["text"]))
                if post.get("url") or post.get("postUrl"):
                    post_urls.append(post.get("url") or post.get("postUrl"))
        if post_urls:
            try:
                comments = await self._run_actor(
                    self.fb_comments_actor,
                    {"startUrls": [{"url": u} for u in post_urls[:5]], "resultsLimit": 60},
                    timeout_s=90,
                )
                result["comments"] = [str(c["text"]) for c in comments if c.get("text")]
            except Exception as e:
                logger.warning(f"Facebook comments scrape failed: {e}")
        if not result.get("title") and not result["posts"]:
            errs = [str(r) for r in (page_res, posts_res) if isinstance(r, Exception)]
            raise RuntimeError("Facebook scrape returned no data" + (f": {' | '.join(errs)}" if errs else ""))

        cache.set(
            sqlite_key,
            result,
            cache_type="facebook_page",
            ttl_seconds=TTL_FACEBOOK,
            url_or_query=clean,
        )
        return result


_apify_instance: Optional[ApifyTikTokService] = None


def get_apify_service() -> ApifyTikTokService:
    global _apify_instance
    if _apify_instance is None:
        _apify_instance = ApifyTikTokService()
    return _apify_instance
