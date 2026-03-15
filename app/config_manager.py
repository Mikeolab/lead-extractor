"""
Settings Persistence Module
Saves and loads user configurations automatically.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any
from app.config import APP_NAME


SETTINGS_FILE = Path.home() / f".{APP_NAME.lower().replace(' ', '_')}_settings.json"


def load_settings() -> Dict[str, Any]:
    """Load saved settings from file."""
    default = {
        "search_engine": "duckduckgo",  # DuckDuckGo avoids Google CAPTCHA
        "search_mode": "pdf",
        "max_pages": 10,
        "delay_pages": 2.0,
        "max_retries": 2,
        "timeout": 15,
        "deep_mode": True,
        "delay_scrape": 0.5,
        "scrape_retries": 2,
        "auto_save": True,
        "output_format": "PDF",
        "output_file": "results",
        "headless": True,  # Default ON: works everywhere (Cursor, Terminal, CI). Uncheck + run from Terminal for visible browser.
        "show_browser": True,  # Show live browser view in UI
        "delay_actions": 1.0,
        "filter_domains": "",
        "filter_filetypes": "",
        "max_depth": 3,
    }
    
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r") as f:
                saved = json.load(f)
                default.update(saved)
        except Exception:
            pass
    
    return default


def save_settings(settings: Dict[str, Any]) -> None:
    """Save settings to file."""
    try:
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f, indent=2)
    except Exception:
        pass

