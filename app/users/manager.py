"""
User Management System
Handles user creation, authentication, and data isolation
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from pathlib import Path

from app.database.db import get_connection, using_postgres
from app.license.validator import validate_license, LicenseInfo
from app.license.machine_id import get_machine_id
from app.config import LICENSE_SECRET


class UserManager:
    """Manages users and their data"""
    
    def __init__(self):
        self._ensure_tables()
    
    def _ensure_tables(self):
        """Ensure user tables exist (SQLite or PostgreSQL compatible)."""
        conn = get_connection()
        if using_postgres():
            # Tables already created by db_postgres._init_tables(); only add columns if missing
            try:
                conn.execute("ALTER TABLE searches ADD COLUMN IF NOT EXISTS user_id INTEGER")
            except Exception:
                pass
            try:
                conn.execute("ALTER TABLE leads ADD COLUMN IF NOT EXISTS user_id INTEGER")
            except Exception:
                pass
        else:
            # SQLite
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT,
                    license_key TEXT,
                    machine_id TEXT,
                    plan TEXT DEFAULT 'free',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    session_token TEXT UNIQUE,
                    machine_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            try:
                conn.execute("ALTER TABLE searches ADD COLUMN user_id INTEGER")
            except Exception:
                pass
            try:
                conn.execute("ALTER TABLE leads ADD COLUMN user_id INTEGER")
            except Exception:
                pass
        conn.commit()
        conn.close()
    
    def create_user_from_license(self, license_key: str, username: Optional[str] = None) -> Optional[Dict]:
        """
        Create or get user from license key.
        
        Args:
            license_key: License key string
            username: Optional username (if not provided, uses licensee from license)
        
        Returns:
            User dict or None if license invalid
        """
        # Validate license
        license_info = validate_license(license_key, LICENSE_SECRET)
        if not license_info.valid:
            return None
        
        # Check machine ID
        current_machine_id = get_machine_id()
        # Note: Machine ID check will be added to license payload in next phase
        
        # Get or create user
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check if user exists with this license
        cursor.execute(
            "SELECT * FROM users WHERE license_key = ?",
            (license_key,)
        )
        existing = cursor.fetchone()
        
        if existing:
            # Update last login
            cursor.execute(
                "UPDATE users SET last_login = ? WHERE id = ?",
                (datetime.utcnow().isoformat(), existing[0])
            )
            conn.commit()
            conn.close()
            
            return {
                "id": existing[0],
                "username": existing[1],
                "email": existing[2],
                "license_key": existing[3],
                "machine_id": existing[4],
                "plan": existing[5],
            }
        
        # Create new user
        username = username or license_info.licensee or f"user_{secrets.token_hex(4)}"
        cursor.execute(
            """INSERT INTO users (username, license_key, machine_id, plan, last_login)
               VALUES (?, ?, ?, ?, ?)""",
            (
                username,
                license_key,
                current_machine_id,
                license_info.plan,
                datetime.utcnow().isoformat(),
            )
        )
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return {
            "id": user_id,
            "username": username,
            "license_key": license_key,
            "machine_id": current_machine_id,
            "plan": license_info.plan,
        }
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        """Get user by ID"""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return {
            "id": row[0],
            "username": row[1],
            "email": row[2],
            "license_key": row[3],
            "machine_id": row[4],
            "plan": row[5],
            "created_at": row[6],
            "last_login": row[7],
            "is_active": row[8],
        }
    
    def get_user_by_license(self, license_key: str) -> Optional[Dict]:
        """Get user by license key"""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE license_key = ?", (license_key,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return {
            "id": row[0],
            "username": row[1],
            "email": row[2],
            "license_key": row[3],
            "machine_id": row[4],
            "plan": row[5],
        }
    
    def create_session(self, user_id: int) -> str:
        """Create session token for user"""
        session_token = secrets.token_urlsafe(32)
        expires_at = (datetime.utcnow() + timedelta(days=30)).isoformat()
        machine_id = get_machine_id()
        
        conn = get_connection()
        conn.execute(
            """INSERT INTO user_sessions (user_id, session_token, machine_id, expires_at)
               VALUES (?, ?, ?, ?)""",
            (user_id, session_token, machine_id, expires_at)
        )
        conn.commit()
        conn.close()
        
        return session_token
    
    def validate_session(self, session_token: str) -> Optional[Dict]:
        """Validate session token and return user"""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """SELECT u.* FROM users u
               JOIN user_sessions s ON u.id = s.user_id
               WHERE s.session_token = ? AND s.expires_at > ? AND u.is_active = 1""",
            (session_token, datetime.utcnow().isoformat())
        )
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return {
            "id": row[0],
            "username": row[1],
            "email": row[2],
            "license_key": row[3],
            "machine_id": row[4],
            "plan": row[5],
        }
    
    def get_user_searches(self, user_id: int, limit: int = 50) -> List[Dict]:
        """Get searches for specific user"""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """SELECT * FROM searches 
               WHERE user_id = ? 
               ORDER BY created_at DESC 
               LIMIT ?""",
            (user_id, limit)
        )
        rows = cursor.fetchall()
        conn.close()
        
        searches = []
        for row in rows:
            searches.append({
                "id": row[0],
                "query": row[1],
                "num_results": row[2],
                "num_leads": row[3],
                "created_at": row[4],
                "user_id": row[5] if len(row) > 5 else None,
            })
        
        return searches
    
    def get_user_leads(self, user_id: int, search_id: Optional[int] = None) -> List[Dict]:
        """Get leads for specific user"""
        conn = get_connection()
        cursor = conn.cursor()
        
        if search_id:
            cursor.execute(
                """SELECT * FROM leads 
                   WHERE search_id = ? AND user_id = ?""",
                (search_id, user_id)
            )
        else:
            cursor.execute(
                """SELECT * FROM leads 
                   WHERE user_id = ? 
                   ORDER BY created_at DESC""",
                (user_id,)
            )
        
        rows = cursor.fetchall()
        conn.close()
        
        leads = []
        for row in rows:
            leads.append({
                "id": row[0],
                "search_id": row[1],
                "email": row[2],
                "phone": row[3],
                "contact_name": row[4],
                "business_name": row[5],
                "website": row[6],
                "source_url": row[7],
                "snippet": row[8],
                "created_at": row[9],
                "user_id": row[10] if len(row) > 10 else None,
            })
        
        return leads


# Global instance
user_manager = UserManager()

