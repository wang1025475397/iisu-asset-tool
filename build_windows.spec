# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

# Collect all psd_tools submodules to ensure PSD loading works
psd_tools_imports = collect_submodules('psd_tools')

# Collect psd_tools data files (if any)
psd_tools_datas = collect_data_files('psd_tools')

# Fix numpy 2.x compatibility with PyInstaller
numpy_datas = collect_data_files('numpy', include_py_files=False)
numpy_imports = collect_submodules('numpy')

# Collect additional data files
locales_datas = [('locales/*.json', 'locales')]  # Include language files
# Add other required resource files
resource_datas = [
    ('config.yaml', '.'),
    ('iisu_theme.qss', '.'),
    ('iisu_theme_light.qss', '.'),
]

# Minimal build - assets are distributed alongside the exe by GitHub Actions
a = Analysis(
    ['run_gui.py'],
    pathex=[],
    binaries=[],
    datas=psd_tools_datas + locales_datas + resource_datas + numpy_datas,  # Include psd_tools, locales, resources and numpy files
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
        'numpy._core',
        'numpy._core._multiarray_umath',
        'numpy._core.multiarray',
        'cv2',
        'imagehash',
        'bs4',
        'tqdm',
        'aggdraw',
        'device_asset_dialog'
    ] + psd_tools_imports + numpy_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['hook_numpy_fix.py'],
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='iiSU_Asset_Tool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='logo.png' if os.path.exists('logo.png') else None,
)
