"""
core/replacer.py — Formatting-safe text replacement helpers.

Key design decisions:
  1. Case-insensitive matching (re.IGNORECASE) so that user-entered lowercase
     terms match ALL-CAPS text in the document (e.g. "cansino biologics" →
     "CANSINO BIOLOGICS (HONG KONG) LIMITED").
  2. Use para._p.iter(w:t) instead of para.runs so that text inside SDT
     Content Controls (common in cover pages and form fields) is also reached.
     para.runs only returns *direct* w:r children; SDT-wrapped runs are nested
     deeper and would otherwise be silently skipped.
  3. Single-pass regex substitution prevents shorter patterns from replacing
     text inside an already-substituted replacement string.
  4. Longest key first so "Alpha Capital Limited" wins over "Alpha".
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from docx.text.paragraph import Paragraph


def _build_sub_pattern(replacements: dict[str, str]) -> re.Pattern[str]:
    """
    Build a case-insensitive alternation pattern from *replacements*,
    longest key first so longer matches always win.
    """
    sorted_keys = sorted(replacements, key=len, reverse=True)
    return re.compile(
        "|".join(re.escape(k) for k in sorted_keys),
        re.IGNORECASE,
    )


def _make_sub(replacements: dict[str, str], count: list[int]):
    """
    Return a re.sub callback that:
      1. Tries an exact-case dict lookup first (fast path for auto-detected
         terms that already have correct capitalisation).
      2. Falls back to a lowercase-key lookup (handles user-entered terms
         that differ in case from the document text).
    """
    ci_map = {k.lower(): v for k, v in replacements.items()}

    def _sub(m: re.Match[str]) -> str:
        count[0] += 1
        t = m.group(0)
        return replacements.get(t) or ci_map.get(t.lower(), t)

    return _sub


def replace_in_paragraph(para: "Paragraph", replacements: dict[str, str]) -> int:
    """
    Replace terms in *para* while preserving run-level formatting.

    Collects text from ALL w:t descendants (not just para.runs) so that
    text inside SDT Content Controls is also covered.  Writes the replaced
    text back to the first w:t element and blanks the rest; the surrounding
    w:rPr (bold/italic/font/colour) is untouched.

    Returns:
        Number of replacements made.
    """
    if not replacements:
        return 0

    from docx.oxml.ns import qn

    # Collect every w:t element in this paragraph, regardless of depth.
    # This handles: bare runs, SDT-wrapped runs, hyperlink runs, etc.
    wt_elems = [wt for wt in para._p.iter(qn('w:t')) if wt.text is not None]
    if not wt_elems:
        return 0

    full_text = "".join(wt.text for wt in wt_elems).replace('\xa0', ' ')
    count     = [0]
    pattern   = _build_sub_pattern(replacements)
    new_text  = pattern.sub(_make_sub(replacements, count), full_text)

    if new_text == full_text:
        return 0

    # Write all replaced text into the first w:t; blank subsequent w:t elements.
    wt_elems[0].text = new_text
    for wt in wt_elems[1:]:
        wt.text = ""

    return count[0]


def replace_in_text(text: str, replacements: dict[str, str]) -> tuple[str, int]:
    """
    Apply all replacements to a plain string (used for PDFs / plain-text paths).

    Case-insensitive single-pass substitution.

    Returns:
        (new_text, total_count)
    """
    if not replacements:
        return text, 0

    count    = [0]
    pattern  = _build_sub_pattern(replacements)
    new_text = pattern.sub(_make_sub(replacements, count), text)
    return new_text, count[0]


def escape_for_regex(term: str) -> str:
    """Return regex-escaped version of *term* for use in re.sub."""
    return re.escape(term)
