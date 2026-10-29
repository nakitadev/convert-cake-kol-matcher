"""
Stage 3 — Dynamic Scoring Engine (Spec 4.3 - 100 คะแนนเต็ม).

3 Balanced Dimensions:
1. Brand & Funnel Relevance (40 คะแนน):
   - Semantic & LLM Fit Score (28 คะแนน): Cosine similarity (Brand Embedding vs Bio + Captions)
     blended with LLM Relevance Gate score.
   - Sub-Niche & Work-Ready Bonus (12 คะแนน): Niche keyword matches (8 pts) + Work-Ready signal (4 pts).
2. Engagement Quality & Content Utility (35 คะแนน):
   - Median Engagement Rate (15 คะแนน): (Likes + Comments + Shares + Saves) / Views median on clips >= 500 views.
   - Save & Share Utility Score (10 คะแนน): (collectCount + 0.7 * shareCount) / max(playCount, 500),
     bonus for 'KOL - Expert / Guru'.
   - View Consistency Ratio (10 คะแนน): Median Views / Mean Views.
3. Audience Proxy & Commercial Viability (25 คะแนน):
   - Thai Audience Authenticity (10 คะแนน): Thai character presence in captions and comments.
   - Buyer Intent Proxy (10 คะแนน): Tier-1 Fast Proxy vs Tier-2 Targeted Comment Analysis for Top-K.
   - Brand-Adaptive Affiliate Health (5 คะแนน):
     * ECOMMERCE_PRODUCT: KOC - Hard-Sell Reviewer with high basket & engagement gets full 5/5.
     * LIFESTYLE_EXPERIENCE & HIGH_TICKET_LEADGEN: basket > 70% penalized to favor clean-image creators.
     * Otherwise balanced ratio.
"""
import re
import asyncio
from statistics import median, mean
from typing import List, Tuple, Dict, Any, Optional

import numpy as np

from app.models import (
    BrandDNA,
    KOLProfile,
    SignalBreakdown,
)
from app.services.gemini_service import get_gemini_service

THAI_CHAR_PATTERN = re.compile(r"[\u0E00-\u0E7F]")

BUYER_INTENT_KEYWORDS = [
    "ราคา", "พิกัด", "ซื้อที่ไหน", "ใช้ดีไหม", "ใช้ดีมั้ย", "สั่งซื้อ",
    "เท่าไหร่", "กี่บาท", "สนใจ", "ป้ายยา", "สั่งจากไหน", "ดีจริง", "ของแท้ไหม"
]


