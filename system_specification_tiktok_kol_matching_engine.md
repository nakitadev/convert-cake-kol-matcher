# System Specification: Convert Cake TikTok KOL/KOC Discovery & Matching Engine

## 1. ภาพรวมสถาปัตยกรรม (Pipeline Overview)

ระบบค้นหา คัดกรอง และจัดอันดับ TikTok KOL และ KOC ในประเทศไทยที่ออกแบบตามหลักการทำงานจริงของ **Convert Cake (Performance-Only Marketing Agency)** โดยมุ่งเน้นที่การค้นหาครีเอเตอร์ที่ตรงกับแบรนด์และสร้างยอดขายได้จริง (Discovery & Matching Accuracy) ขับเคลื่อนด้วยสถาปัตยกรรม **Async & Batch Processing** 4 ขั้นตอนหลัก:

1. **ขั้นที่ 1 — Brand DNA & Conversion Model Classification (Concurrent Fetching):** ดึงข้อมูลจากทั้ง Website และ Facebook Page ของลูกค้าพร้อมกันแบบ Async เพื่อจำแนกแบรนด์ตามวิธีทำเงิน (4 Conversion Models) และกำหนดสัดส่วนการใช้ KOL คู่กับ KOC
2. **ขั้นที่ 2 — Plain & Natural Thai Search Query Extraction (Single-Job Batch Discovery):** สกัดคำค้นหา TikTok ที่คนไทยพิมพ์ค้นหาสินค้าจริงๆ ในชีวิตประจำวันจากข้อมูลของแบรนด์โดยตรง (ห้ามใช้คำสแลงประดิษฐ์ และห้ามใส่ตัวอย่าง Hardcoded ใน Prompt หรือโค้ด) แล้วยิงค้นหาผ่าน Apify ใน Job เดียว
3. **ขั้นที่ 3 — Two-Stage Filtering, 2x2 KOL/KOC Classification & Batch Scoring:** คัดร้านค้าและบอทสแปมตะกร้าออก (โดยไม่เผลอตัด KOC สายป้ายยาตัวท็อปทิ้ง) จัดกลุ่มครีเอเตอร์เข้าสู่โครงสร้าง **2 กิ่งหลัก (KOL / KOC) แตกเป็น 4 สไตล์ย่อย** ด้วยระบบ Batch LLM & Vector Embedding พร้อมคำนวณคะแนน 100 คะแนนเต็ม
4. **ขั้นที่ 4 — Curated Agency Dashboard & Grounded Competitor Check:** แสดงผลรายชื่อครีเอเตอร์ที่ผ่านการคัดกรองพร้อมเหตุผลประกอบ (Why this Creator Fits), คะแนนแยกรายมิติ และระบบตรวจสอบการรับงานซ้ำกับแบรนด์คู่แข่งในไทย

---

## 2. ขั้นตอนที่ 1: การสกัด Brand DNA และจำแนกแบรนด์ตามวิธีทำเงิน (Brand Conversion Model)

### 2.1 แหล่งข้อมูลขาเข้าแบบขนาน (Concurrent Input Sources)
* **Website URL:** ดึงเนื้อหาหน้าเว็บผ่าน Jina Reader API (`https://r.jina.ai/...`) พร้อมระบบ Fallback ไปยัง `httpx.AsyncClient` + `BeautifulSoup` เพื่อรองรับเว็บยุคใหม่ที่เรนเดอร์ด้วย JavaScript
* **Facebook Page:** ดึงโพสต์และคอมเมนต์ล่าสุดของเพจควบคู่กันไปโดยใช้ `asyncio.gather()` เพื่อวิเคราะห์ Tone of Voice ภาษาไทยของแบรนด์ และเก็บคำถาม/ปัญหาจริงของลูกค้าคนไทย
* **Optional Competitor Override:** ช่องกรอกรายชื่อคู่แข่งเพิ่มเติมจากทีมการตลาด (หากปล่อยว่าง ระบบจะสกัดให้อัตโนมัติ)

### 2.2 การจำแนกประเภทแบรนด์ 4 กลุ่มตามวิธีทำเงิน (4 Brand Conversion Models)
ระบบให้ LLM จำแนกแบรนด์ของลูกค้าเข้าสู่ 1 ใน 4 โมเดลธุรกิจของลูกค้า Convert Cake เพื่อกำหนดกลยุทธ์สัดส่วน KOL:KOC และเกณฑ์การให้คะแนนที่เหมาะสม:

