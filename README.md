# ⚖ Legal Document Desensitizer  法律文件脱敏工具

> **100% offline · Zero cloud uploads · Chinese + English contracts**
> **完全本地运行 · 数据不上传网络 · 支持中英文合同**

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Supports](https://img.shields.io/badge/Supports-DOCX%20%7C%20PDF-orange)]()

---

## What it does / 功能简介

A desktop GUI tool for legal professionals to redact sensitive information from Word (`.docx`) and PDF files before sharing with third parties.

供法律专业人员使用的桌面工具，在向第三方分享文件前，自动识别并脱敏 Word (`.docx`) 与 PDF 文件中的敏感信息。

### Smart auto-detection / 智能自动检测

| Entity type / 信息类型 | Example / 示例 | Replaced with / 替换为 |
|----------------------|----------------|----------------------|
| Contract parties (EN) | `XYZ Co. Ltd. ("Company")` | alias `Company` |
| Contract parties (CN) | `某某有限公司（"甲方"）` | alias `甲方` |
| Amounts (EN) | `USD 1,000,000` | `[AMOUNT]` |
| Amounts (CN) | `人民币500万元` / `一百万元` | `[金额]` |
| Phone numbers | `13812345678` / `+852 2345 6789` | `[PHONE]` / `[电话]` |
| Email addresses | `john@example.com` | `[EMAIL]` |
| ID / Passport | `110101199001011234` | `[证件号码]` |
| Addresses (CN) | `上海市浦东新区XX路100号` | `[地址]` |
| Addresses (EN) | `10 Exchange Square, Central` | `[ADDRESS]` |
| Person names | `Attention: John Smith` | `[NAME]` |
| Other companies | `ABC Holdings Limited` | `[COMPANY NAME]` |
| Custom terms | user-defined | `【】` (configurable) |

### Key features / 主要特性

- **Formatting-safe**: Run-level replacement preserves bold, italic, font size, colour in Word documents
- **Batch mode**: Process an entire folder of files in one click
- **PDF support**: PyMuPDF-based redaction with white-fill overlay
- **Config persistence**: Settings and custom terms saved between sessions
- **Bilingual UI**: Full Chinese + English interface

---

## Installation / 安装

### Requirements / 环境要求

- Python 3.9 or later
- macOS / Windows / Linux

### Quick start / 快速开始

```bash
git clone https://github.com/duyangpku-beep/legal-desensitizer.git
cd legal-desensitizer
./start.sh        # handles everything: venv + deps + launch
```

`start.sh` creates a virtual environment on first run, installs dependencies, and launches the app. Just run it again next time — no setup needed.

**Windows users:** open the folder in terminal and run:
```bat
python -m venv venv && venv\Scripts\activate && pip install -r requirements.txt && python app.py
```

### Dependencies / 依赖

```
python-docx>=1.1.0   # Word document processing
PyMuPDF>=1.23.0      # PDF support (optional but recommended)
tkinter              # GUI — built into Python standard library
```

---

## Usage / 使用方法

1. **Select file(s)** — single `.docx`/`.pdf`, or a folder for batch processing
   选择文件（单个或整个文件夹批量处理）

2. **Auto Detect tab** — choose which entity types to auto-detect and replace
   在「自动检测」标签页中，勾选需要自动检测的信息类型

3. **Custom Terms tab** — enter any additional terms to redact (one per line)
   在「自定义词语」标签页中，输入其他需要脱敏的词语

4. **Preview** — review what will be replaced before committing
   点击「预览」查看即将替换的内容

5. **Desensitize** — outputs `{filename}_脱敏.docx` / `.pdf` in the same folder
   点击「开始脱敏」，输出文件保存至原文件夹，后缀为 `_脱敏`

---

## How contract party detection works / 合同签署方检测原理

The tool scans for the standard legal defined-term pattern:

**English:** `Company Full Name, a [type] company ... ("Alias")`
→ maps `Company Full Name` → `Alias` throughout the document

**Chinese:** `某某有限公司（以下简称"甲方"）`
→ maps `某某有限公司` → `甲方` throughout the document

This means all instances of the full company name are replaced with the shorter alias — matching how the document itself refers to the party after the definition clause.

---

## Build standalone executable / 打包可执行文件

```bash
pip install pyinstaller
pyinstaller build.spec
# Output: dist/LegalDesensitizer  (macOS .app or Windows .exe)
```

GitHub Releases will provide pre-built binaries:
- `LegalDesensitizer-macOS.zip`
- `LegalDesensitizer-Windows.exe`

---

## Project structure / 项目结构

```
legal-desensitizer/
├── app.py                  # Entry point / 启动入口
├── core/
│   ├── detector.py         # SmartDetector — all regex patterns
│   ├── processor.py        # DocxProcessor + PdfProcessor
│   └── replacer.py         # Formatting-safe run-level replacement
├── gui/
│   ├── main_window.py      # Main tkinter window
│   └── styles.py           # ttk style definitions
├── utils/
│   ├── config.py           # JSON config persistence
│   └── logger.py           # File + console logging
├── tests/
│   ├── test_detector.py    # Detector unit tests
│   └── test_processor.py   # Processor + replacer unit tests
├── requirements.txt
├── build.spec              # PyInstaller spec
└── LICENSE                 # MIT
```

---

## Running tests / 运行测试

```bash
pip install pytest
python -m pytest tests/ -v
```

---

## Roadmap & Paid Version / 路线图与付费版本

This tool is and will remain **free and open source** on GitHub.

A paid desktop binary is planned for users who want a one-click install without Python setup:

| Tier | What | When |
|------|------|------|
| **Free** | This repo — run from source via `start.sh` | Now |
| **Pro** | Signed `.dmg` (macOS) and `.exe` (Windows) — no Python needed, auto-updates | Coming |
| **Enterprise** | Bulk licence, MDM-deployable `.pkg` for law firms | On request |

The Pro binary will be the **same codebase** — you're just paying to skip the Python setup and get automatic updates. If you're comfortable running `./start.sh`, you never need to pay anything.

> **Want to be notified when the paid version launches?** Star this repo — release announcements go out via GitHub.

---

## Privacy / 隐私说明

All processing happens entirely on your local machine.
No data is transmitted to any server or cloud service.

所有处理均在本地计算机上完成，不向任何服务器或云服务传输数据。

---

## License / 许可证

MIT — see [LICENSE](LICENSE)

---

## Contributing / 贡献

Issues and pull requests welcome.
欢迎提交 Issue 和 Pull Request。
