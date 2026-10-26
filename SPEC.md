# Convert Cake — TikTok KOL Matcher (Thailand) Architecture Spec

## 1. Objective
Build a working prototype for Convert Cake (Digital Marketing Agency) that:
1. Analyzes a client's Facebook Page and Website to extract Brand DNA (industry/vertical, target audience, brand tone, content style, price positioning, Thai search keywords/hashtags).
2. Identifies & evaluates relevant Thai TikTok Influencers / KOLs using a Two-Stage RAG + Live Apify Enrichment pipeline (with resilient local fallback dataset).
3. Ranks KOLs using a Hybrid Scoring Engine:
   - **Brand & Content Relevance (45%)**: Semantic vector similarity + LLM rubric alignment.
   - **Engagement Quality & Consistency (35%)**: Deterministic math on recent videos (`Median((Likes + Comments*2 + Shares*3) / Views)` + `Views-to-Followers Ratio`) with an **Affiliate Spam / Yellow-Basket Penalty Filter**.
   - **Multi-Signal Audience Alignment (20%)**: Public data inference across 4 signals (1. Creator persona & visual style, 2. Product price-point proxy, 3. Thai geo/language & check-in signals, 4. Commenters sample) + explicit `Confidence Level (High/Medium/Low)` and evidence list.
4. Outputs a curated, ranked list of Thai TikTok KOLs with direct TikTok profile links (`https://www.tiktok.com/@handle`), score breakdowns, audience persona alignment, and custom Thai TikTok campaign hook ideas.

## 2. Architecture & Stack
- **Backend (`/backend`)**:
  - Python FastAPI (`app/main.py`)
  - LangGraph 2-Stage Workflow (`app/workflow/graph.py`):
    - Stage 1 (`analyze_brand_node`): Scrapes Website (via Jina Reader / BeautifulSoup httpx + Apify FB fallback + preset Thai brand cases) -> produces structured `BrandDNA` (supports Human-in-the-Loop review/edit before Stage 2, plus 1-click Auto-Run).
    - Stage 2 (`discover_kols_node` -> `enrich_apify_node` -> `score_and_rank_node` -> `generate_hooks_node`): Queries the pre-indexed Thai TikTok KOL pool (in-memory cosine vector search + TF-IDF/embedding hybrid + optional live Apify `clockworks/tiktok-scraper` or `apify/tiktok-scraper` actor call when `APIFY_API_TOKEN` is set) -> computes deterministic engagement + multi-signal audience alignment + LLM/heuristic rationale & Thai campaign hooks.
  - Seed Dataset (`app/data/thai_kols_seed.json` & `app/data/sample_brands.json`):
    - ~36 realistic, richly detailed Thai TikTok KOL profiles across 3 core verticals (**Beauty & Skincare**, **Cafe / F&B & Lifestyle**, **Gadgets / Home & Living**), including several deliberate 'trap/affiliate spam' profiles so the anti-spam penalty filter is demonstrably tested.
    - Each KOL has real TikTok URL format (`https://www.tiktok.com/@...`), bio, follower count, recent 10 videos metrics (views, likes, comments, shares, captions, hashtags, price-point signals, location tags, sample Thai comments).
  - Comprehensive `pytest` test suite (`backend/tests/test_api_and_scoring.py`) testing Stage 1, Stage 2, math scoring, anti-spam penalty, multi-signal demographics, and API endpoints.
- **Frontend (`/frontend`)**:
  - Next.js (App Router, TypeScript, Tailwind CSS, Lucide icons) agency dashboard.
  - Features:
    - Sample Thai Brand quick-fill presets (e.g., *Srichand / Cute Press Skincare*, *After You / Specialty Cafe BKK*, *Ergonomic Desk & Gadget Brand*) + custom Website URL & Facebook URL inputs.
    - Step 1: Interactive **Brand DNA Card** (editable target audience, tone, price tier, Thai hashtags) with 'Confirm & Match KOLs' button + '1-Click Auto Match'.
    - Step 2: **Curated Ranked KOL List** with Total Match Score, 3-part progress bars (Relevance 45%, Engagement 35%, Multi-Signal Demographics 20%), Confidence Badge, Evidence Pills (Price proxy, Geo signal, Persona, Comment sample), Affiliate Spam warning badge (if penalized), Custom Thai TikTok Hook idea, Direct link to TikTok profile, and CSV/JSON Export.
