# High-Volume Email Sender: 10,000+ Emails/Day Plan

## 🎯 Goal
Send 10,000+ emails per day with **zero cost** using multiple free mailboxes, with AWS SES as fallback option.

---

## 💰 Cost Analysis

### Option 1: Free Multi-Mailbox (RECOMMENDED)
**Setup:**
- 20 Gmail accounts × 500 emails/day = **10,000 emails/day**
- OR 34 Outlook accounts × 300 emails/day = **10,200 emails/day**
- **Cost: $0/month** ✅

**Requirements:**
- Create 20+ free email accounts
- Use app passwords (not regular passwords)
- Rotate between accounts automatically
- Connection pooling for efficiency

### Option 2: AWS SES (Fallback)
**Pricing:**
- First 62,000 emails/month FREE (if receiving to verified address)
- After free tier: **$0.10 per 1,000 emails**
- **10,000 emails/day = ~300k/month = ~$30/month** (after free tier)

**Advantages:**
- No mailbox management
- Better deliverability
- Higher sending limits (can send 200 emails/second)
- Professional infrastructure

---

## 🏗️ Architecture for 10k+ Emails/Day

### Core Components

```
┌─────────────────────────────────────────────────────┐
│         Lead Extractor Pro (Streamlit UI)           │
├─────────────────────────────────────────────────────┤
│  📧 High-Volume Email Module                       │
│  ├── Mailbox Pool Manager                          │
│  │   ├── 20+ Gmail/Outlook accounts               │
│  │   ├── Auto-rotation (round-robin)              │
│  │   ├── Health monitoring                         │
│  │   └── Daily limit tracking                     │
│  ├── Connection Pool Manager                       │
│  │   ├── SMTP connection pooling                   │
│  │   ├── Max 20 concurrent connections            │
│  │   ├── Connection reuse (keep-alive)            │
│  │   └── Auto-reconnect on failure                │
│  ├── Queue System (Redis/RabbitMQ)                │
│  │   ├── Queue 10k+ emails                        │
│  │   ├── Process in batches                       │
│  │   ├── Retry failed emails                      │
│  │   └── Priority queue support                   │
│  ├── Rate Limiter                                  │
│  │   ├── Per-mailbox daily limits                 │
│  │   ├── Velocity control (emails/min)            │
│  │   ├── Delay between sends (2-5 seconds)         │
│  │   └── Exponential backoff on errors            │
│  └── Background Worker Pool                        │
│      ├── Multiple worker threads                  │
│      ├── Process queue continuously                │
│      ├── Real-time progress updates               │
│      └── Error handling & logging                 │
└─────────────────────────────────────────────────────┘
```

---

## 📋 Implementation Strategy

### Phase 1: Multi-Mailbox SMTP Pool (FREE)

#### 1.1 Mailbox Pool Manager
**File:** `app/email/mailbox_pool.py`

**Features:**
- Store 20+ mailbox credentials (encrypted)
- Round-robin rotation
- Track daily usage per mailbox
- Auto-disable exhausted mailboxes
- Health checks (test connection before use)

**Database Schema:**
```sql
CREATE TABLE mailboxes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    provider TEXT NOT NULL,              -- 'gmail', 'outlook', 'custom'
    smtp_host TEXT NOT NULL,             -- smtp.gmail.com
    smtp_port INTEGER NOT NULL,          -- 587 (TLS) or 465 (SSL)
    smtp_username TEXT NOT NULL,
    smtp_password_encrypted TEXT NOT NULL, -- Encrypted app password
    daily_limit INTEGER DEFAULT 500,      -- Gmail: 500, Outlook: 300
    sent_today INTEGER DEFAULT 0,
    sent_total INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT 1,
    last_used TIMESTAMP,
    last_error TEXT,
    error_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_mailboxes_active ON mailboxes(is_active, sent_today);
```

#### 1.2 SMTP Connection Pool
**File:** `app/email/smtp_pool.py`

