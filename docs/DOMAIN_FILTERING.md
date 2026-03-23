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

## Implementation

- Rules parser & matching: `app/filters/email_domain_rules.py`
- Export / merge pipeline: `filter_merged_leads_for_export(..., email_domain_allowlist=...)` in `app/export/exporter.py`
- Live automation: `app/server/automation_server.py` (`run_automation` + WebSocket `start` payload)
