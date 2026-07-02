# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec: native macOS .app wrapping dashboard_app.py + static assets.

import pathlib

from PyInstaller.utils.hooks import collect_all

SPECDIR = pathlib.Path(SPECPATH).resolve()  # noqa: F821 …/native_app
PACKAGE = SPECDIR.parent  # …/token-telemetry

webview_datas, webview_binaries, webview_hidden = collect_all("webview")

block_cipher = None

datas = [
    (str(PACKAGE / "dashboard.html"), "."),
    (str(PACKAGE / "dashboard.js"), "."),
    (str(PACKAGE / "dashboard.css"), "."),
    (str(PACKAGE / "icon.jpg"), "."),
    (str(PACKAGE / "providers_config.yaml"), "."),
] + webview_datas

a = Analysis(
    [str(PACKAGE / "dashboard_app.py")],
    pathex=[str(PACKAGE)],
    binaries=webview_binaries,
    datas=datas,
    hiddenimports=list(webview_hidden),
    hookspath=[],
    hooksconfig={},
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

icon_path = SPECDIR / "SCROOGE.icns"
icon_arg = str(icon_path) if icon_path.is_file() else None

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="SCROOGE",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_arg,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="SCROOGE",
)

app = BUNDLE(
    coll,
    name="SCROOGE.app",
    bundle_identifier="com.local.cursor.SCROOGE",
    icon=icon_arg,
    info_plist={
        "CFBundleDisplayName": "S.C.R.O.O.G.E.",
        "CFBundleName": "S.C.R.O.O.G.E.",
        "NSHumanReadableCopyright": "Local tooling; not affiliated with Cursor.",
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": "11.0",
    },
)
