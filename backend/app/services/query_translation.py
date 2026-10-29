"""
Stage 2 — Plain & Natural Thai Search Query Extraction guardrails (Spec 3.2).

Validates LLM-generated natural search queries against the TikTok Search Syntax rules:
  1. Short & Native: 2-4 words, at most 18 Thai letters (combining vowels / tone marks are not letters)
  2. Zero Hardcoded Examples & Templates: queries must be grounded in brand niche
  3. Anti-Merchant Guardrail: no ราคาส่ง, ขายถูก, โปรโมชั่น, โปรโมชัน, ตัวแทนจำหน่าย, เปิดบิล
"""
import math
import re
from typing import List, Tuple, Dict

from app.models import SearchQuery

MAX_LETTERS = 18
MAX_WORDS = 4
MERCHANT_QUERY_TERMS = ["ราคาส่ง", "ขายถูก", "โปรโมชั่น", "โปรโมชัน", "ตัวแทนจำหน่าย", "เปิดบิล"]
DIRECT_SHARE = 0.6

# Thai combining characters (above/below vowels, tone marks, thanthakhat) do not count as letters.
_THAI_COMBINING = re.compile(r"[\u0E31\u0E34-\u0E3A\u0E47-\u0E4E]")


def letter_count(query: str) -> int:
    stripped = re.sub(r"\s+", "", query)
    return len(_THAI_COMBINING.sub("", stripped))


def validate_query(query: str) -> Tuple[bool, str]:
    q = (query or "").strip()
    if not q:
        return False, "empty"
    if any(term in q for term in MERCHANT_QUERY_TERMS):
        return False, "anti-merchant guardrail"
    if len(q.split()) > MAX_WORDS:
        return False, f"more than {MAX_WORDS} words"
    if letter_count(q) > MAX_LETTERS:
        return False, f"longer than {MAX_LETTERS} letters"
    if re.search(r"[.!?,;:]", q):
        return False, "sentence punctuation"
    return True, ""


def normalize(query: str) -> str:
    return re.sub(r"\s+", " ", (query or "").lstrip("#").strip())


def split_valid(queries: List[SearchQuery]) -> Tuple[List[SearchQuery], List[str]]:
    valid, rejected, seen = [], [], set()
    for q in queries:
        text = normalize(q.query)
        ok, reason = validate_query(text)
        key = text.lower()
        if not ok:
            rejected.append(f"{text} ({reason})")
            continue
        if key in seen:
            continue
        seen.add(key)
        valid.append(
            SearchQuery(
                query=text,
                side=q.side or "NATURAL_QUERY",
                specificity=q.specificity or "direct",
                syntax_rule=q.syntax_rule,
            )
        )
    return valid, rejected


def required_split(total: int) -> Dict[str, int]:
    direct = int(math.ceil(total * DIRECT_SHARE))
    return {"direct": direct, "adjacent": total - direct}


def select_funnel(queries: List[SearchQuery], side: str, per_side: int) -> List[SearchQuery]:
    """Pick `per_side` queries for one side honouring the 60/40 direct/adjacent funnel."""
    side_qs = [q for q in queries if q.side == side]
    if not side_qs:
        side_qs = queries
    need = required_split(per_side)
    direct = [q for q in side_qs if q.specificity == "direct"][: need["direct"]]
    adjacent = [q for q in side_qs if q.specificity == "adjacent"][: need["adjacent"]]
    picked = direct + adjacent
    if len(picked) < per_side:  # top up from whichever bucket still has queries
        rest = [q for q in side_qs if q not in picked]
        picked += rest[: per_side - len(picked)]
    return picked


def missing_counts(queries: List[SearchQuery], side: str, per_side: int) -> Dict[str, int]:
    side_qs = [q for q in queries if q.side == side]
    if not side_qs:
        side_qs = queries
    need = required_split(per_side)
    have_d = sum(1 for q in side_qs if q.specificity == "direct")
    have_a = sum(1 for q in side_qs if q.specificity == "adjacent")
    return {"direct": max(0, need["direct"] - have_d), "adjacent": max(0, need["adjacent"] - have_a)}
