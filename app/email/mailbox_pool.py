"""
Mailbox Pool Manager
Manages multiple mailboxes with rotation and health monitoring
"""
from __future__ import annotations
import sqlite3
from datetime import datetime, date
from typing import Optional, Dict, List
from app.database.db import get_connection
from app.email.credential_manager import get_credential_manager


class MailboxPool:
    """Manages pool of mailboxes with rotation and limits"""
    
    def __init__(self):
        self.credential_manager = get_credential_manager()
        self._reset_daily_counts_if_needed()
    
    def _reset_daily_counts_if_needed(self):
        """Reset sent_today counters if it's a new day"""
        conn = get_connection()
        today = date.today()
        
        # Get mailboxes that need reset
        rows = conn.execute(
            "SELECT id, last_used FROM mailboxes WHERE sent_today > 0"
        ).fetchall()
        
        for row in rows:
            mailbox_id = row['id']
            last_used_str = row['last_used']
            
            if last_used_str:
                try:
                    last_used = datetime.fromisoformat(last_used_str).date()
                    if last_used < today:
                        # Reset counter for new day
                        conn.execute(
                            "UPDATE mailboxes SET sent_today = 0 WHERE id = ?",
                            (mailbox_id,)
                        )
                except Exception:
                    pass
        
        conn.commit()
        conn.close()
    
    def add_mailbox(
        self,
        name: str,
        email: str,
        provider: str,
        smtp_host: str,
        smtp_port: int,
        smtp_username: str,
        smtp_password: str,
        api_key: str = None,
        daily_limit: int = 500
    ) -> int:
        """Add a new mailbox to the pool"""
        conn = get_connection()
        
        # Encrypt password
        password_encrypted = self.credential_manager.encrypt(smtp_password)
        api_key_encrypted = None
        if api_key:
            api_key_encrypted = self.credential_manager.encrypt(api_key)
        
        cursor = conn.execute(
            """INSERT INTO mailboxes 
               (name, email, provider, smtp_host, smtp_port, smtp_username, 
                smtp_password_encrypted, api_key_encrypted, daily_limit)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                name, email, provider, smtp_host, smtp_port, smtp_username,
                password_encrypted, api_key_encrypted, daily_limit
            )
        )
        mailbox_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return mailbox_id
    
    def get_available_mailbox(self) -> Optional[Dict]:
        """Get next available mailbox (round-robin)"""
        conn = get_connection()
        today = date.today()
        
        # Reset daily counts if needed
        self._reset_daily_counts_if_needed()
        
        # Get active mailbox with capacity remaining
        row = conn.execute(
            """SELECT * FROM mailboxes 
               WHERE is_active = 1 
               AND sent_today < daily_limit
               ORDER BY last_used ASC, sent_today ASC
               LIMIT 1"""
        ).fetchone()
        
        if not row:
            conn.close()
            return None
        
        mailbox = dict(row)
        
        # Decrypt password
        mailbox['smtp_password'] = self.credential_manager.decrypt(
            mailbox['smtp_password_encrypted']
        )
        
        if mailbox.get('api_key_encrypted'):
            mailbox['api_key'] = self.credential_manager.decrypt(
                mailbox['api_key_encrypted']
            )
        
        conn.close()
        return mailbox
    
    def mark_sent(self, mailbox_id: int, conn=None):
        """Mark that an email was sent from this mailbox"""
        own_conn = False
        if conn is None:
            conn = get_connection()
            own_conn = True

        now = datetime.now().isoformat()
        conn.execute(
            """UPDATE mailboxes 
               SET sent_today = sent_today + 1,
                   sent_total = sent_total + 1,
                   last_used = ?
               WHERE id = ?""",
            (now, mailbox_id)
        )

        if own_conn:
            conn.commit()
            conn.close()

    def mark_error(self, mailbox_id: int, error_message: str, conn=None):
        """Record an error for this mailbox"""
        own_conn = False
        if conn is None:
            conn = get_connection()
            own_conn = True

        conn.execute(
            """UPDATE mailboxes 
               SET error_count = error_count + 1,
                   last_error = ?
               WHERE id = ?""",
            (error_message[:500], mailbox_id)  # Limit error message length
        )

        if own_conn:
            conn.commit()
            conn.close()
    
    def deactivate_mailbox(self, mailbox_id: int):
        """Deactivate a mailbox (e.g., if blocked)"""
        conn = get_connection()
        conn.execute(
            "UPDATE mailboxes SET is_active = 0 WHERE id = ?",
            (mailbox_id,)
        )
        conn.commit()
        conn.close()
    
    def get_all_mailboxes(self) -> List[Dict]:
        """Get all mailboxes with stats"""
        conn = get_connection()
        rows = conn.execute(
            """SELECT id, name, email, provider, daily_limit, sent_today, 
                      sent_total, is_active, last_used, error_count
               FROM mailboxes
               ORDER BY created_at DESC"""
        ).fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def test_connection(self, mailbox_id: int) -> tuple[bool, str]:
        """Test SMTP connection for a mailbox"""
        mailbox = self._get_mailbox_by_id(mailbox_id)
        if not mailbox:
            return False, "Mailbox not found"

        import smtplib

        provider = str(mailbox.get('provider', '')).lower()
        host = mailbox.get('smtp_host')
        port = mailbox.get('smtp_port') or 587
        username = mailbox.get('smtp_username')
        password = mailbox.get('smtp_password')

        if not host or not username or not password:
            return False, "Missing SMTP host/username/password"

        error_messages = []

        # Bounce through common SMTP connection options
        attempts = []

        # Try SMTPS on SSL port (465) if applicable
        attempts.append(('ssl', host, 465))
        # Try starttls on provided port first (587 default)
        attempts.append(('starttls', host, port))

        # as fallback try 587 starttls and 465 ssl in case custom port was wrong
        if port != 587:
            attempts.append(('starttls', host, 587))
        if port != 465:
            attempts.append(('ssl', host, 465))

        for mode, attempt_host, attempt_port in attempts:
            try:
                if mode == 'ssl':
                    smtp = smtplib.SMTP_SSL(attempt_host, attempt_port, timeout=20)
                else:
                    smtp = smtplib.SMTP(attempt_host, attempt_port, timeout=20)
                    smtp.ehlo()
                    smtp.starttls()

                smtp.login(username, password)
                smtp.quit()
                return True, f"Connection successful via {mode.upper()}:{attempt_host}:{attempt_port}"
            except Exception as e:
                error_messages.append(f"{mode.upper()} {attempt_host}:{attempt_port} -> {e}")
                continue

        return False, "; ".join(error_messages)
    
    def _get_mailbox_by_id(self, mailbox_id: int) -> Optional[Dict]:
        """Get mailbox by ID with decrypted password"""
        conn = get_connection()
        row = conn.execute(
            "SELECT * FROM mailboxes WHERE id = ?",
            (mailbox_id,)
        ).fetchone()
        
        if not row:
            conn.close()
            return None
        
        mailbox = dict(row)
        mailbox['smtp_password'] = self.credential_manager.decrypt(
            mailbox['smtp_password_encrypted']
        )
        
        if mailbox.get('api_key_encrypted'):
            mailbox['api_key'] = self.credential_manager.decrypt(
                mailbox['api_key_encrypted']
            )
        
        conn.close()
        return mailbox

