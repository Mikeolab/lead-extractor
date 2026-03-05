# macOS Build Status

## Current Status: ⚠️ Not Recommended

Based on research and testing, **Streamlit has known compatibility issues with macOS GUI app bundling**. The app works perfectly when run on localhost, but bundling as a `.app` file causes:

- App bouncing in dock
- Silent crashes
- Multiple instance spawning
- Browser opening loops

## Research Findings

From Streamlit community forums:
- Streamlit is designed for web/terminal use, not GUI app bundling
- macOS has specific requirements that conflict with Streamlit's architecture
- Windows has better support for packaged Python apps

## Recommended Approach

**Use localhost for development and testing:**

```bash
# Start the server
python3 -m uvicorn app.server.automation_server:app --host 0.0.0.0 --port 8000

# In another terminal, start Streamlit
streamlit run app/main.py
```

Then access at: `http://localhost:8501`

## Windows Build

Focus on Windows deployment next - it has better support for PyInstaller + Streamlit bundling.

## If You Still Want to Try macOS Build

The simplified launcher (`launch_app_simple.py`) removes threading complexity, but may still have issues:

```bash
./build_macos.sh
open dist/LeadExtractorPro.app
```

If it doesn't work, check logs:
```bash
cat ~/Library/Application\ Support/LeadExtractorPro/error.log
```

