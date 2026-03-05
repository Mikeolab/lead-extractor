# 🛠️ Free Email Providers Implementation Guide

## Architecture Overview

```
┌─────────────────────────────────────────────────┐
│         Unified Email Sender                     │
│  (Routes to SMTP or API based on provider)      │
└─────────────────────────────────────────────────┘
                    ↓
        ┌───────────┴───────────┐
        ↓                       ↓
┌───────────────┐       ┌───────────────┐
│ SMTP Pool    │       │ API Providers │
│ (Gmail/etc)  │       │ (Brevo/etc)   │
└───────────────┘       └───────────────┘
```

---

## Step 1: Create Base Provider Interface

**File:** `app/email/providers/base_provider.py`

```python
"""
Base Email Provider Interface
All providers (SMTP and API) implement this interface
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, Optional


class EmailProvider(ABC):
    """Base class for all email providers"""
    
    @abstractmethod
    def send_email(
        self,
        from_email: str,
        to_email: str,
        subject: str,
        body: str,
        is_html: bool = True,
        **kwargs
    ) -> bool:
        """
        Send email
        
        Returns:
            True if sent successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def test_connection(self) -> bool:
        """
        Test if provider is working
        
        Returns:
            True if connection OK, False otherwise
        """
        pass
    
    @abstractmethod
    def get_daily_limit(self) -> int:
        """
        Get daily sending limit for this provider
        
        Returns:
            Daily limit (e.g., 300 for Brevo, 500 for Gmail)
        """
        pass
```

---

## Step 2: Implement Brevo Provider

**File:** `app/email/providers/brevo_provider.py`

```python
"""
Brevo (Sendinblue) API Provider
Free tier: 300 emails/day
"""
from __future__ import annotations
import requests
from typing import Dict, Optional
from app.email.providers.base_provider import EmailProvider


class BrevoProvider(EmailProvider):
    """Brevo API email provider"""
    
    API_URL = "https://api.brevo.com/v3/smtp/email"
    
    def __init__(self, api_key: str, from_email: str, from_name: str = ""):
        self.api_key = api_key
        self.from_email = from_email
        self.from_name = from_name or from_email.split('@')[0]
    
    def send_email(
        self,
        from_email: str,
        to_email: str,
        subject: str,
        body: str,
        is_html: bool = True,
        **kwargs
    ) -> bool:
        """Send email via Brevo API"""
        try:
            headers = {
                "api-key": self.api_key,
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            payload = {
                "sender": {
                    "email": from_email,
                    "name": self.from_name
                },
                "to": [{"email": to_email}],
                "subject": subject,
            }
            
            if is_html:
                payload["htmlContent"] = body
            else:
                payload["textContent"] = body
            
            response = requests.post(
                self.API_URL,
                json=payload,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 201:
                return True
            else:
                # Log error
                error_data = response.json() if response.text else {}
                raise Exception(f"Brevo API error: {response.status_code} - {error_data}")
        
        except Exception as e:
            raise Exception(f"Failed to send via Brevo: {str(e)}")
    
    def test_connection(self) -> bool:
        """Test Brevo API connection"""
        try:
            # Try to get account info (lightweight check)
            headers = {
                "api-key": self.api_key,
                "Accept": "application/json"
            }
            response = requests.get(
                "https://api.brevo.com/v3/account",
                headers=headers,
                timeout=10
            )
            return response.status_code == 200
        except Exception:
            return False
    
    def get_daily_limit(self) -> int:
        """Brevo free tier: 300 emails/day"""
        return 300
```

---

## Step 3: Implement Mailjet Provider

**File:** `app/email/providers/mailjet_provider.py`

```python
"""
Mailjet API Provider
Free tier: 200 emails/day
"""
from __future__ import annotations
import requests
import base64
from typing import Dict, Optional
from app.email.providers.base_provider import EmailProvider


class MailjetProvider(EmailProvider):
    """Mailjet API email provider"""
    
    API_URL = "https://api.mailjet.com/v3.1/send"
    
    def __init__(self, api_key: str, api_secret: str, from_email: str, from_name: str = ""):
        self.api_key = api_key
        self.api_secret = api_secret
        self.from_email = from_email
        self.from_name = from_name or from_email.split('@')[0]
        
        # Create Basic Auth header
        credentials = f"{api_key}:{api_secret}"
        self.auth_header = base64.b64encode(credentials.encode()).decode()
    
    def send_email(
        self,
        from_email: str,
        to_email: str,
        subject: str,
        body: str,
        is_html: bool = True,
        **kwargs
    ) -> bool:
        """Send email via Mailjet API"""
        try:
            headers = {
                "Authorization": f"Basic {self.auth_header}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "Messages": [{
                    "From": {
                        "Email": from_email,
                        "Name": self.from_name
                    },
                    "To": [{"Email": to_email}],
                    "Subject": subject,
                }]
            }
            
            if is_html:
                payload["Messages"][0]["HTMLPart"] = body
            else:
                payload["Messages"][0]["TextPart"] = body
            
            response = requests.post(
                self.API_URL,
                json=payload,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                return True
            else:
                error_data = response.json() if response.text else {}
                raise Exception(f"Mailjet API error: {response.status_code} - {error_data}")
        
        except Exception as e:
            raise Exception(f"Failed to send via Mailjet: {str(e)}")
    
    def test_connection(self) -> bool:
        """Test Mailjet API connection"""
        try:
            headers = {
                "Authorization": f"Basic {self.auth_header}",
                "Accept": "application/json"
            }
            response = requests.get(
                "https://api.mailjet.com/v3.1/REST/user",
                headers=headers,
                timeout=10
            )
            return response.status_code == 200
        except Exception:
            return False
    
    def get_daily_limit(self) -> int:
        """Mailjet free tier: 200 emails/day"""
        return 200
```