| Brand Conversion Model | ลักษณะธุรกิจและวิธีปิดการขาย | สัดส่วน KOL : KOC แนะนำ | เป้าหมายหลักในการหาครีเอเตอร์ |
| :--- | :--- | :--- | :--- |
| **1. `ECOMMERCE_PRODUCT`** | สินค้าซื้อซ้ำ/ตัดสินใจไวผ่านตะกร้าหรือ E-Commerce | **KOL 30% : KOC 70%** | เน้น KOC สายป้ายยาและรีวิวผลลัพธ์การใช้จริงเพื่อปิดการขายทันที |
| **2. `APP_DIGITAL_SERVICE`** | แอปพลิเคชัน, แพลตฟอร์มดิจิทัล, FinTech, AI, SaaS | **KOL 60% : KOC 40%** | เน้น KOL สายสอนใช้งาน อธิบายฟีเจอร์เข้าใจง่าย และ KOC แชร์ทริคใช้งานจริง |
| **3. `HIGH_TICKET_LEADGEN`** | สินค้า/บริการมูลค่าสูงที่ต้องปรึกษาก่อนซื้อ (คลินิก, คอร์สเรียน, อสังหาฯ, ประกัน) | **KOL 70% : KOC 30%** | เน้น KOL ผู้เชี่ยวชาญสร้างความน่าเชื่อถือสูง คู่กับ KOC แชร์ประสบการณ์จริง |
| **4. `LIFESTYLE_EXPERIENCE`** | สถานที่, โรงแรม, ร้านอาหาร, แฟชั่น, สินค้าภาพลักษณ์พรีเมียม | **KOL 60% : KOC 40%** | เน้น KOL สายถ่ายภาพสวย Mood & Tone ดี คู่กับ KOC สายพากินพาเที่ยว |

---

## 3. ขั้นตอนที่ 2: การสร้างคำค้นหา TikTok ธรรมชาติ (Plain & Natural Thai Search Query Extraction)

### 3.1 กฎเหล็ก: Zero Hardcoded Examples & Templates Policy (สำคัญที่สุด)
เพื่อป้องกันปัญหา LLM ลอกคำตัวอย่างจากธุรกิจหนึ่งไปใช้กับอีกธุรกิจหนึ่ง (Few-Shot Contamination):
1. **ห้ามใส่ตัวอย่างคำค้นหาเฉพาะหมวดหมู่ลงใน System Prompt หรือ Schema Description เด็ดขาด:** ห้ามมีคำตัวอย่างตายตัวอยู่ใน Prompt หรือในโค้ด
2. **ห้ามเขียนโค้ดต่อคำสำเร็จรูป (No Hardcoded String Concatenation):** ห้ามใช้ Python เอาคำนำหน้าสำเร็จรูปมาบวกกับชื่อสินค้า และห้ามมีลิสต์คำค้นหาสำรองแบบ Hardcode ที่ไม่เกี่ยวกับแบรนด์
3. **ยึดข้อมูลจริงจากหน้าเว็บและเพจลูกค้า 100% (Strict Brand Grounding):** คำค้นหาทุกคำต้องเกิดจากการผสมคำนามหมวดสินค้าจริงของลูกค้ารายนั้น เข้ากับคุณสมบัติหรือจุดเด่นที่สกัดได้จากเนื้อหาของแบรนด์นั้นเท่านั้น

### 3.2 หลักการสร้างคำค้นหาตามพฤติกรรมคนไทยจริง (Everyday Search Behavior)
คนไทยเวลาพิมพ์ค้นหาข้อมูลในช่อง Search ของ TikTok จะใช้คำธรรมดาที่ตรงไปตรงมา ไม่ได้พิมพ์คำสแลงประดิษฐ์:
* **ไม่ต้องฝืนแยกคำค้นหาด้วยคำสแลง KOL/KOC ตอนเสิร์ช:** ให้สร้างชุดคำค้นหาหลักที่เป็นธรรมชาติจำนวน 6–8 คำ เพื่อดึงคลิปในหมวดสินค้านั้นออกมาให้ตรงที่สุด แล้วค่อยจำแนก KOL กับ KOC ในขั้นตอนที่ 3 หลังจากดึงข้อมูลโปรไฟล์มาแล้ว
* **โครงสร้างคำค้นหาที่อนุญาตให้ LLM สร้าง (Abstract Syntax Rules):**
  1. `<คำนามหมวดหมู่สินค้าย่อยของแบรนด์> + <คุณสมบัติเด่นหรือผลลัพธ์หลัก>`
  2. `<คำนามหมวดหมู่สินค้าย่อยของแบรนด์> + <สัญชาติแบรนด์ / ประเภท / กลุ่มเป้าหมาย>`
  3. `รีวิว + <คำนามหมวดหมู่สินค้าย่อยของแบรนด์>` หรือ `แนะนำ + <คำนามหมวดหมู่สินค้าย่อยของแบรนด์>`
  4. `<คำนามหมวดหมู่สินค้าย่อยของแบรนด์> + <ชื่อแบรนด์ลูกค้า หรือ ชื่อแบรนด์คู่แข่งในไทย>`
