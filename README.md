# Convert Cake — Thai TikTok KOL Matcher

AI Automation & Influencer Matching Prototype for Digital Marketing Agencies.

---

## 🎧 Quick Start Guide

### 1-Click Launch (All Services)
```bash
cd /home/ubuntu/projects/convert-cake-kol-matcher
./run_dev.sh
```
- **Dashboard UI:** `http://localhost:3000`
- **Swagger API Docs:** `http://localhost:8000/docs`
- **Health Check:** `http://localhost:8000/api/health`

---

### Manual Launch Option

#### Backend (FastAPI + LangGraph)
```bash
cd /home/ubuntu/projects/convert-cake-kol-matcher
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### Frontend (Next.js 16 + Tailwind CSS + Lucide)
```bash
cd /home/ubuntu/projects/convert-cake-kol-matcher/frontend
npm run dev
```

#### Run Test Suite (pytest)
```bash
cd /home/ubuntu/projects/convert-cake-kol-matcher
./venv/bin/pytest -v
```
*(8/8 unit & integration tests covering Brand DNA ingestion, seed repository, deterministic engagement math, anti-spam penalty filter, and LangGraph workflow)*

---

## 🧠 System Architecture

1. **Stage 1: Brand Ingestion & Analysis (`BrandAnalyzerNode`)**
   - Ingests Client Website & Facebook profile via Jina Reader / HTTPX with local fallback snapshots.
   - Extracts structured **Brand DNA** (Vertical, Target Audience, Brand Tone, Content Styles, Price Tier, Thai Search Keywords/Hashtags).
   - Supports **Human-in-the-Loop review & edit** on the UI before initiating KOL discovery, plus a **1-Click Auto Match** mode.

2. **Stage 2: Two-Stage Discovery & Apify Live Enrichment**
   - Semantic Cosine Vector search against pre-indexed Thai TikTok KOL database across 3 core agency verticals (*Beauty & Skincare*, *F&B / Cafe & Lifestyle*, *Gadgets / Home & Living*).
   - Supports live handle/hashtag enrichment using Apify (`clockworks/tiktok-scraper` or `apify/tiktok-scraper`) with resilient fallback when API tokens are omitted.

3. **Stage 3: Hybrid Scoring & Anti-Spam Engine (100 Points)**
   - **Brand & Content Relevance (45%)**: Vector similarity + LLM content rubric alignment.
   - **Engagement Quality (35%)**: Deterministic math on recent 10 videos (`Median((Likes + Comments*2 + Shares*3) / Views)` + `View-to-Follower Ratio`) with an automatic **Affiliate Spam / Yellow-Basket Penalty Filter** (flags accounts with >70% yellow-basket videos and low engagement, deducting 55 points).
   - **Multi-Signal Audience Alignment (20%)**: Public data inference across 4 signals (Creator Persona/Visual, Price-Point Proxy, Thai Geo/Language, Commenter Sample) with confidence scoring.

4. **Stage 4: Curated Output & Thai Campaign Hooks**
   - Ranked list with direct TikTok profile links (`https://www.tiktok.com/@...`), 3-part score breakdown bars, audience evidence pills, and custom Thai TikTok hook ideas ready for client pitch decks.
   - One-click CSV and JSON exports for agency team handoffs.

---

## 🎬 Loom Presentation Script & Key Talking Points (5–10 Mins)

1. **0:00–1:30 | Business Problem & Executive Summary**: Contextualize agency pain points (manual creator vetting, affiliate spam in Thai hashtags like `#ป้ายยา` and `#รีวิวบิวตี้`, Meta/TikTok scraping walls).
2. **1:30–4:00 | Live Demo on UI**: Run a sample Thai brand (e.g., Srichand Skincare or After You Cafe), review Brand DNA Card, click Match, showcase ranked KOLs with score breakdowns, confidence badges, and Thai hook ideas. Demonstrate the **Anti-Spam Filter Catch** tab to show budget protection.
3. **4:00–7:00 | Architecture & Code Walkthrough**: Explain LangGraph workflow, deterministic engagement math vs semantic LLM reasoning, and the Multi-Signal Demographics Triangulation.
4. **7:00–8:30 | Ethical & Privacy Considerations**: Explain why public scrapers cannot legitimately return first-party follower demographics, and how our inference respects platform boundaries.
5. **8:30–10:00 | Future Enhancements**: Plug-and-play TikTok Creator Marketplace OAuth adapter, automated outreach DM generator, and post-campaign conversion tracking.
