"""
core/processor.py — Document processors for DOCX and PDF formats.

DocxProcessor: iterates paragraphs + table cells, calls replace_in_paragraph.
PdfProcessor:  uses PyMuPDF (fitz) for text search + redaction annotation.
"""

from __future__ import annotations

import os
import re
import logging
from typing import Callable

from docx import Document

from .replacer import replace_in_paragraph

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# PDF text normalisation helpers
# ─────────────────────────────────────────────────────────────────────────────

_LIGATURES = str.maketrans({
    'ﬁ': 'fi', 'ﬂ': 'fl', 'ﬀ': 'ff', 'ﬃ': 'ffi', 'ﬄ': 'ffl', 'ﬅ': 'st', 'ﬆ': 'st',
})


def _normalize_pdf_text(text: str) -> str:
    """Collapse letter-spaced digits/chars and expand ligatures."""
    # Collapse spaces between individual CJK characters
    text = re.sub(r'(?<=[\u4e00-\u9fff])\s(?=[\u4e00-\u9fff])', '', text)
    # Collapse spaces between digits (letter-spaced numbers)
    text = re.sub(r'(?<=\d) (?=\d)', '', text)
    # Expand ligatures
    text = text.translate(_LIGATURES)
    # Remove soft hyphens and line-break hyphens
    text = re.sub(r'-\n', '', text)
    text = text.replace('\xad', '')
    return text


def _find_by_words(page, term: str) -> list:
    """Find `term` by reassembling adjacent words — handles ligatures + spacing."""
    import fitz  # noqa: F401 (imported for fitz.Rect)
    words = page.get_text("words")  # (x0,y0,x1,y1,text,block,line,word_no)
    parts = term.strip().split()
    n = len(parts)
    if n == 0 or not words:
        return []
    results = []
    for i in range(len(words) - n + 1):
        chunk = [words[i + j][4].lower() for j in range(n)]
        if chunk == [p.lower() for p in parts]:
            x0 = min(words[i + j][0] for j in range(n))
            y0 = min(words[i + j][1] for j in range(n))
            x1 = max(words[i + j][2] for j in range(n))
            y1 = max(words[i + j][3] for j in range(n))
            results.append(fitz.Rect(x0, y0, x1, y1))
    return results


def _find_text_instances(page, term: str) -> list:
    """Find all bounding boxes for `term` on `page` using three-tier fallback."""
    # Tier 1: direct exact search
    rects = page.search_for(term)
    if rects:
        return rects
    # Tier 2: case-normalised (English terms)
    rects = page.search_for(term.lower())
    if rects:
        return rects
    # Tier 3: word-level reassembly
    return _find_by_words(page, term)


# ─────────────────────────────────────────────────────────────────────────────
# DOCX paragraph collection helper
# ─────────────────────────────────────────────────────────────────────────────

def _collect_all_paragraphs(doc: "Document") -> list:
    """
    Collect ALL Paragraph objects in a DOCX document, including:
    - Body paragraphs
    - Table cell paragraphs (all nesting levels)
    - Text box paragraphs (w:txbxContent, floating and inline)
    - Header and footer paragraphs (and their text boxes)

    Uses XML iter() so no paragraph is ever missed regardless of nesting depth.
    """
    from docx.oxml.ns import qn
    from docx.text.paragraph import Paragraph

    paras: list = []
    seen: set[int] = set()

    def _harvest(root_elem) -> None:
        for p_elem in root_elem.iter(qn('w:p')):
            eid = id(p_elem)
            if eid not in seen:
                seen.add(eid)
                paras.append(Paragraph(p_elem, doc))

    _harvest(doc.element.body)
    for section in doc.sections:
        for hf in (
            section.header, section.footer,
            section.even_page_header, section.even_page_footer,
            section.first_page_header, section.first_page_footer,
        ):
            if hf is not None:
                _harvest(hf._element)

    return paras


# ─────────────────────────────────────────────────────────────────────────────
# DocxProcessor
# ─────────────────────────────────────────────────────────────────────────────

