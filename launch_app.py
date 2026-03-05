#!/usr/bin/env python3
"""
Launcher script for Lead Extractor Pro
Runs Streamlit app properly, whether bundled or in development
"""
import sys
import subprocess
from pathlib import Path

def main():
    # Determine if we're bundled
    if getattr(sys, 'frozen', False):
        # Bundled app - use sys._MEIPASS for resources
        app_dir = Path(sys._MEIPASS)
        main_script = app_dir / "app" / "main.py"
    else:
        # Development mode
        app_dir = Path(__file__).parent
        main_script = app_dir / "app" / "main.py"
    
    # Run Streamlit
    try:
        # Use streamlit command
        cmd = [
            sys.executable,
            "-m", "streamlit", "run",
            str(main_script),
            "--server.port=8501",
            "--server.address=localhost",
            "--browser.gatherUsageStats=false",
            "--server.headless=true",
        ]
        
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\n👋 App closed by user")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error launching app: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

