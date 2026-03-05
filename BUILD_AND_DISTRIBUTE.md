# Build Once, Distribute .exe — No Manual CMD

## The Problem

- **Windows .exe must be built on Windows** — can't build it on Mac
- **GitHub Actions** solves this: builds run on Windows in the cloud

## New Flow (No RDP, No Manual CMD)

### One-time setup

1. Create a GitHub repo (if you don't have one)
2. Push your `lead-extractor` project to it
3. The `.github/workflows/build-windows.yml` file is already included

### Every time you want a new .exe

1. **Push** your code to GitHub (or click "Run workflow" in Actions)
2. **Wait** ~5–10 minutes for the build to finish
3. **Download** the `.exe` from the Actions run:
   - Go to repo → Actions tab
   - Click the latest "Build Windows EXE" run
   - Scroll to "Artifacts"
   - Download **LeadExtractorPro-Windows** (it contains `LeadExtractorPro.exe`)

### For your users

- Send them **only** `LeadExtractorPro.exe`
- They double-click to run
- No Python, no pip, no CMD
- Works like a normal application

---

## If You Don't Use GitHub Yet

1. Go to github.com → New repository
2. Name it `lead-extractor` (or any name)
3. Locally:
   ```bash
   cd /Users/mikeolab/lead-extractor
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/YOUR_USERNAME/lead-extractor.git
   git push -u origin main
   ```
4. The build will start automatically
5. Download the .exe from Actions when it finishes

---

## Manual trigger

You can also start a build without pushing:

1. Repo → **Actions** → **Build Windows EXE**
2. Click **Run workflow** → **Run workflow**
3. Wait, then download the artifact

---

## Summary

| Before                          | After                         |
|---------------------------------|-------------------------------|
| RDP → install Python → pip → build | Push to GitHub → Download .exe |
| Manual CMD on Windows           | Fully automated in the cloud  |
| Stress every time               | One-click (or push) build     |
