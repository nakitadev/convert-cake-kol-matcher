# Convert Cake — Thai TikTok KOL Performance Matcher
## Project Memory & Architectural Guidelines (เตือนความจำ)

---

### 1. Project Overview & Vision
- **Project:** Convert Cake — Thai TikTok KOL Matcher
- **Goal:** ระบบค้นหาและวิเคราะห์ครีเอเตอร์ (KOL/Influencer) บน TikTok ประเทศไทยแบบเรียลไทม์ 100% เพื่อจับคู่กับแบรนด์ลูกค้า มุ่งเน้น Performance Marketing & ROAS
- **Client Archetype:** Modern B2B Performance Marketing Agency (Convert Cake)
- **Target Platform:** TikTok Thailand Market (สอดคล้องกับพฤติกรรมผู้บริโภคและครีเอเตอร์ชาวไทย)

---

### 2. Brand Identity & UI Theme (Convert Cake CI)
ยึดตามเอกลักษณ์ของเว็บไซต์ convertcake.com อย่างเคร่งครัด:
- **สีหลัก (Primary Canvas):** ขาวบริสุทธิ์ (`#ffffff`) และ Slate Light (`#f8fafc`) เป็นพื้นหลังและ Card พื้นฐาน ให้ความรู้สึกโปร่ง สะอาดตา
- **สีน้ำเงิน Convert Cake (Brand Accent):** Deep Blue (`#0536d2`), Royal Blue (`#597ef3`) ใช้กับปุ่ม Call-to-Action, Badges สำคัญ และ Accent Highlights
- **สีดำ (Midnight/Dark Elements):** Midnight Black (`#020027`), Slate 900 (`#0f172a`) สำหรับ Typography ตัวหนังสือคมชัดสูง (High Contrast) และ Navbar Header
- **สี Accent ความสำเร็จ/สถานะ (Performance Mint):** Mint Green (`#03e78b`) สำหรับคะแนน Match Score และ Service Status
- **สีระวัง/แจ้งเตือน (Affiliate Yellow/Amber):** Amber 500/600 สำหรับดักจับขยะตะกร้าเหลือง (Yellow-Basket Affiliate Spam)
- **Tone & Feel:** สไตล์ Clean B2B Performance Agency ทันสมัย ไม่ใช้ Dark Mode ม่วงนีออนทึบตา

---

### 3. Strict Zero-Mock, Zero-Fallback & Zero-Hardcode Policy (กฎเหล็ก)
- **ห้ามใช้ Mock Data, Fallback หรือ Hardcoded Defaults โดยเด็ดขาด 100% (Zero-Mock & Zero-Hardcode Policy)**
- **ห้ามใส่ Hardcoded Else/Default Strings** ในโค้ด เช่น `vertical = ... if ... else "Beauty & Skincare"`, `clean_tags = ["รีวิว", "ป้ายยา"]` หรือค่าคงที่อื่นๆ หากข้อมูลขาดหายหรือไม่ส่งมา ต้อง Raise Error (`ValueError` / `RuntimeError`) อย่างตรงไปตรงมา ห้ามแอบเติม Default แทนเด็ดขาด
- **ห้ามใส่ Hardcoded Heuristic Numbers / Tables** เช่น การเดาราคาคงที่ 690, 280, 2900 หรือการเขียน `if "beauty" in ... elif "f&b" in ... else ...` ทุกอย่างต้องสกัดจากข้อมูลจริง (Regex ดึงราคาที่ระบุในคลิปจริง, ใช้ Bio/Hashtags ของครีเอเตอร์จริง, Brand Category จริงจาก LLM)
- ห้ามใช้ Seed Pool (`thai_kols_seed.json`) มาเป็น Fallback เมื่อค้นหาไม่เจอ
- ห้ามใช้ Hardcoded Comments ใน `apify_service.py` ทุกคอมเมนต์ต้องมาจากการสังเคราะห์สดผ่าน Gemini จาก Live Video Captions
- **Fail-Loud / Transparent Reporting:** หาก Apify หรือ Gemini ขัดข้อง ให้รายงาน Error สดตามจริงบน UI เพื่อให้ผู้ใช้ทราบสถานะจริงของ API เสมอ

---

### 4. Technical Architecture & AI Models
- **Frontend Architecture:** **Vite 6 + React 19 (TypeScript + Tailwind CSS v4 + Lucide React)**
  - *เหตุผลเชิงสถาปัตยกรรม:* เครื่องมือภายใน Agency (Internal Tool) ไม่ต้องการ Server-Side Rendering (SSR) หรือ Public SEO การใช้ SPA บน Vite ทำให้ Build Time รวดเร็ว (<600ms), HMR ทันใจ, ไม่มีปัญหา Port Binding หรือ Static Proxy Rewrite Bake-in แบบ Next.js
  - *API Proxy:* ตั้งค่า Reverse Proxy ใน `vite.config.ts` ให้ส่งต่อ `/api` ไปยัง FastAPI Backend (Port 8000)
