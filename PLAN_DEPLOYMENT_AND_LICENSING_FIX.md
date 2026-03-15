# Plan: Deployment, Scaling & Dynamic Licensing

## Current State
- **Deployment**: Local `.exe` on each customer PC → Streamlit runs on localhost
- **Load time**: Slow (Playwright + Streamlit + large deps = 30–60s cold start)
- **Licensing**: Strict machine ID binding → breaks when hostname, MAC, or hardware changes

---

## Part 1: Deployment & Scaling Options

### Option A: Cloud-Hosted (Recommended for scaling)
**How it works**: You host the app once; customers access via URL (e.g. `https://yourapp.onrender.com`).

| Pros | Cons |
|------|------|
| One deployment serves many users | Need to handle multi-tenant data isolation |
| No local install for customers | Playwright/browser automation is harder in cloud |
| Fast load after first visit | Costs: ~$7–25/mo (Render, Railway) |
| Easy to update | |

**Best for**: Lead extraction that runs on your server (you control the browser). Customers log in, you run jobs in the cloud.

### Option B: Hybrid (Current + Optimized)
**How it works**: Keep local exe, but optimize startup and move heavy logic to a small cloud API.

| Pros | Cons |
|------|------|
| Browser automation stays local | Still need to distribute exe |
| Faster startup if UI is lighter | |
| License check can be online | |

### Option C: Local-Only (Current, Optimized)
**How it works**: Keep full local exe, improve load time and licensing only.

| Pros | Cons |
|------|------|
| No cloud cost | Slow startup remains |
| Works offline | Hard to scale support |
| Full control on customer PC | |

**Recommendation**: 
- **Short term**: Option C (optimize current exe + fix licensing)
- **Mid term**: Option B (add online license validation API)
- **Long term**: Option A if you move to fully cloud-based extraction

---

## Part 2: Load Time Improvements

### Quick wins (1–2 days)
1. **Lazy imports** – Import Playwright/Streamlit only when needed
2. **Reduce bundled size** – Exclude unused deps, use `--exclude-module`
3. **Splash screen** – Show “Loading…” immediately so it feels faster
4. **Pre-warm** – Start FastAPI in background before Streamlit

### Medium effort (3–5 days)
5. **Lighter launcher** – Separate launcher exe that downloads/starts a smaller runtime
6. **Streamlit config** – `server.runOnSave=false`, `fileWatcherType=none` (already set)
7. **Profile** – Use `py-spy` or similar to find slow imports

### Lower priority
8. **Alternative UI** – e.g. FastAPI + simple frontend instead of Streamlit (large refactor)

---

## Part 3: Dynamic Licensing (Priority)

### Problem
- Machine ID changes when: OS reinstall, hardware change, VM migration, hostname change
- Current behavior: License fails → “License not valid for this computer”

### Solution: Multi-Machine + Optional Binding

#### 3a. Optional Machine Binding (Quick fix – Day 1)
- Add `--no-machine-id` to generator → creates “floating” license
- Valid on any machine; useful for support and testing
- Activation UI: if license has no `machine_id`, skip machine check

#### 3b. Multiple Machines Per License (Day 2)
- License payload: `machine_ids: ["abc...", "def...", "7099..."]` (up to N)
- Validator: accept if current machine_id is in the list
- Generator: `--machine-ids "id1,id2,id3"` or `--add-machine "new_id"` for existing license
- Lets one customer use a few devices (e.g. desktop + laptop)

#### 3c. Stable Machine ID (Day 2)
- Use more stable identifiers:
  - Windows: `wmic csproduct get uuid` or serial
  - Fallback chain: UUID → MAC → hostname (current)
- Reduce machine ID changes from routine updates

#### 3d. Online License Validation (Day 3–5)
- Add a small API: `POST /license/validate` with `{license_key, machine_id}`
- You store: `license_key → [allowed_machine_ids]` in DB
- You can add/remove machines via admin UI
- App: optional online check; falls back to offline if no network

---

## Implementation Order

### Phase 1: Licensing Fixes (ASAP)
1. **Optional machine binding** (`--no-machine-id`)
2. **Multiple machines per license** (`machine_ids` array)
3. **More stable machine ID** (Windows UUID, fallbacks)

### Phase 2: Load Time
4. Lazy imports for heavy modules
5. Splash/loading screen
6. Dependency cleanup in spec

### Phase 3: Deployment (if needed)
7. Online license API
8. Cloud hosting (if moving to Option A/B)

---

## File Changes Summary

| File | Change |
|------|--------|
| `app/license/generator.py` | Support `machine_ids` array, `machine_id=""` for floating |
| `app/license/validator.py` | Accept `machine_ids` list, skip check if empty |
| `app/license/machine_id.py` | Add Windows UUID, improve stability |
| `generate_license_admin.py` | Add `--no-machine-id`, `--machine-ids "a,b,c"` |
| `app/license/activation_ui.py` | Clearer error when machine ID changes |
| `launch_app_windows.py` | Optional splash / loading indicator |

---

## Commands After Implementation

```bash
# Floating license (any machine)
python3 generate_license_admin.py --name "Customer" --plan enterprise --type yearly --no-machine-id

# Multi-machine (desktop + laptop)
python3 generate_license_admin.py --name "Customer" --plan enterprise --type yearly --machine-ids "7e36b498e6991ac9,70998ed59f0f1577"

# Single machine (current behavior)
python3 generate_license_admin.py --name "Customer" --machine-id "7e36b498e6991ac9" --plan enterprise --type yearly
```
