# -*- mode: python ; coding: utf-8 -*-

import os

a = Analysis(
    ['gui.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

if os.name == "nt":
    splash = Splash(
        'splash.png',
        binaries=a.binaries,
        datas=a.datas,
        text_pos=(10, 10),
        text_size=12,
        minify_script=True,
        always_on_top=True,
    )

    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        splash,
        splash.binaries,
        [],
        name='Bead Tracker.exe',
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
        icon=['icon.icns'],
    )
else:
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        [],
        name='Bead Tracker',
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
        icon=['icon.icns'],
    )

    os.system("chmod +x dist/Bead\ Tracker")


app = BUNDLE(
    exe,
    name='Bead Tracker.app',
    icon='icon.icns',
    bundle_identifier=None,
)
