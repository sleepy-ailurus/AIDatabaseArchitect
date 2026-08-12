# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['run.py'],
    pathex=['C:/Users/Tby/Desktop/AIDatabaseArchitect/backend'],
    binaries=[],
    datas=[('C:/Users/Tby/Desktop/AIDatabaseArchitect/frontend/dist', 'frontend_dist'), ('C:/Users/Tby/Desktop/AIDatabaseArchitect/backend/.venv/Lib/site-packages/webview/lib/Microsoft.Web.WebView2.Core.dll', 'Microsoft.Web.WebView2.Core.dll'), ('C:/Users/Tby/Desktop/AIDatabaseArchitect/backend/.venv/Lib/site-packages/webview/lib/Microsoft.Web.WebView2.WinForms.dll', 'Microsoft.Web.WebView2.WinForms.dll'), ('C:/Users/Tby/Desktop/AIDatabaseArchitect/backend/.venv/Lib/site-packages/webview/lib/runtimes/win-x64/native', 'win-x64')],
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
    icon=['C:/Users/Tby/Desktop/AIDatabaseArchitect/icon/show.ico'],
)
