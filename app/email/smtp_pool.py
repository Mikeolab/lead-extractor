"""
SMTP Connection Pool
Manages reusable SMTP connections for efficient bulk sending
"""
from __future__ import annotations
import smtplib
import ssl
import threading
import time
from typing import Dict, Optional, List
# Use importlib to force stdlib email (avoids collision with app.email in PyInstaller bundle)
import importlib
_mime_text = importlib.import_module('email.mime.text')
_mime_multipart = importlib.import_module('email.mime.multipart')
MIMEText = _mime_text.MIMEText
MIMEMultipart = _mime_multipart.MIMEMultipart
from collections import defaultdict

from app.email.smtp_tls import resolve_connection_mode


class SMTPConnectionPool:
    """Manages pool of SMTP connections per mailbox"""
    
    def __init__(self, max_connections_per_mailbox: int = 5):
        self.max_connections = max_connections_per_mailbox
        self.pools: Dict[int, List[smtplib.SMTP]] = defaultdict(list)
        self.locks: Dict[int, threading.Lock] = defaultdict(threading.Lock)
        self.connection_times: Dict[int, float] = defaultdict(float)
        self.connection_timeout = 300  # 5 minutes - close idle connections
    
    def get_connection(self, mailbox_config: Dict) -> Optional[smtplib.SMTP]:
        """Get or create SMTP connection for mailbox"""
        mailbox_id = mailbox_config['id']
        pool = self.pools[mailbox_id]
        lock = self.locks[mailbox_id]
        
        with lock:
            # Try to reuse existing connection
            while pool:
                conn = pool.pop()
                try:
                    # Test if connection is still alive
                    conn.noop()
                    # Check if connection is too old
                    if time.time() - self.connection_times.get(id(conn), 0) < self.connection_timeout:
                        return conn
                    else:
                        # Connection too old, close it
                        try:
                            conn.quit()
                        except:
                            pass
                except Exception:
                    # Connection dead, try next one
                    try:
                        conn.quit()
                    except:
                        pass
                    continue
            
            # Create new connection if under limit
            if len(self.pools[mailbox_id]) < self.max_connections:
                try:
                    host = (mailbox_config.get("smtp_host") or "").strip()
                    port = int(mailbox_config.get("smtp_port") or 587)
                    user = (mailbox_config.get("smtp_username") or "").strip()
                    pwd = (mailbox_config.get("smtp_password") or "").strip()
                    ctx = ssl.create_default_context()
                    mode = resolve_connection_mode(
                        mailbox_config.get("smtp_encryption"), port
                    )
                    # ssl = SMTP_SSL (implicit TLS). starttls = plain socket then STARTTLS.
                    if mode == "ssl":
                        conn = smtplib.SMTP_SSL(host, port, timeout=30, context=ctx)
                    else:
                        conn = smtplib.SMTP(host, port, timeout=30)
                        conn.ehlo()
                        conn.starttls(context=ctx)
                        conn.ehlo()
                    conn.login(user, pwd)
                    self.connection_times[id(conn)] = time.time()
                    return conn
                except Exception as e:
                    raise ConnectionError(f"Failed to create SMTP connection: {str(e)}")
        
        return None  # Pool exhausted
    
    def return_connection(self, mailbox_id: int, conn: smtplib.SMTP):
        """Return connection to pool"""
        lock = self.locks[mailbox_id]
        with lock:
            try:
                # Test connection before returning
                conn.noop()
                self.pools[mailbox_id].append(conn)
            except Exception:
                # Connection dead, don't return it
                try:
                    conn.quit()
                except:
                    pass
    
    def close_all(self, mailbox_id: int = None):
        """Close all connections for a mailbox or all mailboxes"""
        if mailbox_id:
            lock = self.locks[mailbox_id]
            with lock:
                for conn in self.pools[mailbox_id]:
                    try:
                        conn.quit()
                    except:
                        pass
                self.pools[mailbox_id].clear()
        else:
            for mb_id in list(self.pools.keys()):
                self.close_all(mb_id)
    
    def send_email(
        self,
        conn: smtplib.SMTP,
        from_email: str,
        to_email: str,
        subject: str,
        body: str,
        is_html: bool = True
    ) -> bool:
        """Send email using connection"""
        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = from_email
            msg['To'] = to_email
            msg['Subject'] = subject
            
            if is_html:
                msg.attach(MIMEText(body, 'html'))
            else:
                msg.attach(MIMEText(body, 'plain'))
            
            conn.sendmail(from_email, [to_email], msg.as_string())
            return True
        except Exception as e:
            raise Exception(f"Failed to send email: {str(e)}")

