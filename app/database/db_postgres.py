"""
PostgreSQL/Neon Database Module
Uses same interface as db.py for SQLite - swap when DATABASE_URL is set.
"""
from __future__ import annotations
import os
import re
import psycopg2
from psycopg2.extras import RealDictCursor


def _param_style(sql: str) -> str:
    """Convert SQLite ? placeholders to PostgreSQL %s."""
    return re.subn(r"\?", "%s", sql)[0]


class _CompatRow:
    """Row that supports both row[0] and row['col'] access for compatibility."""

    def __init__(self, row_dict: dict, col_order: list):
        self._dict = row_dict
        self._list = [row_dict.get(k) for k in col_order]

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._list[key] if key < len(self._list) else None
        return self._dict.get(key)

    def __contains__(self, key):
        return key in self._dict

    def keys(self):
        return self._dict.keys()


class _CursorAdapter:
    """Makes psycopg2 cursor behave like sqlite3 for existing code."""

    def __init__(self, cursor):
        self._cur = cursor
        self.lastrowid = None
        self._col_order = [d[0] for d in (cursor.description or [])]

    def execute(self, sql: str, params=None):
        sql = _param_style(sql)
        if params:
            self._cur.execute(sql, params)
        else:
            self._cur.execute(sql)
        # Capture last inserted id for INSERT
        if sql.strip().upper().startswith("INSERT") and "RETURNING" not in sql.upper():
            try:
                self._cur.execute("SELECT lastval()")
                self.lastrowid = self._cur.fetchone()[0]
            except Exception:
                self.lastrowid = None
        else:
            self.lastrowid = getattr(self._cur, "lastrowid", None)
        return self

    def fetchone(self):
        row = self._cur.fetchone()
        if row is None:
            return None
        if isinstance(row, dict):
            return _CompatRow(row, self._col_order)
        return row

    def fetchall(self):
        rows = self._cur.fetchall()
        if not rows:
            return []
        if isinstance(rows[0], dict):
            return [_CompatRow(r, self._col_order) for r in rows]
        return rows

    @property
    def rowcount(self):
        return self._cur.rowcount


class _ConnectionAdapter:
    """Makes psycopg2 connection behave like sqlite3 for existing code."""

    def __init__(self, conn):
        self._conn = conn
        self._last_cursor = None

    def execute(self, sql: str, params=None):
        sql = _param_style(sql)
        cur = self._conn.cursor(cursor_factory=RealDictCursor)
        self._last_cursor = _CursorAdapter(cur)
        if params:
            cur.execute(sql, params)
        else:
            cur.execute(sql)
        self._last_cursor._col_order = [d[0] for d in (cur.description or [])]
        if sql.strip().upper().startswith("INSERT") and "RETURNING" not in sql.upper():
            try:
                cur.execute("SELECT lastval()")
                self._last_cursor.lastrowid = cur.fetchone()["lastval"]
            except Exception:
                self._last_cursor.lastrowid = None
        return self._last_cursor

    def cursor(self):
        cur = self._conn.cursor(cursor_factory=RealDictCursor)
        return _CursorAdapter(cur)

    def commit(self):
        self._conn.commit()

    def close(self):
        self._conn.close()


def _get_raw_conn():
    return psycopg2.connect(os.environ["DATABASE_URL"])


def _get_conn():
    return psycopg2.connect(
        os.environ["DATABASE_URL"],
        cursor_factory=RealDictCursor,
    )


