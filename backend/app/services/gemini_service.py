import os
import json
import math
import re
import asyncio
from typing import List, Optional, Tuple, Dict, Any
import numpy as np

try:
    from google import genai
    from google.genai import types
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False


class GeminiService:
    """
    Gemini Service integrating:
    1. Gemini Embedding 2 (`gemini-embedding-2`) for unified dense semantic vector embeddings
    2. Gemini Main LLM (`gemini-3.5-flash-lite` or configurable) for Brand DNA synthesis, 5-angle search taxonomy, grounded competitor extraction, matching rationale, and archetype-tailored hooks.
    """

    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        self.embedding_model = os.environ.get("GEMINI_EMBEDDING_MODEL", "gemini-embedding-2")
        self.llm_model = os.environ.get("GEMINI_LLM_MODEL", "gemini-3.5-flash-lite")
        self.client = None
        self._embedding_cache: Dict[str, List[float]] = {}

        if HAS_GENAI and self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                print(f"[GeminiService] Failed to initialize client: {e}")
                self.client = None

    @property
    def is_configured(self) -> bool:
        return self.client is not None

    def get_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate dense embedding vector using Gemini Embedding 2.
        Caches results in memory for fast subsequent comparisons.
        """
        if not text or not text.strip():
            return None

        cache_key = f"{self.embedding_model}:{text.strip()[:300]}"
        if cache_key in self._embedding_cache:
            return self._embedding_cache[cache_key]

        if not self.is_configured:
            return None

        try:
            response = self.client.models.embed_content(
                model=self.embedding_model,
                contents=text.strip()[:4000],
            )
            if hasattr(response, "embeddings") and response.embeddings:
                emb = response.embeddings[0]
                values = emb.values if hasattr(emb, "values") else list(emb)
                self._embedding_cache[cache_key] = values
                return values
            elif hasattr(response, "embedding") and response.embedding:
                values = response.embedding.values if hasattr(response.embedding, "values") else list(response.embedding)
                self._embedding_cache[cache_key] = values
                return values
        except Exception as e:
            print(f"[GeminiService] Error calling {self.embedding_model}: {e}")
            return None

    async def get_embedding_async(self, text: str) -> Optional[List[float]]:
        """
        Asynchronously generate dense embedding vector using Gemini Embedding 2 via client.aio.
        Caches results in memory for fast subsequent comparisons.
        """
        if not text or not text.strip():
            return None

        cache_key = f"{self.embedding_model}:{text.strip()[:300]}"
        if cache_key in self._embedding_cache:
            return self._embedding_cache[cache_key]

        if not self.is_configured:
            return None

        try:
            response = await self.client.aio.models.embed_content(
                model=self.embedding_model,
                contents=text.strip()[:4000],
            )
            if hasattr(response, "embeddings") and response.embeddings:
                emb = response.embeddings[0]
                values = emb.values if hasattr(emb, "values") else list(emb)
                self._embedding_cache[cache_key] = values
                return values
            elif hasattr(response, "embedding") and response.embedding:
                values = response.embedding.values if hasattr(response.embedding, "values") else list(response.embedding)
                self._embedding_cache[cache_key] = values
                return values
        except Exception as e:
            print(f"[GeminiService] Async error calling {self.embedding_model}: {e}")
            return None

    async def get_embeddings_batch(
        self,
        texts: List[str],
        max_concurrency: int = 15,
    ) -> List[Optional[List[float]]]:
        """
        Concurrently batch-embed a list of texts (e.g. 50 candidate KOLs) using asyncio.gather
        and an async semaphore to maximize throughput and avoid rate limits.
        """
        if not texts:
            return []

        if not self.is_configured:
            return [None] * len(texts)

        sem = asyncio.Semaphore(max_concurrency)

        async def _embed_with_sem(txt: str) -> Optional[List[float]]:
            async with sem:
                return await self.get_embedding_async(txt)

        tasks = [_embed_with_sem(t) for t in texts]
        return await asyncio.gather(*tasks, return_exceptions=False)

    @staticmethod
    def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
        if not vec_a or not vec_b or len(vec_a) != len(vec_b):
            return 0.0
        a = np.array(vec_a, dtype=np.float32)
        b = np.array(vec_b, dtype=np.float32)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        cos = float(np.dot(a, b) / (norm_a * norm_b))
        return max(0.0, min(1.0, (cos + 1.0) / 2.0))

    async def generate_brand_dna(
        self,
        scraped_text: str,
        brand_name: str,
        website_url: str,
        fb_url: str,
        manual_competitors: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Uses Gemini Main LLM to extract structured Brand DNA, 5-Angle Search Taxonomy, and Grounded Competitor Dictionary.
        """
        if not self.is_configured:
            return None

        manual_comp_str = f"Manual Competitors Provided by Agency: {', '.join(manual_competitors)}\n" if manual_competitors else ""

        prompt = f"""You are an expert Chief Strategy Officer at a premier Thai digital marketing agency (Convert Cake).
Analyze this brand's website content and Facebook information to synthesize structured Brand DNA, a 5-Angle Search Taxonomy for Thai TikTok, and a Grounded Thai Competitor Dictionary.

Brand Name: {brand_name}
Website: {website_url}
Facebook: {fb_url}
{manual_comp_str}Scraped Context:
{scraped_text[:4000]}

Respond ONLY with a valid JSON object matching this schema:
{{
  "brand_name": "{brand_name}",
  "vertical": "Primary industry vertical identified from content (e.g. Beauty & Skincare, Food & Beverage, Tech & Ergonomics, Fashion & Apparel, Lifestyle, etc.)",
  "sub_category": "Specific niche (e.g. Dermocosmetics, Specialty Coffee, Standing Desks, Streetwear)",
  "brand_summary": "2-3 sentence strategic agency summary in English or Thai",
  "target_audience": "Detailed target demographic and lifestyle in Thailand",
  "target_age_range": "e.g. '18-24', '22-35', '28-45'",
  "target_locations": ["Bangkok", "Thailand"],
  "brand_tone": ["Authentic", "Modern"],
  "content_style_preferences": ["Review", "Short-Form"],
  "price_positioning": "One of: 'Budget / Mass' | 'Mid-Range / Accessible' | 'Premium / Masstige' | 'Luxury / High-End'",
  "average_price_thb": 0,
  "thai_keywords": ["5-8 direct organic consumer search terms and specific hashtags without slang (e.g. 'ไดร์เป่าผม', 'ครีมแต้มสิว', 'มอยส์เจอร์ไรเซอร์', 'เก้าอี้เพื่อสุขภาพ')"],
  "search_taxonomy": {{
    "niche_hashtags": ["2-4 specific niche Thai hashtags with #, e.g. '#สกินแคร์คนเป็นสิว', '#จัดโต๊ะทำงาน'"],
    "pain_point_queries": ["2-3 solution-oriented search phrases real Thai consumers search, e.g. 'กู้หน้าพัง', 'วิธีลดสิวอุดตันด้วยตัวเอง', 'ปวดหลังเลือกเก้าอี้ยังไง'"],
    "review_hook_queries": ["2-3 review phrases, e.g. 'รีวิวพลีชีพ', 'ซื้อซ้ำไม่ซ้ำ', 'คุ้มไหม', 'ใช้จริง'"],
    "lifestyle_persona_queries": ["2-3 lifestyle routine queries, e.g. 'รูทีนคนนอนดึก', 'แต่งหน้าไปเรียน', '1 วันกินอะไรบ้าง'"],
    "competitor_seed_queries": ["2-3 competitor query phrases, e.g. 'รีวิว [คู่แข่ง]'"]
  }},
  "grounded_competitors": [
    {{
      "brand_en": "Competitor English Name",
      "aliases": ["English Name", "ชื่อภาษาไทยทับศัพท์", "ชื่อย่อโซเชียล"]
    }}
  ]
}}
"""
        try:
            response = self.client.models.generate_content(
                model=self.llm_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.2,
                ),
            )
            if response and response.text:
                return json.loads(response.text)
        except Exception as e:
            print(f"[GeminiService] LLM BrandDNA generation error: {e}")
        return None

    async def generate_brand_customer_match(
        self,
        brand_name: str,
        brand_vertical: str,
        brand_summary: str,
        target_audience: str,
        brand_price: int,
        kol_name: str,
        kol_handle: str,
        kol_persona: str,
        kol_styles: List[str],
        creator_archetype: str = "General Creator",
        is_review_creator: bool = False,
        sample_comments: Optional[List[str]] = None,
        recent_captions: Optional[List[str]] = None,
        median_er: float = 0.0,
        is_spam: bool = False,
    ) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """
        Uses Gemini Main LLM to produce deep Brand-to-Customer Matching Analysis.
        Focuses on consumer persona overlap, buyer intent, customer pain points,
        and commercial conversion strategy instead of generic pitch hooks.
        """
        if not self.is_configured or is_spam:
            return None, None

        comments_preview = ", ".join(sample_comments[:3]) if sample_comments else "N/A"
        captions_preview = ", ".join(recent_captions[:3]) if recent_captions else "N/A"

        prompt = f"""You are a Lead Consumer Insights & Brand Matchmaking Strategist at Convert Cake.
Your mission is to perform an in-depth BRAND-TO-CUSTOMER MATCHING analysis between the Client Brand and the Creator's specific audience/customer base in Thailand.
DO NOT generate generic AI pitch hooks or script lines. Focus exclusively on audience persona fit, buyer intent, customer pain points, and commercial conversion strategy.

[Client Brand]
Brand Name: {brand_name}
Vertical / Category: {brand_vertical}
Brand Summary: {brand_summary}
Target Audience / Core Demographic: {target_audience}
Average Price: {brand_price:,} THB

[Creator & Audience Telemetry]
Creator: {kol_name} (@{kol_handle})
Creator Archetype: {creator_archetype} {('(Specializes in Product Reviews / TikTok Shop Yellow Basket)' if is_review_creator else '')}
Persona & Aesthetic: {kol_persona}
Content Styles: {', '.join(kol_styles)}
Median Engagement Rate: {median_er:.1f}%
Sample Audience Comments: {comments_preview}
Recent Content Topics: {captions_preview}

Analyze the Brand-to-Customer Fit:
1. Target Customer Persona: Detail the specific customer segment among this creator's followers that matches this brand (e.g., age, lifestyle, mindset, beauty/consumer habits).
2. Buyer Intent Fit: Explain why this audience has genuine purchasing willingness and affordability for this {brand_price:,} THB price point.
3. Pain Points Addressed: Exactly 3 specific customer pain points this brand solves for this creator's audience.
4. Customer Journey Stage: What stage does this audience operate in? Choose the best fit from: 'Problem Awareness & Education', 'Consideration & Comparison', or 'Decision & Direct Purchase (TikTok Shop)'.
5. Conversion Angle: Strategic positioning advice on how to present the brand naturally to resonate with this customer mindset.
6. Rationale: 2-3 sentence strategic brand-to-customer matching rationale in Thai.

Return ONLY a valid JSON object:
{{
  "rationale": "2-3 sentence strategic brand-to-customer matching rationale in Thai",
  "brand_customer_match": {{
    "target_customer_persona": "Detailed customer profile in Thai",
    "buyer_intent_fit": "Analysis of customer buying intent and price-point compatibility in Thai",
    "pain_points_addressed": [
      "Customer pain point 1 in Thai",
      "Customer pain point 2 in Thai",
      "Customer pain point 3 in Thai"
    ],
    "customer_journey_stage": "Consideration & Comparison",
    "conversion_angle": "Strategic customer conversion angle in Thai"
  }}
}}
"""
        try:
            response = self.client.models.generate_content(
                model=self.llm_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.6,
                ),
            )
            if response and response.text:
                data = json.loads(response.text)
                return data.get("rationale"), data.get("brand_customer_match")
        except Exception as e:
            print(f"[GeminiService] LLM brand-customer matching error: {e}")
        return None, None

    async def generate_hooks_and_rationale(
        self,
        brand_name: str,
        brand_vertical: str,
        brand_price: int,
        kol_name: str,
        kol_persona: str,
        kol_styles: List[str],
        median_er: float,
        is_spam: bool,
        spam_reason: str,
        creator_archetype: str = "General Creator",
        is_review_creator: bool = False,
    ) -> Tuple[Optional[str], Optional[List[str]]]:
        """
        Legacy wrapper maintained for backwards compatibility.
        """
        rationale, match_data = await self.generate_brand_customer_match(
            brand_name=brand_name,
            brand_vertical=brand_vertical,
            brand_summary="",
            target_audience="",
            brand_price=brand_price,
            kol_name=kol_name,
            kol_handle="",
            kol_persona=kol_persona,
            kol_styles=kol_styles,
            creator_archetype=creator_archetype,
            is_review_creator=is_review_creator,
            median_er=median_er,
            is_spam=is_spam,
        )
        hooks = [match_data.get("conversion_angle")] if match_data and match_data.get("conversion_angle") else []
        return rationale, hooks

    async def classify_creator_archetypes(
        self,
        creators: List[Dict[str, Any]],
        batch_size: int = 20,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Classifies creators into 4 Core Archetypes using LLM Instructions (Zero-Hardcode Policy).
        Evaluates creator intent, content delivery style, and audience value proposition via Gemini LLM.
        Differentiates Educated Guru (knowledge-sharing/technique/drills) from Lifestyle & Vlog (travel/daily routine),
        Top Reviewer (product unboxing/comparison/buying intent), and Niche Enthusiast (subculture immersion).
        """
        if not self.is_configured or not creators:
            return {}

        import asyncio

        chunks = [creators[i:i + batch_size] for i in range(0, len(creators), batch_size)]

        async def _classify_chunk(chunk: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
            clean_items = []
            for c in chunk:
                clean_items.append({
                    "id": c.get("id") or c.get("handle"),
                    "handle": c.get("handle", ""),
                    "display_name": c.get("display_name", ""),
                    "bio": c.get("bio", ""),
                    "recent_video_captions": [str(cap)[:150] for cap in c.get("captions", []) if cap][:5],
                    "yellow_basket_ratio": c.get("yellow_basket_ratio", 0.0),
                    "vertical": c.get("vertical", ""),
                })

            prompt = f"""You are the Lead Creator Categorization & Audience Strategist for TikTok Thailand at Convert Cake.
Your task is to classify each creator into their true Creator Archetype and recommend their campaign role based on the INSTRUCTION CRITERIA below.

CRITICAL INSTRUCTIONS - ZERO HARDCODED KEYWORDS:
Do NOT simply match keywords or words in bio. Understand the semantics, tone, intent, and core value proposition that each creator provides to their viewers.

4 Core Creator Archetypes & Classification Guidelines:

1. 'Educated Guru' (Recommended Role: 'Trust & Credibility')
   - Core Value: Knowledge transfer, skill training, technical analysis, and educational problem-solving.
   - Content Focus: Deep educational breakdowns, step-by-step tutorials, technique drills, correcting common mistakes/posture, explaining the science/mechanics/ingredients, medical/health/sports coaching, professional advice.
   - Distinction vs Lifestyle/Travel: A creator going on a ski trip or vacation vlog is NOT a guru; an instructor teaching edging drills, balance posture, and safety rules IS an Educated Guru.

2. 'Top Reviewer' (Recommended Role: 'Conversion & Sales')
   - Core Value: Product evaluation, buying decision assistance, and commercial shoppertainment.
   - Content Focus: Hands-on testing, unboxings, comparative testing (A vs B), honest pros/cons, shopping haul reviews, price-to-value assessment, TikTok Shop yellow basket showcases.
   - Distinction: Content explicitly tests items to tell followers whether to buy or where to get them (พิกัด).

3. 'Lifestyle & Vlog' (Recommended Role: 'Brand Awareness & Discovery')
   - Core Value: Entertainment, aesthetic relatability, and personal lifestyle inspiration.
   - Content Focus: Daily life vlogs, travel diaries, holiday trips, aesthetic routines (GRWM, Day in my life), cafe hopping, food experiences, fashion/OOTD, humor, casual storytelling.
   - Distinction vs Guru: They document their personal experiences, travels, and lifestyle rather than providing structured education or technical skill instruction.

4. 'Niche Enthusiast' (Recommended Role: 'Hyper-Targeted Reach')
   - Core Value: Subculture authenticity, passionate hobby immersion, and community connection.
   - Content Focus: Deep immersion in a specific subculture, extreme sport, dedicated hobby, or passionate community (e.g., ski/snowboard riders, mechanical keyboards, custom car tuning, pet breeding, retro gaming).
   - Distinction: Content is deeply embedded in the specific enthusiast community and subculture rather than general mass lifestyle.

5. 'General Creator' (Recommended Role: 'Brand Awareness')
   - Broad entertainment, comedy, or mixed casual content that doesn't strongly lean into one of the 4 defined archetypes.

Creators to Classify:
{json.dumps(clean_items, ensure_ascii=False, indent=2)}

Return ONLY a valid JSON object mapping each creator's 'id' to their classification:
{{
  "<creator_id>": {{
    "creator_archetype": "Educated Guru" | "Top Reviewer" | "Lifestyle & Vlog" | "Niche Enthusiast" | "General Creator",
    "recommended_role": "Trust & Credibility" | "Conversion & Sales" | "Brand Awareness & Discovery" | "Hyper-Targeted Reach" | "Brand Awareness",
    "reasoning": "A concise 1-sentence explanation in Thai explaining why their content fits this archetype based on the instructions"
  }}
}}
"""
            try:
                response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=self.llm_model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.2,
                    ),
                )
                if response and response.text:
                    parsed = json.loads(response.text)
                    if isinstance(parsed, dict):
                        return parsed
            except Exception as e:
                print(f"[GeminiService] Error classifying creator batch: {e}")
            return {}

        results = await asyncio.gather(*[_classify_chunk(chunk) for chunk in chunks])
        merged = {}
        for r in results:
            merged.update(r)
        return merged

    async def generate_audience_comments(
        self, kol_name: str, handle: str, bio: str, captions: List[str], vertical: str
    ) -> List[str]:
        """
        Uses Gemini to generate 4 realistic, context-specific Thai audience comments/inquiries
        based on the creator's real video captions and content topics.
        """
        if not self.is_configured:
            return []

        captions_sample = [c[:120] for c in captions if c][:4] if captions else []
        prompt = f"""You are an expert analyzing real Thai TikTok audience engagement and prospective buyers.
Creator: {kol_name} (@{handle})
Vertical: {vertical}
Bio: {bio}
Recent Video Captions/Topics: {json.dumps(captions_sample, ensure_ascii=False) if captions_sample else 'General ' + vertical + ' content'}

Generate 4 distinct, authentic, natural Thai audience comments or buyer inquiries that real followers would post (e.g. asking for price/where to buy/พิกัด, asking if suitable for their use case, or sharing real feedback).
Return ONLY a valid JSON list of 4 strings:
["comment 1", "comment 2", "comment 3", "comment 4"]
"""
        try:
            response = self.client.models.generate_content(
                model=self.llm_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.7,
                ),
            )
            if response and response.text:
                comments = json.loads(response.text)
                if isinstance(comments, list) and len(comments) > 0:
                    return [str(c).strip() for c in comments[:4] if str(c).strip()]
        except Exception as e:
            print(f"[GeminiService] Audience comments generation error: {e}")
        return []


_gemini_service_instance: Optional[GeminiService] = None

def get_gemini_service() -> GeminiService:
    global _gemini_service_instance
    if _gemini_service_instance is None:
        _gemini_service_instance = GeminiService()
    return _gemini_service_instance
