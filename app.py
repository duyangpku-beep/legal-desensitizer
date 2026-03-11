#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Legal Document Desensitizer — Entry Point
法律文件脱敏工具 — 启动入口

Version:  2.0.0
License:  MIT
Author:   Yang Du
Requires: python-docx >= 1.1.0, PyMuPDF >= 1.23.0 (optional, for PDF)
"""

__version__ = "2.0.0"

import sys
import os

# Ensure repo root is on path so `core`, `gui`, `utils` are importable
sys.path.insert(0, os.path.dirname(__file__))


def _check_deps() -> None:
    """Verify required dependencies; print instructions and exit if missing."""
    missing = []
    try:
        import docx  # noqa: F401
    except ImportError:
        missing.append("python-docx")

    if missing:
        print("❌ 缺少依赖 Missing dependencies:")
        for pkg in missing:
            print(f"   {pkg}")
        print("\n请运行 Please run:")
        print(f"   pip install {' '.join(missing)}")
        print("\n可选PDF支持 Optional PDF support:")
        print("   pip install PyMuPDF")
        input("\n按回车退出 Press Enter to exit...")
        sys.exit(1)


def main() -> None:
    _check_deps()

    from utils.logger import setup_logging
    setup_logging()

    from gui.main_window import MainWindow
    app = MainWindow()
    app.run()


if __name__ == "__main__":
    main()