class ScoringEngine:
    """
    Performance & Proxy-Driven Scoring Engine (100 Points Total)
    Spec 4.3 implementation.
    """

    def get_kol_text_corpus(self, kol: KOLProfile) -> str:
        captions = " ".join([v.caption for v in kol.recent_videos if v.caption])
        hashtags = " ".join([t for v in kol.recent_videos for t in v.hashtags if t])
        return f"{kol.display_name} @{kol.handle} {kol.bio} {captions} {hashtags}".lower()

    def get_brand_text_corpus(self, brand: BrandDNA) -> str:
        return (
            f"{brand.brand_name} {brand.vertical} {brand.sub_category} "
            f"{brand.brand_summary} {brand.target_audience} "
            f"{' '.join(brand.brand_tone)} {' '.join(brand.niche_keywords)} "
            f"{' '.join([q.query for q in brand.search_queries])}"
        ).lower()

    def evaluate_kol(
        self,
        kol: KOLProfile,
        brand: BrandDNA,
        kol_embedding: Optional[List[float]] = None,
        brand_embedding: Optional[List[float]] = None,
    ) -> Tuple[float, SignalBreakdown]:
        evidence: List[str] = []

        # -------------------------------------------------------------
        # 1. Brand & Funnel Relevance (40 คะแนน)
        # -------------------------------------------------------------
        # 1.1 Semantic & LLM Fit Score (28 คะแนน)
        gemini = get_gemini_service()
        cos_sim = 0.0
        if kol_embedding and brand_embedding:
            cos_sim = gemini.cosine_similarity(brand_embedding, kol_embedding)
        else:
            # Token fallback if embeddings unavailable
            b_tokens = set(re.findall(r"\w+", self.get_brand_text_corpus(brand)))
            k_tokens = set(re.findall(r"\w+", self.get_kol_text_corpus(kol)))
            overlap = len(b_tokens & k_tokens)
            union = len(b_tokens | k_tokens) or 1
            cos_sim = min(1.0, max(0.05, (overlap / union) * 4.0))

        # Normalized cosine [0, 1]
        norm_cos = max(0.0, min(1.0, (cos_sim + 1.0) / 2.0 if cos_sim < 0 else cos_sim))
        llm_score = kol.llm_relevance_score if kol.llm_relevance_score > 0 else norm_cos
        blended_fit = (norm_cos * 0.5) + (llm_score * 0.5)
        semantic_llm_pts = round(blended_fit * 30.0, 2)

        # 1.2 Sub-Niche & Work-Ready Bonus (10 คะแนน - Spec 4.3)
        corpus = self.get_kol_text_corpus(kol)
        matched_kw: List[str] = []
        for kw in brand.niche_keywords:
            clean_kw = kw.strip().lower()
            if clean_kw and clean_kw in corpus:
                matched_kw.append(kw)

        kw_ratio = len(matched_kw) / max(len(brand.niche_keywords), 1)
        kw_pts = min(6.0, kw_ratio * 6.0)
        work_ready_pts = 4.0 if kol.is_work_ready else 0.0
        subniche_work_pts = round(kw_pts + work_ready_pts, 2)

        relevance_total = round(min(40.0, semantic_llm_pts + subniche_work_pts), 2)
        evidence.append(f"Relevance ({relevance_total}/40): Cosine {cos_sim:.2f}, LLM fit {llm_score:.2f}, matched {len(matched_kw)} niche tags.")
        if kol.is_work_ready:
            evidence.append("Work-Ready signal confirmed (+4.0 bonus).")

        # -------------------------------------------------------------
        # 2. Engagement Quality & Content Utility (35 คะแนน)
        # -------------------------------------------------------------
        videos = kol.recent_videos
        # Filter eligible clips with playCount >= 500 (Spec 4.3)
        eligible = [v for v in videos if v.views >= 500]
        clips_to_score = eligible if eligible else videos
        eligible_count = len(eligible)

        if clips_to_score:
            er_list = [
                ((v.likes + v.comments + v.shares + v.collect_count) / max(v.views, 1))
                for v in clips_to_score
            ]
            median_er = float(median(er_list))
            # 8% ER gets full 15 pts
            er_pts = round(min(15.0, (median_er / 0.08) * 15.0), 2)

            # Save & Share Utility Score (10 pts)
            # equation: (collectCount + 0.7 * shareCount) / max(playCount, 500)
            util_list = [
                ((v.collect_count + (0.7 * v.shares)) / max(v.views, 500))
                for v in clips_to_score
            ]
            median_util = float(median(util_list))
            # 3.5% utility gets 8.0 pts base
            base_util_pts = (median_util / 0.035) * 8.0
            if kol.sub_style == "KOL - Expert / Guru":
                base_util_pts += 2.0  # Special bonus for Expert/Guru
            utility_pts = round(min(10.0, max(1.0, base_util_pts)), 2)

            # View Consistency Ratio (10 pts): Median Views / Mean Views
            views_list = [v.views for v in clips_to_score]
            med_views = float(median(views_list))
            avg_views = float(mean(views_list))
            consistency_ratio = (med_views / max(avg_views, 1.0)) if avg_views > 0 else 0.5
            consistency_pts = round(min(10.0, max(2.0, consistency_ratio * 10.0)), 2)
        else:
            median_er = 0.03
            er_pts = 5.0
            median_util = 0.01
            utility_pts = 3.0
            consistency_ratio = 0.5
            consistency_pts = 5.0

        engagement_total = round(min(35.0, er_pts + utility_pts + consistency_pts), 2)
        evidence.append(
            f"Engagement ({engagement_total}/35): Median ER {median_er*100:.1f}% ({er_pts}/15), "
            f"Utility {median_util*100:.2f}% ({utility_pts}/10), Consistency {consistency_ratio:.2f} ({consistency_pts}/10)."
        )

        # -------------------------------------------------------------
        # 3. Audience Proxy & Commercial Viability (25 คะแนน)
        # -------------------------------------------------------------
        # 3.1 Thai Audience Authenticity (10 คะแนน)
        all_text = " ".join([v.caption for v in videos] + kol.real_comments)
        thai_char_count = len(THAI_CHAR_PATTERN.findall(all_text))
        total_chars = len(all_text) or 1
        thai_ratio = round(min(1.0, (thai_char_count * 2.5) / total_chars), 3) if all_text.strip() else 0.8
        thai_pts = round(min(10.0, max(2.0, thai_ratio * 10.0)), 2)

        # 3.2 Buyer Intent Proxy (10 คะแนน)
        buyer_intent_tier = "tier1_fast_proxy"
        if kol.real_comments and len(kol.real_comments) >= 5:
            buyer_intent_tier = "tier2_comment_analysis"
            # Count comments with purchase intent keywords
            intent_matches = sum(
                1 for c in kol.real_comments
                if any(kw in c.lower() for kw in BUYER_INTENT_KEYWORDS)
            )
            intent_ratio = intent_matches / len(kol.real_comments)
            kol.comment_intent_ratio = round(intent_ratio, 3)
            # 25% purchase-intent comments yields full 10 pts
            buyer_pts = round(min(10.0, max(2.5, (intent_ratio / 0.25) * 10.0)), 2)
            evidence.append(f"Buyer Intent Tier-2 ({buyer_pts}/10): {intent_matches}/{len(kol.real_comments)} comments asked for price/where to buy.")
        else:
            # Tier-1 Fast Proxy: commentCount/diggCount and shareCount/diggCount
            c_to_l = kol.signals.comment_to_like
            s_to_l = kol.signals.share_to_like
            # Typical c_to_l ~ 0.015, s_to_l ~ 0.01
            proxy_val = (c_to_l * 1.5) + (s_to_l * 1.0)
            buyer_pts = round(min(10.0, max(2.5, proxy_val * 200.0)), 2)
            evidence.append(f"Buyer Intent Tier-1 Fast Proxy ({buyer_pts}/10): Comment/Like {c_to_l:.4f}, Share/Like {s_to_l:.4f}.")

        # 3.3 Brand-Adaptive Affiliate Health (5 คะแนน)
        basket_ratio = kol.signals.basket_ratio
        conv_model = brand.conversion_model

        if conv_model == "ECOMMERCE_PRODUCT":
            # E-commerce: KOC - Hard-Sell Reviewer with high basket & engagement gets full 5/5
            if kol.sub_style == "KOC - Hard-Sell Reviewer" and median_er >= 0.015:
                affiliate_pts = 5.0
                evidence.append(f"Affiliate Health (5/5): Top Hard-Sell Reviewer with {basket_ratio:.0%} basket driving direct conversions.")
            elif basket_ratio <= 0.85:
                affiliate_pts = 5.0
            else:
                affiliate_pts = 4.0
        elif conv_model in ("LIFESTYLE_EXPERIENCE", "HIGH_TICKET_LEADGEN"):
            # High-ticket / Luxury: basket > 70% penalized to favor cleaner image channels
            if basket_ratio > 0.70:
                affiliate_pts = 1.5
                evidence.append(f"Affiliate Health (1.5/5): High commercial basket density ({basket_ratio:.0%}) penalized for {conv_model} prestige.")
            elif basket_ratio > 0.40:
                affiliate_pts = 3.5
            else:
                affiliate_pts = 5.0
                evidence.append(f"Affiliate Health (5/5): Clean image profile with low basket density ({basket_ratio:.0%}).")
        else:
            # APP_DIGITAL_SERVICE
            if basket_ratio > 0.70:
                affiliate_pts = 3.0
            else:
                affiliate_pts = 5.0

        audience_total = round(min(25.0, thai_pts + buyer_pts + affiliate_pts), 2)

        # Total 100
        total_score = round(min(100.0, max(0.0, relevance_total + engagement_total + audience_total)), 1)

        breakdown = SignalBreakdown(
            relevance_total=relevance_total,
            semantic_llm_points=semantic_llm_pts,
            cosine_similarity=round(cos_sim, 3),
            subniche_workready_points=subniche_work_pts,
            matched_keywords=matched_kw,
            engagement_total=engagement_total,
            median_er_points=er_pts,
            median_engagement_rate=round(median_er, 4),
            eligible_clips=eligible_count,
            utility_points=utility_pts,
            utility_score=round(median_util, 4),
            consistency_points=consistency_pts,
            view_consistency_ratio=round(consistency_ratio, 3),
            audience_total=audience_total,
            thai_authenticity_points=thai_pts,
            thai_ratio=thai_ratio,
            buyer_intent_points=buyer_pts,
            buyer_intent_tier=buyer_intent_tier,
            affiliate_health_points=round(affiliate_pts, 2),
            evidence=evidence,
        )

        return total_score, breakdown

    async def evaluate_kols_batch(
        self,
        kols: List[KOLProfile],
        brand: BrandDNA,
    ) -> List[Tuple[float, SignalBreakdown]]:
        """
        Batch-evaluate all creators asynchronously with Gemini embeddings.
        """
        if not kols:
            return []

        gemini = get_gemini_service()
        brand_embedding: Optional[List[float]] = None
        kol_embeddings: List[Optional[List[float]]] = [None] * len(kols)

        if gemini.is_configured:
            brand_corpus = self.get_brand_text_corpus(brand)
            kol_corpora = [self.get_kol_text_corpus(k) for k in kols]
            brand_task = gemini.get_embedding_async(brand_corpus)
            kols_task = gemini.get_embeddings_batch(kol_corpora, max_concurrency=15)
            brand_res, kols_res = await asyncio.gather(brand_task, kols_task)
            brand_embedding = brand_res
            kol_embeddings = kols_res

        results = []
        for kol, k_emb in zip(kols, kol_embeddings):
            score, breakdown = self.evaluate_kol(
                kol=kol,
                brand=brand,
                kol_embedding=k_emb,
                brand_embedding=brand_embedding,
            )
            results.append((score, breakdown))

        return results


_engine_instance: Optional[ScoringEngine] = None


def get_scoring_engine() -> ScoringEngine:
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = ScoringEngine()
    return _engine_instance
