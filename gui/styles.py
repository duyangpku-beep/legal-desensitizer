"""
gui/styles.py — ttk style definitions for the Legal Desensitizer UI.
"""

from __future__ import annotations

import sys
import tkinter as tk
from tkinter import ttk


# Colour palette
PALETTE = {
    "bg":          "#F5F5F0",
    "sidebar":     "#2C3E50",
    "accent":      "#2980B9",
    "accent_dark": "#1F618D",
    "success":     "#27AE60",
    "warning":     "#F39C12",
    "danger":      "#E74C3C",
    "text":        "#2C3E50",
    "muted":       "#7F8C8D",
    "white":       "#FFFFFF",
    "border":      "#BDC3C7",
}

# Font stack — prefer system CJK fonts, fall back gracefully
if sys.platform == "darwin":
    FONT_FAMILY = "PingFang SC"
elif sys.platform == "win32":
    FONT_FAMILY = "Microsoft YaHei"
else:
    FONT_FAMILY = "Noto Sans CJK SC"


def apply_styles(root: tk.Tk) -> ttk.Style:
    """Apply all custom ttk styles to *root* and return the Style object."""
    style = ttk.Style(root)

    # Use a clean base theme
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    root.configure(bg=PALETTE["bg"])

    # ── Labels ────────────────────────────────────────────────────────────
    style.configure("Title.TLabel",
                    font=(FONT_FAMILY, 16, "bold"),
                    foreground=PALETTE["text"],
                    background=PALETTE["bg"])

    style.configure("Subtitle.TLabel",
                    font=(FONT_FAMILY, 10),
                    foreground=PALETTE["muted"],
                    background=PALETTE["bg"])

    style.configure("Header.TLabel",
                    font=(FONT_FAMILY, 11, "bold"),
                    foreground=PALETTE["text"],
                    background=PALETTE["bg"])

    style.configure("Normal.TLabel",
                    font=(FONT_FAMILY, 10),
                    foreground=PALETTE["text"],
                    background=PALETTE["bg"])

    style.configure("Muted.TLabel",
                    font=(FONT_FAMILY, 9),
                    foreground=PALETTE["muted"],
                    background=PALETTE["bg"])

    style.configure("Success.TLabel",
                    font=(FONT_FAMILY, 10),
                    foreground=PALETTE["success"],
                    background=PALETTE["bg"])

    # ── Buttons ───────────────────────────────────────────────────────────
    style.configure("Primary.TButton",
                    font=(FONT_FAMILY, 10, "bold"),
                    foreground=PALETTE["white"],
                    background=PALETTE["accent"],
                    padding=(12, 6))
    style.map("Primary.TButton",
              background=[("active", PALETTE["accent_dark"]),
                          ("disabled", PALETTE["border"])])

    style.configure("Secondary.TButton",
                    font=(FONT_FAMILY, 10),
                    padding=(10, 5))

    style.configure("Danger.TButton",
                    font=(FONT_FAMILY, 10),
                    foreground=PALETTE["white"],
                    background=PALETTE["danger"],
                    padding=(10, 5))

    # ── Frames ────────────────────────────────────────────────────────────
    style.configure("Card.TFrame",
                    background=PALETTE["white"],
                    relief="flat")

    style.configure("TFrame",
                    background=PALETTE["bg"])

    style.configure("TLabelframe",
                    background=PALETTE["bg"],
                    foreground=PALETTE["text"],
                    font=(FONT_FAMILY, 10, "bold"))

    style.configure("TLabelframe.Label",
                    background=PALETTE["bg"],
                    foreground=PALETTE["accent"],
                    font=(FONT_FAMILY, 10, "bold"))

    # ── Notebook tabs ─────────────────────────────────────────────────────
    style.configure("TNotebook",
                    background=PALETTE["bg"],
                    tabmargins=[2, 5, 2, 0])

    style.configure("TNotebook.Tab",
                    font=(FONT_FAMILY, 10),
                    padding=[12, 6],
                    background=PALETTE["border"])

    style.map("TNotebook.Tab",
              background=[("selected", PALETTE["white"])],
              foreground=[("selected", PALETTE["accent"])])

    # ── Checkbuttons ──────────────────────────────────────────────────────
    style.configure("TCheckbutton",
                    font=(FONT_FAMILY, 10),
                    background=PALETTE["bg"])

    # ── Entry ─────────────────────────────────────────────────────────────
    style.configure("TEntry",
                    font=(FONT_FAMILY, 10),
                    padding=4)

    # ── Progressbar ───────────────────────────────────────────────────────
    style.configure("Accent.Horizontal.TProgressbar",
                    troughcolor=PALETTE["border"],
                    background=PALETTE["accent"],
                    thickness=12)

    # ── Separator ─────────────────────────────────────────────────────────
    style.configure("TSeparator", background=PALETTE["border"])

    return style
