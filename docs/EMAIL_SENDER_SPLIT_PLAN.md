# Splitting the Email Sender out of Lead Extractor Pro

**Status:** Locked — extractor Phase 0/1 (port-sync, native window, clear errors) is being implemented now. Sender split (Phase 2 onwards) starts after the extractor is stabilised.
**Goal:** Lead Extractor Pro becomes one focused product (extract leads). The Email Sender becomes a **second, independent product** called **Grand Mailer**, with its own license, installer, and pricing. Each can be sold and supported separately.

---

## 1. Why split?

| Reason | What it gains us |
|--------|------------------|
| **Clear product story** | "Lead Extractor = find / extract." "Grand Mailer = send / track." Two simple promises instead of one bloated app. |
| **Independent pricing** | Two SKUs. A user can buy Extractor only, Sender only, or both as a bundle. Bigger total addressable market and higher ARPU on heavy senders. |
| **Smaller blast radius** | A Streamlit/UI bug or DB migration in the email module never breaks the extractor (and vice versa). Shorter QA cycles. |
| **Compliance & risk isolation** | Sending mail has its own legal/abuse profile (CAN-SPAM, GDPR, AWS SES suppression, ISP throttling). Keeping it isolated makes it easier to apply email-specific guardrails, and lets us refuse Email-Sender refunds/abuse without touching extractor users. |
| **Easier support** | Logs, errors, and updates can be answered per product. "Extraction broken" and "SMTP/SES broken" are different tickets owned by different code. |
| **Independent release cadence** | We can iterate Sender features (templates, suppression, A/B) without re-shipping the extractor binary. |

---

## 2. What is being split (current footprint)

Inside the existing repo, the email sender already lives in well-defined places. That's what we cut out.

### Code

- `app/email/__init__.py`
- `app/email/email_ui.py`                  ← Streamlit page rendered as **"📧 Email Sender"** in `app/main.py`
- `app/email/credential_manager.py`        ← keyring-based secret storage
- `app/email/mailbox_pool.py`              ← multi-mailbox rotation
- `app/email/mailbox_validation.py`
- `app/email/rate_limiter.py`
- `app/email/smtp_pool.py`
- `app/email/smtp_tls.py`
- `app/email/phase1_test.py`
- `app/email/providers/__init__.py`
- `app/email/providers/base_provider.py`
- `app/email/providers/ses_provider.py`    ← AWS SES integration

### Database tables (currently in `data/leads.db`)

- `mailboxes`
- `email_campaigns`
- `email_queue`

Created in `app/database/db.py` (`init_db`) alongside `searches` / `leads`. After the split these belong to the **Sender** product's database, not the Extractor's.

### Lead Extractor wiring to remove

- `app/main.py`: `from app.email.email_ui import render_email_sender_page`
- `app/main.py`: nav entry **"📧 Email Sender"** in `NAV_OPTIONS`
- `requirements.txt`: SES / SMTP dependencies that are unused by the extractor (`boto3`, possibly `email-validator` if no other extractor code needs it — verify before pruning)
- Build spec (`LeadExtractorPro_windows.spec`): no longer collect `boto3`, `app.email`, `email_validator` — produces a smaller binary

### Lead Extractor → Sender bridge that stays

The extractor will continue to export leads (CSV/Excel/PDF). The Sender will accept those files as input. **No live database link** between the two apps.

---

## 3. Proposed product names and identifiers

| Item | Lead Extractor (existing) | Grand Mailer (new) |
|------|---------------------------|--------------------|
| Product name | Lead Extractor Pro | **Grand Mailer** |
| Windows binary | `LeadExtractorPro.exe` | `GrandMailer.exe` |
| User data dir | `%APPDATA%\LeadExtractorPro\` | `%APPDATA%\GrandMailer\` |
| Database | `leads.db` | `mail.db` |
| Default UI port | 8501 (random fallback) | 8502 (random fallback) |
| Default API port | 8000 (random fallback) | 8003 (random fallback) |
| License secret (HMAC) | existing extractor secret | **new, independent secret** |
| License keys | only valid for Extractor | only valid for Grand Mailer |
| Vendor brand (umbrella) | "Grand Suite" *(placeholder — confirm before public launch)* | same |

> Two independent secrets means a leaked Extractor key cannot unlock the Mailer, and pricing/durations can diverge.

---

## 4. Target architecture (after split, per Windows machine)

```
┌──────────────────────────────────────────────────────────────────┐
│  Windows PC                                                      │
│                                                                  │
│  ┌──────────────────────────┐      ┌──────────────────────────┐  │
│  │  Lead Extractor Pro      │      │  Grand Mailer            │  │
│  │  (existing)              │      │  (new)                   │  │
│  │                          │      │                          │  │
│  │  WebView window          │      │  WebView window          │  │
│  │  Streamlit UI 8501       │      │  Streamlit UI 8502       │  │
│  │  FastAPI    8000         │      │  FastAPI    8003 (opt.)  │  │
│  │  Playwright (extract)    │      │  SMTP / SES (send)       │  │
│  │  leads.db                │      │  mail.db                 │  │
│  │                          │      │                          │  │
│  │  Export CSV/Excel ──────────────►  Import CSV              │  │
│  └──────────────────────────┘      └──────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

