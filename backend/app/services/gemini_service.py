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
        # Fallback: clean unescaped newlines/control characters, quote unquoted keys and retry
        cleaned = re.sub(r"[\x00-\x1f\x7f-\x9f]+", " ", text)
        cleaned = re.sub(r",\s*([\]}])", r"\1", cleaned)
        try:
            return json.loads(cleaned)
        except Exception:
            # Fix unquoted JSON keys (e.g. aliases: [ ... ] -> "aliases": [ ... ])
            quoted = re.sub(r'([{,]\s*)([a-zA-Z_][a-zA-Z0-9_-]*)\s*:', r'\1"\2":', cleaned)
            try:
                return json.loads(quoted)
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

BRAND_DNA_SYSTEM_INSTRUCTION = f"""# Role & Identity
You are the Chief Strategy Officer of Convert Cake, a leading performance-only influencer marketing agency in Thailand.

# Primary Objective
Analyze raw client submissions (scraped website markdown, Facebook posts, customer comments) to extract the Brand DNA, identify the business conversion model, construct high-precision Thai TikTok search queries, and list Thai competitors.

# Methodologies & Frameworks
{CONVERSION_MODEL_GUIDE}

{NATURAL_SEARCH_SYNTAX_GUIDE}

# Behavioral Rules & Constraints
- Demand-Side vs Supply-Side: NEVER use wholesale, manufacturing, or factory terms (e.g. ราคาส่ง, รับสกรีน, โรงงาน, ขายส่ง, เปิดบิล, ตัวแทนจำหน่าย) which flood discovery with competitor merchant stores. Focus purely on consumer & creator search intent (e.g. OOTD, how-to, styling, everyday solutions).
- Short & Natural: Queries must be 2 to 4 words joined, at most 18 Thai letters (combining vowels and tone marks do not count towards the limit).
- Strict Brand Grounding: Words MUST come strictly from the client's actual niche, features, and target audience. No artificial slang or generic templates.

# Tasks
A. Classify the brand into ONE conversion model by HOW IT MAKES MONEY.
B. Extract Thai tone of voice and REAL Thai customer questions / pain points (from Facebook comments when present).
C. Plain & Natural Thai Search Query Extraction: produce 6 to 8 natural Thai TikTok search queries strictly adhering to the 4 Abstract Syntax Rules. Base them 100% on the brand's extracted content.
D. 4-8 niche_keywords: Thai/English sub-niche words that a matching creator's captions or hashtags would contain (no '#').
E. Up to 6 Thai-market competitor brands in the same category & price tier with English + Thai transliteration aliases.

# Output Format Specification
Return ONLY a valid JSON object matching this schema:
{{
  "brand_name": "string",
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

QUERY_REPAIR_SYSTEM_INSTRUCTION = f"""# Role & Identity
You are the Natural Thai Search Query Optimization Specialist for TikTok Discovery at Convert Cake.

# Primary Objective
Replace rejected candidate queries with compliant, high-performing Thai search queries adhering strictly to the 4 Abstract Syntax Rules.

# Syntax Rules & Guardrails
{NATURAL_SEARCH_SYNTAX_GUIDE}
- Length: 2 to 4 words, at most 18 Thai letters.
- Native Phrasing: Everyday conversational search intent (how Thai consumers actually search on TikTok).
- Demand-Side Guardrail: STRICTLY FORBIDDEN words: ราคาส่ง, ขายส่ง, โรงงาน, รับทำ, ผลิต, โปรโมชั่น, ตัวแทนจำหน่าย.
- Grounding: Must reflect the provided brand summary and conversion model.

# Output Format Specification
Return ONLY a valid JSON list:
[
  {{"query": "คำค้นหา", "syntax_rule": "rule_1|rule_2|rule_3|rule_4", "specificity": "direct|adjacent"}}
]"""

GROUNDED_COMPETITORS_SYSTEM_INSTRUCTION = """# Role & Identity
You are a Thai Market Competitive Intelligence Analyst specialized in social commerce and retail.

# Primary Objective
Use Google Search Grounding to find brands currently active and sold in Thailand that compete directly with the target brand in the same category and price tier.

# Guidelines
- Return up to 6 direct competitors currently sold in Thailand.
- For each competitor, provide its English canonical name and the Thai transliterations / colloquial nicknames Thai consumers use on TikTok.
- Exclude the target brand itself.

# Output Format Specification
Return ONLY a valid JSON list (no conversational prose):
[
  {"brand": "Canonical Name", "aliases": ["Canonical Name", "ชื่อภาษาไทย"]}
]"""

COOCCURRENCE_SYSTEM_INSTRUCTION = """# Role & Identity
You are a Brand Entity Disambiguation Specialist for Thai TikTok.

# Primary Objective
Identify and isolate commercial competitor brand names from a frequency list of terms and hashtags scraped from TikTok clips.

# Filtering Rules
- Include ONLY genuine commercial brand names competing in the specified category.
- STRICTLY EXCLUDE: the client brand itself, generic words/adjectives, locations/places, social platforms (TikTok, Shopee, Lazada, IG), and creator usernames/handles.

# Output Format Specification
Return ONLY a valid JSON list (or [] if none):
[
  {"brand": "canonical name", "aliases": ["term as seen", "Thai/English variant"], "mentions": 1}
]"""

RELEVANCE_GATE_SYSTEM_INSTRUCTION = f"""# Role & Identity
You are the Creator Relevance Gate & Persona Classifier of Convert Cake (Thai TikTok Influencer Engine).

# Primary Objective
Evaluate candidate creators against the client Brand DNA in a single batch pass, assessing topical relevance and classifying into the 2x2 Funnel Matrix.

