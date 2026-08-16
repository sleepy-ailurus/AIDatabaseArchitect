# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

ROOT = Path(SPECPATH).resolve().parent   # project root (this spec lives in backend/)
BACKEND = Path(SPECPATH).resolve()

a = Analysis(
    ['run.py'],
    pathex=[str(BACKEND)],
    binaries=[],
    datas=[
        (str(ROOT / 'frontend' / 'dist'), 'frontend_dist'),
        (str(BACKEND / '.venv/Lib/site-packages/webview/lib/Microsoft.Web.WebView2.Core.dll'), 'Microsoft.Web.WebView2.Core.dll'),
        (str(BACKEND / '.venv/Lib/site-packages/webview/lib/Microsoft.Web.WebView2.WinForms.dll'), 'Microsoft.Web.WebView2.WinForms.dll'),
        (str(BACKEND / '.venv/Lib/site-packages/webview/lib/runtimes/win-x64/native'), 'win-x64'),
    ],
    hiddenimports=['uvicorn.logging', 'uvicorn.loops.auto', 'uvicorn.protocols.http.auto', 'uvicorn.protocols.websockets.auto', 'webview', 'clr', 'clr_loader', 'proxy_tools', 'bottle'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='AIDatabaseArchitect',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=[str(ROOT / 'icon' / 'show.ico')],
)
