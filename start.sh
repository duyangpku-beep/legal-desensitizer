#!/bin/bash
# ─────────────────────────────────────────────────────────────
# Legal Desensitizer — Quick Start
# Run this once to set up, then again any time to launch.
# ─────────────────────────────────────────────────────────────

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR="$SCRIPT_DIR/venv"

# ── 1. Create venv if it doesn't exist ───────────────────────
if [ ! -d "$VENV_DIR" ]; then
    echo "⚙ First run — setting up virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

# ── 2. Activate ──────────────────────────────────────────────
source "$VENV_DIR/bin/activate"

# ── 3. Install / update dependencies silently ────────────────
echo "⚙ Checking dependencies..."
pip install -q -r requirements.txt

# ── 4. Launch ────────────────────────────────────────────────
echo "✓ Launching Legal Desensitizer..."
python app.py
