"""
Streamlit download UI helper — works in both browser and standalone PyWebView app.

Browser mode:     Renders a normal st.download_button (browser handles save dialog).
Standalone mode:  Renders a st.button that writes the file directly to ~/Downloads
                  and shows a brief success toast.  No tkinter dialog (freezes
                  PyWebView) and no nested layout columns.
"""
from __future__ import annotations

import streamlit as st
from app.utils.download_helper import (
    is_standalone_app,
    save_file_native,
    open_downloads_folder,
)


def download_button_with_fallback(
    label: str,
    data: bytes | str,
    file_name: str,
    mime: str = "text/csv",
    key: str | None = None,
    help_text: str | None = None,
    use_container_width: bool = True,
) -> None:
    """
    Drop-in replacement for ``st.download_button`` that also works inside a
    PyWebView standalone window.

    * **Browser** — delegates to ``st.download_button`` (unchanged behaviour).
    * **Standalone** — renders a regular ``st.button``; on click, writes *data*
      to ``~/Downloads/<file_name>`` and shows a success toast with the path.
      If a collision exists the file gets a ``_<timestamp>`` suffix.
    """
    if is_standalone_app():
        # ── Standalone: save straight to ~/Downloads ────────────────────────
        if st.button(label, key=key, help=help_text, use_container_width=use_container_width):
            filepath = save_file_native(data, file_name)
            if filepath:
                st.toast(f"✅ Saved → {filepath.name}", icon="📁")
                st.success(f"Saved to **Downloads/{filepath.name}**")
            else:
                st.error("Failed to save file — check folder permissions.")
    else:
        # ── Browser: normal Streamlit download ──────────────────────────────
        if isinstance(data, str):
            data = data.encode("utf-8")
        st.download_button(
            label,
            data=data,
            file_name=file_name,
            mime=mime,
            key=key,
            help=help_text,
            use_container_width=use_container_width,
        )
