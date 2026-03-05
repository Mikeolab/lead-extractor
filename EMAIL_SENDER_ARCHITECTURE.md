# Email Sender Architecture & Research

## Executive Summary

This document outlines the architecture for integrating a bulk email sending system into Lead Extractor Pro. The system will support multiple mailboxes, rate limiting, deliverability optimization, and seamless integration with the existing lead extraction workflow.

---

## 1. Email Sending Methods Comparison

### 1.1 SMTP (Simple Mail Transfer Protocol)
**Pros:**
- Direct control over sending
- No per-email costs (uses your own mailboxes)
- Works with Gmail, Outlook, custom SMTP servers
- Full control over email content and headers

**Cons:**
- Rate limits are strict (Gmail: 500/day, Outlook: 300/day)
- Requires mailbox credentials
- Higher risk of being flagged as spam
- Need to manage multiple mailboxes for scale
- Requires proper SPF/DKIM/DMARC setup

**Best For:** Small to medium volumes (< 10,000 emails/day), cost-sensitive operations

### 1.2 Email Service APIs (SendGrid, Mailgun, AWS SES, etc.)
**Pros:**
- Higher sending limits (SendGrid: 100/day free, then pay-per-email)
- Better deliverability (managed infrastructure)
- Built-in analytics and bounce handling
- No mailbox management needed
- Professional reputation management

**Cons:**
- Per-email costs (typically $0.001-$0.01 per email)
- Less control over sending infrastructure
- API rate limits still apply
- Monthly subscription fees for higher tiers

**Best For:** Large volumes, professional campaigns, when deliverability is critical

### 1.3 Hybrid Approach (Recommended)
**Best of Both Worlds:**
- Use SMTP for smaller volumes (cost-effective)
- Use API services for larger campaigns (better deliverability)
- Automatically switch based on volume and mailbox availability
- Distribute load across multiple methods

---

## 2. Architecture Options

### Option A: Integrated Module (Recommended)
**Structure:**
```
lead-extractor/
├── app/
│   ├── email/
│   │   ├── __init__.py
│   │   ├── sender.py          # Main email sending logic
│   │   ├── mailbox_manager.py  # Manage multiple mailboxes
│   │   ├── rate_limiter.py     # Rate limiting per mailbox
│   │   ├── templates.py        # Email templates
│   │   ├── providers/
│   │   │   ├── __init__.py
│   │   │   ├── smtp_provider.py    # SMTP implementation
│   │   │   ├── sendgrid_provider.py # SendGrid API
│   │   │   ├── mailgun_provider.py  # Mailgun API
│   │   │   └── ses_provider.py      # AWS SES API
│   │   └── models.py          # Database models for email tracking
│   ├── database/
│   │   └── db.py              # Add email tables
│   └── main.py                # Add email UI section
```

**Pros:**
- Single codebase, easier maintenance
- Shared database and UI
- Users can send emails directly from extracted leads
- Unified license management
- Easier to deploy as one app

**Cons:**
- Larger application size
- All features bundled together

### Option B: Separate Service
**Structure:**
```
lead-extractor/          # Existing app
email-sender-service/    # Separate FastAPI service
├── app/
│   ├── sender.py
│   ├── mailbox_manager.py
│   └── api.py           # REST API for integration
```

**Pros:**
- Modular architecture
- Can be used by other applications
- Independent scaling
- Separate deployment

**Cons:**
- More complex deployment
- Need API communication between services
- Two separate applications to maintain
- Additional infrastructure costs

**Recommendation: Option A (Integrated)** - Better user experience, simpler deployment, unified license management.

---

## 3. Recommended Architecture: Integrated Module

### 3.1 Core Components

#### 3.1.1 Mailbox Manager (`mailbox_manager.py`)
**Responsibilities:**
- Store mailbox credentials securely (encrypted)
- Rotate between multiple mailboxes
- Track usage per mailbox (daily limits)
- Health monitoring (test connectivity)
- Automatic failover if mailbox is blocked

