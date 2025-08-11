# -*- mode: python ; coding: utf-8 -*-

import rasterio
from PyInstaller.utils.hooks import collect_submodules
from PyInstaller.building.build_main import Analysis, PYZ, EXE, COLLECT

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
    ['swe_convert_upload.py'],
    pathex=[],
    binaries=[],
    datas=[(os.path.join(rasterio.__path__[0], 'gdal_data'), 'gdal/data'),],
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
    upx_exclude=[],
    name='SWE_data_uploader'
)