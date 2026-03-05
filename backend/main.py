"""
Lead Extractor - FastAPI Backend

Main application entry point with all API endpoints.
"""
import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config import LICENSE_MASTER_KEY, SERPAPI_KEY, TIER_LIMITS
from backend.license.validator import validate_license_key, LicenseInfo
from backend.search.google_search import google_search_with_context
from backend.search.serp_api import serpapi_search
from backend.extractor.page_scraper import scrape_multiple_pages
from backend.extractor.email_extractor import extract_emails
from backend.extractor.name_extractor import extract_names
from backend.database.db import (
    init_db, save_search, save_leads, get_search_history,
    get_leads_for_search, get_all_leads, increment_usage, get_daily_usage,
)
from backend.export.exporter import leads_to_csv, leads_to_excel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="Lead Extractor",
    description="Extract emails and contact info from Google search results",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend static files
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


# ========== Models ==========

class LicenseRequest(BaseModel):
    license_key: str


class SearchRequest(BaseModel):
    keyword: str
    license_key: str
    num_results: int = 20
    include_contact_pages: bool = True


class ExportRequest(BaseModel):
    license_key: str
    search_id: Optional[int] = None
    format: str = "csv"  # csv or excel


# ========== Helper ==========

def _validate_license(license_key: str) -> LicenseInfo:
    """Validate a license key and return info."""
    if not LICENSE_MASTER_KEY:
        # If no master key configured, allow all (dev mode)
        return LicenseInfo(
            email="dev@localhost",
            tier="enterprise",
            expiry=__import__("datetime").datetime(2099, 12, 31),
            max_daily_searches=9999,
            created=__import__("datetime").datetime.utcnow(),
            is_valid=True,
        )
    
    info = validate_license_key(license_key, LICENSE_MASTER_KEY)
    if not info.is_valid:
        raise HTTPException(status_code=403, detail=info.error or "Invalid license key")
    return info


# ========== Startup ==========

@app.on_event("startup")
async def startup():
    """Initialize database on startup."""
    await init_db()
    logger.info("Lead Extractor started!")
    if not LICENSE_MASTER_KEY:
        logger.warning("⚠️  No LICENSE_MASTER_KEY set - running in DEV MODE (no license required)")


# ========== Endpoints ==========

@app.get("/")
async def root():
    """Serve the frontend."""
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"message": "Lead Extractor API v1.0.0"}


@app.post("/api/validate-license")
async def validate_license(request: LicenseRequest):
    """Validate a license key and return tier info."""
    info = _validate_license(request.license_key)
    usage = await get_daily_usage(info.email)
    
    return {
        "valid": True,
        "email": info.email,
        "tier": info.tier,
        "expiry": info.expiry.isoformat(),
        "max_daily_searches": info.max_daily_searches,
        "today_usage": usage,
        "remaining": info.max_daily_searches - usage,
    }


@app.post("/api/search")
async def search_leads(request: SearchRequest):
    """
    Main search endpoint.
    
    1. Validates license
    2. Checks rate limits
    3. Searches Google
    4. Scrapes result pages
    5. Extracts emails and names
    6. Saves to database
    7. Returns results
    """
    # 1. Validate license
    info = _validate_license(request.license_key)
    
    # 2. Check rate limits
    current_usage = await get_daily_usage(info.email)
    if current_usage >= info.max_daily_searches:
        raise HTTPException(
            status_code=429,
            detail=f"Daily search limit reached ({info.max_daily_searches}). Upgrade your license for more searches.",
        )
    
    # 3. Increment usage
    await increment_usage(info.email)
    
    logger.info(f"Search: '{request.keyword}' by {info.email} ({info.tier})")
    
    # 4. Search Google
    if SERPAPI_KEY:
        search_results = await serpapi_search(
            query=request.keyword,
            api_key=SERPAPI_KEY,
            num_results=request.num_results,
        )
    else:
        search_results = await google_search_with_context(
            query=request.keyword,
            num_results=request.num_results,
            include_contact_pages=request.include_contact_pages,
        )
    
    if not search_results:
        return {
            "keyword": request.keyword,
            "total_urls": 0,
            "total_leads": 0,
            "leads": [],
            "message": "No search results found. Try a different keyword.",
        }
    
    # 5. Scrape pages
    urls = [r.url for r in search_results]
    scraped_pages = await scrape_multiple_pages(urls)
    
    # 6. Extract emails and names
    leads = []
    for url, text, soup in scraped_pages:
        emails = extract_emails(text, soup)
        name_info = extract_names(text, soup)
        
        if emails or name_info.get("business_name"):
            lead = {
                "source_url": url,
                "business_name": name_info.get("business_name", ""),
                "contact_names": name_info.get("contact_names", []),
                "emails": emails,
                "phones": name_info.get("phones", []),
            }
            leads.append(lead)
    
    # 7. Save to database
    search_id = await save_search(request.keyword, info.email, len(leads))
    if leads:
        await save_leads(search_id, leads)
    
    logger.info(f"Search complete: {len(leads)} leads from {len(scraped_pages)} pages")
    
    return {
        "search_id": search_id,
        "keyword": request.keyword,
        "total_urls": len(urls),
        "pages_scraped": len(scraped_pages),
        "total_leads": len(leads),
        "leads": leads,
        "usage": {
            "today": current_usage + 1,
            "limit": info.max_daily_searches,
            "remaining": info.max_daily_searches - current_usage - 1,
        },
    }


@app.post("/api/export")
async def export_leads(request: ExportRequest):
    """Export leads as CSV or Excel."""
    info = _validate_license(request.license_key)
    
    if request.search_id:
        leads = await get_leads_for_search(request.search_id)
    else:
        leads = await get_all_leads(info.email)
    
    if not leads:
        raise HTTPException(status_code=404, detail="No leads found to export")
    
    if request.format == "excel":
        content = leads_to_excel(leads)
        return Response(
            content=content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=leads.xlsx"},
        )
    else:
        content = leads_to_csv(leads)
        return Response(
            content=content,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=leads.csv"},
        )


@app.get("/api/history")
async def search_history(license_key: str = Query(...)):
    """Get search history."""
    info = _validate_license(license_key)
    history = await get_search_history(info.email)
    return {"history": history}


@app.get("/api/leads/{search_id}")
async def get_leads(search_id: int, license_key: str = Query(...)):
    """Get leads for a specific search."""
    _validate_license(license_key)
    leads = await get_leads_for_search(search_id)
    return {"leads": leads}


@app.get("/api/health")
async def health():
    """Health check."""
    return {"status": "healthy", "version": "1.0.0"}

