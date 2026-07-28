"""PDF text extraction using PyMuPDF.

Extracts text page-by-page from PDF documents, preserving page numbers
for downstream metadata attachment. PyMuPDF is chosen over PyPDF2
for significantly better multilingual text extraction, particularly
for Tamil scripts and mixed English/Tamil documents.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PageContent:
    """Text content extracted from a single PDF page.

    Attributes:
        text: Raw text content of the page.
        page_number: 1-indexed page number.
        document_name: Filename of the source PDF.
    """

    text: str
    page_number: int
    document_name: str


def load_pdf(file_path: Path) -> list[PageContent]:
    """Extract text from every page of a PDF document.

    Args:
        file_path: Absolute path to the PDF file.

    Returns:
        List of PageContent objects, one per page that contained
        extractable text. Pages with no text are logged and skipped.

    Raises:
        FileNotFoundError: If the PDF does not exist.
        RuntimeError: If PyMuPDF cannot open the file.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"PDF not found: {file_path}")

    document_name = file_path.name
    pages: list[PageContent] = []

    try:
        doc = fitz.open(str(file_path))
    except Exception as exc:
        raise RuntimeError(f"Failed to open PDF '{file_path}': {exc}") from exc

    try:
        for page_idx in range(len(doc)):
            page = doc[page_idx]
            text = page.get_text("text")

            if not text or not text.strip():
                logger.warning(
                    "Page %d of '%s' has no extractable text — skipping",
                    page_idx + 1,
                    document_name,
                )
                continue

            pages.append(
                PageContent(
                    text=text,
                    page_number=page_idx + 1,
                    document_name=document_name,
                )
            )

        logger.info(
            "Extracted %d pages from '%s' (%d total pages)",
            len(pages),
            document_name,
            len(doc),
        )
    finally:
        doc.close()

    return pages