# 2x2 Funnel Matrix Classification Guide
{SUB_STYLE_GUIDE}

# Rules & Constraints
- News channels, meme / comedy channels, and creators who only share a homonym word but are in a different industry
  -> is_relevant_creator = false.
- Otherwise is_relevant_creator = true and provide:
  * relevance_score: 0.0-1.0 fit with the brand's audience & category
  * main_role: exactly 'KOL' or 'KOC'
  * sub_style: exactly one of the 4 sub-styles above (use the numeric signals provided: basket_ratio, save_rate, comment_to_like, avg_caption_length)
  * why_it_fits: ONE short Thai sentence on why this creator fits this brand.

# Output Format Specification
Return ONLY a valid JSON object keyed by creator id:
{{
  "<id>": {{
    "is_relevant_creator": true,
    "relevance_score": 0.85,
    "main_role": "KOC",
    "sub_style": "KOC - Hard-Sell Reviewer",
    "why_it_fits": "..."
  }}
}}"""


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
    async def _generate_json(
        self,
        prompt: str,
        temperature: float = 0.2,
        grounded: bool = False,
        system_instruction: Optional[str] = None,
    ) -> Any:
        self._require()
        config_kwargs: Dict[str, Any] = {"temperature": temperature}
        if system_instruction:
            config_kwargs["system_instruction"] = system_instruction.strip()
        if grounded:
            # Google Search grounding cannot be combined with JSON mime type -> parse from text.
            config_kwargs["tools"] = [types.Tool(google_search=types.GoogleSearch())]
        else:
            config_kwargs["response_mime_type"] = "application/json"
        config = types.GenerateContentConfig(**config_kwargs)
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
        manual_xml = f"  <competitor_override>{', '.join(manual_competitors)}</competitor_override>\n" if manual_competitors else ""
        user_prompt = f"""<client_submission>
  <brand_name>{brand_name}</brand_name>
  <website_url>{website_url or 'N/A'}</website_url>
  <facebook_url>{facebook_url or 'N/A'}</facebook_url>
{manual_xml}</client_submission>

<scraped_context>
{context[:7000]}
</scraped_context>

Please extract the Brand DNA, conversion model, 6-8 natural Thai search queries, and Thai competitors strictly adhering to your system instructions."""
        data = await self._generate_json(
            user_prompt,
            system_instruction=BRAND_DNA_SYSTEM_INSTRUCTION,
            temperature=0.2,
        )
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

        user_prompt = f"""<brand_context>
  <brand_summary>{brand_summary}</brand_summary>
  <conversion_model>{conversion_model}</conversion_model>
</brand_context>

<rejected_queries>
{json.dumps(rejected, ensure_ascii=False)}
</rejected_queries>

Please generate {max(count, 4)} replacement natural Thai TikTok search queries strictly following the 4 Abstract Syntax Rules in your system instructions."""
        data = await self._generate_json(
            user_prompt,
            system_instruction=QUERY_REPAIR_SYSTEM_INSTRUCTION,
            temperature=0.3,
        )
        if not isinstance(data, list):
            raise RuntimeError("Gemini query repair payload is not a JSON list")
        return data

    async def extract_grounded_competitors(
        self, brand_name: str, vertical: str, sub_category: str, price_positioning: str
    ) -> List[Dict[str, Any]]:
        """Layer 1 — Google Search grounded competitor discovery for the Thai market."""
        user_prompt = f"""<target_brand>
  <name>{brand_name}</name>
  <vertical>{vertical}</vertical>
  <sub_category>{sub_category}</sub_category>
  <price_positioning>{price_positioning}</price_positioning>
</target_brand>

Using Google Search, find direct competitor brands currently active and sold in Thailand for this target brand."""
        data = await self._generate_json(
            user_prompt,
            system_instruction=GROUNDED_COMPETITORS_SYSTEM_INSTRUCTION,
            temperature=0.1,
            grounded=True,
        )
        if not isinstance(data, list):
            raise RuntimeError("Grounded competitor payload is not a JSON list")
        return data

    # ------------------------------------------------------------------
    # Stage 2 — Layer 2 co-occurrence
    # ------------------------------------------------------------------
    async def identify_cooccurring_brands(
        self, brand_name: str, sub_category: str, frequent_terms: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        user_prompt = f"""<client_brand>
  <name>{brand_name}</name>
  <sub_category>{sub_category}</sub_category>
</client_brand>

<frequent_terms>
{json.dumps(frequent_terms, ensure_ascii=False)}
</frequent_terms>

Identify commercial competitor brands from these terms according to your system instructions."""
        data = await self._generate_json(
            user_prompt,
            system_instruction=COOCCURRENCE_SYSTEM_INSTRUCTION,
            temperature=0.1,
        )
        if not isinstance(data, list):
            raise RuntimeError("Co-occurrence payload is not a JSON list")
        return data

    # ------------------------------------------------------------------
    # Stage 3 — Batch LLM Relevance Gate (one call)
    # ------------------------------------------------------------------
    async def relevance_gate(self, brand: Dict[str, Any], creators: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        user_prompt = f"""<brand_dna>
{json.dumps(brand, ensure_ascii=False)}
</brand_dna>

<candidate_creators>
{json.dumps(creators, ensure_ascii=False)}
</candidate_creators>

Evaluate each creator against the Brand DNA and return the classification JSON according to your system instructions."""
        data = await self._generate_json(
            user_prompt,
            system_instruction=RELEVANCE_GATE_SYSTEM_INSTRUCTION,
            temperature=0.1,
        )
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
