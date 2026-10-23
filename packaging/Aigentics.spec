# Run from repository root: pyinstaller --noconfirm packaging/Aigentics.spec
from pathlib import Path
root = Path(SPECPATH).parent
analysis = Analysis(
    [str(root / "packaging" / "desktop_entry.py")],
    pathex=[str(root)],
    binaries=[],
    datas=[(str(root / "aigentics" / "assets"), "aigentics/assets")],
    hiddenimports=["keyring.backends.Windows", "keyring.backends.chainer", "win32ctypes.pywin32.win32cred"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtQml", "PySide6.QtQuick", "tkinter", "pytest"],
    noarchive=False,
)
pyz = PYZ(analysis.pure)
exe = EXE(
    pyz, analysis.scripts, [], exclude_binaries=True,
    name="Aigentics", debug=False, bootloader_ignore_signals=False,
    strip=False, upx=False, console=False, disable_windowed_traceback=False,
    icon=str(root / "aigentics" / "assets" / "icon.ico"),
)
coll = COLLECT(exe, analysis.binaries, analysis.datas, strip=False, upx=False, name="Aigentics")
