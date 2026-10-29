import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from app.models import BrandAnalyzeRequest, BrandDNA, MatchResponse

logger = logging.getLogger(__name__)

CACHE_FILE_PATH = Path(__file__).resolve().parent.parent / "cache" / "demo_store.json"


def _normalize_string(val: Optional[str]) -> str:
    if not val:
        return ""
    # Remove http/https, www, trailing slashes, and non-alphanumeric Thai/English chars
    cleaned = re.sub(r"https?://(www\.)?", "", val.lower().strip())
    cleaned = re.sub(r"[^\w\u0E00-\u0E7F]+", "", cleaned)
    return cleaned


class DemoCacheService:
    def __init__(self, cache_path: Path = CACHE_FILE_PATH):
        self.cache_path = cache_path
        self._data: Dict[str, Any] = {"presets": [], "brands": {}}
        self._load()

    def _load(self):
        if self.cache_path.exists():
            try:
                content = self.cache_path.read_text(encoding="utf-8")
                self._data = json.loads(content)
                logger.info(
                    "DemoCache loaded %d presets and %d cached brands from %s",
                    len(self._data.get("presets", [])),
                    len(self._data.get("brands", {})),
                    self.cache_path.name,
                )
            except Exception as e:
                logger.warning("Failed to load demo cache: %s", e)
                self._data = {"presets": [], "brands": {}}
        else:
            self._data = {"presets": [], "brands": {}}

    def _save(self):
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            self.cache_path.write_text(
                json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception as e:
            logger.warning("Failed to persist demo cache: %s", e)

    def find_brand_key(
        self,
        brand_name: Optional[str] = None,
        website_url: Optional[str] = None,
        facebook_url: Optional[str] = None,
    ) -> Optional[str]:
        candidates = [
            _normalize_string(brand_name),
            _normalize_string(website_url),
            _normalize_string(facebook_url),
        ]
        candidates = [c for c in candidates if c]
        if not candidates:
            return None

        brands = self._data.get("brands", {})

        # 1. Exact or substring match in brand key or alias
        for key, entry in brands.items():
            norm_key = _normalize_string(key)
            aliases = entry.get("aliases", [])
            norm_aliases = [_normalize_string(a) for a in aliases]

            for cand in candidates:
                if (
                    cand == norm_key
                    or norm_key in cand
                    or (len(cand) >= 4 and cand in norm_key)
                ):
                    return key
                for a in norm_aliases:
                    if not a:
                        continue
                    if cand == a or a in cand or (len(cand) >= 4 and cand in a):
                        return key

        return None

    def get_presets(self) -> List[Dict[str, Any]]:
        return self._data.get("presets", [])

    def get_cached_brand_dna(
        self,
        brand_name: Optional[str] = None,
        website_url: Optional[str] = None,
        facebook_url: Optional[str] = None,
        force_refresh: bool = False,
    ) -> Optional[BrandDNA]:
        if force_refresh:
            return None
        key = self.find_brand_key(brand_name, website_url, facebook_url)
        if not key:
            return None
        entry = self._data.get("brands", {}).get(key, {})
        raw_dna = entry.get("brand_dna")
        if raw_dna:
            try:
                dna = BrandDNA.model_validate(raw_dna)
                logger.info(
                    "⚡ [DemoCache HIT]: Brand DNA for '%s' (0 Gemini tokens consumed)",
                    dna.brand_name,
                )
                return dna
            except Exception as e:
                logger.warning("Corrupted cached Brand DNA for '%s': %s", key, e)
        return None

    def get_cached_match_response(
        self,
        brand_name: Optional[str] = None,
        website_url: Optional[str] = None,
        facebook_url: Optional[str] = None,
        top_k: int = 10,
        force_refresh: bool = False,
    ) -> Optional[MatchResponse]:
        if force_refresh:
            return None
        key = self.find_brand_key(brand_name, website_url, facebook_url)
        if not key:
            return None
        entry = self._data.get("brands", {}).get(key, {})
        raw_match = entry.get("match_response")
        if raw_match:
            try:
                resp = MatchResponse.model_validate(raw_match)
                # Slice by top_k if needed
                if len(resp.ranked_kols) > top_k:
                    resp.ranked_kols = resp.ranked_kols[:top_k]
                logger.info(
                    "⚡ [DemoCache HIT]: MatchResponse for '%s' (0 tokens, 0 Apify credits, <0.1s)",
                    resp.brand_dna.brand_name,
                )
                return resp
            except Exception as e:
                logger.warning("Corrupted cached MatchResponse for '%s': %s", key, e)
        return None

    def save_brand_dna(
        self,
        brand_name: Optional[str],
        website_url: Optional[str],
        facebook_url: Optional[str],
        brand_dna: BrandDNA,
    ):
        key = (
            self.find_brand_key(brand_name, website_url, facebook_url)
            or _normalize_string(brand_name)
            or _normalize_string(website_url)
        )
        if not key:
            return
        if key not in self._data.get("brands", {}):
            self._data.setdefault("brands", {})[key] = {
                "aliases": [
                    a
                    for a in [brand_name, website_url, facebook_url, brand_dna.brand_name]
                    if a
                ],
                "brand_dna": brand_dna.model_dump(),
            }
        else:
            self._data["brands"][key]["brand_dna"] = brand_dna.model_dump()
        self._save()

    def save_match_response(
        self,
        brand_name: Optional[str],
        website_url: Optional[str],
        facebook_url: Optional[str],
        response: MatchResponse,
    ):
        key = (
            self.find_brand_key(brand_name, website_url, facebook_url)
            or _normalize_string(brand_name)
            or _normalize_string(website_url)
            or _normalize_string(response.brand_dna.brand_name)
        )
        if not key:
            return
        if key not in self._data.get("brands", {}):
            self._data.setdefault("brands", {})[key] = {
                "aliases": [
                    a
                    for a in [
                        brand_name,
                        website_url,
                        facebook_url,
                        response.brand_dna.brand_name,
                    ]
                    if a
                ],
                "brand_dna": response.brand_dna.model_dump(),
                "match_response": response.model_dump(),
            }
        else:
            self._data["brands"][key]["brand_dna"] = response.brand_dna.model_dump()
            self._data["brands"][key]["match_response"] = response.model_dump()
        self._save()


_demo_cache_instance: Optional[DemoCacheService] = None


def get_demo_cache() -> DemoCacheService:
    global _demo_cache_instance
    if _demo_cache_instance is None:
        _demo_cache_instance = DemoCacheService()
    return _demo_cache_instance
