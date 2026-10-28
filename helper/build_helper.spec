# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

hidden_imports = [
    'fitz',
    'pptx',
    'pdf2docx',
    'pypdf',
    'PIL',
    'helper.detector',
    'helper.registry',
    'helper.engines.base',
    'helper.engines.libreoffice',
    'helper.engines.office_mac',
    'helper.engines.word_com',
    'helper.engines.pdf_to_docx',
    'helper.engines.pdf_to_pptx',
    'helper.utils.events',
    'helper.utils.paths',
    'helper.utils.tempdir',
]

datas = []

a = Analysis(
    ['main.py'],
    pathex=['..'],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'scipy', 'numpy', 'IPython'],
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
    name='converter-helper',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