- **Backend Architecture:** **FastAPI (Python 3.12)** รันผ่าน Uvicorn พร้อม `watchfiles` โดยกำหนด `--reload-dir backend/app` เพื่อป้องกัน I/O thrashing
- **Workflow Orchestration:** **LangGraph (StateGraph 4 Nodes)**:
  1. `analyze_brand_node`: สกัด Brand DNA และ Thai Keywords
  2. `discover_candidates_node`: ค้นหาครีเอเตอร์และคลิปสดจาก TikTok ผ่าน Apify
  3. `score_and_filter_node`: คำนวณ Hybrid Score 45/35/20 พร้อมกรอง Anti-Spam
  4. `score_rank_hooks_node`: จัดอันดับ Two-Pass Stratified Quota
- **LLM Model:** `gemini-3.5-flash-lite` (วิเคราะห์ Brand DNA & Conversion Models, Google Search Grounding สกัดคู่แข่งในไทย, Batch Relevance Gate)
- **Embedding Model:** `gemini-embedding-2` (เวกเตอร์ขนาด 3,072 มิติ ใช้คำนวณ Cosine Similarity)
- **Assistant Development Engine:** `agy` CLI v1.4.7 (`gemini-3.8-flash-high`)

---

### 5. Multi-Source Ingestion & Scraping Engines
- **Website Brand Ingestion (Two-Tier Architecture):**
  - **Tier 1 (Primary): Jina Reader API (`r.jina.ai`)** — แปลงเว็บ SPA/React/Next.js/Shopify ให้เป็น Clean Markdown ตัดขยะ Navbar/Footer ออกถึง 85% ประหยัด Token ให้ Gemini และลดขนาด Docker Container ไม่ต้องแบก Chromium (+800MB)
  - **Tier 2 (Fallback): HTTPX + BeautifulSoup4** — รองรับกรณี Jina เกิด Timeout หรือ Rate Limit เพื่อให้ระบบทำงานต่อได้อย่างลื่นไหล
- **Facebook Page Ingestion (สำหรับ SME ไทยที่ไม่มีเว็บไซต์):**
  - ใช้ Apify Actor `apify~facebook-pages-scraper` ดึงข้อมูลเพจสด (Title, Bio, Categories, Followers, Likes, Recent Posts) และดึงความคิดเห็นจริงของลูกค้า (Facebook Comments) สู่ Brand DNA
- **TikTok Scraper Engine:**
  - Apify Actor `clockworks~tiktok-scraper` ค้นหาคลิปและโปรไฟล์สดจากคำค้นหา Scene Translation โดยล็อก `proxyCountryCode: "TH"`
  - **Origin Tagging:** ทุกคลิปที่ดึงมาระบุที่มาอย่างแม่นยำว่าเป็น `KOL_QUERY` หรือ `KOC_QUERY`

---

### 6. 4 Brand Conversion Models & Media Mix (Spec 2.2)
1. `ECOMMERCE_PRODUCT`: ซื้อทันทีผ่านตะกร้า/Shopee (สกินแคร์, เครื่องสำอาง, ของใช้) -> สัดส่วน **KOL 30% : KOC 70%**
2. `APP_DIGITAL_SERVICE`: โหลดแอป/สมัครเว็บ/SaaS (FinTech, AI, ซอฟต์แวร์, เกม) -> สัดส่วน **KOL 50% : KOC 50%**
3. `HIGH_TICKET_LEADGEN`: ทักแชท/กรอกฟอร์ม/จองคอร์ส (คลินิก, คอร์สเรียน, อสังหาฯ) -> สัดส่วน **KOL 60% : KOC 40%**
4. `LIFESTYLE_EXPERIENCE`: ไปหน้าร้าน/ภาพลักษณ์หรู (โรงแรม, คาเฟ่, ห้าง, Luxury) -> สัดส่วน **KOL 70% : KOC 30%**

---