**Key Optimizations:**
- **Connection Pooling**: Reuse SMTP connections (don't reconnect for each email)
- **Max Connections**: 20 concurrent connections
- **Keep-Alive**: Keep connections alive between sends
- **Connection Timeout**: 30 seconds
- **Retry Logic**: Auto-retry on connection failures

**Python Implementation:**
```python
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from threading import Lock
from queue import Queue
import time

class SMTPConnectionPool:
    def __init__(self, max_connections=20):
        self.max_connections = max_connections
        self.pools = {}  # One pool per mailbox
        self.locks = {}  # Lock per mailbox
        self.queue = Queue()
    
    def get_connection(self, mailbox_config):
        """Get or create SMTP connection for mailbox"""
        mailbox_id = mailbox_config['id']
        
        if mailbox_id not in self.pools:
            self.pools[mailbox_id] = []
            self.locks[mailbox_id] = Lock()
        
        pool = self.pools[mailbox_id]
        lock = self.locks[mailbox_id]
        
        with lock:
            # Reuse existing connection if available
            if pool:
                conn = pool.pop()
                try:
                    # Test connection
                    conn.noop()
                    return conn
                except:
                    # Connection dead, create new one
                    pass
            
            # Create new connection
            if len(pool) < self.max_connections:
                conn = smtplib.SMTP(
                    mailbox_config['smtp_host'],
                    mailbox_config['smtp_port']
                )
                conn.starttls()
                conn.login(
                    mailbox_config['smtp_username'],
                    mailbox_config['smtp_password']
                )
                return conn
        
        return None  # Pool exhausted
    
    def return_connection(self, mailbox_id, conn):
        """Return connection to pool"""
        if mailbox_id in self.pools:
            self.pools[mailbox_id].append(conn)
```

#### 1.3 Queue System
**File:** `app/email/email_queue.py`

**Why Queue?**
- Can't load 10,000 emails in memory at once
- Need to process in batches
- Handle failures gracefully
- Resume after restart

**Options:**
1. **Redis** (Recommended) - Fast, persistent, supports pub/sub
2. **RabbitMQ** - Robust, but heavier
3. **SQLite Queue** - Simple, but slower for high volume

**Redis Queue Structure:**
```python
import redis
from rq import Queue

redis_conn = redis.Redis(host='localhost', port=6379, db=0)
email_queue = Queue('emails', connection=redis_conn)

# Add email to queue
email_queue.enqueue(
    send_email_task,
    recipient='user@example.com',
    subject='...',
    body='...',
    mailbox_id=1
)
```

**SQLite Queue (Simpler, no Redis needed):**
```sql
CREATE TABLE email_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id INTEGER,
    mailbox_id INTEGER,
    recipient_email TEXT NOT NULL,
    recipient_name TEXT,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    status TEXT DEFAULT 'pending',  -- 'pending', 'processing', 'sent', 'failed'
    priority INTEGER DEFAULT 0,      -- Higher = send first
    attempts INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 3,
    error_message TEXT,
    scheduled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,
    sent_at TIMESTAMP,
    FOREIGN KEY (campaign_id) REFERENCES email_campaigns(id),
    FOREIGN KEY (mailbox_id) REFERENCES mailboxes(id)
);

CREATE INDEX idx_queue_status ON email_queue(status, priority DESC, scheduled_at);
CREATE INDEX idx_queue_mailbox ON email_queue(mailbox_id, status);
```

#### 1.4 Background Worker
**File:** `app/email/worker.py`

**Worker Strategy:**
- Multiple worker threads (one per mailbox or shared pool)
- Process queue continuously
- Respect rate limits
- Update progress in real-time (WebSocket)
- Handle errors gracefully

**Worker Implementation:**
```python
import threading
import time
from app.email.mailbox_pool import MailboxPool
from app.email.smtp_pool import SMTPConnectionPool
from app.email.rate_limiter import RateLimiter

class EmailWorker:
    def __init__(self, num_workers=5):
        self.mailbox_pool = MailboxPool()
        self.smtp_pool = SMTPConnectionPool(max_connections=20)
        self.rate_limiter = RateLimiter()
        self.num_workers = num_workers
        self.workers = []
        self.running = False
    
    def start(self):
        """Start worker threads"""
        self.running = True
        for i in range(self.num_workers):
            worker = threading.Thread(target=self._worker_loop, daemon=True)
            worker.start()
            self.workers.append(worker)
    
    def _worker_loop(self):
        """Main worker loop"""
        while self.running:
            # Get next email from queue
            email_job = self._get_next_email()
            
            if not email_job:
                time.sleep(1)  # No emails, wait
                continue
            
            # Get available mailbox
            mailbox = self.mailbox_pool.get_available_mailbox()
            if not mailbox:
                time.sleep(5)  # No mailboxes available, wait
                continue
            
            # Check rate limits
            if not self.rate_limiter.can_send(mailbox['id']):
                time.sleep(2)  # Rate limited, wait
                continue
            
            # Send email
            try:
                self._send_email(email_job, mailbox)
                self._mark_sent(email_job['id'])
                self.rate_limiter.record_sent(mailbox['id'])
            except Exception as e:
                self._handle_error(email_job['id'], str(e))
    
    def _send_email(self, email_job, mailbox):
        """Send single email"""
        conn = self.smtp_pool.get_connection(mailbox)
        if not conn:
            raise Exception("No connection available")
        
        try:
            msg = MIMEMultipart()
            msg['From'] = mailbox['email']
            msg['To'] = email_job['recipient_email']
            msg['Subject'] = email_job['subject']
            msg.attach(MIMEText(email_job['body'], 'html'))
            
            conn.sendmail(
                mailbox['email'],
                email_job['recipient_email'],
                msg.as_string()
            )
        finally:
            self.smtp_pool.return_connection(mailbox['id'], conn)
```

#### 1.5 Rate Limiter
**File:** `app/email/rate_limiter.py`

**Rate Limiting Rules:**
- **Per-mailbox daily limit**: Gmail (500), Outlook (300)
- **Velocity control**: Max 5 emails/minute per mailbox
- **Delay between sends**: 2-5 seconds (randomized)
- **Exponential backoff**: On errors, wait longer

**Implementation:**
```python
import time
from collections import defaultdict
from datetime import datetime, timedelta

class RateLimiter:
    def __init__(self):
        self.daily_counts = defaultdict(int)  # mailbox_id -> count
        self.last_reset = defaultdict(lambda: datetime.now().date())
        self.last_sent = defaultdict(float)  # mailbox_id -> timestamp
        self.min_delay = 2  # seconds
        self.max_delay = 5  # seconds
        self.max_per_minute = 5
    
    def can_send(self, mailbox_id, daily_limit=500):
        """Check if can send now"""
        # Reset daily count if new day
        today = datetime.now().date()
        if self.last_reset[mailbox_id] != today:
            self.daily_counts[mailbox_id] = 0
            self.last_reset[mailbox_id] = today
        
        # Check daily limit
        if self.daily_counts[mailbox_id] >= daily_limit:
            return False
        
        # Check velocity (emails per minute)
        now = time.time()
        last = self.last_sent[mailbox_id]
        if now - last < (60 / self.max_per_minute):
            return False
        
        return True
    
    def record_sent(self, mailbox_id):
        """Record that email was sent"""
        self.daily_counts[mailbox_id] += 1
        self.last_sent[mailbox_id] = time.time()
    
    def get_delay(self):
        """Get randomized delay between sends"""
        import random
        return random.uniform(self.min_delay, self.max_delay)
```

---

## 🚀 Setup Instructions

### Step 1: Create Multiple Gmail Accounts
1. Create 20+ Gmail accounts (use different names/numbers)
2. Enable 2FA on each account
3. Generate App Password for each:
   - Go to: https://myaccount.google.com/apppasswords
   - Create app password for "Mail"
   - Save the 16-character password

### Step 2: Add Mailboxes to System
1. Open Lead Extractor Pro
2. Go to "Email" → "Mailbox Management"
3. Click "Add Mailbox"
4. Select "Gmail"
5. Enter email and app password
6. Test connection
7. Repeat for all 20 accounts

### Step 3: Configure Rate Limits
- Gmail: 500 emails/day per account
- Outlook: 300 emails/day per account
- Custom SMTP: Configurable

### Step 4: Start Sending
1. Select leads from database
2. Create email template
3. Start campaign
4. System automatically rotates mailboxes
5. Sends 10,000+ emails/day

---

## 📊 Performance Expectations

### With 20 Gmail Accounts:
- **Capacity**: 20 × 500 = 10,000 emails/day
- **Speed**: ~7 emails/minute (with delays)
- **Time to send 10k**: ~24 hours (distributed)
- **Cost**: $0/month ✅

### With 34 Outlook Accounts:
- **Capacity**: 34 × 300 = 10,200 emails/day
- **Speed**: ~7 emails/minute
- **Time to send 10k**: ~24 hours
- **Cost**: $0/month ✅

### With AWS SES (Fallback):
- **Capacity**: Unlimited (200 emails/second = 17M/day)
- **Speed**: Can send 10k in ~1 hour
- **Cost**: ~$30/month (after free tier)
- **Deliverability**: Excellent

---

## 🔧 Technical Requirements

### Dependencies to Add:
```txt
# Email sending
aiosmtplib>=2.0.0        # Async SMTP (better for high volume)
email-validator>=2.0.0   # Validate email addresses

# Queue system (choose one)
redis>=5.0.0             # Redis queue (recommended)
rq>=1.15.0               # Redis Queue (Python wrapper)
# OR
celery>=5.3.0            # Advanced task queue
# OR
# Use SQLite queue (no extra dependencies)

# Security
cryptography>=41.0.0     # Encrypt credentials
keyring>=24.0.0          # OS keychain

# AWS SES (optional fallback)
boto3>=1.28.0            # AWS SDK
```

### System Requirements:
- **RAM**: 2GB+ (for connection pooling)
- **CPU**: Multi-core recommended (for worker threads)
- **Storage**: ~100MB per 10k emails (queue + logs)
- **Network**: Stable internet connection

---

## 🎯 Implementation Phases

### Phase 1: Core Infrastructure (Week 1)
- [ ] Database schema (mailboxes, queue, campaigns)
- [ ] Credential encryption system
- [ ] Mailbox pool manager
- [ ] SMTP connection pool
- [ ] Basic rate limiter

### Phase 2: Queue & Worker (Week 2)
- [ ] Queue system (Redis or SQLite)
- [ ] Background worker threads
- [ ] Email sending logic
- [ ] Error handling & retries
- [ ] Progress tracking

### Phase 3: UI Integration (Week 3)
- [ ] Mailbox management UI
- [ ] Campaign creation UI
- [ ] Lead selection integration
- [ ] Real-time progress (WebSocket)
- [ ] Campaign statistics

### Phase 4: AWS SES Integration (Week 4)
- [ ] AWS SES provider
- [ ] Auto-failover to SES
- [ ] Hybrid mode (SMTP + SES)
- [ ] Cost tracking

---

## 🛡️ Deliverability Best Practices

### For 10k+ Emails/Day:
1. **Warm up mailboxes gradually**
   - Start with 50 emails/day per mailbox
   - Increase by 50 every 3-4 days
   - Reach 500/day after 2-3 weeks

2. **Email content**
   - Personalize subject lines
   - Avoid spam trigger words
   - Include unsubscribe link
   - Use proper HTML structure

3. **Sending behavior**
   - Randomize delays (2-5 seconds)
   - Don't send too fast (max 5/min per mailbox)
   - Handle bounces immediately
   - Respect unsubscribes

4. **Technical setup**
   - SPF/DKIM/DMARC (already configured for Gmail/Outlook)
   - Reverse DNS (for custom SMTP)
   - Clean email list (remove invalid emails)

---

## 🔄 Fallback to AWS SES

### When to Use AWS SES:
1. **Mailboxes exhausted** - All 20 accounts hit daily limit
2. **Better deliverability needed** - Professional campaigns
3. **Faster sending** - Need to send 10k in hours, not days
4. **Scalability** - Need to send 50k+ per day

### AWS SES Setup:
1. **Create AWS Account** (if not already)
2. **Verify sending domain** (or use sandbox mode)
3. **Request production access** (remove sandbox limits)
4. **Get API credentials** (Access Key ID, Secret Key)
5. **Add to Lead Extractor**:
   - Go to "Email" → "Add Provider"
   - Select "AWS SES"
   - Enter credentials
   - Test connection

### AWS SES Configuration:
```python
import boto3

ses_client = boto3.client(
    'ses',
    aws_access_key_id='YOUR_KEY',
    aws_secret_access_key='YOUR_SECRET',
    region_name='us-east-1'
)

response = ses_client.send_email(
    Source='sender@example.com',
    Destination={'ToAddresses': ['recipient@example.com']},
    Message={
        'Subject': {'Data': 'Subject'},
        'Body': {'Html': {'Data': '<html>Body</html>'}}
    }
)
```

---

## 📈 Monitoring & Analytics

### Key Metrics to Track:
- **Emails sent per day** (per mailbox)
- **Success rate** (sent vs failed)
- **Bounce rate** (hard bounces, soft bounces)
- **Spam complaint rate** (should be < 0.1%)
- **Delivery time** (time to send 10k emails)
- **Cost** (if using AWS SES)

### Dashboard:
- Real-time sending progress
- Mailbox health status
- Queue depth (pending emails)
- Error logs
- Campaign statistics

---

## ✅ Success Criteria

### For 10k+ Emails/Day:
- ✅ Send 10,000+ emails/day reliably
- ✅ 95%+ delivery rate (not bounced)
- ✅ < 1% spam complaint rate
- ✅ Automatic mailbox rotation
- ✅ Queue processing without memory issues
- ✅ Real-time progress tracking
- ✅ Cost: $0/month (with free mailboxes)

---

## 🎯 Next Steps

1. **Review this plan** - Confirm approach
2. **Start Phase 1** - Core infrastructure
3. **Test with 1 mailbox** - Verify SMTP connection
4. **Add 5 mailboxes** - Test rotation
5. **Scale to 20 mailboxes** - Full capacity
6. **Monitor & optimize** - Fine-tune rate limits
7. **Add AWS SES** - Fallback option

---

## 💡 Pro Tips

1. **Start small**: Test with 1-2 mailboxes first
2. **Warm up gradually**: Don't send 500/day immediately
3. **Monitor closely**: Watch for errors, bounces, complaints
4. **Rotate IPs**: If possible, use different IPs for different mailboxes
5. **Clean lists**: Remove invalid emails before sending
6. **Personalize**: Better open rates = better deliverability
7. **Comply**: Include unsubscribe links, respect opt-outs

---

**Ready to implement?** Let's start with Phase 1! 🚀

