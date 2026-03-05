# 📧 Complete Email Setup Guide: Mailboxes, Bulk Sending & Anti-Spam Strategy

## 🎯 What Kind of Mailbox Should You Use?

### Option 1: Personal Gmail (Quick Start) ✅
**Pros:**
- ✅ Free and immediate
- ✅ Already have the account
- ✅ Easy to set up
- ✅ Good for testing

**Cons:**
- ⚠️ Risk to personal account if flagged
- ⚠️ Limited to 500 emails/day
- ⚠️ If account gets suspended, you lose access

**Recommendation:** Use for **testing only** or **low volume** (< 500 emails/day)

### Option 2: Dedicated Gmail Accounts (Recommended for Bulk) ⭐
**Pros:**
- ✅ Separate from personal account
- ✅ Can create 20+ accounts = 10,000 emails/day capacity
- ✅ If one gets flagged, others continue working
- ✅ Free (just need phone numbers for verification)

**How to Create:**
1. Create new Gmail accounts: `yourname1@gmail.com`, `yourname2@gmail.com`, etc.
2. Use different phone numbers (or Google Voice numbers)
3. Enable 2FA on each
4. Generate App Password for each

**Recommendation:** **Best for bulk sending** (10,000+ emails/day)

### Option 3: Google Workspace (Professional) 💼
**Pros:**
- ✅ Higher limits (319,444 emails per 10-minute window!)
- ✅ Better deliverability
- ✅ Professional domain
- ✅ Exempt from 2024 bulk sender guidelines

**Cons:**
- 💰 Costs ~$6/month per user
- ⚠️ Still need to warm up accounts

**Recommendation:** For **professional campaigns** or **very high volume**

---

## 📝 What Details Do You Input?

### Required Fields:

1. **Provider**: `gmail`, `outlook`, or `custom`
   - Gmail: Auto-fills `smtp.gmail.com:587`
   - Outlook: Auto-fills `smtp-mail.outlook.com:587`
   - Custom: You enter SMTP details manually

2. **Name**: Friendly identifier like `"Gmail #1"`, `"Marketing Account"`, `"Sales Team"`

3. **Email Address**: Full email like `yourname@gmail.com`

4. **SMTP Host**: Usually auto-filled
   - Gmail: `smtp.gmail.com`
   - Outlook: `smtp-mail.outlook.com`

5. **SMTP Port**: Usually `587` (TLS) or `465` (SSL)
   - Port 587 is recommended (STARTTLS)

6. **SMTP Username**: Usually same as email address

7. **SMTP Password**: ⚠️ **CRITICAL - Use App Password, NOT regular password!**
   - **Gmail**: Go to https://myaccount.google.com/apppasswords
   - Generate 16-character app password
   - Use that instead of your regular password
   - **Why?** Gmail blocks regular passwords for security

8. **Daily Limit**: 
   - Gmail: `500` emails/day
   - Outlook: `300` emails/day
   - Custom: Depends on your SMTP provider

---

## 🚀 Bulk Sending Strategy: How It Works

### Architecture Overview

```
┌─────────────────────────────────────────────────┐
│         Email Campaign (10,000 emails)         │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│         Email Queue (SQLite Database)          │
│  - Stores all emails with status: pending      │
│  - Tracks: recipient, subject, body, mailbox  │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│      Mailbox Pool Manager (Round-Robin)         │
│  - Rotates between 20 mailboxes                │
│  - Checks daily limits (500/day each)           │
│  - Skips exhausted mailboxes                   │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│         Rate Limiter (Anti-Spam)                │
│  - Max 5 emails/minute per mailbox             │
│  - Random delay: 2-5 seconds between sends     │
│  - Prevents velocity spikes                    │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│      SMTP Connection Pool (Efficiency)         │
│  - Reuses connections (don't reconnect each)  │
│  - Max 5 connections per mailbox               │
│  - Auto-reconnect on failure                   │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│              Email Sent! ✅                     │
│  - Updates queue status: sent                  │
│  - Increments mailbox sent_today counter       │
│  - Logs timestamp                              │
└─────────────────────────────────────────────────┘
```

