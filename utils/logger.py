"""
utils/logger.py — Logging setup.

Writes to ~/legal_desensitizer_log.txt and to the console.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

LOG_FILE = Path.home() / "legal_desensitizer_log.txt"


def setup_logging(level: int = logging.INFO) -> None:
    """
    Configure root logger with:
    - FileHandler → ~/legal_desensitizer_log.txt
    - StreamHandler → stderr
    """
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    handlers: list[logging.Handler] = [
        logging.StreamHandler(),
    ]

    try:
        fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
        handlers.append(fh)
    except OSError:
        pass  # If log file can't be created, just use console

    logging.basicConfig(level=level, format=fmt, datefmt=datefmt, handlers=handlers)
    logging.getLogger(__name__).info("Logging initialised → %s", LOG_FILE)