Two separate processes. Two separate installers. They are aware of each other only through **CSV files on disk**, not shared databases or shared sockets.

---

## 5. New repository layout (for Grand Mailer)

```
grand-mailer/
  app/
    __init__.py
    config.py                  # mail.db path, ports, license secret (NEW)
    main.py                    # Streamlit UI: dashboard, mailboxes, campaigns
    database/
      __init__.py
      db.py                    # mailboxes, email_campaigns, email_queue only
    email/                     # copied from current app/email/
      __init__.py
      mailbox_pool.py
      mailbox_validation.py
      rate_limiter.py
      smtp_pool.py
      smtp_tls.py
      credential_manager.py
      providers/
    license/                   # cloned from extractor, NEW secret
      __init__.py
      generator.py
      validator.py
      machine_id.py
      activation_ui.py
    server/
      __init__.py
      sender_worker.py         # background loop that drains email_queue
    importers/
      __init__.py
      csv_importer.py          # accepts Lead Extractor exports
  data/                        # mail.db lives here in dev mode
  exports/
  docs/
    README.md
    SETUP.md
  requirements.txt
  launch_app_windows.py
  GrandMailer_windows.spec
  build_windows.bat
  package_windows.bat
```

The license, launcher, and build files start as **adapted copies** of the extractor's, not branches of the same codebase. Two separate Git repos make pricing/release/branding cleaner.

---

## 6. Bridge between the two apps

The two apps must work well together without being coupled.

| Direction | How it works |
|-----------|--------------|
| **Extractor → Grand Mailer** | User clicks "Export → CSV" in Lead Extractor as today. In Grand Mailer, the **Import CSV** screen accepts the same file (recognises `email`, `contact_name`, `phone`, `business_name`, `source_url`). |
| **Grand Mailer → Extractor** | None at v1. Suppression / bounces stay inside Grand Mailer. |
| **Single-machine UX (v2, not v1)** | Deep-link handler `grand-mailer://import?path=...` is **deferred** to v2. v1 ships **manual CSV import only** to keep scope tight. |

**Schema for the export bridge** (already implicit in current exporter, document it in both products):

```
email,contact_name,phone,business_name,source_url,snippet,search_query
```

---

## 7. Migration plan for **existing** users

Some early customers have been using the bundled email sender. They must not lose their mailboxes / campaigns when we ship the split.

1. **Last bundled release**, mark in changelog: *"Email Sender will move to a separate app; data stays where it is."*
2. **Grand Mailer v1.0** ships with a one-click migration:
   - Detects `%APPDATA%\LeadExtractorPro\leads.db`.
   - Copies `mailboxes`, `email_campaigns`, `email_queue` rows into `%APPDATA%\GrandMailer\mail.db`.
   - Leaves the extractor DB untouched (extractor v_next will simply stop reading those tables).
3. **Lead Extractor v_next** removes the email UI tab, drops the `boto3` and `email-validator` imports it doesn't need, but keeps the tables in place for one more minor release in case rollback is needed.
4. After two minor releases, an extractor cleanup migration drops the unused tables.
5. **Communication**: short email to active customers explaining: "your extraction app is the same, the email feature now lives here, click to download."
6. **Grandfathering window (locked):** customers who bought the bundled app within the **12 months** before the split get a free Grand Mailer key valid for the **same expiry date** as their existing extractor license. After that window, Grand Mailer is paid-only. We can revisit this number once we know how many active bundled customers we have on launch day.

---

## 8. Pricing model after the split (placeholder — these are *fake* anchor numbers, real prices will come after we have 5–10 paying users)

