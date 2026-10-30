"""
SQLite Scraper Cache Layer for Convert Cake KOL Matcher.

Caches raw and processed payloads from external network scrapers:
- Jina Reader (website scraping / clean markdown)
- Apify Facebook Pages Scraper
- Apify TikTok Scraper (discovery batches)
- Apify TikTok Profile Clips (multi-clip enrichment)
- Apify TikTok Comments

Provides real-time instant replay for repeated tests, dev cycles, and client demos,
while maintaining live fallback and configurable TTLs.
"""
import os
import time
import json
import sqlite3
import hashlib
import logging
from pathlib import Path
from typing import Any, Dict, Optional, List, Union

logger = logging.getLogger(__name__)

DEFAULT_CACHE_DIR = Path(__file__).resolve().parent.parent / "cache"
DEFAULT_DB_PATH = DEFAULT_CACHE_DIR / "scraper_cache.sqlite"

# Default TTLs (seconds)
TTL_WEBSITE = int(os.environ.get("CACHE_TTL_WEBSITE", 86400 * 3))     # 3 days for websites
TTL_FACEBOOK = int(os.environ.get("CACHE_TTL_FACEBOOK", 86400 * 2))    # 2 days for FB pages
TTL_TIKTOK_SEARCH = int(os.environ.get("CACHE_TTL_TIKTOK_SEARCH", 3600 * 12))  # 12 hours for search
TTL_TIKTOK_PROFILE = int(os.environ.get("CACHE_TTL_TIKTOK_PROFILE", 86400))    # 24 hours for profiles
TTL_TIKTOK_COMMENTS = int(os.environ.get("CACHE_TTL_TIKTOK_COMMENTS", 86400 * 2)) # 2 days for comments


class ScraperCache:
    def __init__(self, db_path: Optional[Union[str, Path]] = None):
        self.db_path = Path(db_path or os.environ.get("SCRAPER_CACHE_DB", str(DEFAULT_DB_PATH)))
        self.enabled = os.environ.get("SCRAPER_CACHE_ENABLED", "true").lower() in ("1", "true", "yes")
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA busy_timeout = 5000;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        return conn

    def _init_db(self):
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            with self._get_connection() as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS scraper_cache (
                        cache_key TEXT PRIMARY KEY,
                        cache_type TEXT NOT NULL,
                        url_or_query TEXT,
                        payload_json TEXT NOT NULL,
                        created_at REAL NOT NULL,
                        ttl_seconds INTEGER NOT NULL
                    );
                    """
                )
                conn.execute("CREATE INDEX IF NOT EXISTS idx_cache_type ON scraper_cache(cache_type);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON scraper_cache(created_at);")
                conn.commit()
        except Exception as e:
            logger.warning("Failed to initialize SQLite scraper cache at %s: %s", self.db_path, e)

    @staticmethod
    def hash_key(*parts: Any) -> str:
        """Generate a deterministic SHA256 hex string from cache components."""
        canonical = "||".join(str(p).strip().lower() for p in parts if p is not None)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def get(self, key: str, ignore_ttl: bool = False) -> Optional[Any]:
        if not self.enabled:
            return None
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT payload_json, created_at, ttl_seconds FROM scraper_cache WHERE cache_key = ?",
                    (key,),
                )
                row = cursor.fetchone()
                if not row:
                    return None

                payload_json, created_at, ttl_seconds = row
                now = time.time()
                if not ignore_ttl and (now - created_at) > ttl_seconds:
                    # Expired — cleanup lazily
                    conn.execute("DELETE FROM scraper_cache WHERE cache_key = ?", (key,))
                    conn.commit()
                    return None

                return json.loads(payload_json)
        except Exception as e:
            logger.warning("Error reading from scraper cache: %s", e)
            return None

    def set(
        self,
        key: str,
        data: Any,
        cache_type: Optional[Any] = None,
        ttl_seconds: Optional[int] = None,
        url_or_query: str = "",
        ttl: Optional[int] = None,
        **kwargs: Any,
    ) -> bool:
        if not self.enabled:
            return False
        try:
            effective_ttl = ttl if ttl is not None else (ttl_seconds if ttl_seconds is not None else 86400)
            if isinstance(data, str) and cache_type is not None and not isinstance(cache_type, str):
                actual_type = data
                actual_data = cache_type
            else:
                actual_data = data
                actual_type = str(cache_type or kwargs.get("cache_type") or "default")

            if actual_data is None:
                return False

            payload_json = json.dumps(actual_data, ensure_ascii=False)
            now = time.time()
            with self._get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO scraper_cache (cache_key, cache_type, url_or_query, payload_json, created_at, ttl_seconds)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(cache_key) DO UPDATE SET
                        payload_json = excluded.payload_json,
                        created_at = excluded.created_at,
                        ttl_seconds = excluded.ttl_seconds,
                        url_or_query = excluded.url_or_query;
                    """,
                    (key, actual_type, str(url_or_query)[:500], payload_json, now, effective_ttl),
                )
                conn.commit()
            return True
        except Exception as e:
            logger.warning("Error writing to scraper cache (%s): %s", key, e)
            return False

    def delete(self, key: str) -> bool:
        try:
            with self._get_connection() as conn:
                conn.execute("DELETE FROM scraper_cache WHERE cache_key = ?", (key,))
                conn.commit()
            return True
        except Exception as e:
            logger.warning("Error deleting scraper cache key %s: %s", key, e)
            return False

    def clear(self, cache_type: Optional[str] = None) -> int:
        try:
            with self._get_connection() as conn:
                if cache_type:
                    cursor = conn.execute("DELETE FROM scraper_cache WHERE cache_type = ?", (cache_type,))
                else:
                    cursor = conn.execute("DELETE FROM scraper_cache")
                conn.commit()
                return cursor.rowcount
        except Exception as e:
            logger.warning("Error clearing scraper cache: %s", e)
            return 0

    def prune_expired(self) -> int:
        try:
            now = time.time()
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "DELETE FROM scraper_cache WHERE (? - created_at) > ttl_seconds", (now,)
                )
                conn.commit()
                return cursor.rowcount
        except Exception as e:
            logger.warning("Error pruning scraper cache: %s", e)
            return 0

    def stats(self) -> Dict[str, Any]:
        if not self.db_path.exists():
            return {"enabled": self.enabled, "total_entries": 0, "active_entries": 0, "expired_entries": 0, "db_size_kb": 0, "by_type": {}}
        try:
            size_kb = round(self.db_path.stat().st_size / 1024, 2)
            now = time.time()
            with self._get_connection() as conn:
                total = conn.execute("SELECT COUNT(*) FROM scraper_cache").fetchone()[0]
                active = conn.execute(
                    "SELECT COUNT(*) FROM scraper_cache WHERE (? - created_at) <= ttl_seconds", (now,)
                ).fetchone()[0]
                rows = conn.execute(
                    "SELECT cache_type, COUNT(*) FROM scraper_cache GROUP BY cache_type"
                ).fetchall()
                by_type = {r[0]: r[1] for r in rows}
            return {
                "enabled": self.enabled,
                "total_entries": total,
                "active_entries": active,
                "expired_entries": max(0, total - active),
                "db_size_kb": size_kb,
                "by_type": by_type,
            }
        except Exception as e:
            return {"enabled": self.enabled, "error": str(e)}


_scraper_cache_instance: Optional[ScraperCache] = None


def get_scraper_cache() -> ScraperCache:
    global _scraper_cache_instance
    if _scraper_cache_instance is None:
        _scraper_cache_instance = ScraperCache()
    return _scraper_cache_instance
