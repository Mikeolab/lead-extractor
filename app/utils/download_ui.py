"""
Streamlit download UI helper - works in both browser and standalone PyWebView app.
"""
import streamlit as st
from pathlib import Path
from app.utils.download_helper import (
    is_standalone_app,
    save_file_native,
    open_downloads_folder,
    get_downloads_folder,
)


def download_button_or_save(
    label: str,
    data: bytes,
    file_name: str,
    mime: str = "text/csv",
    key: str = None,
    help_text: str = None,
) -> bool:
    """
    Smart download button that works in both browser and standalone app.
    
    In browser: Shows Streamlit download button (data flows through browser)
    In standalone: Shows button that opens native file dialog and saves to Downloads
    
    Args:
        label: Button label (e.g., "⬇️ Download CSV")
        data: File content as bytes
        file_name: Suggested filename
        mime: MIME type
        key: Streamlit key
        help_text: Help tooltip
    
    Returns:
        True if file was saved/downloaded, False if canceled
    """
    if is_standalone_app():
        # Standalone PyWebView app - use native file dialog
        col1, col2 = st.columns([3, 1])
        
        with col1:
            if st.button(label, key=key, help=help_text, use_container_width=True):
                with st.spinner(f"Saving {file_name}…"):
                    filepath = save_file_native(data, file_name)
                    if filepath:
                        st.success(f"✅ Saved to: {filepath.name}")
                        # Offer button to open Downloads folder
                        col_a, col_b = st.columns(2)
                        with col_a:
                            if st.button("📂 Open Downloads folder", key=f"{key}_open_folder"):
                                if open_downloads_folder():
                                    st.info("📂 Opening Downloads folder...")
                                else:
                                    st.warning("Could not open folder")
                        return True
                    else:
                        st.error("❌ Failed to save file")
                        return False
        return False
    else:
        # Browser mode - use Streamlit's native download button
        st.download_button(
            label,
            data=data,
            file_name=file_name,
            mime=mime,
            key=key,
            help=help_text,
            use_container_width=True,
        )
        return True


def download_button_with_fallback(
    label: str,
    data: bytes,
    file_name: str,
    mime: str = "text/csv",
    key: str = None,
    help_text: str = None,
) -> None:
    """
    Simple wrapper - if standalone, shows button to save. If browser, shows download button.
    This is the main function to use in place of st.download_button.
    """
    download_button_or_save(label, data, file_name, mime, key, help_text)
