# 🎯 Lead Extractor Pro — Setup Guide

Welcome! This guide gets you from download to your first leads in **under 10 minutes**.

---

## 📋 Requirements

- **Python 3.10 or higher** ([download here](https://www.python.org/downloads/))
- **macOS, Linux, or Windows**
- **8GB RAM minimum** (16GB recommended for large query batches)
- **Stable internet connection**

---

## 📦 Step 1: Install Python (if you don't have it)

### Check if you have Python
Open Terminal (Mac/Linux) or Command Prompt (Windows) and run:
```bash
python3 --version
```

If you see `Python 3.10.x` or higher → you're good. Skip to Step 2.

### If not installed
- **Mac:** Run `brew install python@3.11` or download from [python.org](https://www.python.org/downloads/)
- **Windows:** Download installer from [python.org](https://www.python.org/downloads/) — make sure to check "Add Python to PATH"
- **Linux:** `sudo apt install python3.11 python3-pip python3-venv`

---

## 📦 Step 2: Install Lead Extractor Pro

1. **Unzip** the file you downloaded
2. Open Terminal/Command Prompt
3. Navigate to the unzipped folder:
   ```bash
   cd path/to/lead-extractor-pro
   ```
4. (Recommended) Create a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate    # Mac/Linux
   venv\Scripts\activate       # Windows
   ```
5. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   *This takes 3-5 minutes — it's installing Streamlit, Playwright, and other libraries.*

6. Install the browser used for scraping:
   ```bash
   playwright install chromium
   ```
   *Downloads ~200MB Chromium browser. One-time only.*

---

## 🚀 Step 3: Launch the App

```bash
./start_app.sh         # Mac/Linux
# OR on Windows:
start_app.bat
```

You'll see:
```
✅ Streamlit running at http://localhost:8501
✅ Automation server running at http://localhost:8000
```

Open your browser → **http://localhost:8501**

---

## 🎯 Step 4: Your First Extraction

1. Go to **"Live Extractor"** in the left sidebar
2. Use the **3-panel Query Builder**:
   - **Site Footprint** — pick which sites to search (LinkedIn, Crunchbase, etc.)
   - **@Patterns** — choose email domains to look for (`@gmail.com`, custom)
   - **Location** — narrow by city/country
3. The app generates a list of search queries automatically
4. Click **Start Extraction**
5. Watch the live activity log + leads dashboard
6. When done → click **Download CSV/Excel**

---

## 💾 Saved Leads

- Every extraction is auto-saved to the local database
- Go to **"Saved Leads"** → browse, filter, tag, re-export
- **Upload External Leads** tab lets you import existing CSVs for enrichment

---

## 🆘 Troubleshooting

**"Command not found: python3"**
→ Python isn't installed or isn't on your PATH. See Step 1.

**"pip: command not found"**
→ Try `python3 -m pip install -r requirements.txt`

**"playwright: command not found"**
→ Try `python3 -m playwright install chromium`

**App opens but no leads found**
→ Some queries return 0 results — try broader keywords or different patterns. Check the activity log for blocked requests.

**Browser detected as bot**
→ The app uses Stealth Mode by default. If you still get blocked, slow down the request rate in `app/config.py` or use a VPN.

**Port 8501 already in use**
→ Another app is using it. Stop that app, or edit `start_app.sh` to use a different port.

---

## ⚙️ Configuration

- App settings → edit `app/config.py`
- Database location → `data/leads.db` (auto-created on first run)
- Export files → saved to `exports/`

---

## 📬 Support

Stuck? Email **support@buildwithai.com** — we respond within 24 hours.

Enjoy faster lead generation! 🎯

— **Build With AI**
