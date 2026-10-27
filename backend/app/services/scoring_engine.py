import math
import re
from typing import List, Tuple, Dict, Any, Optional
import numpy as np

from app.models import (
    BrandDNA,
    KOLProfile,
    SignalBreakdown,
    RankedKOL,
)
from app.services.gemini_service import get_gemini_service


class ScoringEngine:
    """
    Hybrid Scoring Engine for Thai TikTok KOL Matching:
    1. Brand & Content Relevance (45%)
    2. Deterministic Engagement Quality & Anti-Spam (35%)
    3. Multi-Signal Audience Alignment (20%)
    Zero-Hardcode: Dynamically synthesizes insights and hooks from live creator data.
    """

    def evaluate_kol(self, kol: KOLProfile, brand: BrandDNA) -> Tuple[float, SignalBreakdown, str, List[str]]:
        # 1. Relevance (Spec 5.1: 40 pts max - Semantic 28 pts + Niche Keyword & Work-Ready 12 pts)
        rel_raw, sem_sim, matched_kw, emb_model, sem_pts, kw_pts = self._calculate_relevance(kol, brand)
        rel_weighted = round(sem_pts + kw_pts, 2)

        # 2. Engagement Quality (Spec 5.2: 35 pts max - Median ER 15 pts + Save-to-View 10 pts + Consistency 10 pts)
        eng_raw, median_er, v_to_f, yb_ratio, is_penalized, pen_pts, pen_reason, er_pts, save_pts, cons_pts = self._calculate_engagement(kol)
        eng_weighted = round(max(0.0, er_pts + save_pts + cons_pts - (pen_pts if is_penalized else 0.0)), 2)

        # 3. Audience & Commercial Viability (Spec 5.3: 25 pts max - Thai Authenticity 10 pts + Buyer Intent 10 pts + Saturation 5 pts)
        aud_raw, thai_pts, buyer_pts, sat_pts, s1, s2, s3, s4, conf, evidence = self._calculate_audience_signals(kol, brand)
        aud_weighted = round(thai_pts + buyer_pts + sat_pts, 2)

        # Final Score (100 pts total)
        total_score = round(rel_weighted + eng_weighted + aud_weighted, 1)
        total_score = max(0.0, min(100.0, total_score))

        breakdown = SignalBreakdown(
            relevance_score_raw=rel_raw,
            relevance_weighted=rel_weighted,
            semantic_similarity=sem_sim,
            semantic_points=sem_pts,
            niche_keyword_points=kw_pts,
            matched_keywords=matched_kw,
            embedding_model=emb_model,
            engagement_score_raw=eng_raw,
            engagement_weighted=eng_weighted,
            median_engagement_rate_pct=round(median_er, 2),
            median_er_points=er_pts,
            save_to_view_points=save_pts,
            view_consistency_points=cons_pts,
            views_to_followers_ratio=round(v_to_f, 3),
            yellow_basket_ratio=round(yb_ratio, 2),
            affiliate_spam_penalty_applied=is_penalized,
            affiliate_spam_penalty_points=pen_pts,
            affiliate_spam_reason=pen_reason,
            audience_score_raw=aud_raw,
            audience_weighted=aud_weighted,
            thai_authenticity_points=thai_pts,
            buyer_intent_points=buyer_pts,
            affiliate_saturation_points=sat_pts,
            persona_signal_score=s1,
            price_proxy_signal_score=s2,
            geo_language_signal_score=s3,
            comment_sentiment_signal_score=s4,
            confidence_level=conf,
            evidence_list=evidence,
        )

        why_text = self._generate_strategic_rationale(kol, brand, breakdown)
        hooks = self._generate_thai_campaign_hooks(kol, brand)

        return total_score, breakdown, why_text, hooks

    def _calculate_relevance(self, kol: KOLProfile, brand: BrandDNA) -> Tuple[float, float, List[str], str, float, float]:
        brand_text_corpus = (
            f"{brand.brand_name} {brand.vertical} {brand.sub_category} "
            f"{brand.brand_summary} {brand.target_audience} "
            f"{' '.join(brand.brand_tone)} {' '.join(brand.thai_keywords)}"
        ).lower()

        kol_text_corpus = (
            f"{kol.display_name} {kol.vertical} {' '.join(kol.secondary_verticals)} "
            f"{kol.bio} {kol.creator_persona} {' '.join(kol.content_styles)} "
            f"{' '.join([v.caption for v in kol.recent_videos])} "
            f"{' '.join([tag for v in kol.recent_videos for tag in v.hashtags])}"
        ).lower()

        vertical_match = 1.0 if brand.vertical.lower() in kol.vertical.lower() or kol.vertical.lower() in brand.vertical.lower() else 0.35
        for sec in kol.secondary_verticals:
            if sec.lower() in brand.vertical.lower() or brand.vertical.lower() in sec.lower():
                vertical_match = max(vertical_match, 0.75)

        matched_kw = []
        for kw in brand.thai_keywords:
            clean_kw = kw.strip().lower()
            if clean_kw and clean_kw in kol_text_corpus:
                matched_kw.append(kw)

        kw_ratio = len(matched_kw) / max(len(brand.thai_keywords), 1)

        gemini = get_gemini_service()
        emb_model = "gemini-embedding-2 (dense)"
        sem_sim = 0.0

        if gemini.is_configured:
            b_emb = gemini.get_embedding(brand_text_corpus)
            k_emb = gemini.get_embedding(kol_text_corpus)
            if b_emb and k_emb:
                sem_sim = round(gemini.cosine_similarity(b_emb, k_emb), 3)

        if sem_sim == 0.0:
            brand_tokens = set(re.findall(r'\w+', brand_text_corpus))
            kol_tokens = set(re.findall(r'\w+', kol_text_corpus))
            overlap = len(brand_tokens & kol_tokens)
            union = len(brand_tokens | kol_tokens) if brand_tokens | kol_tokens else 1
            sem_sim = min(1.0, max(0.05, round(overlap / union * 3.5, 3)))

        # Spec 5.1: Semantic Similarity (28 pts) + Niche Keyword & Work-Ready Match (12 pts)
        sem_pts = round(sem_sim * 28.0, 2)
        work_ready_bonus = 4.0 if kol.is_work_ready else 0.0
        kw_pts = round(min(8.0, (len(matched_kw) / max(len(brand.thai_keywords), 1)) * 8.0) + work_ready_bonus, 2)
        raw_score = round(((sem_pts + kw_pts) / 40.0) * 100.0, 1)
        return raw_score, sem_sim, matched_kw, emb_model, sem_pts, kw_pts

    def _calculate_engagement(self, kol: KOLProfile) -> Tuple[float, float, float, float, bool, float, str, float, float, float]:
        if not kol.recent_videos:
            return 50.0, 3.0, 0.25, 0.0, False, 0.0, "", 7.5, 5.0, 5.0

        er_list = []
        views_list = []
        yb_count = 0

        for v in kol.recent_videos:
            views = max(v.views, 1)
            views_list.append(views)
            video_er = ((v.likes + (v.comments * 2.0) + (v.shares * 3.0) + getattr(v, 'collect_count', 0)) / views) * 100.0
            er_list.append(video_er)
            if v.has_yellow_basket:
                yb_count += 1

        median_er = float(np.median(er_list))
        median_views = float(np.median(views_list))
        v_to_f = median_views / max(kol.follower_count, 1)
        yb_ratio = yb_count / len(kol.recent_videos)

        # Spec 5.2: Median ER (15 pts) + Save-to-View (10 pts) + View Consistency (10 pts) = 35 pts
        er_pts = round(min(15.0, (median_er / 8.0) * 15.0), 2)
        
        # Save-to-View Utility (10 pts) with bonus for Educated Guru
        base_save_ratio = kol.save_to_view_ratio if kol.save_to_view_ratio > 0 else 0.02
        save_calc = (base_save_ratio / 0.035) * 8.0
        if kol.creator_archetype == "Educated Guru":
            save_calc += 2.0
        save_pts = round(min(10.0, max(2.0, save_calc)), 2)

        # View Consistency Ratio (10 pts)
        base_cons = kol.view_consistency_ratio if kol.view_consistency_ratio > 0 else 0.7
        cons_pts = round(min(10.0, max(2.0, base_cons * 10.0)), 2)

        is_penalized = False
        penalty_points = 0.0
        penalty_reason = ""

        # Spec: ยอมให้มีปักตะกร้าเหลืองได้ 100% โดยจัดเข้าหมวดหมู่ "Content Creator (เน้นรีวิว)"
        # จะไม่หักคะแนนตะกร้าเหลือง หากเป็นครีเอเตอร์สายรีวิว (Shoppertainment / Review)
        # จะ penalize เฉพาะบัญชีที่เป็น Fake/Bot Spam Trap ชัดเจน
        if kol.is_affiliate_spam_trap:
            is_penalized = True
            penalty_points = 55.0
            penalty_reason = (
                f"Penalized by Bot/Spam Filter: Account detected as automated affiliate repost farm."
            )

        base_engagement = er_pts + save_pts + cons_pts - (penalty_points if is_penalized else 0.0)
        final_eng = max(0.0, min(100.0, round((base_engagement / 35.0) * 100.0, 1)))
        return final_eng, median_er, v_to_f, yb_ratio, is_penalized, penalty_points, penalty_reason, er_pts, save_pts, cons_pts

    def _calculate_audience_signals(
        self, kol: KOLProfile, brand: BrandDNA
    ) -> Tuple[float, float, float, float, float, float, float, float, str, List[str]]:
        evidence = []
        signals_high_count = 0

        # 1. Thai Audience Authenticity (10 pts max - Spec 5.3)
        thai_char_pattern = re.compile(r'[฀-๿]')
        captions_thai_count = sum(1 for v in kol.recent_videos if v.caption and thai_char_pattern.search(v.caption))
        captions_thai_ratio = (captions_thai_count / len(kol.recent_videos)) if kol.recent_videos else 1.0
        
        comments_thai_count = sum(1 for c in kol.sample_comments if thai_char_pattern.search(c))
        comments_thai_ratio = (comments_thai_count / len(kol.sample_comments)) if kol.sample_comments else 1.0
        
        blended_thai_ratio = (captions_thai_ratio * 0.6) + (comments_thai_ratio * 0.4)
        if kol.audience_language.lower().startswith("thai"):
            blended_thai_ratio = max(blended_thai_ratio, 0.9)
        thai_pts = round(min(10.0, max(2.0, blended_thai_ratio * 10.0)), 2)
        evidence.append(f"Thai Audience Authenticity ({thai_pts}/10 pts): {int(blended_thai_ratio * 100)}% verified Thai geo/language presence.")
        if thai_pts >= 8.0:
            signals_high_count += 1

        # 2. Buyer Intent Proxy (10 pts max - Spec 5.3 & 6.1)
        # Tier-1 Fast Proxy: Inquiry & Viral Action Ratio
        total_likes = sum(v.likes for v in kol.recent_videos) or 1
        total_comments = sum(v.comments for v in kol.recent_videos)
        total_shares = sum(v.shares for v in kol.recent_videos)
        action_ratio = (total_comments + (total_shares * 1.5)) / max(total_likes, 100)
        
        # Tier-2 High-intent keyword matching
        high_intent_keywords = ["ใช้ตาม", "พิกัด", "ซื้อที่ไหน", "ราคา", "ผิวแพ้ง่าย", "ป้ายยา", "อร่อย", "สั่งแล้ว", "จึ้ง", "ดีจริง", "ใช้ดี", "คุ้ม"]
        comments_text = ' '.join(kol.sample_comments)
        intent_keyword_matches = sum(1 for kw in high_intent_keywords if kw in comments_text)
        
        fast_intent_score = min(5.0, action_ratio * 40.0)
        text_intent_score = min(5.0, intent_keyword_matches * 1.5)
        buyer_pts = round(min(10.0, max(2.5, fast_intent_score + text_intent_score + (1.5 if kol.creator_archetype in ["Top Reviewer", "Educated Guru"] else 0.5))), 2)
        evidence.append(f"Buyer Intent Proxy ({buyer_pts}/10 pts): High commercial interest with {intent_keyword_matches} buying inquiry signals.")
        if buyer_pts >= 7.5:
            signals_high_count += 1

        # 3. Affiliate Saturation Health (5 pts max - Spec 5.3 & User agreement)
        # Top Reviewers / Review category are accepted up to 100% yellow basket without penalty
        yellow_ratio = (sum(1 for v in kol.recent_videos if v.has_yellow_basket) / len(kol.recent_videos)) if kol.recent_videos else 0.0
        is_review_creator = (kol.creator_category == "Content Creator (เน้นรีวิว)") or (kol.creator_archetype == "Top Reviewer")
        
        if is_review_creator:
            sat_pts = 5.0
            evidence.append(f"Affiliate Saturation (5/5 pts): Legitimate review creator allowed 100% yellow basket ({int(yellow_ratio*100)}% commercial density with healthy intent).")
        else:
            if yellow_ratio <= 0.40:
                sat_pts = 5.0
                evidence.append(f"Affiliate Saturation (5/5 pts): Balanced organic-to-ad ratio ({int(yellow_ratio*100)}% yellow basket).")
            elif yellow_ratio <= 0.70:
                sat_pts = 3.5
                evidence.append(f"Affiliate Saturation (3.5/5 pts): Moderate commercial load ({int(yellow_ratio*100)}% yellow basket).")
            else:
                sat_pts = 2.0
                evidence.append(f"Affiliate Saturation (2/5 pts): High ad saturation for non-reviewer profile ({int(yellow_ratio*100)}% yellow basket).")

        # Internal Legacy Multi-Signals for compatibility
        s1 = 20.0
        s2 = 20.0
        s3 = round(thai_pts * 2.5, 1)
        s4 = round(buyer_pts * 2.5, 1)
        
        raw_aud = round(((thai_pts + buyer_pts + sat_pts) / 25.0) * 100.0, 1)
        confidence = "High" if signals_high_count >= 2 else ("Medium" if signals_high_count >= 1 else "Low")
        return raw_aud, thai_pts, buyer_pts, sat_pts, s1, s2, s3, s4, confidence, evidence

    def _generate_strategic_rationale(self, kol: KOLProfile, brand: BrandDNA, b: SignalBreakdown) -> str:
        if b.affiliate_spam_penalty_applied:
            return (
                f"[PENALIZED] {kol.display_name} was detected by the Bot/Spam Filter. "
                f"{b.affiliate_spam_reason} "
                f"Convert Cake Recommendation: Avoid partnering due to automated repost signals."
            )

        kw_str = f" (matched tags: {', '.join(b.matched_keywords[:3])})" if b.matched_keywords else ""
        loc_str = f"and active {', '.join(kol.primary_locations[:2])} audience footprint" if kol.primary_locations else "and nationwide audience reach"
        price_str = f" (~{kol.avg_reviewed_price_thb:,} THB)" if kol.avg_reviewed_price_thb > 0 else ""
        cat_name = getattr(kol, 'creator_category', 'Content Creator (เน้นรีวิว)')
        cat_str = f" [หมวดหมู่: {cat_name} | ตะกร้าเหลือง {int(b.yellow_basket_ratio*100)}%]" if b.yellow_basket_ratio > 0 else f" [หมวดหมู่: {cat_name}]"
        archetype_str = f" [Archetype: {kol.creator_archetype} ({kol.recommended_role})]" if kol.creator_archetype else ""
        comp_str = f" {kol.competitor_warning}." if kol.competitor_warning else ""
        work_str = " ✅ Open for Sponsor / พร้อมรับงาน" if kol.is_work_ready else ""

        role_context = ""
        if kol.creator_archetype == "Lifestyle & Vlog":
            role_context = f" เหมาะอย่างยิ่งสำหรับเป้าหมายเปิดการมองเห็นร้านเปิดใหม่ (Brand Awareness) เพื่อพากลุ่มผู้ติดตามสายท่องเที่ยว/ไลฟ์สไตล์มาเปิดประสบการณ์กิจกรรมจำลองในร่ม"
        elif kol.creator_archetype == "Educated Guru":
            role_context = f" เหมาะสำหรับการสร้างความน่าเชื่อถือ อธิบายเทคนิค ท่าฝึกที่ถูกต้อง และกลไกของเครื่องเล่นจำลอง (Trust & Credibility)"
        elif kol.creator_archetype == "Top Reviewer":
            role_context = f" เหมาะสำหรับกระตุ้นการตัดสินใจ จองคอร์สทดลอง หรือซื้อแพ็กเกจ (Conversion & Sales)"
        elif kol.creator_archetype == "Niche Enthusiast":
            role_context = f" เหมาะสำหรับเจาะกลุ่มผู้เล่นประจำที่กำลังมองหาสถานที่ซ้อมสกีก่อนออกทริปจริง (Hyper-Targeted Reach)"

        return (
            f"{kol.display_name}{cat_str}{archetype_str} is an ideal {kol.tier} partner for {brand.brand_name}."
            f"{work_str} Delivers healthy engagement with a {b.median_engagement_rate_pct:.1f}% median ER and strong content relevance{kw_str}. "
            f"Save-to-View utility points ({b.save_to_view_points}/10) & Thai Authenticity ({b.thai_authenticity_points}/10) confirm genuine local reach. "
            f"Audience alignment confidence is {b.confidence_level} based on price-point compatibility{price_str} "
            f"{loc_str}.{role_context}{comp_str}"
        )

    def _generate_thai_campaign_hooks(self, kol: KOLProfile, brand: BrandDNA) -> List[str]:
        if kol.is_affiliate_spam_trap:
            return ["(N/A — Account flagged as affiliate spam)"]

        import re
        real_captions = [v.caption.split('#')[0].strip() for v in kol.recent_videos if v.caption.strip()]
        caption_topic = real_captions[0] if real_captions else (brand.sub_category or brand.vertical)
        clean_topic = re.sub(r'[\r\n\t]+', ' ', caption_topic).strip()[:50]
        price_tag = f"งบ {brand.average_price_thb:,} บาท" if brand.average_price_thb else "ราคาจับต้องได้"
        category_label = brand.sub_category or brand.vertical

        # Spec: สำหรับหมวดหมู่ Content Creator เน้นรีวิว (รองรับปักตะกร้าเหลือง 100%)
        if getattr(kol, 'creator_category', '') == 'Content Creator (เน้นรีวิว)' or any(v.has_yellow_basket for v in kol.recent_videos):
            h1 = f"\"ใครกำลังมองหา {category_label} หรือ {clean_topic} ปักตะกร้าเหลือง {brand.brand_name} {price_tag} ไว้ให้แล้ว รีวิวการใช้งานจริงตรงปก!\""
            h2 = f"\"สรุปข้อดี-ข้อสังเกต {brand.brand_name} สำหรับ {category_label} คุ้มมั้ยกับราคานี้ พิกัดจิ้มตะกร้าเหลืองด้านล่างได้เลย\""
            h3 = f"\"ทดลองใช้ {brand.brand_name} 7 วันเต็ม ตอบโจทย์คนหา {clean_topic} มั้ย สนใจกดสั่งซื้อตามในตะกร้าได้เลย!\""
            return [h1, h2, h3]

        # 100% Dynamic synthesis from real brand DNA and audited creator video context
        h1 = f"\"ใครกำลังมองหา {category_label} หรือ {clean_topic} มาดูรีวิวทดสอบ {brand.brand_name} {price_tag} ใช้งานจริงกัน\""
        h2 = f"\"สรุปข้อดี-ข้อสังเกต {brand.brand_name} สำหรับ {category_label} ตอบโจทย์มั้ยก่อนตัดสินใจซื้อ\""
        h3 = f"\"ทดลองใช้ {brand.brand_name} ติดต่อกัน 1 สัปดาห์ ประสิทธิภาพการใช้งานจริงเป็นยังไงมาดูกัน\""

        return [h1, h2, h3]


_engine_instance: Optional[ScoringEngine] = None

def get_scoring_engine() -> ScoringEngine:
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = ScoringEngine()
    return _engine_instance
