# SpotifyRotator.spec
# PyInstaller spec for Spotify Playlist Rotator v4.0
# Build with: pyinstaller SpotifyRotator.spec

import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

block_cipher = None

# ── Collect pywebview data files ──────────────────────────────
webview_datas = collect_data_files('webview')

# ── App data files to bundle ──────────────────────────────────
app_datas = [
    ('index.html', '.'),      # frontend HTML — goes to root of bundle
    ('ding.mp3',   '.'),      # notification sound
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=webview_datas + app_datas,
    hiddenimports=[
        # spotipy
        'spotipy',
        'spotipy.oauth2',
        'spotipy.client',
        # webview backends
        'webview',
        'webview.platforms.winforms',
        'webview.platforms.edgechromium',
        # dotenv
        'dotenv',
        # standard lib things PyInstaller sometimes misses
        'http.server',
        'urllib.request',
        'urllib.parse',
        'urllib.error',
        'json',
        'csv',
        're',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Things we definitely don't need
        'tkinter',
        'customtkinter',
        'PyQt5',
        'PyQt6',
        'PySide2',
        'PySide6',
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'PIL.ImageQt',
        'IPython',
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
    [],
    exclude_binaries=True,          # onedir mode (smaller, more reliable)
    name='SpotifyRotator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,                  # no console window
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico',
    version_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SpotifyRotator',          # output folder name in dist/
)
