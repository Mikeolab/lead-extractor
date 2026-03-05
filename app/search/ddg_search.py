"""
DuckDuckGo Search Module - No API Key Required
Multi-page search with configurable timing, retries, and batch support.
Uses requests library for maximum SSL compatibility (LibreSSL 2.8+).
"""
from __future__ import annotations

import time
import random
import requests
import warnings
from dataclasses import dataclass, field
from urllib.parse import urlparse, quote_plus, parse_qs
from bs4 import BeautifulSoup

warnings.filterwarnings("ignore", category=UserWarning)


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    display_link: str = ""
    is_pdf: bool = False


@dataclass
class SearchResponse:
    query: str
    total_results: int
    results: list[SearchResult] = field(default_factory=list)
    error: str = ""
    search_mode: str = ""
    pages_fetched: int = 0


# ─── Search Modes ────────────────────────────────────────────────────────────
SEARCH_MODES = {
    "general": {
        "name": "🌐 General Web Search",
        "description": "Broad web search — finds all types of pages",
        "suffix": "",
        "icon": "🌐",
    },
    "pdf": {
        "name": "📄 PDF Documents Only",
        "description": "Search exclusively for PDF files (company lists, directories, reports)",
        "suffix": "filetype:pdf",
        "icon": "📄",
    },
    "pdf_emails": {
        "name": "📄📧 PDFs with Emails",
        "description": "PDF documents likely containing email addresses",
        "suffix": "filetype:pdf intext:@",
        "icon": "📄",
    },
    "email_focus": {
        "name": "📧 Email-Rich Pages",
        "description": "Targets pages likely to contain email addresses",
        "suffix": 'email "contact us" "@"',
        "icon": "📧",
    },
    "directories": {
        "name": "📇 Business Directories",
        "description": "Search business listing sites (BBB, Yelp, YellowPages)",
        "suffix": "directory listing business",
        "icon": "📇",
    },
    "contact_pages": {
        "name": "📞 Contact Pages",
        "description": "Find contact and about pages with phone/email info",
        "suffix": '"contact us" OR "about us" OR "get in touch" phone email',
        "icon": "📞",
    },
    "associations": {
        "name": "🏢 Associations & Chambers",
        "description": "Find industry associations and chamber member lists",
        "suffix": "association OR chamber OR members list OR directory",
        "icon": "🏢",
    },
    "social": {
        "name": "👔 Professional Profiles",
        "description": "Search for professional and social profiles",
        "suffix": "linkedin OR facebook OR profile",
        "icon": "👔",
    },
}


def get_search_modes() -> dict:
    return SEARCH_MODES


# ─── Session Management ─────────────────────────────────────────────────────
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]


def _get_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    })
    return session


# ─── HTML Parser ─────────────────────────────────────────────────────────────
def _parse_ddg_results(html: str) -> list[SearchResult]:
    results = []
    soup = BeautifulSoup(html, "lxml")
    for item in soup.select(".result"):
        title_el = item.select_one(".result__a")
        snippet_el = item.select_one(".result__snippet")
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        href = title_el.get("href", "")
        if "uddg=" in href:
            parsed_qs = parse_qs(urlparse(href).query)
            if "uddg" in parsed_qs:
                href = parsed_qs["uddg"][0]
        snippet = snippet_el.get_text(strip=True) if snippet_el else ""
        if not href or not title:
            continue
        parsed = urlparse(href)
        display_link = parsed.netloc
        if "duckduckgo.com" in display_link:
            continue
        is_pdf = href.lower().endswith(".pdf")
        results.append(SearchResult(
            title=title, url=href, snippet=snippet,
            display_link=display_link, is_pdf=is_pdf,
        ))
    return results


def _fetch_next_page(session: requests.Session, html: str, timeout: int = 15) -> tuple:
    """Find the 'next' button in DDG HTML and fetch page 2+. Returns (html, success)."""
    soup = BeautifulSoup(html, "lxml")
    next_form = soup.find("form", class_="nav-link")
    if not next_form:
        return "", False
    form_data = {}
    for inp in next_form.find_all("input"):
        name = inp.get("name", "")
        value = inp.get("value", "")
        if name:
            form_data[name] = value
    action = next_form.get("action", "/html/")
    next_url = f"https://html.duckduckgo.com{action}"
    try:
        resp = session.post(next_url, data=form_data, timeout=timeout)
        if resp.status_code in (200, 202) and "anomaly" not in resp.text.lower():
            return resp.text, True
    except Exception:
        pass
    return "", False


