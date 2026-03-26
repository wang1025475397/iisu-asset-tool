# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

# Collect all psd_tools submodules to ensure PSD loading works
psd_tools_imports = collect_submodules('psd_tools')

# Collect psd_tools data files (if any)
psd_tools_datas = collect_data_files('psd_tools')

# Build datas list, skipping missing paths and excluding OST mp3s from src/
_datas = []
for src, dst in [
    ('iisu_theme.qss', '.'),
    ('iisu_theme_light.qss', '.'),
    ('logo.png', '.'),
    ('audio.mp3', '.'),
    ('config.yaml', '.'),
    ('fonts', 'fonts'),
    ('platform_icons', 'platform_icons'),
    ('fallback_icons', 'fallback_icons'),
    ('borders', 'borders'),
    ('templates', 'templates'),
    ('locales/*.json', 'locales'),
]:
    if os.path.exists(src):
        _datas.append((src, dst))

# Only bundle PNGs from src/ (UI icons), not the iisuost/ mp3s
if os.path.isdir('src'):
    for f in os.listdir('src'):
        if f.endswith('.png'):
            _datas.append((os.path.join('src', f), 'src'))

a = Analysis(
    ['run_gui.py'],
    pathex=[],
    binaries=[],
    datas=_datas + psd_tools_datas,
    hiddenimports=[
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'PySide6.QtSvg',
        'PIL',
        'PIL.ImageQt',
        'yaml',
        'requests',
        'numpy',
        'cv2',
        'imagehash',
        'bs4',
        'tqdm',
        'aggdraw',  # Required by psd_tools for vector shape rendering
        'device_asset_dialog',  # Dynamically imported by options_dialog
        'adb_setup',  # Required by device_asset_dialog
        'custom_image_tab',  # Dynamically imported by custom_tab
        'border_generator_tab',  # Dynamically imported by custom_tab
        'cover_generator_tab',  # Dynamically imported by custom_tab
        'game_search_dialog',  # Dynamically imported by rom_browser_tab
        'update_dialog',  # Dynamically imported by ui_app_with_tabs
        'grid_crop_dialog',  # Dynamically imported by artwork_picker_dialog
    ] + psd_tools_imports,  # Add all psd_tools submodules
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        '_tkinter',
        'PIL._imagingtk',
        'PIL._tkinter_finder',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='iiSU_Asset_Tool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # UPX can corrupt macOS binaries, especially on arm64
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,  # UPX can corrupt macOS binaries
    upx_exclude=[],
    name='iiSU_Asset_Tool',
)

app = BUNDLE(
    coll,
    name='iiSU Asset Tool.app',
    # Note: macOS requires .icns format for app icons. The icon is set by the CI/CD workflow
    # which creates app_icon.icns from logo.png using iconutil, then injects it into the bundle.
    icon=None,
    bundle_identifier='com.iisu.assettool',
    info_plist={
        'NSPrincipalClass': 'NSApplication',
        'NSAppleScriptEnabled': False,
        'CFBundleDocumentTypes': [],
        'CFBundleShortVersionString': '2.0.2',
        'CFBundleVersion': '2.0.2',
        # Icon will be set by the workflow post-build
        'CFBundleIconFile': 'app_icon',
    },
)