**Database Schema:**
```sql
CREATE TABLE mailboxes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,                    -- User-friendly name
    email TEXT NOT NULL UNIQUE,            -- Email address
    provider TEXT NOT NULL,                -- 'gmail', 'outlook', 'custom', 'sendgrid', etc.
    smtp_host TEXT,                        -- For SMTP: smtp.gmail.com
    smtp_port INTEGER,                     -- 587, 465, etc.
    smtp_username TEXT,                    -- Usually the email
    smtp_password TEXT,                    -- ENCRYPTED app password
    api_key TEXT,                          -- ENCRYPTED API key (for SendGrid, etc.)
    daily_limit INTEGER DEFAULT 500,       -- Max emails per day
    sent_today INTEGER DEFAULT 0,          -- Counter (reset daily)
    is_active BOOLEAN DEFAULT 1,           -- Enable/disable
    last_used TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE email_campaigns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    subject_template TEXT NOT NULL,
    body_template TEXT NOT NULL,
    status TEXT DEFAULT 'draft',          -- 'draft', 'sending', 'paused', 'completed'
    total_recipients INTEGER DEFAULT 0,
    sent_count INTEGER DEFAULT 0,
    failed_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE TABLE email_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id INTEGER,
    mailbox_id INTEGER,
    recipient_email TEXT NOT NULL,
    recipient_name TEXT,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    status TEXT DEFAULT 'pending',         -- 'pending', 'sending', 'sent', 'failed'
    attempts INTEGER DEFAULT 0,
    error_message TEXT,
    sent_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (campaign_id) REFERENCES email_campaigns(id),
    FOREIGN KEY (mailbox_id) REFERENCES mailboxes(id)
);

CREATE INDEX idx_email_queue_status ON email_queue(status);
CREATE INDEX idx_email_queue_campaign ON email_queue(campaign_id);
```

#### 3.1.2 Rate Limiter (`rate_limiter.py`)
**Responsibilities:**
- Enforce per-mailbox daily limits
- Implement delays between sends (avoid spam detection)
- Track sending velocity (emails per minute/hour)
- Queue management (FIFO)

**Rate Limiting Strategy:**
```python
# Per mailbox limits
GMAIL_LIMIT = 500 emails/day
OUTLOOK_LIMIT = 300 emails/day
CUSTOM_SMTP_LIMIT = 1000 emails/day (configurable)

# Sending velocity (to avoid spam detection)
MIN_DELAY_BETWEEN_EMAILS = 2 seconds  # Minimum delay
MAX_EMAILS_PER_HOUR = 50              # Per mailbox
MAX_EMAILS_PER_MINUTE = 5             # Per mailbox
```

#### 3.1.3 Email Sender (`sender.py`)
**Responsibilities:**
- Abstract interface for different providers
- Handle retries and error recovery
- Log all sending attempts
- Update queue status

**Provider Interface:**
```python
class EmailProvider:
    def send_email(self, to: str, subject: str, body: str, **kwargs) -> bool:
        """Send email, return True if successful"""
        pass
    
    def test_connection(self) -> bool:
        """Test if provider is working"""
        pass
```

#### 3.1.4 Provider Implementations

**SMTP Provider (`smtp_provider.py`):**
- Uses Python's `smtplib`
- Supports TLS/SSL
- Handles authentication (OAuth2 for Gmail, password for others)
- Implements connection pooling

**API Providers:**
- SendGrid: REST API with API keys
- Mailgun: REST API with API keys
- AWS SES: AWS SDK with credentials

---

## 4. Security & Credential Management

### 4.1 Encryption
**Store credentials encrypted:**
- Use `cryptography` library (Fernet symmetric encryption)
- Master key stored in user's OS keychain (macOS Keychain, Windows Credential Manager)
- Never store passwords in plain text

