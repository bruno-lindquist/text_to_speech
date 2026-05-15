# PyInstaller spec — build do MVP (Fase 1)
# Validação empírica: confirma que just_playback/miniaudio/edge-tts/flet empacotam.
# Build minimalista — ícone e ajustes finais virão na Fase 7.

# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

# Flet carrega icons.json e outros recursos em runtime
flet_datas = collect_data_files("flet", includes=["**/*.json", "**/*.txt"])


a = Analysis(
    ["../main.py"],
    pathex=[".."],
    binaries=[],
    datas=flet_datas,
    hiddenimports=[
        "just_playback",
        "edge_tts",
        "loguru",
        "flet",
        "_cffi_backend",  # required by just_playback (cffi C extension)
        "cffi",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
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
    name="FizzyBee",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,  # arquitetura nativa
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="FizzyBee",
)

app = BUNDLE(
    coll,
    name="FizzyBee.app",
    icon=None,
    bundle_identifier="dev.flybruno.fizzybee",
)