* **ความยาวคำค้นหา:** กระชับ เป็นธรรมชาติ (2–4 คำติดกัน ความยาวไม่เกิน 18 ตัวอักษรไทย) เพื่อให้ TikTok Search Engine จับคู่กับแคปชันและเสียงพูดในคลิปได้แม่นยำที่สุด

---

## 4. ขั้นตอนที่ 3: การคัดกรอง 2 ชั้น, การจัดกลุ่ม 2x2 Matrix และการให้คะแนน (Filter, Classify & Score)

### 4.1 ด่านคัดกรองที่ 1: Rule-Based Merchant vs. KOC Separator
ระบบต้องคัด **"ร้านค้าของแบรนด์อื่น"** และ **"บอทสแปมตะกร้า"** ออก โดย **ห้ามเผลอตัด KOC สายป้ายยาตัวจริงทิ้ง**:

1. **การคัดร้านค้าออก (Merchant Store Exclusion):**
   * ตัดออกทันทีหาก `Bio` หรือ `Nickname` มีคำบ่งชี้ร้านค้าชัดเจน (*Official, Store, Shop, ตัวแทนจำหน่าย, ราคาส่ง, เปิดบิล, สั่งซื้อจิ้มลิงก์*) **และไม่มี** สัญญาณการเป็นครีเอเตอร์รับงานรีวิว (`For work`, `ติดต่องาน`, `DM for work`, `รับรีวิว`)
2. **การแยก "บอทสแปมตะกร้า (Spam Bot)" ออกจาก "KOC สายป้ายยาตัวจริง (Real KOC)":**
   * **ห้ามตัดคนออกเพียงเพราะปักตะกร้าเหลืองเยอะอย่างเดียว** เพราะ KOC ตัวท็อปมักปักตะกร้าเกือบทุกคลิป
   * ระบบจะตีตราว่าเป็น `Affiliate Spam Bot` และตัดออก **ก็ต่อเมื่อเข้าเงื่อนไขครบทั้ง 3 ข้อพร้อมกัน (Multi-Condition AND Gate)**:
     1. สัดส่วนคลิปปักตะกร้าเหลืองสูงผิดปกติ (`Commerce Video Ratio > 85%`) **AND**
     2. ไม่มีข้อมูลตัวตนหรือช่องทางติดต่องานรีวิวใน Bio (`is_work_ready == False`) **AND**
     3. ขาดการมีส่วนร่วมของคนดูจริง (`Median Comments per Video <= 1` หรือ `Median Views < 300`)

### 4.2 ด่านคัดกรองที่ 2: Batch LLM Relevance Gate & 2x2 Role Classification
สำหรับครีเอเตอร์ที่ผ่านด่านแรก ระบบจะรวบรวมข้อมูลย่อ (`@handle`, `Bio`, `ตัวอย่างแคปชัน 3 คลิปล่าสุด`) ส่งเข้า `Gemini 3.5 Flash Lite` พร้อมกันใน **1 API Call (Batch Screening)** เพื่อคัดคนที่หลุดหมวดหมู่ออก (`is_relevant_creator = false`) และจัดกลุ่มคนที่ผ่านเข้ารอบเข้าสู่โครงสร้าง **2 กิ่งหลัก แตกเป็น 4 สไตล์ย่อย (2x2 Matrix)**:

#### กิ่งที่ 1: 🧠 KOL (Key Opinion Leader) — *สำหรับทำ Top & Mid-Funnel (สร้างการรับรู้และความน่าเชื่อถือ)*
1. **`KOL - Expert / Guru` (สายผู้เชี่ยวชาญ / ให้ความรู้เจาะลึก):**
   * **เอกลักษณ์:** อธิบายหลักการ วิเคราะห์ส่วนผสม/สเปก สอนวิธีแก้ปัญหา หรือเปรียบเทียบเชิงลึก
   * **สัญญาณสถิติ:** ยอดกดเซฟเก็บไว้ดูซ้ำสูง (`Save Rate = collectCount / playCount` สูง)
