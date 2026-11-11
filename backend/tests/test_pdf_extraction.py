from __future__ import annotations
from pathlib import Path
import pytest
from app.services.pdf_processor import PDFProcessor, PDFProcessingError


def test_extract_text_valid_pdf(tmp_path: Path, sample_pdf_bytes: bytes):
    pdf_path = tmp_path / "valid_invoice.pdf"
    pdf_path.write_bytes(sample_pdf_bytes)

    processor = PDFProcessor()
    text, file_hash, page_count = processor.extract_text_and_hash(pdf_path)

    assert "TAX INVOICE" in text
    assert "INV-2026-001" in text
    assert "59,000.00" in text
    assert len(file_hash) == 64  # SHA-256 hex string
    assert page_count == 1


def test_reject_empty_or_scanned_pdf(tmp_path: Path, empty_pdf_bytes: bytes):
    pdf_path = tmp_path / "empty_invoice.pdf"
    pdf_path.write_bytes(empty_pdf_bytes)

    processor = PDFProcessor()
    with pytest.raises(PDFProcessingError) as exc_info:
        processor.extract_text_and_hash(pdf_path)

    assert "does not contain extractable text" in str(exc_info.value)


def test_file_not_found_handling(tmp_path: Path):
    non_existent = tmp_path / "does_not_exist.pdf"
    processor = PDFProcessor()
    with pytest.raises(PDFProcessingError) as exc_info:
        processor.extract_text_and_hash(non_existent)

    assert "File not found" in str(exc_info.value)
