"""
Deep Scraper Module
Follows contact/about links, parses PDFs, extracts content from deeper pages.
Configurable retries, timing, and live progress callbacks.
"""
from __future__ import annotations

import io
import time
import requests
import warnings
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.config import REQUEST_TIMEOUT, MAX_CONCURRENT_SCRAPES, USER_AGENT

warnings.filterwarnings("ignore", category=UserWarning)


@dataclass
class DeepScrapedPage:
    url: str
    title: str = ""
    text_content: str = ""
    html_content: str = ""
    meta_description: str = ""
    sub_pages: list[dict] = field(default_factory=list)
    pdf_texts: list[str] = field(default_factory=list)
    success: bool = False
    error: str = ""


# ─── Contact Page Detection ─────────────────────────────────────────────────
CONTACT_KEYWORDS = [
    "contact", "about", "team", "staff", "people", "leadership",
    "our-team", "about-us", "contact-us", "get-in-touch", "meet",
    "directory", "management", "who-we-are",
]


def _is_contact_link(href: str, text: str) -> bool:
    combined = f"{href} {text}".lower()
    return any(kw in combined for kw in CONTACT_KEYWORDS)


def _find_contact_links(html: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    links = set()
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        text = a_tag.get_text(strip=True)
        if _is_contact_link(href, text):
            full_url = urljoin(base_url, href)
            if urlparse(full_url).netloc == urlparse(base_url).netloc:
                links.add(full_url)
    return list(links)[:5]


def _find_pdf_links(html: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    pdfs = set()
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        if href.lower().endswith(".pdf"):
            full_url = urljoin(base_url, href)
            pdfs.add(full_url)
    return list(pdfs)[:3]


# ─── Fetch Helpers ───────────────────────────────────────────────────────────
HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def _fetch_page(url: str, timeout: int = REQUEST_TIMEOUT, retries: int = 2) -> tuple:
    """Fetch a page with retries. Returns (html, content_type, status_code)."""
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=timeout,
                                allow_redirects=True)
            ct = resp.headers.get("content-type", "")
            return resp.text, ct, resp.status_code
        except Exception:
            if attempt < retries - 1:
                time.sleep(1)
    return "", "", 0


def _fetch_pdf_text(url: str, timeout: int = 20) -> str:
    """Download a PDF and extract its text."""
    try:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT},
                            timeout=timeout, allow_redirects=True)
        if resp.status_code != 200:
            return ""
        ct = resp.headers.get("content-type", "")
        if "pdf" not in ct and not url.lower().endswith(".pdf"):
            return ""
        import pdfplumber
        pdf_bytes = io.BytesIO(resp.content)
        text_parts = []
        with pdfplumber.open(pdf_bytes) as pdf:
            for page in pdf.pages[:20]:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        return "\n".join(text_parts)
    except Exception:
        return ""


def _extract_text_from_html(html: str) -> tuple:
    soup = BeautifulSoup(html, "lxml")
    for el in soup(["script", "style", "nav", "footer", "header", "noscript"]):
        el.decompose()
    title = soup.title.get_text(strip=True) if soup.title else ""
    meta_desc = ""
    meta_tag = soup.find("meta", attrs={"name": "description"})
    if meta_tag:
        meta_desc = meta_tag.get("content", "")
    text = soup.get_text(separator=" ", strip=True)
    return title, meta_desc, text


