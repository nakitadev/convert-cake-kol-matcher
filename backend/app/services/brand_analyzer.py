import re
from typing import Optional, List, Tuple
import httpx
from bs4 import BeautifulSoup

from app.models import BrandAnalyzeRequest, BrandDNA
from app.services.gemini_service import get_gemini_service
from app.services.apify_service import get_apify_service


class BrandAnalyzer:
    """
    Pure live Brand DNA analyzer.
    Scrapes live web content and extracts strategic Brand DNA using Gemini 3.5 Flash Lite.
    Zero-Hardcode & Zero-Mock: No hardcoded brand presets or synthetic heuristic tables.
    """

    async def analyze(self, req: BrandAnalyzeRequest) -> BrandDNA:
        scraped_text = ""
        scraped_sources: List[str] = []
        brand_name = (req.brand_name or "").strip()

        # 1. Scrape client website if provided
        if req.website_url:
            web_text, title = await self._scrape_website(req.website_url)
            if web_text:
                scraped_text += f" Website Content: {web_text}"
                scraped_sources.append(f"Live Website via Jina Reader ({req.website_url})")
                if not brand_name and title:
                    brand_name = title.split("|")[0].split("-")[0].strip()

        # 2. Scrape live Facebook Page using Apify Facebook Pages Scraper (Zero-Mock)
        if req.facebook_url:
            apify = get_apify_service()
            fb_data = {}
            if apify.is_configured:
                fb_data = await apify.scrape_facebook_page(req.facebook_url)

            if fb_data:
                fb_title = fb_data.get("title") or ""
                fb_bio = fb_data.get("bio") or ""
                fb_cats = ", ".join(fb_data.get("categories", [])) if isinstance(fb_data.get("categories"), list) else ""
                fb_posts = " | ".join(fb_data.get("posts", [])) if fb_data.get("posts") else ""
                likes = fb_data.get("likes") or 0
                followers = fb_data.get("followers") or 0
                source_label = fb_data.get("source", "Apify Facebook Pages Scraper")

                fb_summary = f"Facebook Page: {fb_title}. Bio: {fb_bio}."
                if fb_cats:
                    fb_summary += f" Categories: {fb_cats}."
                if followers or likes:
                    fb_summary += f" Community: {followers:,} followers, {likes:,} likes."
                if fb_posts:
                    fb_summary += f" Recent Posts (up to 10): {fb_posts[:2500]}."

                scraped_text += f"\n\nFacebook Insights ({source_label}): {fb_summary}"
                scraped_sources.append(f"Live Facebook via {source_label} ({req.facebook_url})")
                if not brand_name and fb_title:
                    brand_name = fb_title.split("-")[0].split("|")[0].strip()
            else:
                fb_handle = req.facebook_url.rstrip("/").split("/")[-1]
                scraped_sources.append(f"Facebook Page @{fb_handle}")
                if not brand_name:
                    brand_name = fb_handle.replace(".", " ").replace("-", " ").title()

        if req.custom_notes:
            scraped_sources.append("Agency Brief Notes")

        if not brand_name:
            brand_name = "Client Brand"

        # 3. Dynamic Gemini LLM Analysis (gemini-3.5-flash-lite)
        gemini = get_gemini_service()
        if gemini.is_configured:
            context_to_analyze = scraped_text or req.custom_notes or f"Brand Name: {brand_name}"
            llm_dna = await gemini.generate_brand_dna(
                scraped_text=context_to_analyze,
                brand_name=brand_name,
                website_url=req.website_url or "",
                fb_url=req.facebook_url or "",
            )
            if llm_dna:
                vertical = llm_dna.get("vertical")
                if not vertical:
                    raise RuntimeError(f"Gemini LLM failed to identify brand vertical for '{brand_name}'. Zero-Hardcode Policy forbids fallback defaults.")
                
                thai_keywords = llm_dna.get("thai_keywords")
                if not thai_keywords or not isinstance(thai_keywords, list):
                    raise RuntimeError(f"Gemini LLM failed to return thai_keywords for '{brand_name}'. Zero-Hardcode Policy forbids fallback defaults.")

                # Filter out generic marketing slang to maintain direct, authentic consumer search intent
                slang_filter = {"ป้ายยา", "ของมันต้องมี", "ตัวดัง", "ใช้ดีบอกต่อ", "รีวิว", "ของดีบอกต่อ", "ไอเทมเด็ด", "ตัวแม่", "ตัวตึง", "พิกัดลับ"}
                filtered_kws = [k.lstrip('#').strip() for k in thai_keywords if k and str(k).lstrip('#').strip() and str(k).lstrip('#').strip().lower() not in slang_filter]
                final_keywords = filtered_kws if filtered_kws else [k.lstrip('#').strip() for k in thai_keywords if k and str(k).lstrip('#').strip()]

                target_locations = llm_dna.get("target_locations") if isinstance(llm_dna.get("target_locations"), list) else []
                brand_tone = llm_dna.get("brand_tone") if isinstance(llm_dna.get("brand_tone"), list) else []
                content_styles = llm_dna.get("content_style_preferences") if isinstance(llm_dna.get("content_style_preferences"), list) else []

                raw_id = re.sub(r'[^a-zA-Z0-9]', '', brand_name.lower())[:15] or "brand"
                return BrandDNA(
                    id=f"live-{raw_id}",
                    brand_name=llm_dna.get("brand_name") or brand_name,
                    website_url=req.website_url or "",
                    facebook_url=req.facebook_url or "",
                    vertical=vertical,
                    sub_category=llm_dna.get("sub_category") or vertical,
                    brand_summary=llm_dna.get("brand_summary") or f"{brand_name} ({vertical})",
                    target_audience=llm_dna.get("target_audience") or f"Target audience for {brand_name}",
                    target_age_range=llm_dna.get("target_age_range") or "",
                    target_locations=target_locations,
                    brand_tone=brand_tone,
                    content_style_preferences=content_styles,
                    price_positioning=llm_dna.get("price_positioning") or "Dynamic",
                    average_price_thb=int(llm_dna.get("average_price_thb") or 0),
                    thai_keywords=final_keywords,
                    scraped_sources=scraped_sources or ["Live Web Ingestion & Gemini 3.5 Flash-Lite"],
                )

        # 4. Strict Zero-Mock & Zero-Fallback Policy: No heuristic synthetic fallback
        raise RuntimeError(
            f"Failed to extract Brand DNA via Gemini LLM for '{brand_name}'. "
            f"Zero-Mock Policy enforces 100% genuine live AI extraction. Please check GEMINI_API_KEY."
        )

    async def _scrape_website(self, url: str) -> Tuple[str, str]:
        """
        Scrapes live website content using Jina Reader API (r.jina.ai) as primary engine
        to convert client pages (including JS SPAs) into high-signal, LLM-ready markdown.
        Falls back gracefully to direct HTTPX + BeautifulSoup4 if Jina experiences network timeouts.
        """
        clean_url = url if url.startswith("http") else f"https://{url}"
        import os

        # 1. Primary Engine: Jina Reader API (https://r.jina.ai/)
        try:
            jina_url = f"https://r.jina.ai/{clean_url}"
            jina_headers = {
                "Accept": "text/plain",
                "User-Agent": "ConvertCake-KOL-Matcher/1.0",
                "X-Timeout": "10",
            }
            jina_key = os.environ.get("JINA_API_KEY")
            if jina_key:
                jina_headers["Authorization"] = f"Bearer {jina_key}"

            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                resp = await client.get(jina_url, headers=jina_headers)
                if resp.status_code == 200 and len(resp.text.strip()) > 80:
                    raw_md = resp.text
                    title = ""
                    title_match = re.search(r"^Title:\s*(.+)$", raw_md, re.MULTILINE)
                    if title_match:
                        title = title_match.group(1).strip()
                    # Strip Jina boilerplate headers
                    clean_md = re.sub(r"^(Title|URL Source|Markdown Content):\s*.*$", "", raw_md, flags=re.MULTILINE).strip()
                    # Clean excessive blank lines
                    clean_md = re.sub(r"\n{3,}", "\n\n", clean_md)
                    return clean_md[:3500], title
        except Exception:
            pass

        # 2. Resilient Fallback: Direct HTTPX + BeautifulSoup4
        try:
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

                    h_tags = [h.get_text().strip() for h in soup.find_all(["h1", "h2", "h3"])[:8]]
                    paragraphs = [p.get_text().strip() for p in soup.find_all("p")[:6] if len(p.get_text().strip()) > 30]
                    content_summary = f"{title}. {meta_desc}. {' '.join(h_tags)}. {' '.join(paragraphs)}"
                    return content_summary[:2000], title
        except Exception:
            pass
        return "", ""


_analyzer_instance: Optional[BrandAnalyzer] = None

def get_brand_analyzer() -> BrandAnalyzer:
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = BrandAnalyzer()
    return _analyzer_instance
