# Email Sender Quick Start Guide

## 🎯 Quick Decision Matrix

### Choose Your Approach:

| Volume | Budget | Recommended Method |
|--------|--------|-------------------|
| < 500 emails/day | Free | Gmail SMTP (1 mailbox) |
| 500-5,000 emails/day | Free | Multiple Gmail/Outlook mailboxes |
| 5,000-50,000 emails/day | $20-50/month | SendGrid or Mailgun API |
| > 50,000 emails/day | $50+/month | AWS SES or multiple API accounts |

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────┐
│         Lead Extractor Pro (Streamlit UI)       │
├─────────────────────────────────────────────────┤
│  📧 Email Module (NEW)                          │
│  ├── Mailbox Manager                            │
│  │   ├── Add Gmail/Outlook/Custom SMTP          │
│  │   ├── Add SendGrid/Mailgun API               │
│  │   └── Rotate & Load Balance                  │
│  ├── Campaign Manager                           │
│  │   ├── Select Leads from DB                  │
│  │   ├── Email Templates                       │
│  │   └── Queue Management                      │
│  ├── Rate Limiter                               │
│  │   ├── Per-mailbox daily limits              │
│  │   ├── Velocity control (emails/min)          │
│  │   └── Delay between sends                   │
│  └── Background Worker                         │
│      ├── Process queue                         │
│      ├── Retry failed emails                    │
│      └── Update statistics                     │
└─────────────────────────────────────────────────┘
```

---

## 📋 Implementation Checklist

### Phase 1: Foundation
- [ ] Create `app/email/` directory structure
- [ ] Design database schema (mailboxes, campaigns, queue)
- [ ] Implement credential encryption (`cryptography` + `keyring`)
- [ ] Create SMTP provider class
- [ ] Basic mailbox manager (add/test/list)

### Phase 2: Core Features
- [ ] Rate limiter (daily limits, delays)
- [ ] Email queue system
- [ ] Background worker thread
- [ ] Campaign creation logic
- [ ] Email template system

### Phase 3: UI Integration
- [ ] Mailbox management UI (Streamlit)
- [ ] Campaign creation UI
- [ ] Lead selection from database
- [ ] Campaign queue display
- [ ] Real-time progress (WebSocket)

### Phase 4: Advanced
- [ ] API providers (SendGrid, Mailgun)
- [ ] Error handling & retries
- [ ] Bounce management
- [ ] Analytics dashboard

---

## 🔐 Security Best Practices

1. **Encrypt all credentials** using OS keychain
2. **Never log passwords** in plain text
3. **Use app passwords** for Gmail/Outlook (not regular passwords)
4. **Store API keys encrypted** in database
5. **Test connections** before saving credentials

---

## 📊 Database Schema (Quick Reference)

```sql
-- Mailboxes
mailboxes (id, name, email, provider, smtp_host, smtp_port, 
           smtp_username, smtp_password_encrypted, api_key_encrypted,
           daily_limit, sent_today, is_active)

-- Campaigns
email_campaigns (id, name, subject_template, body_template,
                 status, total_recipients, sent_count, failed_count)

-- Queue
email_queue (id, campaign_id, mailbox_id, recipient_email,
             subject, body, status, attempts, error_message, sent_at)
```

---

## 🚀 Quick Start: Adding Your First Mailbox

### Gmail Setup:
1. Enable 2FA on Gmail account
2. Generate App Password: https://myaccount.google.com/apppasswords
3. In Lead Extractor:
   - Click "Add Mailbox"
   - Select "Gmail"
   - Enter email and app password
   - Test connection
   - Save (encrypted)

### Outlook Setup:
1. Enable 2FA on Outlook account
2. Generate App Password: https://account.microsoft.com/security
3. In Lead Extractor:
   - Click "Add Mailbox"
   - Select "Outlook"
   - Enter email and app password
   - Test connection
   - Save (encrypted)

---

## 💡 Key Features

### ✅ What It Will Do:
- Send bulk emails from extracted leads
- Rotate between multiple mailboxes automatically
- Respect rate limits (avoid spam detection)
- Queue emails for reliable delivery
- Track sent/failed emails
- Retry failed emails automatically
- Real-time progress updates

### ❌ What It Won't Do (Out of Scope):
- Email warmup service (can add later)
- Advanced analytics (open rates, clicks) - can add later
- A/B testing - can add later
- Automated follow-ups - can add later

---

## 📈 Scaling Strategy

### Start Small:
- 1 Gmail mailbox = 500 emails/day
- Free, easy setup

### Scale Up:
- Add more Gmail/Outlook mailboxes
- Each adds 300-500 emails/day capacity
- Still free

### Go Big:
- Add SendGrid API ($19.95/month for 50k emails)
- Better deliverability
- Higher limits

---

## 🎨 UI Mockup (Conceptual)

```
┌─────────────────────────────────────────────┐
│  📧 Email Campaigns                        │
├─────────────────────────────────────────────┤
│                                             │
│  Mailboxes (3 active)                      │
│  ┌──────────┬──────────┬──────────┐      │
│  │ Gmail    │ Outlook  │ SendGrid  │      │
│  │ 450/500  │ 280/300  │ 1,200/∞   │      │
│  │ ✅ Active│ ✅ Active│ ✅ Active │      │
│  └──────────┴──────────┴──────────┘      │
│                                             │
│  Create Campaign                           │
│  ├── Select Leads: [Browse Database]      │
│  ├── Template: [Choose Template ▼]        │
│  ├── Mailbox: [Auto-rotate ▼]            │
│  └── [Start Campaign]                     │
│                                             │
│  Active Campaigns                          │
│  ┌─────────────────────────────────────┐   │
│  │ Campaign #1: "Product Launch"       │   │
│  │ Progress: ████████░░ 1,234/2,000   │   │
│  │ Status: Sending...                  │   │
│  └─────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

---

## 🔧 Technical Stack

```python
# Core
smtplib          # SMTP sending
email            # Email formatting
cryptography     # Credential encryption
keyring          # OS keychain

# Optional (for API providers)
sendgrid         # SendGrid API
boto3            # AWS SES
requests         # Mailgun API

# Background processing
asyncio          # Async operations
threading        # Background worker
```

---

## 📝 Next Steps

1. **Review architecture document** (`EMAIL_SENDER_ARCHITECTURE.md`)
2. **Confirm approach** (integrated vs separate)
3. **Start Phase 1** implementation
4. **Test with single mailbox** first
5. **Iterate and improve**

---

## ❓ FAQ

**Q: Can I use my own Gmail account?**  
A: Yes! Just generate an app password and add it as a mailbox.

**Q: How many emails can I send per day?**  
A: Depends on mailboxes: Gmail (500/day), Outlook (300/day), SendGrid (unlimited on paid plan).

**Q: Will my emails go to spam?**  
A: Follow best practices (personalization, proper content, rate limiting) to minimize spam risk.

**Q: Can I send to unsubscribed emails?**  
A: No, the system will track unsubscribes and skip those emails (compliance feature).

**Q: How much will this cost?**  
A: Free if using Gmail/Outlook SMTP. $20-50/month if using SendGrid/Mailgun for higher volumes.

---

## 🎯 Success Metrics

- ✅ Send 1,000+ emails/day with multiple mailboxes
- ✅ 95%+ delivery rate (not bounced)
- ✅ < 1% spam complaint rate
- ✅ Automatic retry for failed emails
- ✅ Real-time progress tracking

---

**Ready to implement?** Start with Phase 1 and build incrementally! 🚀

