# 🚀 AWS SES Setup Guide: Step-by-Step

## ✅ Good News: Use Your Existing AWS Account!

**You don't need a new AWS account!** Just add SES to your existing account.

---

## 💰 Cost Breakdown (Very Cheap!)

### Free Tier (First 12 Months)
- **3,000 emails/month** = **FREE**
- **62,000 emails/month** = **FREE** (if receiving emails to verified addresses)

### After Free Tier
- **$0.10 per 1,000 emails** sent
- **$0.12 per GB** of attachments
- **No monthly fees** - pay only for what you use!

### Real-World Examples:
```
10,000 emails/month  = $1.00/month
30,000 emails/month  = $3.00/month
100,000 emails/month = $10.00/month
300,000 emails/month = $30.00/month
```

**Compare to:**
- SendGrid: $89.95/month for 100k emails
- Mailgun: $35/month for 50k emails

**AWS SES is 3-9x cheaper!** 🎉

---

## 📋 Step-by-Step Setup

### Step 1: Log into AWS Console

1. Go to https://aws.amazon.com/
2. Click **"Sign In to the Console"**
3. Use your **existing AWS account** credentials
4. If you don't have an account, create one (free, just need email + credit card)

**Note:** AWS account is free. You only pay for services you use.

---

### Step 2: Navigate to SES

1. In AWS Console, search for **"SES"** in the top search bar
2. Click **"Amazon SES"** (Simple Email Service)
3. Make sure you're in the right region (e.g., **US East (N. Virginia)** - `us-east-1`)

**Why Region Matters:**
- Choose region closest to you
- Popular: `us-east-1`, `us-west-2`, `eu-west-1`
- Can't change region later (need to create new identity)

---

### Step 3: Verify Your Email Address (Quick Start)

**For Testing (Sandbox Mode):**

1. In SES Console, click **"Verified identities"** in left sidebar
2. Click **"Create identity"**
3. Select **"Email address"**
4. Enter your email (e.g., `yourname@gmail.com`)
5. Click **"Create identity"**
6. **Check your email** - AWS sends verification email
7. **Click verification link** in email
8. ✅ Email verified!

**Limitation:** In sandbox mode, you can **only send to verified email addresses**.

**To send to ANY email:** Need to request production access (Step 6).

---

### Step 4: Verify Your Domain (Recommended for Production)

**Why Verify Domain?**
- ✅ Send from `yourname@yourdomain.com` (professional)
- ✅ Better deliverability
- ✅ Required for production access
- ✅ Can send to any email address (after production approval)

**Steps:**

1. **Have a domain?** (e.g., `yourdomain.com`)
   - If not, buy one (~$10-15/year from Namecheap, GoDaddy, etc.)

2. In SES Console → **"Verified identities"** → **"Create identity"**
3. Select **"Domain"**
4. Enter your domain (e.g., `yourdomain.com`)
5. Click **"Create identity"**

6. **Add DNS Records** (AWS shows you exactly what to add):
   - **SPF Record**: `v=spf1 include:amazonses.com ~all`
   - **DKIM Records**: 3 CNAME records (AWS provides exact values)
   - **DMARC Record** (optional but recommended)

7. **Add records to your domain DNS:**
   - Go to your domain registrar (Namecheap, GoDaddy, etc.)
   - Find DNS management
   - Add the records AWS provided
   - **Wait 24-48 hours** for DNS propagation

8. **Check verification status** in SES Console
   - Status changes to **"Verified"** when DNS records propagate

---

### Step 5: Create IAM User & Access Keys

**Why?** Need API keys to use SES from Lead Extractor.

**Steps:**

1. In AWS Console, search for **"IAM"**
2. Click **"IAM"** → **"Users"** in left sidebar
3. Click **"Create user"**
4. Enter username: `lead-extractor-ses` (or any name)
5. Click **"Next"**
6. **Attach policies:**
   - Search for: `AmazonSESFullAccess`
   - Check the box
   - Click **"Next"**
7. Click **"Create user"**

8. **Get Access Keys:**
   - Click on the user you just created
   - Go to **"Security credentials"** tab
   - Click **"Create access key"**
   - Select **"Application running outside AWS"**
   - Click **"Next"**
   - Click **"Create access key"**
   - **IMPORTANT:** Copy both:
     - **Access Key ID** (starts with `AKIA...`)
     - **Secret Access Key** (long string - only shown once!)
   - **Save these securely!** You'll need them in Lead Extractor.

---

### Step 6: Request Production Access (Remove Sandbox Limits)

**Current Status:** Sandbox mode
- ✅ Can send to verified email addresses
- ❌ Cannot send to unverified emails
- ❌ Limited to 200 emails/day, 1 email/second

**After Production Access:**
- ✅ Can send to ANY email address
- ✅ Higher sending limits (request increases as needed)
- ✅ Production-ready

**Steps:**

