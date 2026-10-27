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
- ห้ามใช้ Template Campaign Hooks แบบตายตัว ต้องสร้างแบบไดนามิก 100% จาก Context ของวิดีโอจริงและ Brand DNA จริง
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
  4. `rank_and_hook_node`: จัดอันดับ และสร้าง Thai Campaign Pitch Hooks
- **LLM Model:** `gemini-3.5-flash-lite` (วิเคราะห์ Brand DNA, สังเคราะห์คอมเมนต์ผู้ชมสด, สร้าง Campaign Hooks ภาษาไทย)
- **Embedding Model:** `gemini-embedding-2` (เวกเตอร์ขนาด 3,072 มิติ ใช้คำนวณ Cosine Similarity)
- **Assistant Development Engine:** `agy` CLI v1.4.7 (`gemini-3.8-flash-high`)

---

### 5. Multi-Source Ingestion & Scraping Engines
- **Website Brand Ingestion (Two-Tier Architecture):**
  - **Tier 1 (Primary): Jina Reader API (`r.jina.ai`)** — แปลงเว็บ SPA/React/Next.js/Shopify ให้เป็น Clean Markdown ตัดขยะ Navbar/Footer ออกถึง 85% ประหยัด Token ให้ Gemini และลดขนาด Docker Container ไม่ต้องแบก Chromium (+800MB)
  - **Tier 2 (Fallback): HTTPX + BeautifulSoup4** — รองรับกรณี Jina เกิด Timeout หรือ Rate Limit เพื่อให้ระบบทำงานต่อได้อย่างลื่นไหล
- **Facebook Page Ingestion (สำหรับ SME ไทยที่ไม่มีเว็บไซต์):**
  - ใช้ Apify Actor `apify~facebook-pages-scraper` ดึงข้อมูลเพจสด (Title, Bio, Categories, Followers, Likes, Recent Posts) พร้อม Fallback สู่ Jina Reader
- **TikTok Scraper Engine:**
  - Apify Actor `clockworks~tiktok-scraper` ค้นหาคลิปและโปรไฟล์สดจากแฮชแท็กภาษาไทย
  - **Thai Hashtag Preservation:** จัดการแฮชแท็กภาษาไทยด้วย `t.lstrip('#').strip()` ป้องกัน Regex เดิมที่ลบสระ/พยัญชนะไทยออก
  - **Latency & Reliability:** ตั้ง Timeout ไว้ที่ 90 วินาที พร้อมระบบ Auto-Recovery ตรวจสอบ Dataset ID เมื่อ Sync Call ใช้เวลานาน เพื่อป้องกัน Network Drop

---

### 6. Scoring Engine & Multi-Signal Algorithms (Dynamic 40 / 35 / 25 Pts)
คะแนนรวม 100 คะแนน แบ่งออกเป็น 3 มิติเชิงกลยุทธ์ตาม Full System Specification:
1. **Relevance Score (40 คะแนน):**
   - **Semantic Similarity (28 คะแนน):** Cosine Similarity ระหว่าง Brand DNA กับ Creator Content (Gemini Embeddings 3,072 มิติ)
   - **Niche Keyword & Work-Ready Match (12 คะแนน):** จับคู่คีย์เวิร์ดแบรนด์ตรงตัว (8 คะแนน) + โบนัส Work-Ready Status พร้อมรับสปอนเซอร์ (4 คะแนน)
2. **Engagement Quality (35 คะแนน):**
   - **Median Engagement Rate (15 คะแนน):** วัดจาก `(Likes + 2*Comments + 3*Shares + Saves) / Views` ใช้ค่ามัธยฐานของคลิปย้อนหลัง
   - **Save-to-View Utility Ratio (10 คะแนน):** คำนวณ `(Collects + 0.7*Shares) / Views` พร้อมโบนัส +2 คะแนนสำหรับครีเอเตอร์สาย Educated Guru
   - **View Consistency Ratio (10 คะแนน):** คำนวณ `Median Views / Mean Views` ตรวจสอบความสม่ำเสมอของยอดวิว ไม่พึ่งพาไวรัลฟลุ๊ค
   - **Updated Spec — รองรับการปักตะกร้าเหลือง 100% สำหรับ "Content Creator (เน้นรีวิว)" / Top Reviewer:**
     - ยอมรับการปักตะกร้าเหลืองได้ถึง 100% โดยจัดเข้าหมวดหมู่ **"Content Creator (เน้นรีวิว)"** และ Archetype **"Top Reviewer"** ไม่หักคะแนนหรือตีเป็น Spam Trap เพราะในตลาด TikTok ประเทศไทย ครีเอเตอร์สายรีวิว/Shoppertainment จำเป็นต้องปักตะกร้าทุกคลิปเพื่อสร้าง Direct Conversion ให้แบรนด์
     - ระบบมีแท็บและป้ายกำกับแยกเฉพาะ **"Content Creator เน้นรีวิว (ตะกร้าเหลือง 100%)"** เพื่อให้ทีม Performance Marketing เลือกใช้งานตามวัตถุประสงค์
     - จะ Flag และหักคะแนนเฉพาะบัญชีที่เป็น Bot/Spam Farm ชัดเจนเท่านั้น