class DocxProcessor:
    """
    Process a single .docx file: replace all sensitive terms while preserving
    run-level character formatting (bold, italic, font, colour, etc.).
    """

    def process(
        self,
        input_path: str,
        replacements: dict[str, str],
        output_path: str,
        progress_cb: Callable[[int, int], None] | None = None,
    ) -> dict[str, int]:
        """
        Args:
            input_path:   Path to source .docx file.
            replacements: Mapping {original → replacement}.
            output_path:  Where to write the desensitised file.
            progress_cb:  Optional callback(current_para, total_paras).

        Returns:
            Dict of {entity_text: count_replaced}.
        """
        doc   = Document(input_path)
        stats: dict[str, int] = {}

        # Collect ALL paragraphs: body, nested tables, text boxes, headers/footers
        all_paras = _collect_all_paragraphs(doc)

        total = len(all_paras)
        for idx, para in enumerate(all_paras):
            n = replace_in_paragraph(para, replacements)
            if n:
                # Attribute count to each replacement that matched
                for original in replacements:
                    if original in para.runs[0].text or \
                       any(original in run.text for run in para.runs):
                        stats[original] = stats.get(original, 0)
                # Rough: accumulate total per file
                stats["__total__"] = stats.get("__total__", 0) + n
            if progress_cb:
                progress_cb(idx + 1, total)

        doc.save(output_path)
        logger.info("DOCX saved → %s (%d replacements)", output_path, stats.get("__total__", 0))
        return stats

    @staticmethod
    def extract_text(input_path: str) -> str:
        """Extract plain text from a .docx file (for detection phase).

        Covers body paragraphs, nested tables, text boxes, and headers/footers.
        Normalises non-breaking spaces (\\xa0) → regular spaces so that
        detection regex patterns match reliably.
        """
        from docx.oxml.ns import qn
        doc = Document(input_path)
        parts = [para.text for para in _collect_all_paragraphs(doc)]
        return "\n".join(parts).replace('\xa0', ' ')


# ─────────────────────────────────────────────────────────────────────────────
# PdfProcessor
# ─────────────────────────────────────────────────────────────────────────────

class PdfProcessor:
    """
    Process a single .pdf file using PyMuPDF redaction annotations.

    Strategy:
    - For each term, search every page for occurrences.
    - Add a white-fill redaction rectangle over each hit.
    - Overlay the replacement text centred in the redaction box.
    - Apply redactions and save.

    Note: PDF text layout is not perfectly preserved after redaction — this is
    the industry-standard approach for PDF desensitisation.
    """

    def process(
        self,
        input_path: str,
        replacements: dict[str, str],
        output_path: str,
        progress_cb: Callable[[int, int], None] | None = None,
    ) -> dict[str, int]:
        """
        Args:
            input_path:   Path to source .pdf file.
            replacements: Mapping {original → replacement}.
            output_path:  Where to write the redacted PDF.
            progress_cb:  Optional callback(current_page, total_pages).

        Returns:
            Dict {"__total__": count}.
        """
        try:
            import fitz  # PyMuPDF
        except ImportError as exc:
            raise RuntimeError(
                "PyMuPDF is required for PDF support.\n"
                "Install with: pip install PyMuPDF\n"
                "PyMuPDF 需要安装才能支持 PDF 文件。"
            ) from exc

        doc   = fitz.open(input_path)
        total = doc.page_count
        count = 0

        for page_idx, page in enumerate(doc):
            for original, replacement in replacements.items():
                instances = _find_text_instances(page, original)
                if not instances:
                    logger.debug("PDF: no match for %r on page %d", original, page_idx + 1)
                for rect in instances:
                    # Add redaction annotation: white fill, overlay replacement text
                    annot = page.add_redact_annot(
                        rect,
                        text=replacement,
                        fontsize=10,
                        fill=(1, 1, 1),      # white background
                        text_color=(0, 0, 0), # black text
                    )
                    count += 1
            page.apply_redactions()
            if progress_cb:
                progress_cb(page_idx + 1, total)

        doc.save(output_path)
        doc.close()
        logger.info("PDF saved → %s (%d redactions)", output_path, count)
        return {"__total__": count}

    @staticmethod
    def extract_text(input_path: str) -> str:
        """Extract plain text from a .pdf file (for detection phase)."""
        try:
            import fitz
        except ImportError:
            return ""
        doc   = fitz.open(input_path)
        parts = [page.get_text() for page in doc]
        doc.close()
        return _normalize_pdf_text("\n".join(parts))


# ─────────────────────────────────────────────────────────────────────────────
# Batch helper
# ─────────────────────────────────────────────────────────────────────────────

def make_output_path(input_path: str, suffix: str = "_脱敏") -> str:
    """
    Derive output path from input path.
    e.g. /dir/contract.docx → /dir/contract_脱敏.docx
    """
    base, ext = os.path.splitext(input_path)
    return f"{base}{suffix}{ext}"


def get_processor(file_path: str) -> DocxProcessor | PdfProcessor:
    """Return the appropriate processor based on file extension."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        return PdfProcessor()
    return DocxProcessor()