2. **`KOL - Lifestyle / Aesthetic` (สายไลฟ์สไตล์ / สร้างภาพลักษณ์):**
   * **เอกลักษณ์:** ถ่ายคลิปสวย Mood & Tone ดี นำเสนอผ่านไลฟ์สไตล์ การท่องเที่ยว คาเฟ่ การแต่งตัว
   * **สัญญาณสถิติ:** ยอดวิวเฉลี่ยสูง ภาพลักษณ์ช่องคลีน ปักตะกร้าขายของน้อย (`< 20%`)

#### กิ่งที่ 2: 🛍️ KOC (Key Opinion Consumer) — *สำหรับทำ Bottom-Funnel (เร่งการตัดสินใจซื้อและปิดการขาย)*
3. **`KOC - Hard-Sell Reviewer` (สายป้ายยา / รีวิวเน้นปิดการขาย):**
   * **เอกลักษณ์:** รีวิวตรงไปตรงมา โชว์ผลลัพธ์การใช้จริง เทียบความคุ้มค่า ปักตะกร้าเก่งและกระตุ้นให้คนกดซื้อตาม
   * **สัญญาณสถิติ:** มีสัดส่วนคนคอมเมนต์ถามราคา/พิกัดสูง (`Comment-to-Like Ratio` สูง) และมีคนดูจริง
4. **`KOC - Everyday User / Vlog` (สายผู้ใช้จริงในชีวิตประจำวัน):**
   * **เอกลักษณ์:** คนธรรมดาที่ถ่ายคลิปชีวิตประจำวันเรียลๆ แล้วหยิบของที่ใช้จริงมาบอกต่อแบบเพื่อนแนะนำเพื่อน
   * **สัญญาณสถิติ:** Engagement Rate สูง มีความเป็นธรรมชาติและเข้าถึงง่าย (มักอยู่ในกลุ่ม Nano ถึง Micro Tier)

---

### 4.3 สูตรคำนวณคะแนน 100 คะแนนเต็ม (Dynamic & Proxy-Based Scoring)

#### หมวดที่ 1: Brand & Content Relevance (40 คะแนน)
* **Semantic & LLM Fit Score (30 คะแนน):** คำนวณจากค่า Cosine Similarity (ผ่าน `gemini-embedding-2` แบบ Batch Vectorization) ร่วมกับคะแนนความตรงหมวดหมู่จาก LLM Relevance Gate
* **Work-Ready & Niche Match Bonus (10 คะแนน):** ได้คะแนนพิเศษเมื่อตรวจพบช่องทางติดต่องานใน Bio (`is_work_ready`) และมีเนื้อหาตรงกับ Sub-category ของลูกค้า

#### หมวดที่ 2: Engagement Quality & View Consistency (35 คะแนน)
* **Median Engagement Rate (15 คะแนน):**
  $$\text{ER\%} = \frac{\text{Likes} + \text{Comments} + \text{Shares} + \text{Saves}}{\text{Views}} \times 100$$
  *(คำนวณจากค่า **Median** ของคลิปที่มียอดวิว $\ge 500$ วิว เพื่อป้องกันค่าเพี้ยนจากคลิปไวรัลฟลุ๊คคลิปเดียว)*
* **Save & Share Utility Score (10 คะแนน):** คำนวณจาก `(collectCount + 0.7 * shareCount) / playCount` เพื่อวัดว่าคอนเทนต์มีคุณค่าต่อการตัดสินใจซื้อหรือไม่
* **View Consistency Ratio (10 คะแนน):** คำนวณจาก `Median Views / Mean Views` เพื่อวัดความเสถียรของยอดวิวทุกคลิป

#### หมวดที่ 3: Audience Proxy & Commercial Fit (25 คะแนน)
* **Thai Audience Authenticity (10 คะแนน):** สัดส่วนการใช้ภาษาไทยในแคปชันและชื่อช่อง เพื่อยืนยันฐานผู้ชมในประเทศไทย
* **Buyer Intent Proxy (10 คะแนน):** วัดจากสัดส่วน `commentCount / diggCount` (ช่องที่คนดูสนใจซื้อจะมีอัตราการพิมพ์คอมเมนต์ถามสูงกว่าช่องที่คนกดไลก์ผ่านๆ)
* **Brand-Adaptive Commercial Health (5 คะแนน):**
  * หากแบรนด์ลูกค้าเป็น `ECOMMERCE_PRODUCT`: ครีเอเตอร์กลุ่ม KOC ที่ปักตะกร้าเก่งและมี Engagement ดีจะได้คะแนนเต็ม 5/5
  * หากแบรนด์ลูกค้าเป็น `LIFESTYLE_EXPERIENCE` หรือ `HIGH_TICKET_LEADGEN`: ช่องที่เน้นความน่าเชื่อถือและไม่สแปมขายของจิปาถะจะได้คะแนนสูงกว่า

