# Render + Neon — Can It Handle Lead Extractor Pro?

## Summary: **Yes, with one caveat**

| Question | Answer |
|----------|--------|
| Can Render run Playwright/Chromium? | **Yes** — Docker with Playwright works. Render has Browser-Use template proof. |
| Can we use Neon for database? | **Yes** — Neon + Render is a documented pattern. Same as your other app. |
| Will free tier work? | **Risky** — 512MB RAM. Chromium headless ≈ 690MB. May OOM. |
| Will paid tier work? | **Yes** — Starter ($7/mo) has more RAM. Should run fine. |

---

## Memory reality

- **Render free tier:** 512MB RAM
- **Chromium headless:** ~690MB minimum
- **Streamlit + FastAPI + Python:** ~150–250MB

**Total:** ~850MB+ — exceeds free tier.

---

## Recommendation

### Option A: Try free tier first (worth a shot)

- Deploy as-is.
- Add Chromium memory flags to shrink usage.
- If it OOMs, upgrade to Starter ($7/mo).

### Option B: Start on Starter ($7/mo)

- Same setup as your other app.
- More reliable from day one.
- Pay when you’re ready to scale.

---

## Neon integration

Same pattern as your other app:

1. Create a Neon project (or reuse one).
2. Copy the connection string.
3. Add `DATABASE_URL` in Render env vars.
4. App uses PostgreSQL when `DATABASE_URL` is set; SQLite for local dev.

---

## Bottom line

**Render + Neon works.**  
- **Free:** Possible but may hit memory limits; try it first.  
- **Starter ($7/mo):** Reliable and consistent with your other app.
