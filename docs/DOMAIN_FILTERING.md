# Domain filtering (search + email)

## Why two layers?

| Layer | What it does | Best for |
|--------|----------------|----------|
| **Restrict search to websites** | Appends `(site:example.org OR site:other.gov)` to every query sent to Google/DuckDuckGo. | PDFs hosted on specific domains (government, a single university, etc.). |
| **Email domain allowlist (live)** | After extraction, drops rows where **no** address in the email field matches your rules. | “Only @gmail.com”, “only .edu”, “only our company”, even if the PDF is hosted elsewhere. |
| **Email domain filter (export)** | Same matching rules, applied in the UI when merging sessions for CSV/Excel. | Narrowing a run that already finished without re-scraping. |

Search engines cannot express “only @yahoo.com addresses” in the query. Use the **email allowlist** for mailbox domains.

## Syntax (one entry per line; commas OK)

- `company.com` — matches `user@company.com` and `user@mail.company.com`.
- `@company.com` — same as above.
- `*.edu` or `.edu` — matches any host ending in `.edu` (e.g. `x@utexas.edu`, `y@law.harvard.edu`).

Lines starting with `#` are comments.

## `site:` restriction details

- Use **registrable** hostnames: `state.gov`, `redcross.org`.  
- **`*.edu` is not used** for `site:` (not valid in search operators). Use concrete sites, or rely on the email allowlist for “any .edu address”.
- Overly narrow `site:` + niche keywords may return **zero** results — relax keywords or remove some sites.

### Search / social portals (auto-skipped)

Putting **`google.com`**, **`facebook.com`**, **`bing.com`**, **`duckduckgo.com`**, etc. in “Restrict search to websites” is almost always wrong: the `site:` operator limits results to **pages hosted on that domain**, not “use Google to search.” That often yields **no PDF hits**. The app **drops** known portal domains from the `site:` clause and logs why; leave the box empty for a normal broad search, or list real document hosts (`.gov`, a company’s public file server, a university site).

### Reddit (`site:reddit.com` / `redd.it`)

Reddit threads are **HTML**, not PDFs. The default DuckDuckGo path adds **`filetype:pdf`** and only followed **`.pdf`** links, so **`site:reddit.com` looked like “no results.”** When **every** site you list is Reddit-only (e.g. just `reddit.com` or `redd.it`), the app **does not** add `filetype:pdf`, follows Reddit result URLs, and extracts emails/phones/names from the **page text** (best effort; Reddit may block some automated fetches). If you mix Reddit with a PDF host (e.g. `reddit.com` + `state.gov`), the run stays in **PDF mode** for all queries.

## Implementation

- Rules parser & matching: `app/filters/email_domain_rules.py`
- Export / merge pipeline: `filter_merged_leads_for_export(..., email_domain_allowlist=...)` in `app/export/exporter.py`
- Live automation: `app/server/automation_server.py` (`run_automation` + WebSocket `start` payload)
