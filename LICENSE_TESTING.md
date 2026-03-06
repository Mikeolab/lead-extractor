# License testing and how to create keys

## Quick test license (for the deployed app)

Use a **single key with no machine binding** so it works in the browser (Render):

```bash
cd /Users/mikeolab/lead-extractor
python generate_license.py --name "Test User" --plan pro --days 365
```

Copy the printed license key and paste it into the activation screen on `https://lead-extractor-xxxx.onrender.com`.  
**One license = one active session:** if you open the same app in another browser or incognito and enter the same key, you’ll get “This license is already in use on another device or browser.”

---

## One license per user (recommended)

- **Create one license per user** (or per seat) with your admin script.
- **Desktop (bound to one PC):** use the admin script with the user’s Hardware ID so the key only works on that machine:
  ```bash
  python generate_license_admin.py --name "Jane Doe" --machine-id "70998ed59f0f1577" --plan pro --days 365
  ```
- **Web (deployed app):** use a key **without** `--machine-id` (e.g. `generate_license.py` above). The same key can only be used in **one browser session at a time** (single-session lock).

---

## Optional: list of licenses

To create many keys at once (e.g. for a list of users), you can:

1. Use a small loop or script that calls `generate_license_key()` from `app.license.generator` with different `licensee_name` (and optional `machine_id`), and write the keys to a CSV or file.
2. Or run `generate_license.py` (or `generate_license_admin.py`) once per user and collect the printed keys.

**Best practice:** keep a list of (licensee_name, license_key, plan, expires_at) in your own records; don’t commit license keys to the repo.

---

## Summary

| Use case              | Script / approach                    | Binding              |
|-----------------------|--------------------------------------|----------------------|
| Test deployed (Render)| `generate_license.py --name "Test"` | None (web, 1 session)|
| Desktop user          | `generate_license_admin.py --machine-id XXX` | One machine   |
| Web user (per seat)   | `generate_license.py --name "User"` | One session at a time|
