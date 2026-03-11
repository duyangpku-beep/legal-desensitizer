"""
core/replacer.py — Formatting-safe text replacement helpers.

Key fix over v1: replacements operate at run level so bold/italic/font/color
formatting is preserved.  A "re-flow" strategy is used: collect all run text
into one string, apply replacements, then write the result back to the first
run and blank the rest.  This preserves the first run's formatting for the
full paragraph — adequate for legal documents where leading text carries the
relevant formatting.

Single-pass regex substitution is used (rather than chained str.replace) so
that shorter patterns cannot accidentally replace text inside an already-
substituted replacement string.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from docx.text.paragraph import Paragraph


def _build_sub_pattern(replacements: dict[str, str]) -> re.Pattern[str]:
    """
    Build a compiled alternation pattern from *replacements*, longest key first.
    This guarantees that longer matches take priority over shorter ones and that
    each span of text is replaced at most once.
    """
    sorted_keys = sorted(replacements, key=len, reverse=True)
    return re.compile("|".join(re.escape(k) for k in sorted_keys))


def replace_in_paragraph(para: "Paragraph", replacements: dict[str, str]) -> int:
    """
    Replace terms in *para* while preserving run-level formatting.

    Args:
        para:         python-docx Paragraph object.
        replacements: Mapping of {original_text: replacement_text}.

    Returns:
        Number of replacements made.
    """
    if not para.runs or not replacements:
        return 0

    full_text = "".join(run.text for run in para.runs)
    count     = [0]
    pattern   = _build_sub_pattern(replacements)

    def _sub(m: re.Match[str]) -> str:
        count[0] += 1
        return replacements[m.group(0)]

    new_text = pattern.sub(_sub, full_text)

    if new_text == full_text:
        return 0

    # Re-distribute: first run gets all text, remaining runs are blanked.
    # This keeps the first run's character formatting (font, size, bold, etc.).
    para.runs[0].text = new_text
    for run in para.runs[1:]:
        run.text = ""

    return count[0]


def replace_in_text(text: str, replacements: dict[str, str]) -> tuple[str, int]:
    """
    Apply all replacements to a plain string (used for PDFs / plain-text paths).

    Single-pass: each position in the string is considered exactly once,
    so shorter patterns cannot replace text inside a substituted replacement.

    Returns:
        (new_text, total_count)
    """
    if not replacements:
        return text, 0

    count   = [0]
    pattern = _build_sub_pattern(replacements)

    def _sub(m: re.Match[str]) -> str:
        count[0] += 1
        return replacements[m.group(0)]

    new_text = pattern.sub(_sub, text)
    return new_text, count[0]


def escape_for_regex(term: str) -> str:
    """Return regex-escaped version of *term* for use in re.sub."""
    return re.escape(term)