# ─── Deep Scrape Single ─────────────────────────────────────────────────────
def deep_scrape_single(
    url: str,
    timeout: int = REQUEST_TIMEOUT,
    retries: int = 2,
    delay: float = 0.5,
    callback=None,
    stop_flag=None,
) -> DeepScrapedPage:
    """
    Deep scrape a single URL:
    1. Fetch main page
    2. Find and scrape contact/about sub-pages
    3. Find and parse PDF links
    """
    domain = urlparse(url).netloc

    try:
        if stop_flag and stop_flag.get("stop"):
            return DeepScrapedPage(url=url, error="Stopped")

        # Step 1: Main page
        if callback:
            callback(f"  [*] Loading: {url[:70]}...")
        html, ct, status = _fetch_page(url, timeout, retries)

        if status != 200 or "text/html" not in ct:
            err = f"HTTP {status}" if status else "Connection failed"
            if callback:
                callback(f"  [!] Failed: {domain} ({err})")
            return DeepScrapedPage(url=url, error=err)

        title, meta_desc, main_text = _extract_text_from_html(html)
        if callback:
            callback(f"  [✓] Loaded: {domain} - \"{title[:50]}\"")

        # Step 2: Find links
        contact_links = _find_contact_links(html, url)
        pdf_links = _find_pdf_links(html, url)

        if callback and (contact_links or pdf_links):
            callback(f"      Found {len(contact_links)} contact pages, {len(pdf_links)} PDF links")

        # Step 3: Scrape contact sub-pages
        sub_pages = []
        for i, link in enumerate(contact_links):
            if stop_flag and stop_flag.get("stop"):
                break
            if delay > 0:
                time.sleep(delay)
            if callback:
                callback(f"      [→] Visiting: {link.split('/')[-1] or link[:50]}...")
            sub_html, sub_ct, sub_status = _fetch_page(link, timeout, retries)
            if sub_status == 200 and "text/html" in sub_ct:
                _, _, sub_text = _extract_text_from_html(sub_html)
                sub_pages.append({"url": link, "text": sub_text, "html": sub_html})
                if callback:
                    callback(f"      [✓] Scraped sub-page ({len(sub_text)} chars)")
            else:
                if callback:
                    callback(f"      [!] Sub-page failed (HTTP {sub_status})")

        # Step 4: Parse PDFs
        pdf_texts = []
        for i, link in enumerate(pdf_links):
            if stop_flag and stop_flag.get("stop"):
                break
            if callback:
                pdf_name = link.split("/")[-1][:40]
                callback(f"      [📄] Opening PDF: {pdf_name}...")
            text = _fetch_pdf_text(link, timeout)
            if text:
                pdf_texts.append(text)
                if callback:
                    callback(f"      [✓] Extracted {len(text)} chars from PDF")
            else:
                if callback:
                    callback(f"      [!] No text extracted from PDF")

        # Combine
        all_text = main_text
        for sp in sub_pages:
            all_text += " " + sp["text"]
        for pt in pdf_texts:
            all_text += " " + pt

        if callback:
            callback(f"  [✓] Done: {domain} ({len(sub_pages)} sub-pages, {len(pdf_texts)} PDFs)")

        return DeepScrapedPage(
            url=url, title=title, text_content=all_text,
            html_content=html + "".join(sp.get("html", "") for sp in sub_pages),
            meta_description=meta_desc, sub_pages=sub_pages,
            pdf_texts=pdf_texts, success=True,
        )

    except Exception as e:
        if callback:
            callback(f"  [!] Error on {domain}: {str(e)[:60]}")
        return DeepScrapedPage(url=url, error=f"Error: {str(e)[:60]}")


# ─── Deep Scrape Multiple ───────────────────────────────────────────────────
def deep_scrape_pages(
    urls: list[str],
    timeout: int = REQUEST_TIMEOUT,
    retries: int = 2,
    delay: float = 0.5,
    max_workers: int = MAX_CONCURRENT_SCRAPES,
    callback=None,
    stop_flag=None,
) -> list[DeepScrapedPage]:
    """
    Deep scrape multiple URLs concurrently.
    """
    results = [None] * len(urls)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_idx = {
            executor.submit(
                deep_scrape_single, url, timeout, retries, delay, callback, stop_flag
            ): i
            for i, url in enumerate(urls)
        }
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            try:
                results[idx] = future.result()
            except Exception as e:
                results[idx] = DeepScrapedPage(url=urls[idx], error=str(e))

    return results
