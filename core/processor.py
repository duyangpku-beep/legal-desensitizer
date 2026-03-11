"""
core/processor.py — Document processors for DOCX and PDF formats.

DocxProcessor: iterates paragraphs + table cells, calls replace_in_paragraph.
PdfProcessor:  uses PyMuPDF (fitz) for text search + redaction annotation.
"""

from __future__ import annotations

import os
import logging
from typing import Callable

from docx import Document

from .replacer import replace_in_paragraph

logger = logging.getLogger(__name__)


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

        # Collect all paragraphs: body + all table cells
        all_paras = list(doc.paragraphs)
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    all_paras.extend(cell.paragraphs)

        # Also process headers / footers
        for section in doc.sections:
            for hf in (section.header, section.footer,
                       section.even_page_header, section.even_page_footer,
                       section.first_page_header, section.first_page_footer):
                if hf is not None:
                    all_paras.extend(hf.paragraphs)

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
        """Extract plain text from a .docx file (for detection phase)."""
        doc   = Document(input_path)
        parts = [p.text for p in doc.paragraphs]
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    parts.extend(p.text for p in cell.paragraphs)
        return "\n".join(parts)


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
                instances = page.search_for(original)
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
        return "\n".join(parts)


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