### How Mailboxes Are Differentiated

Each mailbox is tracked separately:

1. **Unique ID**: Database assigns `id=1`, `id=2`, etc.
2. **Separate Counters**: Each has its own `sent_today` and `sent_total`
3. **Individual Limits**: Each has its own `daily_limit` (500 for Gmail)
4. **Rotation Logic**: System picks mailbox with:
   - `is_active = 1` (not deactivated)
   - `sent_today < daily_limit` (has capacity)
   - Oldest `last_used` timestamp (round-robin)

**Example Flow:**
```
Email 1 → Mailbox #1 (sent_today: 0/500) ✅
Email 2 → Mailbox #2 (sent_today: 0/500) ✅
Email 3 → Mailbox #3 (sent_today: 0/500) ✅
...
Email 501 → Mailbox #1 (sent_today: 500/500) ❌ Skip
Email 501 → Mailbox #2 (sent_today: 0/500) ✅ Use this!
```

---

## 🛡️ Anti-Spam Measures: How We Prevent Issues

### 1. **Rate Limiting (Velocity Control)**

**Problem:** Sending 500 emails instantly = spam trigger

**Solution:** Spread sends over time
- **Max 5 emails/minute** per mailbox
- **Random delay: 2-5 seconds** between each email
- **Minimum 12 seconds** between emails (60 seconds ÷ 5)

**Code Implementation:**
```python
# From rate_limiter.py
max_per_minute = 5  # Max emails per minute
min_delay = 2       # Minimum seconds between emails
max_delay = 5       # Maximum seconds between emails

# Before sending, check:
if time_since_last_email < (60 / max_per_minute):
    wait()  # Don't send yet

# After sending, wait random delay:
time.sleep(random.uniform(2, 5))
```

**Result:** 500 emails spread over ~2 hours (not instant)

### 2. **Mailbox Rotation (Load Distribution)**

**Problem:** Using one mailbox for everything = account suspension

**Solution:** Distribute across 20+ mailboxes
- Each mailbox sends max 500/day
- System automatically rotates
- If one gets flagged, others continue

**Example:**
```
10,000 emails ÷ 20 mailboxes = 500 emails per mailbox ✅
Each mailbox stays under limit ✅
No single account overloaded ✅
```

### 3. **Connection Pooling (Efficiency)**

**Problem:** Reconnecting for each email = slow + suspicious

**Solution:** Reuse SMTP connections
- Keep connections alive between sends
- Max 5 concurrent connections per mailbox
- Auto-reconnect if connection dies

**Result:** Faster sending + less suspicious behavior

### 4. **Daily Limit Enforcement**

**Problem:** Exceeding provider limits = account suspension

**Solution:** Hard limits per mailbox
- Gmail: 500/day enforced
- Outlook: 300/day enforced
- System automatically stops when limit reached
- Resets at midnight (new day)

### 5. **Error Handling & Health Monitoring**

**Problem:** Dead mailboxes keep getting used

**Solution:** Track errors and deactivate bad mailboxes
- Count errors per mailbox
- Test connection before use
- Auto-deactivate if too many errors
- Manual deactivate option in UI

---

## 🏢 How Professional Services Work (SendGrid, Mailgun, AWS SES)

### Professional Email Services Architecture

**SendGrid / Mailgun / AWS SES:**

```
┌─────────────────────────────────────────────────┐
│         Your Application                        │
│  - Sends email request via API                 │
│  - JSON payload: to, subject, body             │
└─────────────────────────────────────────────────┘
                    ↓ HTTP POST
┌─────────────────────────────────────────────────┐
│      Email Service API (SendGrid/Mailgun)      │
│  - Accepts request                              │
│  - Validates content                            │
│  - Checks spam filters                          │
│  - Queues email                                 │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│      Infrastructure (Managed Servers)           │
│  - Multiple IP addresses                        │
│  - Pre-warmed domains                           │
│  - SPF/DKIM/DMARC configured                   │
│  - Reputation management                        │
└─────────────────────────────────────────────────┘
                    ↓ SMTP
┌─────────────────────────────────────────────────┐
│         Recipient Email Server                  │
│  - Gmail, Outlook, etc.                        │
└─────────────────────────────────────────────────┘
```

