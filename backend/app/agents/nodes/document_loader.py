from __future__ import annotations
from pathlib import Path
from app.agents.state import InvoiceState
from app.config import get_settings


async def run(state: InvoiceState) -> dict:
    """
    Validates that the file exists and is accessible.
    """
    settings = get_settings()
    file_path_str = state.get("file_path")
    if not file_path_str:
        return {"error_message": "Document file path is missing from state."}

    file_path = Path(file_path_str)
    if not file_path.exists():
        return {"error_message": f"Document file not found at: {file_path.name}"}

    file_size_mb = file_path.stat().st_size / (1024 * 1024)
    if file_size_mb > settings.MAX_FILE_SIZE_MB:
        return {
            "error_message": (
                f"File size ({file_size_mb:.2f} MB) exceeds maximum allowed "
                f"limit of {settings.MAX_FILE_SIZE_MB} MB."
            )
        }

    return {"error_message": None}