| Plan | Lead Extractor Pro | Grand Mailer | Bundle |
|------|--------------------|--------------|--------|
| **Solo** | $39 / mo | $29 / mo | $59 / mo |
| **Team** (up to 5 seats) | $129 / mo | $99 / mo | $199 / mo |
| **Business** (up to 10) | $399 / mo | $299 / mo | $599 / mo |
| **Enterprise / larger teams** | custom | custom | custom (anchor $999+/mo) |

> These prices are **placeholders for the marketing site / pricing page mock-up only**. They are not on any invoice yet. We will validate them with the first paying users before locking.

The bundle is the upsell. Each product still works alone, so we can sell to extractor-only buyers (researchers, lead-gen agencies who already have their own mail stack) and Grand-Mailer-only buyers (people who already have lists and just need a high-volume sender).

License keys remain **per-machine** as today; team / enterprise tiers will be addressed in a later phase.

---

## 9. Phased delivery (so the split is low risk)

### Phase 0 — Decide & document (this doc) ✅ DONE
- Product name **Grand Mailer** locked. Ports, data dirs, secrets locked.
- v1 of Grand Mailer is **CSV import only**, no live DB link, no deep-link handler.

### Phase 1 — Stabilise extractor with email still bundled (in progress)
- **Port-sync + clear-error work** + native PyWebview window for Windows ships first (current work).
- Confirms the extractor is rock-solid before we cut anything out.

### Phase 2 — Stand up the Grand Mailer repo
- Create `grand-mailer/` (new repo).
- Copy `app/email/` into it.
- Add own `config.py`, `database/db.py` (mail tables only), `license/`, `launch_app_windows.py`, spec, batch files.
- Add **Import CSV** screen.
- Build a Windows EXE end-to-end. Verify SMTP and SES from scratch.

### Phase 3 — Cut email out of the extractor
- Remove `app/email/`, `from app.email...` imports, the `📧 Email Sender` nav entry.
- Drop unused deps (`boto3`, etc.) from `requirements.txt` and the spec.
- Bump extractor version, ship.

### Phase 4 — Migration helper in Grand Mailer v1
- On first launch, detect old extractor DB and offer to copy the email tables over.

### Phase 5 — Cross-promo
- "Need to email these leads? Get Grand Mailer" inside the extractor's export screen.
- "Need more leads? Get Lead Extractor Pro" inside Grand Mailer's import screen.

Each phase is shippable on its own and reversible.

---

## 10. Risks and how we handle them

| Risk | Mitigation |
|------|------------|
| Existing customers who bought the bundled app feel it was taken away | Ship the Mailer **before** removing it from the extractor; honour current licenses with a free Mailer key for impacted users for a defined window. |
| Migration corrupts data | Migration only **reads** the extractor DB and **writes** to a fresh `mail.db`. Never modifies `leads.db`. Backup before copy. |
| Two binaries fighting over ports | Ports are different by default (8501/8000 vs 8502/8003) and each launcher chooses a free port if its default is taken. |
| Two licenses to manage | Use the same admin generator pattern, two scripts, two secrets. Document clearly which key goes into which app. |
| Anti-spam / SES suspension | This is now isolated to the Mailer product, which is exactly the point. We can add stricter guardrails (suppression list, opt-out footer, throttle) without touching the extractor. |

---

## 11. Decisions log (locked for now, all reversible before Phase 2 ships)

| Question | Locked answer | Notes |
|----------|---------------|-------|
| 1. Final product name for the email app | **Grand Mailer** | Binary `GrandMailer.exe`, AppData `%APPDATA%\GrandMailer\`. |
| 2. License grandfathering window | **12 months** before split date | Affected customers get a free Grand Mailer key valid until their existing extractor key expires. |
| 3. Pricing | §8 numbers used as **placeholder anchors** for the pricing page only | Real prices set after first 5–10 paying users; bundle stays the upsell. |
| 4. Bridge handler | **Manual CSV import only in v1.** | Deep-link `grand-mailer://import?path=...` deferred to v2. |
| 5. Vendor / umbrella brand | Working name **"Grand Suite"** *(placeholder)* | Confirm before we publish either product's marketing site. Has no impact on the technical split. |

These are written down so we don't re-debate them mid-implementation. They can be changed later — the only one that's expensive to change after Phase 2 ships is the product name (binary path, AppData folder, license-secret rotation), so that one is the most "real" decision in the table.