**Implementation:**
```python
from cryptography.fernet import Fernet
import keyring  # For OS keychain access

class CredentialManager:
    def encrypt_password(self, password: str) -> str:
        key = self._get_master_key()
        f = Fernet(key)
        return f.encrypt(password.encode()).decode()
    
    def decrypt_password(self, encrypted: str) -> str:
        key = self._get_master_key()
        f = Fernet(key)
        return f.decrypt(encrypted.encode()).decode()
```

### 4.2 Mailbox Setup Flow
1. User clicks "Add Mailbox"
2. Select provider (Gmail, Outlook, Custom SMTP, SendGrid, etc.)
3. Enter credentials (email, password/API key)
4. System tests connection
5. Credentials encrypted and stored
6. Mailbox appears in list with status (active/inactive)

---

## 5. Email Sending Workflow

### 5.1 Campaign Creation
1. User selects leads from database (or imports CSV)
2. Choose email template (or create new)
3. Select mailbox(es) to use
4. Set sending schedule (immediate or scheduled)
5. Preview emails
6. Start campaign

### 5.2 Sending Process
```
1. Campaign created → Emails added to queue (status: 'pending')
2. Background worker picks up emails
3. For each email:
   a. Select available mailbox (check daily limit, health)
   b. Apply rate limiting (delay if needed)
   c. Send email via provider
   d. Update queue status:
      - Success → status: 'sent', update sent_at
      - Failure → status: 'failed', increment attempts, log error
   e. If attempts < 3 and failed → retry later
4. Update campaign statistics
5. Continue until queue empty or campaign paused
```

### 5.3 Background Worker
- Separate thread/process for sending emails
- Processes queue continuously
- Respects rate limits
- Handles errors gracefully
- Updates UI via WebSocket (real-time progress)

---

## 6. Integration with Lead Extractor

### 6.1 UI Integration
**New Section in Streamlit UI:**
```
📧 Email Campaigns
├── Mailbox Management
│   ├── Add Mailbox (Gmail, Outlook, Custom, SendGrid)
│   ├── List Mailboxes (with status, daily usage)
│   └── Test Mailbox
├── Campaign Management
│   ├── Create Campaign
│   ├── Select Leads (from database)
│   ├── Email Templates
│   ├── Campaign Queue (pending/sent/failed)
│   └── Campaign Statistics
└── Settings
    ├── Rate Limiting
    ├── Default Mailbox
    └── Email Templates
```

### 6.2 Database Integration
- Extend existing `leads` table with email tracking
- Add `email_sent` boolean field
- Add `email_sent_at` timestamp
- Add `email_campaign_id` foreign key

### 6.3 API Integration
- Add FastAPI endpoints for email operations:
  - `POST /api/email/mailboxes` - Add mailbox
  - `GET /api/email/mailboxes` - List mailboxes
  - `POST /api/email/campaigns` - Create campaign
  - `GET /api/email/campaigns/{id}/status` - Get campaign status
  - `POST /api/email/send` - Send single email (for testing)

---

## 7. Deliverability Best Practices

### 7.1 Email Content
- Avoid spam trigger words
- Use proper HTML structure
- Include plain text alternative
- Personalize subject lines and body
- Include unsubscribe link (for compliance)

### 7.2 Sending Behavior
- Start slow (warm up new mailboxes)
- Gradually increase sending volume
- Avoid sending to invalid emails
- Handle bounces gracefully
- Respect unsubscribe requests

### 7.3 Technical Setup
- SPF record: Authorize sending server
- DKIM signature: Verify email authenticity
- DMARC policy: Protect domain reputation
- Reverse DNS: Match sending IP to domain

**Note:** For Gmail/Outlook mailboxes, SPF/DKIM/DMARC are already configured. For custom SMTP, user needs to set these up.

---

## 8. Implementation Phases

### Phase 1: Core Infrastructure (Week 1)
- [ ] Database schema for mailboxes and campaigns
- [ ] Credential encryption system
- [ ] SMTP provider implementation
- [ ] Basic mailbox manager
- [ ] Rate limiter

### Phase 2: UI & Integration (Week 2)
- [ ] Streamlit UI for mailbox management
- [ ] Campaign creation UI
- [ ] Lead selection integration
- [ ] Email template editor
- [ ] Campaign queue display