def _init_tables(conn):
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS searches (
                id SERIAL PRIMARY KEY,
                query TEXT NOT NULL,
                num_results INTEGER DEFAULT 0,
                num_leads INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS leads (
                id SERIAL PRIMARY KEY,
                search_id INTEGER REFERENCES searches(id),
                business_name TEXT DEFAULT '',
                contact_name TEXT DEFAULT '',
                email TEXT DEFAULT '',
                phone TEXT DEFAULT '',
                website TEXT DEFAULT '',
                source_url TEXT DEFAULT '',
                snippet TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_leads_search_id ON leads(search_id);
            CREATE INDEX IF NOT EXISTS idx_leads_email ON leads(email);
            CREATE TABLE IF NOT EXISTS mailboxes (
                id SERIAL PRIMARY KEY,
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
                is_active BOOLEAN DEFAULT TRUE,
                last_used TIMESTAMP,
                last_error TEXT,
                error_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS email_campaigns (
                id SERIAL PRIMARY KEY,
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
                id SERIAL PRIMARY KEY,
                campaign_id INTEGER REFERENCES email_campaigns(id),
                mailbox_id INTEGER REFERENCES mailboxes(id),
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
                sent_at TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_mailboxes_active ON mailboxes(is_active, sent_today);
            CREATE INDEX IF NOT EXISTS idx_queue_status ON email_queue(status, priority DESC, scheduled_at);
            CREATE INDEX IF NOT EXISTS idx_queue_mailbox ON email_queue(mailbox_id, status);
            CREATE INDEX IF NOT EXISTS idx_queue_campaign ON email_queue(campaign_id, status);
            CREATE TABLE IF NOT EXISTS app_license (
                id SERIAL PRIMARY KEY,
                license_key TEXT UNIQUE,
                machine_id TEXT,
                activated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE
            );
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                email TEXT,
                license_key TEXT,
                machine_id TEXT,
                plan TEXT DEFAULT 'free',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE
            );
            CREATE TABLE IF NOT EXISTS user_sessions (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                session_token TEXT UNIQUE,
                machine_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP
            );
        """)
        # Add user_id to searches/leads if missing (idempotent)
        for tbl, col in [("searches", "user_id"), ("leads", "user_id")]:
            try:
                cur.execute(f"ALTER TABLE {tbl} ADD COLUMN IF NOT EXISTS {col} INTEGER")
            except psycopg2.ProgrammingError:
                pass  # Column exists
    conn.commit()


def get_connection():
    """Get connection - returns adapter for SQLite-compatible API."""
    conn = _get_raw_conn()
    _init_tables(conn)
    return _ConnectionAdapter(conn)


def save_search(query: str, num_results: int = 0) -> int:
    conn = _get_conn()
    _init_tables(conn)
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO searches (query, num_results) VALUES (%s, %s) RETURNING id",
            (query, num_results),
        )
        search_id = cur.fetchone()["id"]
    conn.commit()
    conn.close()
    return search_id


def save_leads(search_id: int, leads: list[dict], replace: bool = False) -> int:
    if not leads:
        return 0
    conn = _get_conn()
    with conn.cursor() as cur:
        if replace:
            cur.execute("DELETE FROM leads WHERE search_id = %s", (search_id,))
        count = 0
        for lead in leads:
            cur.execute(
                """INSERT INTO leads 
                   (search_id, business_name, contact_name, email, phone, website, source_url, snippet)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
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
        cur.execute("UPDATE searches SET num_leads = %s WHERE id = %s", (count, search_id))
    conn.commit()
    conn.close()
    return count


def get_recent_searches(limit: int = 20) -> list[dict]:
    conn = _get_conn()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM searches ORDER BY created_at DESC LIMIT %s", (limit,))
        rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_leads_by_search(search_id: int) -> list[dict]:
    conn = _get_conn()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM leads WHERE search_id = %s ORDER BY id", (search_id,))
        rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_all_leads(limit: int = 1000) -> list[dict]:
    conn = _get_conn()
    with conn.cursor() as cur:
        cur.execute(
            """SELECT l.*, s.query as search_query 
               FROM leads l 
               LEFT JOIN searches s ON l.search_id = s.id 
               ORDER BY l.created_at DESC 
               LIMIT %s""",
            (limit,),
        )
        rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def delete_search(search_id: int) -> None:
    conn = _get_conn()
    with conn.cursor() as cur:
        cur.execute("DELETE FROM leads WHERE search_id = %s", (search_id,))
        cur.execute("DELETE FROM searches WHERE id = %s", (search_id,))
    conn.commit()
    conn.close()


def get_lead_stats() -> dict:
    conn = _get_conn()
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) as c FROM searches")
        total_searches = cur.fetchone()["c"]
        cur.execute("SELECT COUNT(*) as c FROM leads")
        total_leads = cur.fetchone()["c"]
        cur.execute("SELECT COUNT(DISTINCT email) as c FROM leads WHERE email != ''")
        unique_emails = cur.fetchone()["c"]
        cur.execute("SELECT COUNT(DISTINCT website) as c FROM leads WHERE website != ''")
        unique_domains = cur.fetchone()["c"]
    conn.close()
    return {
        "total_searches": total_searches,
        "total_leads": total_leads,
        "unique_emails": unique_emails,
        "unique_domains": unique_domains,
    }
