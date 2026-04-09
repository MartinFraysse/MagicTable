# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec pour MagicTable
# Lancer depuis la racine du projet : pyinstaller MagicTable.spec
#

from pathlib import Path

SRC = Path("src")

a = Analysis(
    [str(SRC / "app.py")],
    pathex=[str(SRC)],
    binaries=[],
    datas=[
        # Ressources read-only embarquées dans le bundle
        (str(SRC / "assets"),  "assets"),
        (str(SRC / "styles"),  "styles"),
        # ⚠️  src/data/ N'est PAS inclus : les données utilisateur
        #     sont stockées à côté du .exe (voir storage/base.py)
    ],
    hiddenimports=[
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
        "PySide6.QtMultimedia",
        "PySide6.QtNetwork",
        "ssl",
        "certifi",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="MagicTable",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # Pas de fenêtre console
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="src/assets/MT_logo.ico",
)
