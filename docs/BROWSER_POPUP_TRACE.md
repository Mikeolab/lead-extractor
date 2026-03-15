# Browser Popup Trace - Line-by-Line Analysis

## Root Cause

**The browser does not pop up when the app is run from Cursor's terminal** because the process inherits Cursor's context, which may not have proper display/WindowServer access for spawning visible GUI windows on macOS.

**Fix:** Run the app from **Terminal.app** (or by double-clicking `START_LEAD_EXTRACTOR.command`). Processes started from Terminal have full display access.

---

## Trace: What Happens When You Click Start

### 1. UI (main.py)
- **Line 265:** `headless = bool(st.session_state.settings.get("headless", False))`
  - Reads headless from saved settings. If user saved with checkbox checked → `headless=True`
- **Line 266-274:** Sends WebSocket message with `headless`, `search_engine`, etc.

### 2. Server (automation_server.py)
- **Line 1358:** `headless = bool(data.get("headless", False))`
  - Receives headless from client
- **Line 339:** `use_headless = is_rdp_session() or (headless if sys.platform != "darwin" else False)`
  - On macOS: **forces** `use_headless = False` (ignores UI setting)
  - On Windows: uses RDP check or UI setting
- **Line 360:** `headless=use_headless` in launch_opts → should be `False` on macOS
- **Line 374:** `self.browser = await self.playwright.chromium.launch(**launch_opts)`

### 3. Bug Found & Fixed
- **Line 404 (was):** `self.page.on("close", lambda: on_page_close())`
  - **BUG:** `on_page_close` was never defined. Should be `on_browser_disconnected`.
  - **Fixed:** Changed to `on_browser_disconnected`.

### 4. Why It Works from Terminal But Not Cursor

| Run From | Parent Process | Display Access |
|----------|----------------|----------------|
| Terminal.app | Terminal | ✅ Yes |
| Double-click .command | Terminal (via Finder) | ✅ Yes |
| Cursor terminal | Cursor/Electron | ❌ Limited |
| SSH/nohup | No display | ❌ No |

Playwright's Chromium, when launched with `headless=False`, creates a window. On macOS, that requires the parent process to have a valid GUI session. Cursor's subprocess may not have that.

---

## How to Get the Browser to Pop Up

1. **Click "Launch in Terminal"** (new button on Live Extractor page) → Opens Terminal and runs the app. Use that instance.
2. **Or** Double-click `START_LEAD_EXTRACTOR.command` in Finder.
3. **Or** Manually run in Terminal:
   ```bash
   cd /Users/mikeolab/lead-extractor
   python3 launch_app_simple.py
   ```

Then open http://localhost:8501 in your browser and click Start.
