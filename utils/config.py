"""
utils/config.py — Persistent JSON config for user preferences.

Config file: ~/.legal_desensitizer/config.json
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

CONFIG_DIR  = Path.home() / ".legal_desensitizer"
CONFIG_FILE = CONFIG_DIR / "config.json"


@dataclass
class AppConfig:
    """All user-configurable settings."""
    custom_terms:             list[str] = field(default_factory=list)
    custom_replacement:       str       = "【】"
    last_output_dir:          str       = ""
    detect_parties:           bool      = True
    detect_amounts:           bool      = True
    detect_phones:            bool      = True
    detect_emails:            bool      = True
    detect_ids:               bool      = True
    detect_addresses:         bool      = True
    detect_names:             bool      = True
    detect_other_companies:   bool      = True
    window_geometry:          str       = "820x680"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AppConfig":
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        filtered   = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)


def load_config() -> AppConfig:
    """Load config from disk; return defaults if not found or malformed."""
    if not CONFIG_FILE.exists():
        return AppConfig()
    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            data = json.load(f)
        return AppConfig.from_dict(data)
    except (json.JSONDecodeError, TypeError, KeyError) as exc:
        logger.warning("Config load failed (%s) — using defaults.", exc)
        return AppConfig()


def save_config(cfg: AppConfig) -> None:
    """Persist config to disk."""
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg.to_dict(), f, ensure_ascii=False, indent=2)
        logger.debug("Config saved → %s", CONFIG_FILE)
    except OSError as exc:
        logger.error("Config save failed: %s", exc)
