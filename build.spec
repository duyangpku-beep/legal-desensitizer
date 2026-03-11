# build.spec — PyInstaller spec for Legal Desensitizer
#
# Build single-file executables:
#   macOS:   pyinstaller build.spec
#   Windows: pyinstaller build.spec
#
# Output: dist/LegalDesensitizer  (macOS) or dist/LegalDesensitizer.exe (Windows)

import sys
from PyInstaller.building.build_main import Analysis, PYZ, EXE, BUNDLE

block_cipher = None

a = Analysis(
    ['app.py'],
    pathex=['.'],
    binaries=[],
    datas=[],
    hiddenimports=[
        'docx',
        'docx.oxml',
        'docx.oxml.ns',
        'fitz',
        'tkinter',
        'tkinter.ttk',
        'tkinter.filedialog',
        'tkinter.messagebox',
    ],
    hookspath=[],
    hooksconfig={},
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='LegalDesensitizer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,    # windowed app — no terminal window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,        # replace with 'assets/icon.icns' (macOS) or 'assets/icon.ico' (Windows)
)

# macOS .app bundle (comment out for Windows build)
if sys.platform == 'darwin':
    app = BUNDLE(
        exe,
        name='LegalDesensitizer.app',
        icon=None,
        bundle_identifier='com.yangdu.legal-desensitizer',
        info_plist={
            'CFBundleShortVersionString': '2.0.0',
            'CFBundleName': 'Legal Desensitizer',
            'NSHighResolutionCapable': True,
        },
    )
