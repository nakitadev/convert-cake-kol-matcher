import json
from pathlib import Path
from typing import List, Optional
from app.models import KOLProfile

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "thai_kols_seed.json"

class KOLRepository:
    def __init__(self, data_path: Optional[Path] = None):
        self.data_path = data_path or DATA_PATH
        self._kols: List[KOLProfile] = []
        self._load()

    def _load(self):
        if not self.data_path.exists():
            self._kols = []
            return
        with open(self.data_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
            self._kols = [KOLProfile(**item) for item in raw]

    def get_all(self) -> List[KOLProfile]:
        return list(self._kols)

    def get_by_id(self, kol_id: str) -> Optional[KOLProfile]:
        for k in self._kols:
            if k.id == kol_id:
                return k
        return None

    def filter_candidates(
        self,
        vertical: Optional[str] = None,
        min_followers: Optional[int] = None,
        max_followers: Optional[int] = None,
        include_penalized_traps: bool = True
    ) -> List[KOLProfile]:
        results = []
        for kol in self._kols:
            if not include_penalized_traps and kol.is_affiliate_spam_trap:
                continue
            if min_followers is not None and kol.follower_count < min_followers:
                continue
            if max_followers is not None and kol.follower_count > max_followers:
                continue
            # We keep all verticals in candidate set for cross-vertical / semantic ranking,
            # but if exact vertical is specified we can prioritize or keep all
            results.append(kol)
        return results

_repo_instance: Optional[KOLRepository] = None

def get_kol_repository() -> KOLRepository:
    global _repo_instance
    if _repo_instance is None:
        _repo_instance = KOLRepository()
    return _repo_instance