### Phase 3: Sending Engine (Week 3)
- [ ] Background worker for queue processing
- [ ] Error handling and retries
- [ ] Real-time progress updates (WebSocket)
- [ ] Campaign statistics
- [ ] Email logging

### Phase 4: Advanced Features (Week 4)
- [ ] API providers (SendGrid, Mailgun)
- [ ] Email warmup system
- [ ] Bounce handling
- [ ] Unsubscribe management
- [ ] Analytics dashboard

---

## 9. Cost Analysis

### SMTP Approach (Free)
- **Gmail:** Free, 500 emails/day limit
- **Outlook:** Free, 300 emails/day limit
- **Custom SMTP:** Free (if you own the server), no hard limit but reputation matters
- **Total:** $0/month (but limited by mailbox count)

### API Approach (Paid)
- **SendGrid:** Free tier (100 emails/day), then $19.95/month for 50k emails
- **Mailgun:** Free tier (5k emails/month), then $35/month for 50k emails
- **AWS SES:** $0.10 per 1,000 emails (very cheap)
- **Total:** $0-$50/month depending on volume

### Hybrid Approach (Recommended)
- Use SMTP for small volumes (free)
- Use API for large campaigns (paid, better deliverability)
- **Total:** $0-$50/month (pay only when needed)

---

## 10. Recommended Tech Stack

### Core Libraries
```python
# Email sending
smtplib          # Built-in SMTP
email            # Built-in email formatting
sendgrid         # SendGrid API (optional)
boto3            # AWS SES (optional)

# Security
cryptography     # Encryption
keyring          # OS keychain access

# Background processing
asyncio          # Async email sending
threading        # Background worker
celery           # Optional: advanced task queue

# Database
sqlite3          # Already using (extend schema)
```

### Dependencies to Add
```txt
cryptography>=41.0.0
keyring>=24.0.0
python-email-validator>=2.0.0
sendgrid>=6.10.0  # Optional
boto3>=1.28.0     # Optional for AWS SES
```

---

## 11. Architecture Decision: Integrated vs Separate

### Final Recommendation: **INTEGRATED MODULE**

**Reasons:**
1. **User Experience:** Users can send emails directly from extracted leads without switching apps
2. **Deployment:** Single application, easier to distribute
3. **License Management:** Unified license system (email features can be part of plan tiers)
4. **Data Flow:** Direct access to leads database, no API overhead
5. **Cost:** No additional infrastructure needed
6. **Maintenance:** Single codebase, easier updates

**Structure:**
```
lead-extractor/
├── app/
│   ├── email/              # NEW: Email module
│   ├── extractors/         # Existing
│   ├── database/           # Extended with email tables
│   └── main.py            # Extended with email UI
```

---

## 12. Next Steps

1. **Review this architecture** - Confirm approach
2. **Start Phase 1** - Implement core infrastructure
3. **Test with single mailbox** - Gmail SMTP first
4. **Add UI** - Mailbox management interface
5. **Integrate with leads** - Campaign creation from extracted leads
6. **Scale up** - Add multiple mailboxes and API providers

---

## 13. Questions to Consider

1. **Volume Expectations:** How many emails per day/week/month?
2. **Budget:** Willing to pay for API services or prefer free SMTP?
3. **Compliance:** Need unsubscribe handling, GDPR compliance?
4. **Templates:** Pre-built templates or custom HTML editor?
5. **Analytics:** Need open rates, click tracking, bounce reports?

---

## Conclusion

The **integrated module approach** with **hybrid SMTP/API support** provides the best balance of:
- ✅ Cost-effectiveness (free SMTP for small volumes)
- ✅ Scalability (API services for large campaigns)
- ✅ User experience (seamless integration)
- ✅ Maintainability (single codebase)
- ✅ Flexibility (multiple providers)

This architecture allows users to start with free SMTP mailboxes and scale to paid API services as their needs grow, all within the same application.

