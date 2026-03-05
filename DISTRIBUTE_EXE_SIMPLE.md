# Simple Flow: Build Once → Distribute .exe

## Your Flow (No GitHub)

1. **Send zip** to RDP (WeTransfer, etc.)
2. **On RDP:** Extract → run `build_windows.bat` (one time)
3. **Get:** `dist\LeadExtractorPro.exe`
4. **Send that .exe** to users

## For End Users

- They get **only** `LeadExtractorPro.exe`
- Double-click to run
- No Python, no CMD, no installation
- Works like a normal app

## Fixes Applied (This Build)

- **PYTHONPATH** – subprocess can now find `app.*` imports (was likely causing silent crash)
- **Console window** – exe shows a window so you can see errors if anything fails
- **Crash log** – if it crashes, check `%APPDATA%\LeadExtractorPro\crash.log`

## After You Confirm It Works

Once the exe runs correctly, we can turn off the console window so it looks like a normal app.