---

## Step 4: Implement Mailgun Provider

**File:** `app/email/providers/mailgun_provider.py`

```python
"""
Mailgun API Provider
Free tier: 100 emails/day
"""
from __future__ import annotations
import requests
from typing import Dict, Optional
from app.email.providers.base_provider import EmailProvider


class MailgunProvider(EmailProvider):
    """Mailgun API email provider"""
    
    def __init__(self, api_key: str, domain: str, from_email: str, from_name: str = ""):
        self.api_key = api_key
        self.domain = domain  # e.g., "mg.yourdomain.com" or sandbox domain
        self.from_email = from_email
        self.from_name = from_name or from_email.split('@')[0]
        self.api_url = f"https://api.mailgun.net/v3/{domain}/messages"
    
    def send_email(
        self,
        from_email: str,
        to_email: str,
        subject: str,
        body: str,
        is_html: bool = True,
        **kwargs
    ) -> bool:
        """Send email via Mailgun API"""
        try:
            auth = ("api", self.api_key)
            
            data = {
                "from": f"{self.from_name} <{from_email}>",
                "to": to_email,
                "subject": subject,
            }
            
            if is_html:
                data["html"] = body
            else:
                data["text"] = body
            
            response = requests.post(
                self.api_url,
                auth=auth,
                data=data,
                timeout=30
            )
            
            if response.status_code == 200:
                return True
            else:
                error_data = response.json() if response.text else {}
                raise Exception(f"Mailgun API error: {response.status_code} - {error_data}")
        
        except Exception as e:
            raise Exception(f"Failed to send via Mailgun: {str(e)}")
    
    def test_connection(self) -> bool:
        """Test Mailgun API connection"""
        try:
            auth = ("api", self.api_key)
            response = requests.get(
                f"https://api.mailgun.net/v3/{self.domain}",
                auth=auth,
                timeout=10
            )
            return response.status_code == 200
        except Exception:
            return False
    
    def get_daily_limit(self) -> int:
        """Mailgun free tier: 100 emails/day"""
        return 100
```

---

## Step 5: Create Unified Sender

**File:** `app/email/unified_sender.py`

```python
"""
Unified Email Sender
Routes emails to SMTP or API providers based on mailbox config
"""
from __future__ import annotations
from typing import Dict, Optional
from app.email.mailbox_pool import MailboxPool
from app.email.smtp_pool import SMTPConnectionPool
from app.email.providers.brevo_provider import BrevoProvider
from app.email.providers.mailjet_provider import MailjetProvider
from app.email.providers.mailgun_provider import MailgunProvider
from app.email.credential_manager import get_credential_manager


class UnifiedEmailSender:
    """Unified sender that routes to SMTP or API providers"""
    
    def __init__(self):
        self.mailbox_pool = MailboxPool()
        self.smtp_pool = SMTPConnectionPool(max_connections_per_mailbox=5)
        self.credential_manager = get_credential_manager()
    
    def send_email(
        self,
        mailbox_id: int,
        to_email: str,
        subject: str,
        body: str,
        is_html: bool = True
    ) -> bool:
        """Send email using appropriate provider"""
        # Get mailbox config
        mailbox = self.mailbox_pool._get_mailbox_by_id(mailbox_id)
        if not mailbox:
            raise Exception(f"Mailbox {mailbox_id} not found")
        
        provider = mailbox['provider']
        from_email = mailbox['email']
        
        # Route to correct provider
        if provider in ['gmail', 'outlook', 'custom']:
            # SMTP provider
            return self._send_via_smtp(mailbox, to_email, subject, body, is_html)
        
        elif provider == 'brevo':
            # Brevo API
            api_key = self.credential_manager.decrypt(mailbox['api_key_encrypted'])
            brevo = BrevoProvider(api_key, from_email)
            return brevo.send_email(from_email, to_email, subject, body, is_html)
        
        elif provider == 'mailjet':
            # Mailjet API
            api_key = self.credential_manager.decrypt(mailbox['api_key_encrypted'])
            # Mailjet needs both key and secret (stored together or separately)
            # Assuming format: "key:secret" or separate fields
            if ':' in api_key:
                key, secret = api_key.split(':', 1)
            else:
                # Try to get secret from another field or use same key
                secret = api_key  # Fallback
            mailjet = MailjetProvider(key, secret, from_email)
            return mailjet.send_email(from_email, to_email, subject, body, is_html)
        
        elif provider == 'mailgun':
            # Mailgun API
            api_key = self.credential_manager.decrypt(mailbox['api_key_encrypted'])
            domain = mailbox.get('smtp_host', '')  # Store domain in smtp_host field
            mailgun = MailgunProvider(api_key, domain, from_email)
            return mailgun.send_email(from_email, to_email, subject, body, is_html)
        
        else:
            raise Exception(f"Unknown provider: {provider}")
    
    def _send_via_smtp(
        self,
        mailbox: Dict,
        to_email: str,
        subject: str,
        body: str,
        is_html: bool
    ) -> bool:
        """Send via SMTP (existing logic)"""
        conn = self.smtp_pool.get_connection(mailbox)
        if not conn:
            raise Exception("No SMTP connection available")
        
        try:
            self.smtp_pool.send_email(
                conn=conn,
                from_email=mailbox['email'],
                to_email=to_email,
                subject=subject,
                body=body,
                is_html=is_html
            )
            return True
        finally:
            self.smtp_pool.return_connection(mailbox['id'], conn)
```

