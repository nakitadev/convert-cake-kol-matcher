"""
Gemini service: embeddings + all LLM calls used by the 4-stage pipeline.

- Stage 1: Brand DNA, Conversion Model classification, Scene-Translation queries,
           Search-Grounded Thai competitor extraction (Google Search Grounding)
- Stage 2: Bottom-up TikTok co-occurrence brand extraction (competitor Layer 2)
- Stage 3: Batch LLM Relevance Gate (single call) + 2x2 KOL/KOC sub-style classification
- Stage 4: Role-adaptive 3-second pitch hooks

Fail-loud policy: every LLM helper raises RuntimeError when the model is unavailable or
returns an unusable payload. Callers decide whether a failure is fatal.
"""
import os
import re
import json
import asyncio
from typing import List, Optional, Dict, Any

import numpy as np

try:
    from google import genai
    from google.genai import types
    HAS_GENAI = True
except ImportError:  # pragma: no cover
    HAS_GENAI = False


def parse_json_payload(raw: str) -> Any:
    """Parse JSON from an LLM response, tolerating code fences, prose and trailing commas."""
    if raw is None:
        raise ValueError("Empty LLM response")
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    if not text.startswith(("{", "[")):
        starts = [i for i in (text.find("{"), text.find("[")) if i >= 0]
        if not starts:
            raise ValueError(f"No JSON object in LLM response: {raw[:200]}")
        start = min(starts)
        closer = "}" if text[start] == "{" else "]"
        end = text.rfind(closer)
        text = text[start:end + 1]
    text = re.sub(r",\s*([\]}])", r"\1", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Fallback: clean unescaped newlines/control characters and retry
        cleaned = re.sub(r"[\x00-\x1f\x7f-\x9f]+", " ", text)
        cleaned = re.sub(r",\s*([\]}])", r"\1", cleaned)
        try:
            return json.loads(cleaned)
        except Exception:
            import ast
            try:
                return ast.literal_eval(text)
            except Exception:
                pass
        raise


CONVERSION_MODEL_GUIDE = """
4 Brand Conversion Models (choose exactly one based on how the brand makes money):
1. ECOMMERCE_PRODUCT — buy now via TikTok Shop basket / Shopee: skincare, cosmetics, supplements, household goods, gadgets. (KOL 30% : KOC 70%)
2. APP_DIGITAL_SERVICE — download app / sign up / SaaS: fintech & investing apps, AI platforms, software, games. (KOL 60% : KOC 40%)
3. HIGH_TICKET_LEADGEN — consultation / form / booking: beauty & dental clinics, courses (EdTech), real estate, insurance. (KOL 70% : KOC 30%)
4. LIFESTYLE_EXPERIENCE — visit store / premium image: hotels, malls, restaurants & cafes, luxury goods. (KOL 60% : KOC 40%)
"""

NATURAL_SEARCH_SYNTAX_GUIDE = """
Abstract Syntax Rules for Thai TikTok Search Queries (Zero-Mock & Zero Hardcoded Examples):
People in Thailand type plain, everyday words into TikTok's search bar to discover products.
Do NOT use artificial slang, forced KOL/KOC tags, or copied templates.
Generate 6-8 natural Thai search queries grounded 100% on the brand's extracted content using these 4 Abstract Syntax Rules:
1. <brand sub-category noun> + <key benefit or primary outcome>
2. <brand sub-category noun> + <brand origin / type / target demographic>
3. 'รีวิว' + <brand sub-category noun> OR 'แนะนำ' + <brand sub-category noun>
4. <brand sub-category noun> + <client brand name or competitor brand in Thailand>

Syntax Constraints:
- Short & Natural: 2 to 4 words joined, at most 18 Thai letters (tone marks and combining vowels do not count towards the letter limit).
- Anti-Merchant Guardrail: NEVER use words like ราคาส่ง, ขายถูก, โปรโมชั่น, ตัวแทนจำหน่าย, เปิดบิล.
- Strict Brand Grounding: Words MUST come strictly from the client's actual niche, features, and target audience.
"""

SUB_STYLE_GUIDE = """
Convert Cake 2x2 Funnel Matrix (2 roles -> 4 sub-styles):
KOL (Top & Middle funnel: awareness, image, trust)
  - 'KOL - Expert / Guru': deep explanatory content analysing specs/ingredients/principles; notably high save rate (collectCount / playCount).
  - 'KOL - Lifestyle / Aesthetic': lifestyle / travel / mood & tone content; high views, clean image; almost no yellow basket (basket_ratio < 0.20).
KOC (Bottom funnel: purchase decision & closing)
  - 'KOC - Hard-Sell Reviewer': direct product review, before & after, value-for-money proof; consistent yellow basket; high buyer-intent comments (comment_to_like).
  - 'KOC - Everyday User / Vlog': relatable daily routines (office worker, student, mom); friend-to-friend real-life recommendation; natural style (Nano/Micro tier).
"""

HOOK_GUIDE = """
3-Second Opening Hook Guidelines (Role-Adaptive & Dynamic, No Static Templates):
- 'KOL - Expert / Guru': open with deep product knowledge, clinical/technical facts, or expert analysis.
- 'KOL - Lifestyle / Aesthetic': open with atmosphere, mood & tone, aesthetic presentation, or lifestyle elevation.
- 'KOC - Hard-Sell Reviewer': open with real-life usage results, before-and-after proof, or price-to-value comparison.
- 'KOC - Everyday User / Vlog': open with relatable daily situations and natural friend-to-friend recommendation.
"""


class GeminiService:
    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        self.embedding_model = os.environ.get("GEMINI_EMBEDDING_MODEL", "gemini-embedding-2")
        self.llm_model = os.environ.get("GEMINI_LLM_MODEL", "gemini-3.5-flash-lite")
        self.client = None
        self._embedding_cache: Dict[str, List[float]] = {}
        if HAS_GENAI and self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:  # pragma: no cover
                print(f"[GeminiService] Failed to initialize client: {e}")
                self.client = None

    @property
    def is_configured(self) -> bool:
        return self.client is not None

    def _require(self):
        if not self.is_configured:
            raise RuntimeError("Gemini is not configured. Set GEMINI_API_KEY in .env.")

    # ------------------------------------------------------------------
    # Embeddings
    # ------------------------------------------------------------------
    async def get_embedding_async(self, text: str) -> Optional[List[float]]:
        if not text or not text.strip() or not self.is_configured:
            return None
        key = f"{self.embedding_model}:{hash(text.strip()[:2000])}"
        if key in self._embedding_cache:
            return self._embedding_cache[key]
        try:
            resp = await self.client.aio.models.embed_content(
                model=self.embedding_model, contents=text.strip()[:4000]
            )
            if getattr(resp, "embeddings", None):
                emb = resp.embeddings[0]
                values = list(emb.values if hasattr(emb, "values") else emb)
                self._embedding_cache[key] = values
                return values
        except Exception as e:
            print(f"[GeminiService] Embedding error ({self.embedding_model}): {e}")
        return None

    async def get_embeddings_batch(self, texts: List[str], max_concurrency: int = 15) -> List[Optional[List[float]]]:
        if not texts:
            return []
        sem = asyncio.Semaphore(max_concurrency)

        async def _one(t: str):
            async with sem:
                return await self.get_embedding_async(t)

        return list(await asyncio.gather(*[_one(t) for t in texts]))

    @staticmethod
    def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
        """Raw cosine similarity in [-1, 1]."""
        if not vec_a or not vec_b or len(vec_a) != len(vec_b):
            return 0.0
        a = np.asarray(vec_a, dtype=np.float32)
        b = np.asarray(vec_b, dtype=np.float32)
        na, nb = np.linalg.norm(a), np.linalg.norm(b)
        if na == 0 or nb == 0:
            return 0.0
        return float(np.dot(a, b) / (na * nb))

    # ------------------------------------------------------------------
    # Generic LLM call
    # ------------------------------------------------------------------
    async def _generate_json(self, prompt: str, temperature: float = 0.2, grounded: bool = False) -> Any:
        self._require()
        if grounded:
            # Google Search grounding cannot be combined with JSON mime type -> parse from text.
            config = types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                temperature=temperature,
            )
        else:
            config = types.GenerateContentConfig(response_mime_type="application/json", temperature=temperature)
        resp = await self.client.aio.models.generate_content(model=self.llm_model, contents=prompt, config=config)
        text = getattr(resp, "text", None)
        if not text:
            raise RuntimeError(f"Gemini ({self.llm_model}) returned an empty response")
        return parse_json_payload(text)

    # ------------------------------------------------------------------
    # Stage 1 — Brand DNA + conversion model + scene-translation queries
    # ------------------------------------------------------------------
    async def generate_brand_dna(
        self,
        context: str,
        brand_name: str,
        website_url: str,
        facebook_url: str,
        manual_competitors: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        manual = f"Competitor override from marketing team: {', '.join(manual_competitors)}\n" if manual_competitors else ""
        prompt = f"""You are the Chief Strategy Officer of Convert Cake, a Thai performance-only marketing agency.
Analyse the client's website + Facebook page (posts and real customer comments) and output the Brand DNA.

Brand Name: {brand_name}
Website: {website_url}
Facebook: {facebook_url}
{manual}
=== Scraped context ===
{context[:7000]}
=== End context ===

{CONVERSION_MODEL_GUIDE}
{NATURAL_SEARCH_SYNTAX_GUIDE}

Tasks:
A. Classify the brand into ONE conversion model by HOW IT MAKES MONEY.
B. Extract Thai tone of voice and REAL Thai customer questions / pain points (from Facebook comments when present).
C. Plain & Natural Thai Search Query Extraction: produce 6 to 8 natural Thai TikTok search queries strictly adhering to the 4 Abstract Syntax Rules. Base them 100% on the brand's extracted content. Do NOT use artificial slang or hardcoded templates.
D. 4-8 niche_keywords: Thai/English sub-niche words that a matching creator's captions or hashtags would contain (no '#').
E. Up to 6 Thai-market competitor brands in the same category & price tier with English + Thai transliteration aliases.

Return ONLY JSON:
{{
  "brand_name": "{brand_name}",
  "vertical": "industry vertical",
  "sub_category": "specific product / service niche",
  "brand_summary": "2-3 sentences",
  "target_audience": "Thai target audience",
  "target_age_range": "e.g. 22-35",
  "brand_tone": ["Thai tone-of-voice trait", "..."],
  "customer_pain_points": ["real Thai customer question or pain point", "..."],
  "price_positioning": "Budget / Mass | Mid-Range | Premium | Luxury",
  "average_price_thb": 0,
  "conversion_model": "ECOMMERCE_PRODUCT | APP_DIGITAL_SERVICE | HIGH_TICKET_LEADGEN | LIFESTYLE_EXPERIENCE",
  "conversion_model_reason": "1 sentence",
  "search_queries": [{{"query": "...", "syntax_rule": "rule_1|rule_2|rule_3|rule_4", "specificity": "direct|adjacent"}}],
  "niche_keywords": ["..."],
  "competitors": [{{"brand": "Competitor Name", "aliases": ["Competitor Name", "ชื่อไทย"]}}]
}}"""
        data = await self._generate_json(prompt, temperature=0.2)
        if not isinstance(data, dict):
            raise RuntimeError("Gemini Brand DNA payload is not a JSON object")
        return data

    async def repair_queries(
        self,
        brand_summary: str,
        conversion_model: str,
        side_or_rejected: Any = None,
        rejected_or_needed: Any = None,
        needed: Optional[Dict[str, int]] = None,
        needed_count: int = 4,
    ) -> List[Dict[str, str]]:
        if isinstance(side_or_rejected, list):
            rejected = side_or_rejected
            count = rejected_or_needed if isinstance(rejected_or_needed, int) else needed_count
        else:
            rejected = rejected_or_needed if isinstance(rejected_or_needed, list) else []
            count = sum(needed.values()) if isinstance(needed, dict) else needed_count

        prompt = f"""These Thai TikTok search queries were REJECTED (too long, sentence-like, or merchant words):
{json.dumps(rejected, ensure_ascii=False)}

Brand: {brand_summary}
Conversion model: {conversion_model}
{NATURAL_SEARCH_SYNTAX_GUIDE}

Write {max(count, 4)} replacement natural Thai TikTok search queries strictly adhering to the 4 Abstract Syntax Rules.
Base them 100% on the brand's extracted content.
Each MUST be 2-4 words, at most 18 Thai letters, native everyday search phrasing.
Return ONLY JSON: [{{"query": "...", "syntax_rule": "rule_1|rule_2|rule_3|rule_4", "specificity": "direct|adjacent"}}]"""
        data = await self._generate_json(prompt, temperature=0.3)
        if not isinstance(data, list):
            raise RuntimeError("Gemini query repair payload is not a JSON list")
        return data

    async def extract_grounded_competitors(
        self, brand_name: str, vertical: str, sub_category: str, price_positioning: str
    ) -> List[Dict[str, Any]]:
        """Layer 1 — Google Search grounded competitor discovery for the Thai market."""
        prompt = f"""Use Google Search to find brands that are CURRENTLY sold in Thailand and compete directly with
"{brand_name}" ({vertical} / {sub_category}, price tier: {price_positioning}).
Return up to 6 competitors in the same category and price tier. For each give the English name and the
Thai transliterations / nicknames Thai consumers use on TikTok.
Return ONLY JSON (no prose): [{{"brand": "La Roche-Posay", "aliases": ["La Roche-Posay", "ลาโรช", "ลาโรชโพเซย์"]}}]"""
        data = await self._generate_json(prompt, temperature=0.1, grounded=True)
        if not isinstance(data, list):
            raise RuntimeError("Grounded competitor payload is not a JSON list")
        return data

    # ------------------------------------------------------------------
    # Stage 2 — Layer 2 co-occurrence
    # ------------------------------------------------------------------
    async def identify_cooccurring_brands(
        self, brand_name: str, sub_category: str, frequent_terms: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        prompt = f"""Below are the most frequent hashtags / terms in TikTok clips scraped for the client brand "{brand_name}"
(category: {sub_category}). Each item shows the term and how many distinct creators used it.
{json.dumps(frequent_terms, ensure_ascii=False)}

Identify ONLY the terms that are commercial BRAND names competing in the same category (exclude "{brand_name}" itself,
generic words, places, platforms like TikTok/Shopee/Lazada, and creator names).
Return ONLY JSON: [{{"brand": "canonical name", "aliases": ["term as seen", "Thai/English variant"], "mentions": <creator count>}}]
Return [] if none."""
        data = await self._generate_json(prompt, temperature=0.1)
        if not isinstance(data, list):
            raise RuntimeError("Co-occurrence payload is not a JSON list")
        return data

    # ------------------------------------------------------------------
    # Stage 3 — Batch LLM Relevance Gate (one call)
    # ------------------------------------------------------------------
    async def relevance_gate(self, brand: Dict[str, Any], creators: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        prompt = f"""You are the Creator Relevance Gate of Convert Cake (Thai TikTok).
Check each creator against the client Brand DNA in ONE pass.

Brand DNA:
{json.dumps(brand, ensure_ascii=False)}

{SUB_STYLE_GUIDE}

Rules:
- News channels, meme / comedy channels, and creators who only share a homonym word but are in a different industry
  -> is_relevant_creator = false.
- Otherwise is_relevant_creator = true and give:
  * relevance_score: 0.0-1.0 fit with the brand's audience & category
  * main_role: exactly 'KOL' or 'KOC'
  * sub_style: exactly one of the 4 sub-styles above (use the numeric signals provided: basket_ratio,
    save_rate, comment_to_like, avg_caption_length)
  * why_it_fits: ONE short Thai sentence on why this creator fits this brand.

Creators (handle, bio, 3 latest captions, signals):
{json.dumps(creators, ensure_ascii=False)}

Return ONLY JSON keyed by creator id:
{{"<id>": {{"is_relevant_creator": true, "relevance_score": 0.85, "main_role": "KOC", "sub_style": "KOC - Hard-Sell Reviewer", "why_it_fits": "..."}}}}"""
        data = await self._generate_json(prompt, temperature=0.1)
        if not isinstance(data, dict):
            raise RuntimeError("Relevance gate payload is not a JSON object")
        return data

    # ------------------------------------------------------------------
    # Stage 4 — Role-adaptive pitch hooks (BYPASSED for speed)
    # ------------------------------------------------------------------
    async def generate_pitch_hooks(self, brand: Dict[str, Any], creators: List[Dict[str, Any]]) -> Dict[str, str]:
        # Bypassed per requirement to reduce pipeline latency
        return {}


_gemini_service_instance: Optional[GeminiService] = None


def get_gemini_service() -> GeminiService:
    global _gemini_service_instance
    if _gemini_service_instance is None:
        _gemini_service_instance = GeminiService()
    return _gemini_service_instance