3. **Audience Proxy & Commercial Viability (25 คะแนน):**
   - **Thai Audience Authenticity (10 คะแนน):** ตรวจจับสัดส่วนพยัญชนะ/สระภาษาไทยในแคปชันและคอมเมนต์ (Verified Thai Audience)
   - **Buyer Intent Proxy (10 คะแนน):** คำนวณสัดส่วน Inquiry Ratio และคีย์เวิร์ดบอกความสนใจซื้อจริง (เช่น `พิกัด`, `ซื้อที่ไหน`, `ราคา`, `ใช้ดี`, `ป้ายยา`)
   - **Affiliate Saturation Health (5 คะแนน):** ให้คะแนนสุขภาพความหนาแน่นของการขาย (เต็ม 5 คะแนนสำหรับสายรีวิวที่ปักตะกร้า 100%)

---

### 7. Creator Archetypes & Grounded Competitor Detection
- **4 Creator Archetypes:**
  1. **Educated Guru:** ครีเอเตอร์สายให้ความรู้ เจาะลึกส่วนผสม/กลไกการทำงาน (บทบาท: Trust & Credibility)
  2. **Top Reviewer:** ครีเอเตอร์สายป้ายยา สาธิตการใช้งานจริง ยอมรับตะกร้าเหลือง 100% (บทบาท: Conversion & Sales)
  3. **Lifestyle & Vlog:** ครีเอเตอร์สาย GRWM, Daily Vlog สอดแทรกสินค้าอย่างแนบเนียน (บทบาท: Brand Awareness)
  4. **Niche Enthusiast:** ครีเอเตอร์สายเปรียบเทียบหลายแบรนด์ หรือเจาะลึกเฉพาะทาง (บทบาท: Hyper-Targeted Reach)
- **Grounded Thai Competitor Detection (3 ระดับ):**
  - *Layer 1:* Manual Competitor Input จากผู้ใช้
  - *Layer 2:* Discovery Competitors จาก Gemini สกัดชื่อแบรนด์และชื่อเรียกภาษาไทย
  - *Layer 3:* Live Caption Cross-Check ตรวจจับการพูดถึงคู่แข่ง หากพบ 1 แบรนด์จะติดป้ายเตือน `⚠️ Competitor Conflict` หากพบ >=2 แบรนด์จะระบุเป็น `🎯 Niche Enthusiast Opportunity`
- **Two-Stage Entity Filtering:**
  - กรองบัญชีร้านค้า Official/ตัวแทนจำหน่าย (`Official`, `Store`, `Shop`, `ราคาส่ง`, `เปิดบิล`) ออกตั้งแต่ต้นทาง เพื่อป้องกันผลลัพธ์ปนเปื้อน

---

### 7. Tailored Thai Campaign Pitch Hooks
- ระบบสร้าง TikTok Pitch Hooks ภาษาไทย 3 สไตล์ต่อครีเอเตอร์ โดยเชื่อมโยงบริบทของแคปชันคลิปสดจริง (Audited Captions) และราคา/จุดเด่นของแบรนด์:
  - **Beauty & Skincare:** Hook เน้นปัญหาสิว/ผิวแพ้ง่าย, ป้ายยารูทีน GRWM, ท้าพิสูจน์ผลลัพธ์ 7 วัน
  - **Food & Cafe (F&B):** Hook สไตล์ 1 Day Food Vlog, พิกัดเมนูลับตามรอย TikTok, รีวิวรสชาติตรงไปตรงมา
  - **Tech, Gadgets & Ergonomics:** Hook ชาวออฟฟิศปวดหลัง, โต๊ะคอมสไตล์ Minimal, คุ้มค่าตัวไหมกับการใช้งานจริง 1 เดือน
  - **General & Lifestyle:** Hook ป้ายยา Unboxing เรียลๆ แบบโนสปอน, Life Hack เปลี่ยนชีวิต

---

### 8. Containerization & Deployment
- **Docker Compose:** ควบคุมบริการทั้งสองส่วนอย่างเป็นระบบ:
  - `convert-cake-backend`: FastAPI บนพอร์ต 8000 พร้อม Healthcheck (`/api/health`)
  - `convert-cake-frontend`: Vite Preview บนพอร์ต 3000 พร้อม Reverse Proxy
- **Mobile Testing Readiness:** รองรับการเชื่อมต่อผ่าน Cloudflare Tunnel หรือ SSH Port Forward เพื่อเปิดทดสอบบนหน้าจอมือถือจริงได้ทันที