# ─── Main Search Function ───────────────────────────────────────────────────
def ddg_search(
    query: str,
    num_results: int = 10,
    mode: str = "general",
    max_pages: int = 3,
    delay_between_pages: float = 2.0,
    max_retries: int = 2,
    timeout: int = 15,
    callback=None,
    stop_flag=None,
) -> SearchResponse:
    """
    Multi-page DuckDuckGo search with retries and timing.

    Args:
        query: Search query string
        num_results: Target number of results
        mode: Search mode key
        max_pages: Maximum pages to fetch (1 page ≈ 10 results)
        delay_between_pages: Seconds to wait between pages
        max_retries: Number of retries on failure
        timeout: Request timeout in seconds
        callback: Optional function(message) for live updates
        stop_flag: Optional dict with {"stop": bool} to check for cancellation

    Returns:
        SearchResponse with results
    """
    mode_info = SEARCH_MODES.get(mode, SEARCH_MODES["general"])
    suffix = mode_info["suffix"]
    full_query = f"{query} {suffix}".strip() if suffix else query

    if callback:
        callback(f"🔎 Query: \"{full_query}\"")
        callback(f"   Mode: {mode_info['name']} | Max Pages: {max_pages} | Retries: {max_retries}")

    try:
        session = _get_session()
        all_results = []
        pages_fetched = 0
        last_html = ""

        for page_num in range(1, max_pages + 1):
            # Check stop flag
            if stop_flag and stop_flag.get("stop"):
                if callback:
                    callback("🛑 Search stopped by user")
                break

            # Delay between pages (not for first page)
            if page_num > 1:
                if callback:
                    callback(f"   ⏳ Waiting {delay_between_pages}s before page {page_num}...")
                time.sleep(delay_between_pages)

            # Fetch page (with retries)
            success = False
            for attempt in range(1, max_retries + 1):
                if stop_flag and stop_flag.get("stop"):
                    break

                try:
                    if page_num == 1:
                        url = f"https://html.duckduckgo.com/html/?q={quote_plus(full_query)}"
                        resp = session.get(url, timeout=timeout)
                    else:
                        resp_text, ok = _fetch_next_page(session, last_html, timeout)
                        if not ok:
                            if callback:
                                callback(f"   ⚠️ No more pages available")
                            break
                        resp = type("R", (), {"status_code": 200, "text": resp_text})()

                    if hasattr(resp, "status_code") and resp.status_code not in (200, 202):
                        raise Exception(f"HTTP {resp.status_code}")

                    if "anomaly" in resp.text.lower():
                        if callback:
                            callback(f"   ⚠️ Rate limited (attempt {attempt}/{max_retries}), waiting...")
                        time.sleep(5 * attempt)
                        session = _get_session()  # New session with new UA
                        continue

                    page_results = _parse_ddg_results(resp.text)
                    last_html = resp.text

                    if page_results:
                        all_results.extend(page_results)
                        pages_fetched += 1
                        if callback:
                            callback(f"   ✅ Page {page_num}: {len(page_results)} results (total: {len(all_results)})")
                        success = True
                        break
                    else:
                        if callback:
                            callback(f"   ⚠️ Page {page_num}: 0 results (attempt {attempt}/{max_retries})")
                        if attempt < max_retries:
                            time.sleep(3)
                            session = _get_session()

                except Exception as e:
                    if callback:
                        callback(f"   ❌ Page {page_num} attempt {attempt} failed: {str(e)[:50]}")
                    if attempt < max_retries:
                        time.sleep(3 * attempt)
                        session = _get_session()

            # Enough results?
            if len(all_results) >= num_results:
                break

            # If page failed entirely, stop pagination
            if not success and page_num > 1:
                break

        # Trim
        all_results = all_results[:num_results]

        if not all_results:
            return SearchResponse(
                query=query, total_results=0, search_mode=mode,
                pages_fetched=pages_fetched,
                error="No results found. Try a different keyword or search mode.",
            )

        if callback:
            pdf_count = sum(1 for r in all_results if r.is_pdf)
            extra = f" ({pdf_count} PDFs)" if pdf_count else ""
            callback(f"✅ Search done: {len(all_results)} results from {pages_fetched} page(s){extra}")

        return SearchResponse(
            query=query, total_results=len(all_results),
            results=all_results, search_mode=mode,
            pages_fetched=pages_fetched,
        )

    except Exception as e:
        return SearchResponse(
            query=query, total_results=0, search_mode=mode,
            error=f"Search error: {str(e)}",
        )
