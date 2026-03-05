# Deploy Lead Extractor Pro — Step by Step

From GitHub to Render + Neon.

---

## Step 1: Push Your Code to GitHub

If the project is not on GitHub yet:

```bash
cd /Users/mikeolab/lead-extractor

# Initialize git (if needed)
git init

# Add all files
git add .
git commit -m "Ready for deployment"

# Create repo on GitHub (github.com → New repository), then:
git remote add origin https://github.com/YOUR_USERNAME/lead-extractor.git
git branch -M main
git push -u origin main
```

If already on GitHub, just ensure latest changes are pushed:

```bash
git add .
git commit -m "Latest changes"
git push
```

---

## Step 2: Create Neon Database (Free)

1. Go to **https://neon.tech** and sign in (free tier).
2. Click **New Project**.
3. Name it (e.g. `lead-extractor-pro`).
4. Region: choose one near your users (e.g. `us-east-1`).
5. Click **Create project**.
6. On the project dashboard, open **Connection string**.
7. Copy the connection string (e.g. `postgresql://user:pass@ep-xxx.us-east-1.aws.neon.tech/neondb?sslmode=require`).

Keep this string handy for Step 4.

---

## Step 3: Create Render Account & Connect GitHub

1. Go to **https://render.com** and sign up (or log in).
2. Connect your GitHub account if not already:
   - **Account Settings** → **GitHub** → **Connect**.

---

## Step 4: Deploy on Render

### Option A: Use Blueprint (if `render.yaml` exists)

1. **Dashboard** → **New** → **Blueprint**.
2. Connect the `lead-extractor` repo.
3. Render will detect `render.yaml` and create the service.
4. Skip to **Step 5** to add environment variables.

### Option B: Manual Web Service

1. **Dashboard** → **New** → **Web Service**.
2. Connect repository: select your `lead-extractor` repo.
3. Configure:
   - **Name:** `lead-extractor-pro` (or similar)
   - **Region:** Same region as Neon if possible
   - **Branch:** `main`
   - **Runtime:** **Docker**
   - **Plan:** **Free** (or Starter $7/mo for better reliability)

4. **Build & Deploy** (leave default):
   - Build command: *(leave empty — Dockerfile handles it)*
   - Start command: *(leave empty — Dockerfile CMD runs it)*

5. Click **Create Web Service**.

---

## Step 5: Add Environment Variables

In the Render service → **Environment** tab, add:

| Key | Value | Notes |
|-----|-------|------|
| `DATABASE_URL` | `postgresql://...` | Paste full Neon connection string from Step 2 |
| `AUTOMATION_SERVER_URL` | `http://localhost:8000` | Same container; API runs on 8000 |
| `GOOGLE_API_KEY` | *(if you use Google Search)* | Optional |
| `GOOGLE_CSE_ID` | *(if you use Google Search)* | Optional |
| `LICENSE_KEY` | *(if using license checks)* | Optional |

**Important:** For `DATABASE_URL`, use the full Neon URL (including `?sslmode=require` if present).

---

## Step 6: First Deploy

1. After adding env vars, Render will trigger a new deploy.
2. Or: **Manual Deploy** → **Deploy latest commit**.
3. Wait 5–15 minutes (first build with Playwright can be slow).
4. Check the **Logs** tab for progress and errors.

---

## Step 7: Get Your URL

When the deploy succeeds:

- URL: `https://lead-extractor-pro-xxxx.onrender.com` (or similar)
- Share this link with users.

---

## Step 8: Verify

1. Open the URL in a browser.
2. License activation should appear if required.
3. Live Extractor and Saved Leads should load.
4. If Playwright/Chromium fails (e.g. on free tier), consider upgrading to **Starter ($7/mo)**.

---

## Troubleshooting

| Issue | Fix |
|------|-----|
| Build fails on `playwright install` | Check Dockerfile; ensure all system deps are listed. |
| Out of memory (OOM) | Upgrade to Starter plan (512MB → 2GB+). |
| Database errors | Confirm `DATABASE_URL` is set and correct; check Neon dashboard. |
| Service sleeps after 15 min | Free tier behavior; upgrade to paid for always-on. |
| WebSocket / automation not working | Ensure `AUTOMATION_SERVER_URL` is `http://localhost:8000` when running in one container. |

---

## Pre-deploy checklist

- [ ] Code pushed to GitHub
- [ ] Neon project created, connection string copied
- [ ] Render account connected to GitHub
- [ ] `DATABASE_URL` set in Render env vars (Neon connection string)
- [ ] `psycopg2-binary` in `requirements.txt` (for Neon/PostgreSQL)

---

## Quick Reference

```
GitHub (repo) → Render (web service) → Neon (database)
     ↓                  ↓                      ↓
  Source code      Streamlit + API        Persistent data
```

| Step | Action |
|------|--------|
| 1 | Push code to GitHub |
| 2 | Create Neon project, copy connection string |
| 3 | Sign up / log in to Render, connect GitHub |
| 4 | New Web Service → Docker → select repo |
| 5 | Add `DATABASE_URL` and other env vars |
| 6 | Deploy and wait |
| 7 | Use the Render URL |

---

## After Deployment

- **Updates:** Push to `main`; Render auto-deploys.
- **Logs:** Render Dashboard → your service → **Logs**.
- **Scaling:** Plan → Starter or higher for production use.