### Key Differences: Professional Services vs Our Approach

| Feature | Professional Services | Our SMTP Approach |
|---------|----------------------|-------------------|
| **Setup** | API key, instant | Mailbox credentials, manual |
| **Cost** | $0.001-$0.01 per email | Free (uses your mailboxes) |
| **Deliverability** | Excellent (managed reputation) | Good (depends on your accounts) |
| **Rate Limits** | Very high (millions/day) | Low (500/day per mailbox) |
| **Warmup** | Pre-warmed infrastructure | You need to warm up accounts |
| **Scalability** | Unlimited | Limited by mailbox count |
| **Control** | Less control | Full control |
| **Compliance** | Built-in (SPF/DKIM/DMARC) | You manage it |

### Do They Use Scripts?

**Yes!** Professional services use:

1. **Queue Management Scripts:**
   - Sort emails by provider (Gmail, Outlook, etc.)
   - Group by rate limits
   - Schedule sends during off-peak hours
   - Load balancing with pauses

2. **Reputation Management:**
   - Monitor bounce rates
   - Track spam complaints
   - Auto-throttle if issues detected
   - IP rotation

3. **Infrastructure Scripts:**
   - Auto-scaling servers
   - Load balancing
   - Failover handling
   - Monitoring & alerts

**Our Approach:** We use similar scripts but simpler:
- Queue in SQLite database
- Round-robin mailbox rotation
- Rate limiting per mailbox
- Error tracking

---

## 📊 Bulk Sending Plan: Step-by-Step

### Phase 1: Setup (Day 1)

1. **Create 20 Gmail Accounts**
   - Use different names/numbers
   - Enable 2FA on each
   - Generate App Password for each

2. **Add Mailboxes to System**
   - Go to **📧 Sender** → **📬 Mailboxes**
   - Add each account
   - Test connection for each

3. **Verify Setup**
   - Check all mailboxes show "✅ Active"
   - Total capacity: 20 × 500 = 10,000 emails/day

### Phase 2: Warmup (Days 1-14) ⚠️ IMPORTANT!

**Why Warmup?** New accounts sending 500 emails immediately = spam trigger

**Warmup Schedule:**
```
Day 1-3:   50 emails/day per mailbox
Day 4-7:   100 emails/day per mailbox
Day 8-11:  250 emails/day per mailbox
Day 12-14: 400 emails/day per mailbox
Day 15+:   500 emails/day per mailbox (full capacity)
```

**How to Warmup:**
- Start with small campaigns
- Gradually increase volume
- Monitor for errors/bounces
- If issues, slow down

### Phase 3: Full Capacity (Day 15+)

**Now You Can:**
- Send 10,000 emails/day (20 mailboxes × 500)
- System auto-rotates mailboxes
- Rate limiting prevents spam
- Connection pooling for efficiency

**Campaign Flow:**
1. Create campaign with 10,000 leads
2. System queues all emails
3. Background workers process queue
4. Emails sent over ~24 hours (distributed)
5. Monitor progress in **📊 Campaign Queue** tab

---

## 🎯 Best Practices Summary

### ✅ DO:
- ✅ Use **App Passwords** (not regular passwords)
- ✅ **Warm up** new accounts gradually
- ✅ **Rotate** between multiple mailboxes
- ✅ **Respect** daily limits (500 Gmail, 300 Outlook)
- ✅ **Monitor** error rates and deactivate bad mailboxes
- ✅ **Personalize** emails (use {{name}}, {{email}})
- ✅ **Include unsubscribe** links (compliance)
- ✅ **Test** connections before campaigns

### ❌ DON'T:
- ❌ Use **regular passwords** (will fail)
- ❌ Send **500 emails instantly** (spam trigger)
- ❌ Use **one mailbox** for everything (suspension risk)
- ❌ **Exceed** daily limits (account suspension)
- ❌ Send to **invalid emails** (hurts reputation)
- ❌ **Ignore** bounce rates (fix issues)
- ❌ Send **spammy content** (trigger words, etc.)

