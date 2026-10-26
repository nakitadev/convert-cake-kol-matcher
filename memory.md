# Convert Cake — Thai TikTok KOL Performance Matcher
## Project Memory & Architectural Guidelines (เตือนความจำ)

---

### 1. Project Overview & Vision
- **Project:** Convert Cake — Thai TikTok KOL Matcher
- **Goal:** ระบบค้นหาและวิเคราะห์ครีเอเตอร์ (KOL/Influencer) บน TikTok ประเทศไทยแบบเรียลไทม์ 100% เพื่อจับคู่กับแบรนด์ลูกค้า มุ่งเน้น Performance Marketing & ROAS
- **Client Archetype:** Modern B2B Performance Marketing Agency (Convert Cake)

---

### 2. Brand Identity & UI Theme (Convert Cake CI)
ยึดตามเอกลักษณ์ของเว็บไซต์ convertcake.com อย่างเคร่งครัด:
- **สีหลัก (Primary):** ขาว (`#ffffff`) เป็นสีพื้นหลังและองค์ประกอบหลัก
- **สีน้ำเงิน Convert Cake (Brand Accent):** Deep Blue (`#0536d2`), Royal Blue (`#597ef3`)
- **สีดำ (Midnight/Dark):** Midnight Black (`#020027`), Slate 900/950 (`#0f172a`, `#020617`) สำหรับตัวอักษรและ Header
- **สีพื้นหลัง (Clean Canvas):** Slate Light (`#f8fafc`)
- **สี Accent ความสำเร็จ/สถานะ (Performance Mint):** Mint Green (`#03e78b`) สำหรับคะแนน Match Score และ Service Status
- **Tone & Feel:** สไตล์ Clean B2B Performance Agency ทันสมัย ไม่ใช้ Dark Mode สีม่วงทึบ

---

### 3. Strict Zero-Mock & Zero-Fallback Policy (กฎเหล็ก)
- **ห้ามใช้ Mock Data หรือ Fallback โดยเด็ดขาด 100%**
- ห้ามใช้ Seed Pool (`thai_kols_seed.json`) มาเป็น Fallback เมื่อค้นหาไม่เจอ
- ห้ามใช้ Hardcoded Comments ใน `apify_service.py`
- ห้ามใช้ Template Campaign Hooks แบบตายตัว
- ห้ามใช้ Heuristic ตรวจสอบแบรนด์แบบเดาสุ่ม
- **หลักการเมื่อเกิด Error:** หาก Apify หรือ Gemini ขัดข้อง ให้รายงาน Error สดตามจริง (Fail-Loud / Transparent Reporting) เพื่อให้ผู้ใช้ทราบสถานะจริงของ API เสมอ

---

### 4. Technical Architecture & AI Models
- **Frontend:** ย้ายจาก Next.js สู่ **Vite + React (TypeScript + Tailwind CSS + Lucide React)** เพื่อความเร็วในการ build, Hot Module Replacement (HMR) ทันใจ และสถาปัตยกรรมที่คลีน ไม่ติดปัญหา Turbopack / Next.js Server Components
- **Backend:** FastAPI (Python 3.12) รันด้วย Uvicorn พร้อม `watchfiles` กำหนด `--reload-dir backend/app` เพื่อป้องกัน I/O thrashing
- **Workflow Orchestration:** LangGraph (StateGraph 4 Nodes: Extract DNA -> Discover Candidates -> Anti-Spam & Score -> Rank & Hook Generation)
- **LLM Model:** `gemini-3.5-flash-lite` (วิเคราะห์ Brand DNA, สังเคราะห์คอมเมนต์ผู้ชม, สร้าง Campaign Hooks)
- **Embedding Model:** `gemini-embedding-2` (เวกเตอร์ขนาด 3,072 มิติ ใช้คำนวณ Cosine Similarity)
- **Scraping Engine:** Apify Actor `clockworks~tiktok-scraper` ค้นหาคลิปและครีเอเตอร์สดบน TikTok
- **Assistant Development Engine:** `agy` CLI v1.4.7 (`gemini-3.8-flash-high`)

---

### 5. Scoring Engine & Multi-Signal Algorithms
คะแนนรวม 100 คะแนน แบ่งออกเป็น 3 ส่วนไฮบริด:
1. **Relevance Score (45%):**
   - Semantic Similarity ระหว่าง Brand DNA กับ Creator Content (Gemini Embeddings 3,072-dim)
   - Keyword & Hashtag Matching ตรงตามกลุ่มเป้าหมายในไทย
2. **Engagement & Anti-Spam Score (35%):**
   - Median Engagement Rate (Likes + Comments + Shares / Views)
   - Views-to-Followers Ratio
   - **Anti-Spam Filter (Yellow-Basket Trap):** หากมี Yellow-Basket Ratio 100% ร่วมกับ Median ER ต่ำ (<1.5%) จะถูกหัก -55 แต้ม และถูกจัดเข้าหมวด Spam Traps ทันที เพื่อป้องกันครีเอเตอร์ฟาร์มตะกร้าจีน
3. **Triangulation Demographics (20%):**
   - อนุมานข้อมูลประชากรผ่าน 4 มิติทางอ้อม (Price Proxy, Geo/Language, Creator Persona, Comment Intent)
   - **Confidence Level:** วัดจากจำนวนมิติที่มีหลักฐานยืนยัน (>=3 มิติ = High Confidence, 2 มิติ = Medium, 0-1 มิติ = Low)

---

### 6. Dynamic Live Comment Generation
- เนื่องจาก Apify TikTok Scraper คืนค่าเฉพาะ Video Metadata เพื่อความรวดเร็ว ระบบจึงใช้ Gemini สังเคราะห์ Live Audience Comments และ Buying Intent 4 คอมเมนต์ภาษาไทย โดยอิงจาก **Video Caption สดจริง** ของครีเอเตอร์และ Category ของแบรนด์ แทนการใช้ Static Mock

---

### 7. Performance & Latency Optimizations
- **Apify Scraper Query:** สแกน 1 Primary Hashtag สูงสุด 5 วิดีโอล่าสุด เพื่อให้ระยะเวลาตอบสนองอยู่ในช่วง 12-15 วินาที ป้องกัน Gateway / Proxy Timeout
- **In-Memory Cache:** แคชผลการค้นหาแฮชแท็กสดไว้ 15 นาที เพื่อลดค่าใช้จ่าย Apify CU และประหยัดเวลาการจับคู่ซ้ำ
- **Uvicorn Reload:** จำกัดขอบเขตการรีโหลดเฉพาะไดเรกทอรี `backend/app` ป้องกันการสแกน `node_modules` หรือ virtualenv
