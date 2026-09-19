# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules


project_root = Path(SPECPATH).resolve().parent
source_root = project_root / "src"
version_file = project_root / "packaging" / "version_info.txt"
common_paths = [str(project_root), str(source_root)]
core_hidden_imports = collect_submodules("v1_orchestrator")

bundled_harness_dir = project_root / "packaging" / "bundled-harness"
bundled_datas = [(str(bundled_harness_dir), "harness")] if bundled_harness_dir.is_dir() else []

gui_analysis = Analysis(
    [str(project_root / "launcher" / "main.py")],
    pathex=common_paths,
    binaries=[],
    datas=bundled_datas,
    hiddenimports=core_hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
gui_pyz = PYZ(gui_analysis.pure)
gui_exe = EXE(
    gui_pyz,
    gui_analysis.scripts,
    [],
    exclude_binaries=True,
    name="GPT-DeepSeek",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version=str(version_file),
)

cli_analysis = Analysis(
    [str(project_root / "packaging" / "cli_entry.py")],
    pathex=common_paths,
    binaries=[],
    datas=bundled_datas,
    hiddenimports=core_hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
cli_pyz = PYZ(cli_analysis.pure)
cli_exe = EXE(
    cli_pyz,
    cli_analysis.scripts,
    [],
    exclude_binaries=True,
    name="GPT-DeepSeek-CLI",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

distribution = COLLECT(
    gui_exe,
    gui_analysis.binaries,
    gui_analysis.datas,
    cli_exe,
    cli_analysis.binaries,
    cli_analysis.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="GPT-DeepSeek",
)


