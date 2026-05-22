"""
Download helper for standalone PyWebView app and browser mode.
In PyWebView, uses native file save dialog.
In browser, uses Streamlit download_button.
"""
import os
import sys
from pathlib import Path
from typing import Optional


def is_standalone_app() -> bool:
    """Check if running in standalone PyWebView app (frozen executable)."""
    return getattr(sys, "frozen", False)


def get_downloads_folder() -> Path:
    """Get the user's Downloads folder path."""
    if sys.platform == "win32":
        # Windows: %USERPROFILE%\Downloads
        return Path.home() / "Downloads"
    elif sys.platform == "darwin":
        # macOS: ~/Downloads
        return Path.home() / "Downloads"
    else:
        # Linux: ~/Downloads or ~/downloads
        downloads = Path.home() / "Downloads"
        if downloads.exists():
            return downloads
        return Path.home() / "downloads"


def save_file_native(data: bytes, filename: str, default_dir: Optional[Path] = None) -> Optional[Path]:
    """
    Save a file using native dialog (Windows/macOS/Linux).
    
    Args:
        data: File content as bytes
        filename: Default filename
        default_dir: Default directory (defaults to Downloads folder)
    
    Returns:
        Path where file was saved, or None if user canceled
    """
    if default_dir is None:
        default_dir = get_downloads_folder()
    
    default_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        if sys.platform == "win32":
            return _save_file_windows(data, filename, default_dir)
        else:
            # Fallback: just save to Downloads directly
            return _save_file_direct(data, filename, default_dir)
    except Exception as e:
        print(f"Error saving file: {e}", file=sys.stderr)
        # Fallback: save to Downloads directly
        return _save_file_direct(data, filename, default_dir)


def _save_file_windows(data: bytes, filename: str, default_dir: Path) -> Optional[Path]:
    """Use Windows file dialog via tkinter (cross-platform compatible)."""
    try:
        from tkinter import Tk, filedialog
        
        # Create hidden root window
        root = Tk()
        root.withdraw()  # Hide the window
        root.attributes('-topmost', True)  # Bring to front
        
        # Show save dialog
        filepath = filedialog.asksaveasfilename(
            initialdir=str(default_dir),
            initialfile=filename,
            defaultextension=".csv",
            filetypes=[
                ("CSV files", "*.csv"),
                ("Excel files", "*.xlsx"),
                ("PDF files", "*.pdf"),
                ("All files", "*.*"),
            ]
        )
        
        root.destroy()
        
        if filepath:
            # Write the file
            with open(filepath, "wb") as f:
                f.write(data)
            return Path(filepath)
        
        return None
    except ImportError:
        # tkinter not available, fall back to direct save
        return _save_file_direct(data, filename, default_dir)
    except Exception as e:
        print(f"Windows dialog error: {e}", file=sys.stderr)
        return _save_file_direct(data, filename, default_dir)


def _save_file_direct(data: bytes, filename: str, default_dir: Path) -> Optional[Path]:
    """Direct save to Downloads folder without dialog (fallback)."""
    try:
        filepath = default_dir / filename
        
        # Handle filename collision
        if filepath.exists():
            import time
            name, ext = filepath.stem, filepath.suffix
            timestamp = int(time.time())
            filepath = default_dir / f"{name}_{timestamp}{ext}"
        
        with open(filepath, "wb") as f:
            f.write(data)
        
        return filepath
    except Exception as e:
        print(f"Error saving file directly: {e}", file=sys.stderr)
        return None


def open_downloads_folder() -> bool:
    """Open the Downloads folder in file explorer/finder."""
    try:
        downloads = get_downloads_folder()
        
        if sys.platform == "win32":
            import subprocess
            subprocess.Popen(f'explorer "{downloads}"')
            return True
        elif sys.platform == "darwin":
            import subprocess
            subprocess.Popen(["open", str(downloads)])
            return True
        else:
            # Linux
            import subprocess
            subprocess.Popen(["xdg-open", str(downloads)])
            return True
    except Exception as e:
        print(f"Error opening Downloads folder: {e}", file=sys.stderr)
        return False
