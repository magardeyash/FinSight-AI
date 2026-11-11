from __future__ import annotations
import hashlib
from pathlib import Path
from typing import Tuple
import pymupdf  # PyMuPDF / fitz
from app.config import get_settings


class PDFProcessingError(Exception):
    """Raised when PDF extraction fails due to formatting, page limits, or empty content."""
    pass


class PDFProcessor:
    def __init__(self, settings=None):
        self.settings = settings or get_settings()

    def extract_text_and_hash(self, file_path: Path | str) -> Tuple[str, str, int]:
        """
        Extracts digital text from a PDF file using PyMuPDF.
        Computes SHA-256 hash of the file bytes.
        Returns:
            Tuple[raw_text, sha256_hash, page_count]
        Raises:
            PDFProcessingError if file cannot be parsed, exceeds page limits,
            or contains insufficient extractable text (e.g. image-based/scanned).
        """
        path = Path(file_path)
        if not path.exists():
            raise PDFProcessingError(f"File not found at path: {path}")

        try:
            content = path.read_bytes()
            file_hash = hashlib.sha256(content).hexdigest()
        except Exception as exc:
            raise PDFProcessingError(f"Failed to read document bytes: {exc}") from exc

        try:
            doc = pymupdf.open(str(path))
        except Exception as exc:
            raise PDFProcessingError(f"Corrupted or invalid PDF document: {exc}") from exc

        try:
            page_count = doc.page_count
            if page_count > self.settings.MAX_PAGES:
                raise PDFProcessingError(
                    f"Document has {page_count} pages, which exceeds the allowed maximum of {self.settings.MAX_PAGES}."
                )

            extracted_pages: list[str] = []
            for page in doc:
                text = page.get_text("text") or ""
                extracted_pages.append(text)

            full_text = "\n".join(extracted_pages).strip()

            if len(full_text) < self.settings.MIN_TEXT_CHARS:
                raise PDFProcessingError(
                    "This PDF does not contain extractable text. "
                    "Please upload a digitally generated PDF (not a scanned image or photo). "
                    "Only text-based digital PDF invoices are supported."
                )

            return full_text, file_hash, page_count
        finally:
            doc.close()
