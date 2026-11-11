from __future__ import annotations
from app.agents.state import InvoiceState
from app.services.pdf_processor import PDFProcessor, PDFProcessingError
from app.utils.logging import logger


async def run(state: InvoiceState) -> dict:
    """
    Extracts text and SHA-256 hash using PyMuPDF.
    If text is absent or insufficient, returns user-friendly error message.
    """
    processor = PDFProcessor()
    file_path = state["file_path"]

    try:
        raw_text, file_hash, page_count = processor.extract_text_and_hash(file_path)
        logger.info(
            f"Extracted {len(raw_text)} characters across {page_count} pages from {file_path}."
        )
        return {
            "raw_text": raw_text,
            "file_hash": file_hash,
            "error_message": None,
        }
    except PDFProcessingError as exc:
        logger.warning(f"PDF processing failed for {file_path}: {exc}")
        return {
            "error_message": str(exc),
            "raw_text": "",
            "file_hash": state.get("file_hash", ""),
        }
    except Exception as exc:
        logger.error(f"Unexpected error extracting text from {file_path}: {exc}")
        return {
            "error_message": f"Failed to extract document contents: {exc}",
            "raw_text": "",
        }
