import os
import json
import math
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
    2. Gemini Main LLM (`gemini-3.5-flash-lite` or configurable) for Brand DNA synthesis, matching rationale, and Thai campaign hooks.
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
            # Google GenAI SDK embedContent API call for gemini-embedding-2
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
        # Map from [-1, 1] to [0, 1]
        return max(0.0, min(1.0, (cos + 1.0) / 2.0))

    async def generate_brand_dna(
        self, scraped_text: str, brand_name: str, website_url: str, fb_url: str
    ) -> Optional[Dict[str, Any]]:
        """
        Uses Gemini Main LLM to extract structured Brand DNA from scraped web & FB text.
        """
        if not self.is_configured:
            return None

        prompt = f"""You are an expert Chief Strategy Officer at a premier Thai digital marketing agency (Convert Cake).
Analyze this brand's website content and Facebook information to synthesize structured Brand DNA.

Brand Name: {brand_name}
Website: {website_url}
Facebook: {fb_url}
Scraped Context:
{scraped_text[:3500]}

Respond ONLY with a valid JSON object matching this schema:
{{
  "brand_name": "{brand_name}",
  "vertical": "One of: 'Beauty & Skincare' | 'Cafe / F&B & Lifestyle' | 'Gadgets / Home & Living'",
  "sub_category": "Specific niche (e.g. Dermocosmetics, Matcha Specialty, Ergonomic Desks)",
  "brand_summary": "2-3 sentence strategic agency summary in English or Thai",
  "target_audience": "Detailed target demographic and lifestyle in Thailand",
  "target_age_range": "e.g. '18-24', '22-35', '28-45'",
  "target_locations": ["Bangkok", "Nonthaburi", "Chiang Mai"],
  "brand_tone": ["Friendly", "Scientific", "Aesthetic"],
  "content_style_preferences": ["GRWM", "Honest Review", "Aesthetic B-Roll"],
  "price_positioning": "One of: 'Budget / Mass' | 'Mid-Range / Accessible' | 'Premium / Masstige' | 'Luxury / High-End'",
  "average_price_thb": 590,
  "thai_keywords": ["5-8 Thai search tags and hashtags without #, e.g. สกินแคร์, ผิวแพ้ง่าย, ป้ายยา"]
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

    async def generate_hooks_and_rationale(
        self, brand_name: str, brand_vertical: str, brand_price: int,
        kol_name: str, kol_persona: str, kol_styles: List[str],
        median_er: float, is_spam: bool, spam_reason: str
    ) -> Tuple[Optional[str], Optional[List[str]]]:
        """
        Uses Gemini Main LLM to produce creative agency-grade Thai TikTok campaign hooks
        and customized strategic matching rationale.
        """
        if not self.is_configured or is_spam:
            return None, None

        prompt = f"""You are an award-winning Creative Director at Convert Cake, specializing in Thai TikTok viral campaigns.
Draft 3 distinct, viral, high-converting Thai TikTok video opening hooks and a 2-sentence agency rationale for pairing this KOL with the client brand.

Client Brand: {brand_name} (Vertical: {brand_vertical}, Price: {brand_price:,} THB)
Creator: {kol_name}
Persona & Aesthetic: {kol_persona}
Content Styles: {', '.join(kol_styles)}
Median Engagement Rate: {median_er:.1f}%

Return ONLY JSON:
{{
  "rationale": "2-sentence strategic justification for why this creator is an exceptional match for the brand",
  "hooks": [
    "Hook 1: First 3 seconds spoken line or on-screen text in natural Thai language (engaging/curiosity)",
    "Hook 2: Relatable problem/solution hook in Thai",
    "Hook 3: GRWM / Storytelling / Aesthetic hook in Thai"
  ]
}}
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
                data = json.loads(response.text)
                return data.get("rationale"), data.get("hooks")
        except Exception as e:
            print(f"[GeminiService] LLM hooks generation error: {e}")
        return None, None

    async def generate_audience_comments(
        self, kol_name: str, handle: str, bio: str, captions: List[str], vertical: str
    ) -> List[str]:
        """
        Uses Gemini to generate 4 realistic, context-specific Thai audience comments/inquiries
        based on the creator's real video captions and content topics (eliminating static mocks).
        """
        if not self.is_configured:
            return []

        captions_sample = [c[:120] for c in captions if c][:4] if captions else []
        prompt = f"""You are an expert analyzing real Thai TikTok audience engagement and prospective buyers.
Creator: {kol_name} (@{handle})
Vertical: {vertical}
Bio: {bio}
Recent Video Captions/Topics: {json.dumps(captions_sample, ensure_ascii=False) if captions_sample else 'General ' + vertical + ' content'}

Based on this creator's actual content niche and brand vertical, generate 4 distinct, authentic, natural Thai audience comments or buyer inquiries that real followers would post under these videos (e.g. asking for price/where to buy, asking if suitable for their use case, sharing feedback, or asking for usage tips).
IMPORTANT: Strictly match the vertical '{vertical}'! Do NOT use skincare comments for food or tech brands. Make them authentic and conversational.

Return ONLY a valid JSON list of 4 strings:
[
  "comment 1 in natural Thai",
  "comment 2 in natural Thai",
  "comment 3 in natural Thai",
  "comment 4 in natural Thai"
]"""
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
