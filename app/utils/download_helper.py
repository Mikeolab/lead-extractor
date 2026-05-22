"""
Download helper for standalone PyWebView app and browser mode.

Standalone (frozen) builds:
  - save_file_native() writes directly to ~/Downloads (no dialog — tkinter
    dialogs freeze PyWebView). Collision is handled with a timestamp suffix.
  - open_downloads_folder() opens the folder in the system file manager.

Browser (dev) mode:
  - All downloads go through Streamlit's native st.download_button, so these
    helpers are only called when is_standalone_app() returns True.
"""
import os
import sys
import time
from pathlib import Path
from typing import Optional


def is_standalone_app() -> bool:
    """True when running as a PyInstaller-frozen .exe / .app."""
    return getattr(sys, "frozen", False)


def get_downloads_folder() -> Path:
    """Return the platform-appropriate Downloads folder."""
    if sys.platform == "win32":
        return Path.home() / "Downloads"
    elif sys.platform == "darwin":
        return Path.home() / "Downloads"
    else:
        dl = Path.home() / "Downloads"
        return dl if dl.exists() else Path.home() / "downloads"


def save_file_native(
    data: bytes | str,
    filename: str,
    default_dir: Optional[Path] = None,
) -> Optional[Path]:
    """
    Save *data* as *filename* inside ~/Downloads (or *default_dir*).

    Always writes directly — no dialog (tkinter dialogs freeze PyWebView on
    Windows). If a file with the same name already exists, a ``_<timestamp>``
    suffix is appended before the extension so nothing is silently overwritten.

    Accepts both bytes and str (str is encoded to UTF-8).

    Returns the final Path on success, or None on failure.
    """
    if isinstance(data, str):
        data = data.encode("utf-8")

    if default_dir is None:
        default_dir = get_downloads_folder()

    default_dir.mkdir(parents=True, exist_ok=True)
    filepath = default_dir / filename

    # Avoid overwriting
    if filepath.exists():
        stem, ext = filepath.stem, filepath.suffix
        filepath = default_dir / f"{stem}_{int(time.time())}{ext}"

    try:
        with open(filepath, "wb") as f:
            f.write(data)
        return filepath
    except Exception as e:
        print(f"[download_helper] save error: {e}", file=sys.stderr)
        return None


def open_downloads_folder() -> bool:
    """Open ~/Downloads in the platform file manager. Returns True on success."""
    folder = get_downloads_folder()
    try:
        if sys.platform == "win32":
            os.startfile(str(folder))  # type: ignore[attr-defined]
            return True
        elif sys.platform == "darwin":
            import subprocess
            subprocess.Popen(["open", str(folder)])
            return True
        else:
            import subprocess
            subprocess.Popen(["xdg-open", str(folder)])
            return True
    except Exception as e:
        print(f"[download_helper] open_downloads_folder error: {e}", file=sys.stderr)
        return False
