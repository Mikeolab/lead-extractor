"""
Database module - SQLite storage for leads and search history.
"""
import aiosqlite
import json
import logging
from datetime import datetime, date
from pathlib import Path
from typing import List, Optional, Dict, Any
from backend.config import DB_PATH

logger = logging.getLogger(__name__)


async def init_db():
    """Initialize the database and create tables."""
    # Ensure data directory exists
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS searches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword TEXT NOT NULL,
                license_email TEXT,
                results_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                search_id INTEGER,
                source_url TEXT,
                business_name TEXT,
                contact_names TEXT,
                emails TEXT,
                phones TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (search_id) REFERENCES searches(id)
            )
        """)
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                license_email TEXT NOT NULL,
                search_date DATE NOT NULL,
                search_count INTEGER DEFAULT 0,
                UNIQUE(license_email, search_date)
            )
        """)
        
        await db.commit()
        logger.info("Database initialized successfully")


async def save_search(keyword: str, license_email: str, results_count: int) -> int:
    """Save a search record and return its ID."""
    async with aiosqlite.connect(str(DB_PATH)) as db:
        cursor = await db.execute(
            "INSERT INTO searches (keyword, license_email, results_count) VALUES (?, ?, ?)",
            (keyword, license_email, results_count),
        )
        await db.commit()
        return cursor.lastrowid


async def save_leads(search_id: int, leads: List[Dict[str, Any]]):
    """Save extracted leads to the database."""
    async with aiosqlite.connect(str(DB_PATH)) as db:
        for lead in leads:
            await db.execute(
                """INSERT INTO leads (search_id, source_url, business_name, contact_names, emails, phones) 
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    search_id,
                    lead.get("source_url", ""),
                    lead.get("business_name", ""),
                    json.dumps(lead.get("contact_names", [])),
                    json.dumps(lead.get("emails", [])),
                    json.dumps(lead.get("phones", [])),
                ),
            )
        await db.commit()
        logger.info(f"Saved {len(leads)} leads for search #{search_id}")


async def get_search_history(license_email: str, limit: int = 50) -> List[Dict]:
    """Get search history for a license."""
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM searches WHERE license_email = ? ORDER BY created_at DESC LIMIT ?",
            (license_email, limit),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_leads_for_search(search_id: int) -> List[Dict]:
    """Get all leads for a specific search."""
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM leads WHERE search_id = ? ORDER BY id",
            (search_id,),
        )
        rows = await cursor.fetchall()
        results = []
        for row in rows:
            lead = dict(row)
            lead["contact_names"] = json.loads(lead["contact_names"]) if lead["contact_names"] else []
            lead["emails"] = json.loads(lead["emails"]) if lead["emails"] else []
            lead["phones"] = json.loads(lead["phones"]) if lead["phones"] else []
            results.append(lead)
        return results


async def get_all_leads(license_email: str, limit: int = 500) -> List[Dict]:
    """Get all leads across all searches for a license."""
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT l.*, s.keyword FROM leads l 
               JOIN searches s ON l.search_id = s.id 
               WHERE s.license_email = ? 
               ORDER BY l.created_at DESC LIMIT ?""",
            (license_email, limit),
        )
        rows = await cursor.fetchall()
        results = []
        for row in rows:
            lead = dict(row)
            lead["contact_names"] = json.loads(lead["contact_names"]) if lead["contact_names"] else []
            lead["emails"] = json.loads(lead["emails"]) if lead["emails"] else []
            lead["phones"] = json.loads(lead["phones"]) if lead["phones"] else []
            results.append(lead)
        return results


async def increment_usage(license_email: str) -> int:
    """Increment daily usage counter and return current count."""
    today = date.today().isoformat()
    
    async with aiosqlite.connect(str(DB_PATH)) as db:
        # Try to insert or update
        await db.execute(
            """INSERT INTO usage (license_email, search_date, search_count) 
               VALUES (?, ?, 1)
               ON CONFLICT(license_email, search_date) 
               DO UPDATE SET search_count = search_count + 1""",
            (license_email, today),
        )
        await db.commit()
        
        # Get current count
        cursor = await db.execute(
            "SELECT search_count FROM usage WHERE license_email = ? AND search_date = ?",
            (license_email, today),
        )
        row = await cursor.fetchone()
        return row[0] if row else 1


async def get_daily_usage(license_email: str) -> int:
    """Get today's usage count for a license."""
    today = date.today().isoformat()
    
    async with aiosqlite.connect(str(DB_PATH)) as db:
        cursor = await db.execute(
            "SELECT search_count FROM usage WHERE license_email = ? AND search_date = ?",
            (license_email, today),
        )
        row = await cursor.fetchone()
        return row[0] if row else 0

