# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec template — Track 6 P0 (not wired to CI yet).
# Design: docs/architecture/PACKAGING_MSI_DESIGN.md
#
# Usage (when implemented):
#   pyinstaller packaging/windows/ai_command_center.spec --noconfirm
#
# block_cipher = None
#
# a = Analysis(
#     ['main.py'],
#     pathex=[],
#     binaries=[],
#     datas=[],
#     hiddenimports=['ai_command_center'],
#     hookspath=[],
#     hooksconfig={},
#     runtime_hooks=[],
#     excludes=[],
#     win_no_prefer_redirects=False,
#     win_private_assemblies=False,
#     cipher=block_cipher,
#     noarchive=False,
# )
# pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
#
# exe = EXE(
#     pyz,
#     a.scripts,
#     [],
#     exclude_binaries=True,
#     name='AICommandCenter',
#     debug=False,
#     bootloader_ignore_signals=False,
#     strip=False,
#     upx=False,  # avoid AV heuristics
#     console=False,
#     disable_windowed_traceback=False,
#     argv_emulation=False,
#     target_arch=None,
#     codesign_identity=None,
#     entitlements_file=None,
# )
# coll = COLLECT(
#     exe,
#     a.binaries,
#     a.zipfiles,
#     a.datas,
#     strip=False,
#     upx=False,
#     upx_exclude=[],
#     name='AICommandCenter',
# )