1. In SES Console, click **"Account dashboard"** in left sidebar
2. Scroll to **"Sending limits"**
3. Click **"Request production access"**
4. **Fill out the form:**
   - **Mail Type:** Select "Transactional" or "Marketing" (or both)
   - **Website URL:** Your website (or Lead Extractor URL)
   - **Use case description:** 
     ```
     We use Amazon SES to send transactional and marketing emails 
     to leads extracted from our lead generation system. We follow 
     CAN-SPAM compliance, include unsubscribe links, and maintain 
     clean email lists.
     ```
   - **Compliance:** Check boxes for:
     - ✅ "I will remove recipients who submit spam complaints"
     - ✅ "I will remove recipients who submit unsubscribe requests"
     - ✅ "I will only send emails to recipients who have opted in"
   - **Expected sending volume:** 
     - Start: `10,000 emails/month`
     - After 3 months: `50,000 emails/month`
     - After 6 months: `100,000 emails/month`
5. Click **"Submit"**

**Approval Time:**
- Usually **24-48 hours**
- Sometimes instant if domain verified
- AWS reviews your use case

**While Waiting:**
- You can still test with verified email addresses
- Set up Lead Extractor integration
- Test with small volumes

---

### Step 7: Add SES to Lead Extractor

**In Lead Extractor UI:**

1. Go to **📧 Sender** tab
2. Click **📬 Mailboxes** tab
3. Click **➕ Add New Mailbox**
4. Select **Provider:** `aws_ses`
5. Fill in:
   - **Name:** "AWS SES Production"
   - **Email:** Your verified email (e.g., `yourname@yourdomain.com`)
   - **AWS Access Key ID:** (from Step 5)
   - **AWS Secret Key:** (from Step 5)
   - **AWS Region:** `us-east-1` (or your chosen region)
   - **Daily Limit:** System will auto-detect from AWS quota
6. Click **➕ Add Mailbox**
7. **Test Connection** - Should show ✅

**Done!** You can now send emails via AWS SES!

---

## 🔧 Advanced: Increase Sending Limits

**After Production Access:**

If you need to send more than default limits:

1. In SES Console → **"Account dashboard"**
2. Scroll to **"Sending limits"**
3. Click **"Request limit increase"**
4. Fill out:
   - **Desired daily sending quota:** e.g., `100,000`
   - **Maximum send rate:** e.g., `14 emails/second` (for 100k/day)
   - **Use case:** Explain why you need higher limits
5. Submit request

**AWS usually approves reasonable requests quickly.**

---

## 📊 Monitoring & Analytics

**In SES Console:**

1. **"Sending statistics"** - See delivery rates, bounces, complaints
2. **"Reputation metrics"** - Track spam complaint rates
3. **"Configuration sets"** - Set up event tracking (bounces, opens, clicks)

**Best Practices:**
- Keep **bounce rate < 5%**
- Keep **complaint rate < 0.1%**
- Monitor daily sending volume
- Remove bounced/complained emails from lists

---

## 🚨 Important Notes

### Sandbox Mode Limitations:
- ❌ Can only send to verified email addresses
- ❌ Limited to 200 emails/day
- ❌ Limited to 1 email/second

### Production Mode Benefits:
- ✅ Can send to any email address
- ✅ Higher limits (request increases)
- ✅ Production-ready

### Cost Optimization:
- **Free tier:** 3,000 emails/month free (first 12 months)
- **After free tier:** $0.10 per 1,000 emails
- **No monthly fees** - pay only for what you use
- **Attachments:** $0.12 per GB (only if sending attachments)

### Security:
- ✅ **Never commit API keys to git!**
- ✅ Store keys encrypted (we use `credential_manager.py`)
- ✅ Use IAM user (not root account)
- ✅ Rotate keys periodically

---

## ✅ Quick Checklist

- [ ] Log into AWS Console (existing account)
- [ ] Navigate to SES
- [ ] Verify email address (for testing)
- [ ] Verify domain (for production) - optional but recommended
- [ ] Create IAM user with SES permissions
- [ ] Get Access Key ID + Secret Key
- [ ] Request production access
- [ ] Add SES to Lead Extractor
- [ ] Test sending
- [ ] Monitor statistics

---

## 🎯 Summary

**Do you need a new AWS account?** ❌ **NO** - Use existing account!

**Cost:** 
- First 3,000 emails/month: **FREE** (12 months)
- After: **$0.10 per 1,000 emails**
- Example: 30,000 emails/month = **$3/month**

**Setup Time:** 
- Basic setup: **30 minutes**
- Domain verification: **+24-48 hours** (DNS propagation)
- Production access: **+24-48 hours** (AWS approval)

**Total:** **~1-2 hours active work** + waiting for DNS/approval

---

## 🆘 Troubleshooting

### "Access Denied" Error:
- Check IAM user has `AmazonSESFullAccess` policy
- Verify Access Key ID and Secret Key are correct

### "Email address not verified":
- You're in sandbox mode
- Either verify recipient email OR request production access

### "Sending quota exceeded":
- You've hit daily limit
- Request limit increase in SES Console

### "Domain not verified":
- Check DNS records are correct
- Wait 24-48 hours for DNS propagation
- Use DNS checker tools to verify records

---

**Ready to set up?** Follow the steps above, and you'll have AWS SES working in Lead Extractor in about 1-2 hours! 🚀
