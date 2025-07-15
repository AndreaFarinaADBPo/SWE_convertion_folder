# -*- mode: python ; coding: utf-8 -*-

import os
import pyproj
from PyInstaller.utils.hooks import collect_submodules
from PyInstaller.building.build_main import Analysis, PYZ, EXE, COLLECT

# Percorso della cartella che contiene proj.db
proj_data_dir = pyproj.datadir.get_data_dir()

# Includi TUTTI i file dentro la cartella (proj.db, ecc.)
pyproj_datas = [
    (os.path.join(proj_data_dir, filename), os.path.join('share', 'proj', filename))
    for filename in os.listdir(proj_data_dir)
]

# Hidden imports (necessari per rasterio e psycopg2)
hidden = [
    'rasterio._features',
    'rasterio.vrt',
    'rasterio.sample',
    'psycopg2',
    'psycopg2._psycopg'
]

# Analisi del file principale
a = Analysis(
    ['swe_convert_upload.py'],  # Sostituisci con il tuo nome file
    pathex=[],
    binaries=[],
    datas=pyproj_datas,
    hiddenimports=hidden,
    hookspath=[],
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
    name='SWE_data_uploader',
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
)

coll = COLLECT(
    exe, 
    a.binaries, 
    a.zipfiles, 
    a.datas, 
    strip=False, 
    upx=True, 
    name='SWE_data_uploader')
