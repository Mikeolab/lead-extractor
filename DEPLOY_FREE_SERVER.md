# Deploy to Free Server — Users Test via URL

No installation. Users open a link in their browser.

---

## Option 1: Render.com (Recommended — Free Tier)

### One-time setup

1. Create account at **https://render.com** (free)
2. Connect your GitHub (or push project to GitHub first)
3. **New** → **Web Service**
4. Connect repo → select `lead-extractor`
5. Settings:
   - **Runtime:** Docker
   - **Plan:** Free
   - **Build Command:** (leave empty — uses Dockerfile)
   - **Start Command:** (leave empty)

6. Click **Create Web Service**

Wait 5–10 minutes for the first deploy. You’ll get a URL like:

**https://lead-extractor-pro-xxxx.onrender.com**

Share that link. Users open it and use the app.

### Notes

- Free tier sleeps after ~15 minutes of no traffic; first load after sleep can take ~1 minute.
- When you scale, switch to a paid plan (~$7/mo) for no sleep and better performance.

---

## Option 2: Streamlit Community Cloud

Simpler, but **browser automation (Playwright) may not work** in the free sandbox.

1. Push project to **GitHub**
2. Go to **https://share.streamlit.io**
3. Sign in with GitHub
4. **New app** → Select repo `lead-extractor`, file `app/main.py`
5. Deploy

You’ll get: **https://yourapp.streamlit.app**

If the automation server does not start or Playwright fails, use Render instead.

---

## Option 3: Railway.app

1. Go to **https://railway.app**
2. **New Project** → **Deploy from GitHub**
3. Select repo, Railway will detect the Dockerfile
4. Add a domain (free `.railway.app` subdomain)

---

## Env vars (optional)

Add these in your hosting dashboard if needed:

| Variable | Description |
|----------|-------------|
| `GOOGLE_API_KEY` | For Google Custom Search (if used) |
| `GOOGLE_CSE_ID` | For Google Custom Search |
| `LICENSE_KEY` | License key for the app |

---

## Summary

| Platform | Free? | Setup | Notes |
|----------|-------|--------|------|
| **Render** | Yes | Docker, ~10 min | Recommended; Playwright should work |
| **Streamlit Cloud** | Yes | Connect GitHub | Quick; automation may be limited |
| **Railway** | $5 credit/mo | Docker | Good if you want another host |

---

## After deploying

- Share the URL with users
- No install, no CMD, no Python
- When traffic grows, switch to a paid plan (e.g. Render ~$7/mo)
