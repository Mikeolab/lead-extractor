"""
Database Module — SQLite (local) or PostgreSQL/Neon (when DATABASE_URL is set).
"""
from __future__ import annotations
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field
from app.config import DATABASE_PATH

# When DATABASE_URL is set (e.g. on Render + Neon), use PostgreSQL
_use_postgres = bool(os.environ.get("DATABASE_URL"))

if _use_postgres:
    from app.database import db_postgres as _db
else:
    _db = None


def get_connection():
    """Get a database connection, creating the DB and tables if needed."""
    if _use_postgres and _db:
        return _db.get_connection()
    # SQLite path
    # Ensure directory exists
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(DATABASE_PATH), timeout=60)
    conn.row_factory = sqlite3.Row
    # allow longer write-lock wait to avoid locked errors when concurrent threads hit DB
    conn.execute("PRAGMA busy_timeout = 60000")
    conn.execute("PRAGMA journal_mode=WAL")

    # Create tables
    conn.executescript("""        CREATE TABLE IF NOT EXISTS searches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT NOT NULL,
            num_results INTEGER DEFAULT 0,
            num_leads INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            search_id INTEGER,
            business_name TEXT DEFAULT '',
            contact_name TEXT DEFAULT '',
            email TEXT DEFAULT '',
            phone TEXT DEFAULT '',
            website TEXT DEFAULT '',
            source_url TEXT DEFAULT '',
            snippet TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (search_id) REFERENCES searches(id)
        );

        CREATE INDEX IF NOT EXISTS idx_leads_search_id ON leads(search_id);
        CREATE INDEX IF NOT EXISTS idx_leads_email ON leads(email);

        -- Email module tables
        CREATE TABLE IF NOT EXISTS mailboxes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            provider TEXT NOT NULL,
            smtp_host TEXT NOT NULL,
            smtp_port INTEGER NOT NULL,
            smtp_username TEXT NOT NULL,
            smtp_password_encrypted TEXT NOT NULL,
            api_key_encrypted TEXT,
            daily_limit INTEGER DEFAULT 500,
            sent_today INTEGER DEFAULT 0,
            sent_total INTEGER DEFAULT 0,
            is_active BOOLEAN DEFAULT 1,
            last_used TIMESTAMP,
            last_error TEXT,
            error_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS email_campaigns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            subject_template TEXT NOT NULL,
            body_template TEXT NOT NULL,
            status TEXT DEFAULT 'draft',
            total_recipients INTEGER DEFAULT 0,
            sent_count INTEGER DEFAULT 0,
            failed_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            started_at TIMESTAMP,
            completed_at TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS email_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            campaign_id INTEGER,
            mailbox_id INTEGER,
            recipient_email TEXT NOT NULL,
            recipient_name TEXT,
            subject TEXT NOT NULL,
            body TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            priority INTEGER DEFAULT 0,
            attempts INTEGER DEFAULT 0,
            max_attempts INTEGER DEFAULT 3,
            error_message TEXT,
            scheduled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            processed_at TIMESTAMP,
            sent_at TIMESTAMP,
            FOREIGN KEY (campaign_id) REFERENCES email_campaigns(id),
            FOREIGN KEY (mailbox_id) REFERENCES mailboxes(id)
        );

        CREATE INDEX IF NOT EXISTS idx_mailboxes_active ON mailboxes(is_active, sent_today);
        CREATE INDEX IF NOT EXISTS idx_queue_status ON email_queue(status, priority DESC, scheduled_at);
        CREATE INDEX IF NOT EXISTS idx_queue_mailbox ON email_queue(mailbox_id, status);
        CREATE INDEX IF NOT EXISTS idx_queue_campaign ON email_queue(campaign_id, status);
    """)

    conn.commit()
    return conn


def save_search(query: str, num_results: int = 0) -> int:
    """Save a search record and return its ID."""
    if _use_postgres and _db:
        return _db.save_search(query, num_results)
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO searches (query, num_results) VALUES (?, ?)",
        (query, num_results),
    )
    search_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return search_id


def save_leads(search_id: int, leads: list[dict], replace: bool = False) -> int:
    """
    Save a batch of leads for a search.

    Args:
        search_id: The search ID to associate leads with
        leads: List of lead dicts with keys: business_name, contact_name,
               email, phone, website, source_url, snippet
        replace: If True, delete existing leads for this search first (for incremental saves)

    Returns:
        Number of leads saved
    """
    if not leads:
        return 0
    if _use_postgres and _db:
        return _db.save_leads(search_id, leads, replace=replace)

    conn = get_connection()
    if replace:
        conn.execute("DELETE FROM leads WHERE search_id = ?", (search_id,))
    count = 0

    for lead in leads:
        conn.execute(
            """INSERT INTO leads 
               (search_id, business_name, contact_name, email, phone, website, source_url, snippet)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                search_id,
                lead.get("business_name", ""),
                lead.get("contact_name", ""),
                lead.get("email", ""),
                lead.get("phone", ""),
                lead.get("website", ""),
                lead.get("source_url", ""),
                lead.get("snippet", ""),
            ),
        )
        count += 1

    # Update search record with lead count
    conn.execute(
        "UPDATE searches SET num_leads = ? WHERE id = ?",
        (count, search_id),
    )

    conn.commit()
    conn.close()
    return count


def get_recent_searches(limit: int = 20) -> list[dict]:
    """Get recent search history."""
    if _use_postgres and _db:
        return _db.get_recent_searches(limit)
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM searches ORDER BY created_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_leads_by_search(search_id: int) -> list[dict]:
    """Get all leads for a specific search."""
    if _use_postgres and _db:
        return _db.get_leads_by_search(search_id)
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM leads WHERE search_id = ? ORDER BY id",
        (search_id,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_all_leads(limit: int = 1000) -> list[dict]:
    """Get all leads across all searches."""
    if _use_postgres and _db:
        return _db.get_all_leads(limit)
    conn = get_connection()
    rows = conn.execute(
        """SELECT l.*, s.query as search_query 
           FROM leads l 
           LEFT JOIN searches s ON l.search_id = s.id 
           ORDER BY l.created_at DESC 
           LIMIT ?""",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def delete_search(search_id: int) -> None:
    """Delete a search and its associated leads."""
    if _use_postgres and _db:
        return _db.delete_search(search_id)
    conn = get_connection()
    conn.execute("DELETE FROM leads WHERE search_id = ?", (search_id,))
    conn.execute("DELETE FROM searches WHERE id = ?", (search_id,))
    conn.commit()
    conn.close()


def get_lead_stats() -> dict:
    """Get summary statistics about all leads."""
    if _use_postgres and _db:
        return _db.get_lead_stats()
    conn = get_connection()

    total_searches = conn.execute("SELECT COUNT(*) FROM searches").fetchone()[0]
    total_leads = conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
    unique_emails = conn.execute(
        "SELECT COUNT(DISTINCT email) FROM leads WHERE email != ''"
    ).fetchone()[0]
    unique_domains = conn.execute(
        "SELECT COUNT(DISTINCT website) FROM leads WHERE website != ''"
    ).fetchone()[0]

    conn.close()

    return {
        "total_searches": total_searches,
        "total_leads": total_leads,
        "unique_emails": unique_emails,
        "unique_domains": unique_domains,
    }