### 7. 2x2 KOL/KOC Matrix & 4 Sub-Styles (Spec 4.2)
- **กิ่งที่ 1: 🧠 KOL (Key Opinion Leader) — Top & Middle Funnel (สร้างการรับรู้ ภาพลักษณ์ และความน่าเชื่อถือ)**
  - `KOL - Expert / Guru`: สายผู้เชี่ยวชาญ/กูรู แคปชันอธิบายเชิงลึก Save Rate เด่นชัด
  - `KOL - Lifestyle / Aesthetic`: สายไลฟ์สไตล์/ภาพลักษณ์ดูแพง ยอดวิวสูง แคปชันสั้น เน้น Mood & Tone (Basket Ratio < 15%)
- **กิ่งที่ 2: 🛍️ KOC (Key Opinion Consumer) — Bottom Funnel (เร่งการตัดสินใจซื้อ และปิดการขาย)**
  - `KOC - Hard-Sell Reviewer`: สายป้ายยา/รีวิวเน้นปิดการขาย ปักตะกร้าสม่ำเสมอ คนคอมเมนต์ถามซื้อจริง
  - `KOC - Everyday User / Vlog`: สายผู้ใช้จริงในชีวิตประจำวัน เล่าเรื่องแบบเพื่อนบอกเพื่อน ปักตะกร้าประปราย (15%-40%)

---

### 8. Scoring Engine & Multi-Signal Algorithms (Dynamic 40 / 35 / 25 Pts - Spec 4.3)
1. **Brand & Funnel Relevance (40 คะแนน):**
   - Semantic & LLM Fit Score (28 คะแนน): ผสมผสานค่า Cosine Similarity กับคะแนนจาก Batch LLM Relevance Gate
   - Sub-Niche & Work-Ready Bonus (12 คะแนน): ความตรงของคีย์เวิร์ดเฉพาะทาง (8 คะแนน) + โบนัสช่องทางติดต่องานใน Bio (4 คะแนน)
2. **Engagement Quality & Content Utility (35 คะแนน):**
   - Median Engagement Rate (15 คะแนน): `(Likes + Comments + Shares + Saves) / Views` ใช้มัธยฐานเฉพาะคลิปวิว >= 500
   - Save & Share Utility Score (10 คะแนน): `(collectCount + 0.7 * shareCount) / max(playCount, 500)` พร้อมโบนัสพิเศษสำหรับ `KOL - Expert / Guru`
   - View Consistency Ratio (10 คะแนน): `Median Views / Mean Views` ป้องกันการเลือกคลิปไวรัลฟลุ๊ค
3. **Audience Proxy & Commercial Viability (25 คะแนน):**
   - Thai Audience Authenticity (10 คะแนน): สัดส่วนภาษาไทยในแคปชันและคอมเมนต์
   - Buyer Intent Proxy (10 คะแนน): Tier-1 Fast Proxy (`comment/like` + `share/like`) vs Tier-2 Targeted Comment Analysis สกัดคีย์เวิร์ดซื้อจริง (`ราคา`, `พิกัด`, `ซื้อที่ไหน`, `ใช้ดีไหม`)
   - Brand-Adaptive Affiliate Health (5 คะแนน): เต็ม 5/5 สำหรับ KOC สายรีวิวใน E-Commerce แต่หักคะแนนหากตะกร้า > 70% ในแบรนด์หรู/High-Ticket เพื่อรักษาภาพลักษณ์

---

### 9. 3-Layer Grounded Thai Competitor Detection (Spec 5)
- **Layer 1:** Google Search Grounding ร่วมกับ Gemini สกัดแบรนด์คู่แข่งในไทย ณ ปัจจุบัน พร้อมชื่อเรียกทับศัพท์ภาษาไทย
- **Layer 2:** Bottom-Up TikTok Co-occurrence Discovery สกัดชื่อแบรนด์คู่แข่งที่ปรากฏซ้ำบ่อยในแฮชแท็กของคลิปที่ค้นพบ
- **Layer 3:**
  - คลิปรีวิวเดี่ยว -> ติดป้ายเตือน `⚠️ Competitor Conflict: [ชื่อแบรนด์]`
  - คลิปเปรียบเทียบหลายแบรนด์ -> ติดป้ายโอกาสทอง `🎯 Comparison Opportunity`

---

### 8. Containerization & Deployment
- **Docker Compose:** ควบคุมบริการทั้งสองส่วนอย่างเป็นระบบ:
  - `convert-cake-backend`: FastAPI บนพอร์ต 8000 พร้อม Healthcheck (`/api/health`)
  - `convert-cake-frontend`: Vite Preview บนพอร์ต 3000 พร้อม Reverse Proxy
- **Mobile Testing Readiness:** รองรับการเชื่อมต่อผ่าน Cloudflare Tunnel หรือ SSH Port Forward เพื่อเปิดทดสอบบนหน้าจอมือถือจริงได้ทันที