---

## 5. ระบบสกัดและตรวจสอบแบรนด์คู่แข่งในไทย 3 ชั้น (Grounded Thai Competitor Detection)

1. **Layer 1: Search-Grounded Competitor Extraction** — เปิดใช้ Google Search Grounding ร่วมกับ LLM เพื่อค้นหาแบรนด์คู่แข่งที่มีขายจริงในตลาดไทย ณ ปัจจุบัน ในหมวดหมู่และระดับราคาเดียวกัน
2. **Layer 2: Bottom-Up TikTok Co-occurrence Discovery** — สกัดรายชื่อแบรนด์อื่นๆ ที่ถูกพูดถึงหรือติดแฮชแท็กซ้ำบ่อยที่สุดในกลุ่มคลิปที่ดึงมาจาก TikTok จริง
3. **Layer 3: Sub-Category Conflict & UI Override** — ตรวจสอบว่าครีเอเตอร์เพิ่งรับงานรีวิวสินค้าในหมวดย่อยเดียวกันหรือไม่ พร้อมแสดงป้ายเตือน `⚠️ Competitor Conflict` บนหน้า UI

---

## 6. สถาปัตยกรรม Async & Batch Processing และการแสดงผลบน Dashboard

### 6.1 การเพิ่มความเร็วด้วย Async & Batch Pipeline
เพื่อให้ระบบประมวลผลตั้งแต่ต้นจนจบภายในเวลาไม่เกิน **30–45 วินาที** (หรือ **< 2 วินาที** เมื่อใช้ Cache):
* **Concurrent Scraping:** ดึงข้อมูล Website และ Facebook Page พร้อมกันด้วย `asyncio.gather()`
* **Single-Job Apify Batching:** มัดรวมคำค้นหาทั้ง 6–8 คำ ส่งเข้า Apify `clockworks~tiktok-scraper` ใน API Job เดียว (ไม่วนลูปสร้าง Task แยกทีละคำ)
* **Vectorized Embedding Batch:** ส่งข้อความโปรไฟล์ของครีเอเตอร์ทุกคนเข้า `gemini-embedding-2` เป็น Array ก้อนเดียวใน 1 API Call แล้วคำนวณ Cosine Similarity ด้วย `numpy` Matrix Multiplication
* **Single-Call LLM Screening:** คัดกรองความเกี่ยวข้อง (Relevance Gate), จัดกลุ่ม `2x2 KOL/KOC Role`, และสร้างเหตุผลประกอบ (`why_it_fits` 1 ประโยคสั้นๆ) สำหรับครีเอเตอร์ทุกคนพร้อมกันใน 1–2 Batch API Calls โดยไม่ต้องยิง LLM แยกเพื่อเจนสคริปต์รายคน

### 6.2 ข้อมูลที่แสดงบน Agency Dashboard (KOL/KOC Discovery View)
* **Strategy Summary Banner:** แสดงประเภทแบรนด์ (`Conversion Model`), คำค้นหาธรรมชาติที่ใช้ดึงข้อมูล, และสัดส่วน `KOL : KOC` ที่แนะนำสำหรับแคมเปญ
* **Interactive Filters:** กรองรายชื่อตาม **กิ่งหลัก (`All` / `🧠 KOL` / `🛍️ KOC`)**, **สไตล์ย่อย 4 แบบ (`Expert Guru`, `Lifestyle Aesthetic`, `Hard-Sell Reviewer`, `Everyday Vlog`)**, และ **Follower Tier (`Nano`, `Micro`, `Mid-Tier`, `Macro`)**
* **Creator Evaluation Card:**
  * ชื่อช่อง, `@handle`, ลิงก์กดไปหน้าโปรไฟล์ TikTok โดยตรง และสถานะ `✅ Open for Work` / `⚠️ Competitor Conflict`
  * ป้ายกำกับ `Main Role (KOL / KOC)` คู่กับ `Sub-Style` และ `Follower Tier`
  * คะแนนรวมเต็ม 100 พร้อมหลอดคะแนนย่อย 3 แกน (*Brand Relevance 40* / *Engagement & Consistency 35* / *Audience & Commercial Proxy 25*)
  * **Matching Rationale (`Why this Creator Fits`):** สรุปเหตุผลสั้นๆ 1 ประโยคที่อธิบายว่าทำไมเนื้อหาของช่องนี้ถึงเหมาะกับแบรนด์ของลูกค้า
  * สถิติสำคัญ: ยอดผู้ติดตาม, ยอดวิวเฉลี่ย (Median Views), Engagement Rate (%), และ Save Rate (%) พร้อมปุ่ม `Export to CSV`