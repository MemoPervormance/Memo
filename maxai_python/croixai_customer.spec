# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for CroixAI Customer build.
# Run:  pyinstaller croixai_customer.spec
# Output: dist/CroixAI.exe  (single-file, no source visible)

import sys
from pathlib import Path

ROOT = Path(SPECPATH)

block_cipher = None

a = Analysis(
    [str(ROOT / 'main_customer.py')],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        # Web UI and static assets
        (str(ROOT / 'static'),   'static'),
        # Default game profiles
        (str(ROOT / 'profiles'), 'profiles'),
        # Example config (used as template if config.toml missing)
        (str(ROOT / 'config.toml.example'), '.'),
    ],
    hiddenimports=[
        # FastAPI / uvicorn internals
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        # Pydantic
        'pydantic.deprecated.class_validators',
        # PIL / Pillow
        'PIL._tkinter_finder',
        # Input backend optional
        'serial',
        'serial.tools',
        # OpenCV
        'cv2',
        # Win32
        'win32api',
        'win32con',
        'win32gui',
        'pywintypes',
        # capture backends
        'dxcam',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Strip training infrastructure — customers don't train
        'ultralytics',
        'torch',
        'torchvision',
        'tensorboard',
        'matplotlib',
        'IPython',
        'jupyter',
        'notebook',
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
    name='CroixAI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,          # compress with UPX if available
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,      # keep console for key entry prompt
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,         # add .ico path here if you have one
    version=None,
)
