# ✅ Quick Answer: AWS SES Setup

## Do You Need a New AWS Account?

**❌ NO!** Use your **existing AWS account**.

Just add SES service to your current account - no new account needed!

---

## Cost Breakdown

### Free Tier (First 12 Months)
- **3,000 emails/month** = **FREE** ✅
- **62,000 emails/month** = **FREE** (if receiving to verified addresses)

### After Free Tier
- **$0.10 per 1,000 emails** sent
- **No monthly fees** - pay only for what you use!

### Real Examples:
```
10,000 emails/month  = $1.00/month
30,000 emails/month  = $3.00/month  
100,000 emails/month = $10.00/month
300,000 emails/month = $30.00/month
```

**Very cheap!** Compare to SendGrid ($89.95/month for 100k) or Mailgun ($35/month for 50k).

---

## Quick Setup Steps (30 Minutes)

### 1. Log into AWS Console
- Use your **existing AWS account**
- Go to https://aws.amazon.com/console/

### 2. Enable SES
- Search for "SES" in AWS Console
- Click "Amazon SES"
- Choose region (e.g., `us-east-1`)

### 3. Verify Email (Quick Test)
- Click "Verified identities" → "Create identity"
- Select "Email address"
- Enter your email
- Click verification link in email
- ✅ Done!

**Note:** In sandbox mode, you can only send to verified emails.

### 4. Get API Keys
- Go to **IAM** → **Users** → **Create user**
- Name: `lead-extractor-ses`
- Attach policy: `AmazonSESFullAccess`
- Create user → **Security credentials** → **Create access key**
- **Save:** Access Key ID + Secret Key

### 5. Request Production Access (Remove Sandbox)
- In SES Console → **Account dashboard**
- Click **"Request production access"**
- Fill form (explain you're sending to leads)
- Submit
- **Wait 24-48 hours** for approval

**After approval:** Can send to ANY email address!

### 6. Add to Lead Extractor
- Go to **📧 Sender** → **📬 Mailboxes**
- Click **➕ Add New Mailbox**
- Select **Provider:** `aws_ses`
- Fill in:
  - Name: "AWS SES"
  - Email: Your verified email
  - AWS Access Key ID: (from step 4)
  - AWS Secret Key: (from step 4)
  - AWS Region: `us-east-1`
- Click **➕ Add Mailbox**
- ✅ Done!

---

## Total Time & Cost

**Setup Time:** 
- Active work: **30 minutes**
- Waiting (DNS/production approval): **24-48 hours**

**Cost:**
- **$0** for first 3,000 emails/month (12 months)
- **$0.10 per 1,000 emails** after that
- **No monthly fees**

**Example:** 30,000 emails/month = **$3/month** 🎉

---

## Full Guide

See `AWS_SES_SETUP_GUIDE.md` for detailed step-by-step instructions with screenshots and troubleshooting.

---

## Summary

✅ **Use existing AWS account** - no new account needed!  
✅ **Very cheap** - $0.10 per 1,000 emails  
✅ **Single account** - no juggling multiple accounts  
✅ **30 minutes setup** - then wait for production approval  
✅ **Scalable** - start free, scale to millions  

**Ready to set up?** Follow the steps above! 🚀
