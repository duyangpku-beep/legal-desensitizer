#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# Legal Desensitizer v2.1.0 — Start Script
# 法律文件脱敏工具启动脚本
#
# 使用方法 / Usage:
#   chmod +x start.sh   （首次运行前 / before first run）
#   ./start.sh
#
# 自动完成 / Auto-handles:
#   - 创建 Python 虚拟环境 / Creates virtual environment
#   - 安装依赖 / Installs dependencies
#   - 启动 GUI / Launches the GUI
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR="$SCRIPT_DIR/venv"
REQ_FILE="$SCRIPT_DIR/requirements.txt"
REQ_STAMP="$VENV_DIR/.req_installed"

# ── 颜色 / colours ────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✓${NC} $*"; }
info() { echo -e "${YELLOW}⚙${NC} $*"; }
err()  { echo -e "${RED}✗${NC} $*" >&2; }

# ── 1. 检查 python3 / Check python3 ──────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
    err "找不到 python3 / python3 not found."
    err "请先安装 Python 3.9+ / Please install Python 3.9+ first:"
    err "  https://www.python.org/downloads/"
    exit 1
fi

PY_VER=$(python3 -c 'import sys; print(sys.version_info[:2])')
ok "Python $PY_VER"

# ── 2. 创建虚拟环境 / Create venv ─────────────────────────────────────────────
if [ ! -d "$VENV_DIR" ]; then
    info "首次运行，创建虚拟环境... / First run — creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

# ── 3. 安装依赖（仅在 requirements.txt 变化时）/ Install deps if changed ───────
NEEDS_INSTALL=false
if [ ! -f "$REQ_STAMP" ]; then
    NEEDS_INSTALL=true
elif ! diff -q "$REQ_FILE" "$REQ_STAMP" &>/dev/null; then
    NEEDS_INSTALL=true
fi

if $NEEDS_INSTALL; then
    info "安装依赖... / Installing dependencies..."
    pip install -q --upgrade pip
    pip install -q -r "$REQ_FILE"
    cp "$REQ_FILE" "$REQ_STAMP"
    ok "依赖已就绪 / Dependencies ready"
else
    ok "依赖已是最新 / Dependencies up to date"
fi

# ── 4. 启动 / Launch ─────────────────────────────────────────────────────────
echo ""
echo "  ⚖  Legal Document Desensitizer  法律文件脱敏工具  v2.1.0"
echo "  100% offline · 完全本地 · DOCX + PDF"
echo ""
python3 app.py
