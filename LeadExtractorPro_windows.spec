# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Windows build of Lead Extractor Pro
"""
import os
from PyInstaller.utils.hooks import collect_all

# Collect all app data
datas = [('app', 'app')]
binaries = []

# Bundle Playwright Chromium (run build_windows.bat which installs to playwright_browsers/)
# Use manual walk to ensure (src, dest) 2-tuples - Tree() can cause "too many values to unpack"
if os.path.exists('playwright_browsers'):
    for root, _dirs, files in os.walk('playwright_browsers'):
        for f in files:
            src = os.path.normpath(os.path.join(root, f))
            rel = os.path.relpath(src, 'playwright_browsers')
            dest = os.path.join('playwright_browsers', rel)
            datas.append((src, dest))

# Hidden imports - all required modules
hiddenimports = [
    'streamlit',
    'streamlit.web.cli',
    'streamlit.runtime.scriptrunner',
    'playwright',
    'fastapi',
    'uvicorn',
    'uvicorn.lifespan.on',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.protocols.http.auto',
    'websocket',
    'websockets',
    'websocket_client',
    'sqlite3',
    'pdfplumber',
    'httpx',
    'pandas',
    'openpyxl',
    'fpdf',
    'fpdf2',
    'PIL',
    'PIL.Image',
    'cryptography',
    'cryptography.fernet',
    'cryptography.hazmat.primitives.ciphers',
    'cryptography.hazmat.primitives.ciphers.aead',
    'cryptography.hazmat.primitives.ciphers.modes',
    'cryptography.hazmat.primitives.ciphers.algorithms',
    'cryptography.hazmat.backends',
    'cryptography.hazmat.backends.openssl',
    'cryptography.hazmat.bindings._rust',
    'cryptography.hazmat.primitives',
    'cryptography.hazmat.primitives.hashes',
    'cryptography.hazmat.primitives.kdf.pbkdf2',
    'cffi',
    '_cffi_backend',
    'keyring',
    'email_validator',
    'dns',
    'dns.resolver',
    'dns.rdatatype',
    'dns.rdataclass',
    'dns.exception',
    # Stdlib email (different from app.email - prevents resolution to wrong package)
    'email',
    'email.mime',
    'email.mime.text',
    'email.mime.multipart',
    'email.mime.base',
    'email.utils',
    'email.encoders',
    'boto3',
    'bs4',
    'lxml',
    'selenium',
    'undetected_chromedriver',
    'dotenv',
    'socketio',
    # PyWebview is published as 'pywebview' on PyPI but imports as 'webview'.
    # We need the import name plus the Windows backends so the frozen exe can
    # find WebView2/EdgeChromium at runtime.
    'webview',
    'webview.platforms',
    'webview.platforms.edgechromium',
    'webview.platforms.winforms',
    'webview.util',
]

def _toc_to_src_dest(toc_list):
    """Convert PyInstaller TOC format (dest, src, typecode) to (src, dest) 2-tuples."""
    out = []
    for item in toc_list:
        if len(item) == 3:
            dest, src, _ = item
            out.append((src, dest))
        else:
            out.append(item)  # Already (src, dest)
    return out


# Collect all data from streamlit and playwright (TOC has 3-tuples, Analysis expects 2-tuples)
tmp_ret = collect_all('streamlit')
datas += _toc_to_src_dest(tmp_ret[0])
binaries += _toc_to_src_dest(tmp_ret[1])
hiddenimports += tmp_ret[2]

tmp_ret = collect_all('playwright')
datas += _toc_to_src_dest(tmp_ret[0])
binaries += _toc_to_src_dest(tmp_ret[1])
hiddenimports += tmp_ret[2]

tmp_ret = collect_all('fastapi')
datas += _toc_to_src_dest(tmp_ret[0])
binaries += _toc_to_src_dest(tmp_ret[1])
hiddenimports += tmp_ret[2]

tmp_ret = collect_all('uvicorn')
datas += _toc_to_src_dest(tmp_ret[0])
binaries += _toc_to_src_dest(tmp_ret[1])
hiddenimports += tmp_ret[2]

tmp_ret = collect_all('cryptography')
datas += _toc_to_src_dest(tmp_ret[0])
binaries += _toc_to_src_dest(tmp_ret[1])
hiddenimports += tmp_ret[2]

# PyWebview ships HTML/JS bridge assets and platform backends that PyInstaller
# does not pick up unless we collect_all the package. Wrap in try/except so a
# missing optional backend doesn't break the build on machines that don't have
# every webview dependency installed.
try:
    tmp_ret = collect_all('webview')
    datas += _toc_to_src_dest(tmp_ret[0])
    binaries += _toc_to_src_dest(tmp_ret[1])
    hiddenimports += tmp_ret[2]
except Exception as _e:
    print(f"[spec] WARNING: collect_all('webview') failed: {_e}")

a = Analysis(
    ['launch_app_windows.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['hook-email-stdlib.py'],  # Preload stdlib email before app.email
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='LeadExtractorPro',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # UPX can break cryptography .pyd on Windows
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Hide console (errors go to logs in AppData/LeadExtractorPro/)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='LeadExtractorPro.ico',  # NEXUS ◉ icon (256x256, 128x128, etc.)
)
