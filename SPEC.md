# Convert Cake — TikTok KOL/KOC Matching Engine (Thailand) Specification

## 1. Overview & Funnel Pipeline Architecture
ระบบจับคู่แบรนด์ลูกค้าเข้ากับ TikTok KOL และ KOC ในประเทศไทยที่ออกแบบตามหลักการทำงานจริงของ **Convert Cake (Performance-Only Marketing Agency)**
ขับเคลื่อนด้วย Marketing Funnel และ Data Proxy 4 ขั้นตอนหลัก:

1. **ขั้นที่ 1 — Brand DNA & Conversion Model Classification:**
   - วิเคราะห์ Website (Jina Reader API + fallback httpx/BeautifulSoup) และ Facebook Page (Apify Facebook Scraper)
   - จำแนกแบรนด์ตาม 4 โมเดลธุรกิจตามวิธีทำเงิน (`ECOMMERCE_PRODUCT`, `APP_DIGITAL_SERVICE`, `HIGH_TICKET_LEADGEN`, `LIFESTYLE_EXPERIENCE`)
   - กำหนดสัดส่วนแนะนำ Media Mix (KOL : KOC)
   - สกัดคู่แข่งในไทยผ่าน Google Search Grounding (Competitor Layer 1)
2. **ขั้นที่ 2 — Adaptive Scene Translation & TikTok Discovery:**
   - แปลงธุรกิจเป็นคำค้นหาภาษาไทยที่เป็นธรรมชาติ (สั้นกระชับ 2-3 คำ, ไม่เกิน 18 ตัวอักษรไทย, 60/40 Direct vs Adjacent funnel, Anti-Merchant Guardrail)
   - แยกชุดคำค้นหาฝั่ง `KOL_QUERY` และ `KOC_QUERY` กวาดคลิปสดผ่าน Apify (ล็อก `proxyCountryCode: "TH"`)
   - ตรวจจับคู่แข่งร่วมในแฮชแท็กของคลิป (Competitor Layer 2 Co-occurrence)
3. **ขั้นที่ 3 — Two-Stage Filtering, 2x2 KOL/KOC Classification & Dynamic Scoring:**
   - **Gate 1:** กรองร้านค้า/โรงงาน และ Smart Affiliate Bot Filter (ตัดเฉพาะตะกร้า >85% AND ไร้ข้อความรับงาน AND ยอดคอมเมนต์<=1 หรือวิวมัธยฐาน<300) โดยไม่ตัด KOC สายป้ายยาตัวท็อป
   - **Gate 2:** Batch LLM Relevance Gate (1 API Call) คัดช่องหลุดหมวด/มีมตลกออก
   - **2x2 Matrix:** จัดเข้า 2 บทบาทหลัก แตกเป็น 4 สไตล์ย่อย (`KOL - Expert / Guru`, `KOL - Lifestyle / Aesthetic`, `KOC - Hard-Sell Reviewer`, `KOC - Everyday User / Vlog`)
   - **Competitor Layer 3:** ติดป้าย `⚠️ Competitor Conflict` (รีวิวเดี่ยว) หรือ `🎯 Comparison Opportunity` (คลิปเปรียบเทียบหลายแบรนด์)
   - **Dynamic Scoring (100 คะแนนเต็ม):**
     - Brand & Funnel Relevance (40 คะแนน): Semantic & LLM Fit (28) + Niche & Work-Ready Bonus (12)
     - Engagement Quality & Content Utility (35 คะแนน): Median ER บนคลิปวิว >= 500 (15) + Save/Share Utility (10) + Consistency (10)
     - Audience Proxy & Commercial Viability (25 คะแนน): Thai Authenticity (10) + Buyer Intent Proxy (10) + Brand-Adaptive Affiliate Health (5)
4. **ขั้นที่ 4 — Stratified Quota Ranking & Agency Dashboard:**
   - จัดอันดับพอร์ตโฟลิโอแบบ Two-Pass Stratified Quota คัดสรร Top 10 ที่สมดุลตาม Conversion Model และครบทุกสไตล์
   - Frontend Dashboard: Strategy Summary Banner, Filter Bar 3 มิติ, Explainable Creator Cards, Export CSV, และ Excluded Transparency tab.

## 2. Technical Stack
- **Backend:** FastAPI (Python 3.14 / 3.12), LangGraph (StateGraph 4 Nodes), google-genai 2.33, httpx, BeautifulSoup4, numpy.
- **Frontend:** Vite 6 + React 19 + TypeScript + Tailwind CSS v4 + Lucide React.