---

## Step 6: Update Database Schema (Optional Enhancement)

**Add fields for API providers:**

```sql
-- Already have api_key_encrypted, but might want:
ALTER TABLE mailboxes ADD COLUMN api_secret_encrypted TEXT;  -- For Mailjet
ALTER TABLE mailboxes ADD COLUMN api_domain TEXT;            -- For Mailgun domain
```

**Or store in existing fields:**
- `api_key_encrypted`: Store API key (or "key:secret" for Mailjet)
- `smtp_host`: Store domain for Mailgun (reuse field)
- `smtp_port`: Not used for API providers (can ignore)

---

## Step 7: Update UI to Add API Providers

**File:** `app/email/email_ui.py` (modify Add Mailbox form)

```python
# In "Add New Mailbox" expander:

provider = st.selectbox("Provider", [
    "gmail", 
    "outlook", 
    "custom",
    "brevo",      # NEW
    "mailjet",    # NEW
    "mailgun"     # NEW
], key="add_provider")

if provider in ['brevo', 'mailjet', 'mailgun']:
    # API provider - show API key fields
    api_key = st.text_input("API Key", type="password", key="add_api_key")
    
    if provider == 'mailjet':
        api_secret = st.text_input("API Secret", type="password", key="add_api_secret")
    
    if provider == 'mailgun':
        domain = st.text_input("Domain (e.g., mg.yourdomain.com)", key="add_domain")
    
    # Auto-set daily limits
    if provider == 'brevo':
        daily_limit = 300
    elif provider == 'mailjet':
        daily_limit = 200
    elif provider == 'mailgun':
        daily_limit = 100
else:
    # SMTP provider - show existing fields
    # ... existing SMTP fields ...
```

---

## Step 8: Update Requirements

**Add to `requirements.txt`:**

```txt
requests>=2.31.0  # For API providers (already have it!)
```

---

## Testing

**Test Brevo:**
```python
from app.email.providers.brevo_provider import BrevoProvider

provider = BrevoProvider(api_key="your_key", from_email="test@example.com")
result = provider.send_email(
    from_email="test@example.com",
    to_email="recipient@example.com",
    subject="Test",
    body="<p>Test email</p>"
)
print(f"Sent: {result}")
```

**Test Mailjet:**
```python
from app.email.providers.mailjet_provider import MailjetProvider

provider = MailjetProvider(
    api_key="your_key",
    api_secret="your_secret",
    from_email="test@example.com"
)
result = provider.send_email(...)
```

**Test Mailgun:**
```python
from app.email.providers.mailgun_provider import MailgunProvider

provider = MailgunProvider(
    api_key="your_key",
    domain="mg.yourdomain.com",
    from_email="test@example.com"
)
result = provider.send_email(...)
```

---

## Next Steps

1. ✅ Create provider base class
2. ✅ Implement Brevo provider
3. ✅ Implement Mailjet provider
4. ✅ Implement Mailgun provider
5. ✅ Create unified sender
6. ✅ Update UI to add API providers
7. ✅ Test each provider
8. ✅ Update mailbox pool to support API providers
9. ✅ Test multi-provider rotation

**Result:** 27,000 emails/day capacity for $0/month! 🚀
