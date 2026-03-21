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
from app.email.mailbox_validation import validate_aws_ses_mailbox, validate_smtp_mailbox
from app.email.smtp_tls import human_label_for_mode, normalize_encryption_mode, resolve_connection_mode


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
        daily_limit: int = 500,
        smtp_encryption: str = "auto",
    ) -> int:
        """Add a new mailbox to the pool"""
        prov = (provider or "").strip().lower()
        if prov == "aws_ses":
            if not api_key or not str(api_key).strip():
                raise ValueError("AWS SES requires Access Key, Secret Key, and Region.")
            parts = str(api_key).strip().split(":", 2)
            if len(parts) < 3:
                raise ValueError(
                    "AWS credential format is invalid (expected access_key:secret_key:region)."
                )
            ak, sk, reg = parts[0].strip(), parts[1].strip(), parts[2].strip()
            ok, errs, norm = validate_aws_ses_mailbox(
                name=name,
                email=email,
                aws_access_key=ak,
                aws_secret_key=sk,
                aws_region=reg,
                daily_limit=daily_limit,
            )
            if not ok:
                raise ValueError("; ".join(errs))
            name = norm["name"]
            email = norm["email"]
            daily_limit = norm["daily_limit"]
            api_key = f"{norm['aws_access_key']}:{norm['aws_secret_key']}:{norm['aws_region']}"
            smtp_host = ""
            smtp_port = 0
            smtp_username = ""
            smtp_password = ""
            smtp_encryption_val = "auto"
        else:
            ok, errs, norm = validate_smtp_mailbox(
                name=name,
                email=email,
                smtp_host=smtp_host,
                smtp_port=smtp_port,
                smtp_username=smtp_username,
                smtp_password=smtp_password,
                daily_limit=daily_limit,
                provider=prov,
                smtp_encryption=smtp_encryption,
            )
            if not ok:
                raise ValueError("; ".join(errs))
            name = norm["name"]
            email = norm["email"]
            smtp_host = norm["smtp_host"]
            smtp_port = norm["smtp_port"]
            smtp_username = norm["smtp_username"]
            smtp_password = norm["smtp_password"]
            daily_limit = norm["daily_limit"]
            provider = norm["provider"]
            smtp_encryption_val = norm["smtp_encryption"]

        conn = get_connection()

        # Encrypt password
        password_encrypted = self.credential_manager.encrypt(smtp_password)
        api_key_encrypted = None
        if api_key:
            api_key_encrypted = self.credential_manager.encrypt(api_key)
        
        cursor = conn.execute(
            """INSERT INTO mailboxes 
               (name, email, provider, smtp_host, smtp_port, smtp_username, 
                smtp_password_encrypted, api_key_encrypted, daily_limit, smtp_encryption)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                name, email, provider, smtp_host, smtp_port, smtp_username,
                password_encrypted, api_key_encrypted, daily_limit, smtp_encryption_val
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
            """SELECT id, name, email, provider, smtp_host, smtp_port, smtp_encryption,
                      daily_limit, sent_today, sent_total, is_active, last_used, error_count
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
        import ssl

        host = (mailbox.get("smtp_host") or "").strip()
        port = int(mailbox.get("smtp_port") or 587)
        username = (mailbox.get("smtp_username") or "").strip()
        password = (mailbox.get("smtp_password") or "").strip()
        enc_setting = normalize_encryption_mode(mailbox.get("smtp_encryption"))

        if not host or not username or not password:
            return False, "Missing SMTP host, username, or password"

        ctx = ssl.create_default_context()
        error_messages: list[str] = []

        # (label for user, mode, hostname, port)
        attempts: list[tuple[str, str, str, int]] = []
        host_l = host.lower()
        is_gmail = "gmail.com" in host_l

        if is_gmail:
            # Gmail: try both common ports/modes so users see TLS is fine when auth is wrong
            attempts.extend(
                [
                    ("STARTTLS (recommended)", "starttls", host, 587),
                    ("SSL / implicit TLS", "ssl", host, 465),
                ]
            )
        elif enc_setting == "starttls":
            attempts.append(
                (f"STARTTLS — {human_label_for_mode('starttls')}", "starttls", host, port)
            )
        elif enc_setting == "ssl":
            attempts.append(
                (f"SSL — {human_label_for_mode('ssl')}", "ssl", host, port)
            )
        else:
            # auto: one primary attempt from port + setting, optional fallbacks for odd ports
            mode = resolve_connection_mode("auto", port)
            if mode == "ssl":
                attempts.append(
                    (f"Auto → SSL (port {port})", "ssl", host, port)
                )
            else:
                attempts.append(
                    (f"Auto → STARTTLS (port {port})", "starttls", host, port)
                )
                if port not in (587, 465):
                    attempts.append(("Fallback STARTTLS port 587", "starttls", host, 587))
                    attempts.append(("Fallback SSL port 465", "ssl", host, 465))

        seen: set[tuple[str, str, int]] = set()
        ordered: list[tuple[str, str, str, int]] = []
        for label, mode, h, p in attempts:
            key = (mode, h.lower(), p)
            if key in seen:
                continue
            seen.add(key)
            ordered.append((label, mode, h, p))

        header = (
            f"**Configured:** host `{host}`, port **{port}**, encryption **{enc_setting}** "
            f"(effective: {resolve_connection_mode(enc_setting, port)}).\n\n"
        )

        for label, mode, attempt_host, attempt_port in ordered:
            smtp = None
            try:
                if mode == "ssl":
                    smtp = smtplib.SMTP_SSL(attempt_host, attempt_port, timeout=25, context=ctx)
                else:
                    smtp = smtplib.SMTP(attempt_host, attempt_port, timeout=25)
                    smtp.ehlo()
                    smtp.starttls(context=ctx)
                    smtp.ehlo()
                smtp.login(username, password)
                smtp.quit()
                return True, header + f"✅ **OK** — {label} on `{attempt_host}:{attempt_port}`"
            except Exception as e:
                error_messages.append(f"- **{label}** `{attempt_host}:{attempt_port}` → `{e}`")
                try:
                    if smtp:
                        smtp.close()
                except Exception:
                    pass

        summary = header + "**Attempts:**\n" + "\n".join(error_messages)
        low = summary.lower()
        if "535" in summary or "not accepted" in low or "badcredentials" in low or "username and password" in low:
            summary += (
                "\n\n---\n"
                "**What this usually means:** The server accepted the TCP/TLS connection; **535** is an "
                "**authentication** error (wrong password, need **App Password**, or username must be the "
                "full email). It is **not** “wrong encryption” if you see TLS/SSL in the log above.\n\n"
                "**Gmail / Google Workspace:** use a 16-character **App Password** (Account → Security → "
                "2-Step Verification → App passwords), and **full Gmail address** as SMTP username.\n"
            )
        return False, summary
    
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

