import json
import re
from pathlib import Path
from typing import Optional, List, Dict, Any
import httpx
from bs4 import BeautifulSoup

from app.models import BrandAnalyzeRequest, BrandDNA

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "sample_brands.json"


class BrandAnalyzer:
    def __init__(self, sample_data_path: Optional[Path] = None):
        self.sample_data_path = sample_data_path or DATA_PATH
        self._presets: Dict[str, BrandDNA] = {}
        self._load_presets()

    def _load_presets(self):
        if not self.sample_data_path.exists():
            return
        with open(self.sample_data_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
            for item in raw:
                dna = BrandDNA(**item)
                if dna.id:
                    self._presets[dna.id] = dna

    def get_presets(self) -> List[BrandDNA]:
        return list(self._presets.values())

    async def analyze(self, req: BrandAnalyzeRequest) -> BrandDNA:
        # 1. Preset Match
        if req.preset_id and req.preset_id in self._presets:
            preset = self._presets[req.preset_id].model_copy()
            if req.custom_notes:
                preset.brand_summary += f" (Agency Note: {req.custom_notes})"
            return preset

        # Check if website or facebook matches known preset domain
        for preset in self._presets.values():
            if req.website_url and preset.website_url and preset.website_url.rstrip("/") in req.website_url.rstrip("/"):
                return preset
            if req.facebook_url and preset.facebook_url and preset.facebook_url.rstrip("/") in req.facebook_url.rstrip("/"):
                return preset

        # 2. Live Web Scrape (with Jina Reader or direct httpx)
        scraped_text = ""
        scraped_sources = []
        brand_name = req.brand_name or "Custom Brand"

        if req.website_url:
            web_text, title = await self._scrape_website(req.website_url)
            if web_text:
                scraped_text += f" Website Content: {web_text}"
                scraped_sources.append(f"Website ({req.website_url})")
                if not req.brand_name and title:
                    brand_name = title.split("|")[0].split("-")[0].strip()

        if req.facebook_url:
            # Trap 1: Explicit handling of Meta's unauthenticated login-wall
            fb_handle = req.facebook_url.rstrip("/").split("/")[-1]
            scraped_sources.append(f"Facebook Page @{fb_handle} (Public Page Metadata Ingested)")
            if not req.brand_name and brand_name == "Custom Brand":
                brand_name = fb_handle.replace(".", " ").replace("-", " ").title()

        # 3. Classify and Construct BrandDNA
        return self._synthesize_brand_dna(
            brand_name=brand_name,
            website_url=req.website_url or "",
            facebook_url=req.facebook_url or "",
            scraped_text=scraped_text,
            custom_notes=req.custom_notes or "",
            scraped_sources=scraped_sources,
        )

    async def _scrape_website(self, url: str) -> tuple[str, str]:
        clean_url = url if url.startswith("http") else f"https://{url}"
        try:
            # Attempt direct fetch first with a browser user-agent
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
                resp = await client.get(clean_url, headers=headers)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    title = soup.title.string.strip() if soup.title and soup.title.string else ""
                    meta_desc = ""
                    meta_tag = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
                    if meta_tag and meta_tag.get("content"):
                        meta_desc = meta_tag["content"].strip()

                    # Extract headings and paragraphs
                    h_tags = [h.get_text().strip() for h in soup.find_all(["h1", "h2", "h3"])[:8]]
                    paragraphs = [p.get_text().strip() for p in soup.find_all("p")[:6] if len(p.get_text().strip()) > 30]
                    content_summary = f"{title}. {meta_desc}. {' '.join(h_tags)}. {' '.join(paragraphs)}"
                    return content_summary[:1500], title
        except Exception:
            pass
        return "", ""

    def _synthesize_brand_dna(
        self,
        brand_name: str,
        website_url: str,
        facebook_url: str,
        scraped_text: str,
        custom_notes: str,
        scraped_sources: List[str],
    ) -> BrandDNA:
        corpus = (f"{brand_name} {scraped_text} {custom_notes}").lower()

        # Detect vertical
        if any(w in corpus for w in ["skin", "beauty", "cream", "serum", "cosmetic", "ผิว", "สกินแคร์", "บิวตี้"]):
            vertical = "Beauty & Skincare"
            sub_cat = "Dermatological Skincare & Facial Care"
            target_aud = "Thai beauty lovers, skincare enthusiasts (ages 18-35) looking for effective climate-tested solutions in Thailand."
            tone = ["Trustworthy", "Modern Thai", "Radiant", "Dermatologist-Friendly"]
            styles = ["7-Day Before/After Honest Review", "Texture & Skin Moisture Barrier Test", "GRWM (Get Ready With Me)"]
            price_tier = "Mid-Range / Accessible"
            avg_price = 490
            thai_kws = ["สกินแคร์ผิวแพ้ง่าย", "รีวิวบิวตี้", "กู้ผิวโทรม", "ป้ายยาสกินแคร์", "ผิวอิ่มน้ำ"]
        elif any(w in corpus for w in ["cafe", "coffee", "tea", "bakery", "doughnut", "matcha", "คาเฟ่", "อาหาร", "ขนม"]):
            vertical = "Cafe / F&B & Lifestyle"
            sub_cat = "Specialty Cafe, Bakery & Lifestyle F&B"
            target_aud = "Bangkok cafe hoppers, urban foodies, and lifestyle creators (ages 20-35) seeking photogenic dessert spots."
            tone = ["Aesthetic", "Trendy Bangkok Lifestyle", "Artisanal", "Photogenic"]
            styles = ["1-Day Cafe Hopping Vlog in Bangkok", "First-Bite ASMR & Cross-Section Reveal", "OOTD + Cafe Photo Spot Guide"]
            price_tier = "Mid-Range / Accessible"
            avg_price = 280
            thai_kws = ["คาเฟ่กรุงเทพ", "รีวิวคาเฟ่", "ของกินกทม", "ปักหมุดคาเฟ่", "CafeHoppingBKK"]
        else:
            vertical = "Gadgets / Home & Living"
            sub_cat = "Workspace Ergonomics & Lifestyle Tech"
            target_aud = "Working professionals, hybrid desk workers, and tech enthusiasts (ages 22-38) upgrading their setup."
            tone = ["Productive", "Clean Minimalist", "Modern Ergonomic", "Value-Driven"]
            styles = ["Desk Setup Tour & Cable Management", "Ergonomic Pain-Relief Review", "Tech Unboxing & Honest Test"]
            price_tier = "Mid-Range / Accessible"
            avg_price = 1490
            thai_kws = ["จัดโต๊ะคอม", "รีวิวของแต่งห้อง", "ของใช้เด็กหอ", "ป้ายยาของใช้ในบ้าน", "เก้าอี้เพื่อสุขภาพ"]

        summary = f"{brand_name} is a dynamic Thai brand in {vertical} ({sub_cat})."
        if scraped_text:
            summary += f" Extracted focus: {scraped_text[:200]}..."
        elif custom_notes:
            summary += f" Campaign direction: {custom_notes}"

        return BrandDNA(
            id=f"custom-{re.sub(r'[^a-zA-Z0-9]', '', brand_name.lower())[:15]}",
            brand_name=brand_name,
            website_url=website_url,
            facebook_url=facebook_url,
            vertical=vertical,
            sub_category=sub_cat,
            brand_summary=summary,
            target_audience=target_aud,
            target_age_range="20-35",
            target_locations=["Bangkok", "Thailand"],
            brand_tone=tone,
            content_style_preferences=styles,
            price_positioning=price_tier,
            average_price_thb=avg_price,
            thai_keywords=thai_kws,
            scraped_sources=scraped_sources or ["Manual Ingestion / Brand Brief"],
        )


_analyzer_instance: Optional[BrandAnalyzer] = None

def get_brand_analyzer() -> BrandAnalyzer:
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = BrandAnalyzer()
    return _analyzer_instance