---

## 🔧 Technical Details: How Our System Works

### Mailbox Differentiation

Each mailbox is stored in database with:
```sql
mailboxes (
    id INTEGER PRIMARY KEY,           -- Unique ID (1, 2, 3...)
    name TEXT,                        -- "Gmail #1", "Gmail #2"
    email TEXT UNIQUE,                -- Different email addresses
    provider TEXT,                     -- "gmail", "outlook"
    smtp_host TEXT,                    -- SMTP server
    smtp_port INTEGER,                 -- Port number
    smtp_username TEXT,                -- Username
    smtp_password_encrypted TEXT,      -- Encrypted password
    daily_limit INTEGER DEFAULT 500,   -- Max per day
    sent_today INTEGER DEFAULT 0,      -- Counter (resets daily)
    sent_total INTEGER DEFAULT 0,      -- Lifetime counter
    is_active BOOLEAN DEFAULT 1,      -- Enable/disable
    last_used TIMESTAMP,              -- For rotation
    error_count INTEGER DEFAULT 0      -- Track issues
)
```

### Rotation Algorithm

```python
# From mailbox_pool.py
def get_available_mailbox():
    # 1. Reset daily counts if new day
    reset_daily_counts_if_needed()
    
    # 2. Find mailbox with:
    #    - is_active = 1
    #    - sent_today < daily_limit
    #    - Oldest last_used (round-robin)
    mailbox = query(
        "SELECT * FROM mailboxes "
        "WHERE is_active = 1 AND sent_today < daily_limit "
        "ORDER BY last_used ASC, sent_today ASC "
        "LIMIT 1"
    )
    
    return mailbox
```

### Rate Limiting Algorithm

```python
# From rate_limiter.py
def can_send(mailbox_id):
    now = time.time()
    last_sent_time = self.last_sent[mailbox_id]
    
    # Check velocity: max 5 emails/minute
    if last_sent_time > 0:
        time_since_last = now - last_sent_time
        min_interval = 60 / 5  # 12 seconds
        if time_since_last < min_interval:
            return False  # Too fast!
    
    return True  # OK to send

# After sending:
def record_sent(mailbox_id):
    self.last_sent[mailbox_id] = time.time()
    # Wait random delay before next send
    delay = random.uniform(2, 5)  # 2-5 seconds
    time.sleep(delay)
```

---

## 📈 Scaling Strategy

### Start Small:
- **1 mailbox** = 500 emails/day
- **Cost:** $0/month
- **Time to send 500:** ~2 hours (with delays)

### Scale Up:
- **5 mailboxes** = 2,500 emails/day
- **10 mailboxes** = 5,000 emails/day
- **20 mailboxes** = 10,000 emails/day
- **Cost:** Still $0/month!

### Go Big (Hybrid):
- **20 Gmail mailboxes** = 10,000/day (free)
- **+ AWS SES** = Unlimited capacity ($30/month for 300k/month)
- **Auto-failover** when mailboxes exhausted
- **Best of both worlds**

---

## 🎓 Summary

**What Mailbox?** 
- Personal Gmail for testing ✅
- Dedicated Gmail accounts for bulk (recommended) ⭐
- Google Workspace for professional 💼

**What Details?**
- Email, App Password (not regular!), SMTP settings, Daily limit

**Bulk Sending Plan?**
- 20 mailboxes × 500/day = 10,000 emails/day
- Auto-rotation, rate limiting, connection pooling

**Anti-Spam?**
- Rate limiting (5/min), delays (2-5s), rotation, daily limits

**How Differentiated?**
- Each mailbox has unique ID, separate counters, individual limits

**Professional Services?**
- Use APIs, managed infrastructure, pre-warmed domains
- We use SMTP with similar queue/rotation logic

**Ready to blast!** 🚀

Start with 1 mailbox, test, then scale to 20 for 10,000 emails/day!
