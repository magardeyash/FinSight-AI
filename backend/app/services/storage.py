from __future__ import annotations
import uuid
from pathlib import Path
from fastapi import UploadFile
from app.config import get_settings
from app.utils.exceptions import BadRequestError, NotFoundError


class StorageService:
    def __init__(self, settings=None):
        self.settings = settings or get_settings()
        self.upload_dir = Path(self.settings.UPLOAD_DIR).resolve()
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    async def save_upload(self, file: UploadFile) -> tuple[str, Path, int]:
        """
        Validates and saves an uploaded PDF file safely.
        Returns:
            Tuple[original_filename, saved_file_path, file_size_bytes]
        """
        filename = file.filename or "invoice.pdf"
        if not filename.lower().endswith(".pdf"):
            raise BadRequestError("Only PDF documents (.pdf) are allowed.")

        # Read content
        content = await file.read()
        file_size = len(content)

        max_bytes = self.settings.MAX_FILE_SIZE_MB * 1024 * 1024
        if file_size > max_bytes:
            raise BadRequestError(
                f"File size exceeds maximum allowed limit of {self.settings.MAX_FILE_SIZE_MB}MB."
            )

        if not content.startswith(b"%PDF-"):
            raise BadRequestError("Invalid PDF header. File is not a valid PDF document.")

        # Generate unique storage filename
        unique_name = f"{uuid.uuid4().hex}_{Path(filename).name}"
        destination = (self.upload_dir / unique_name).resolve()

        # Path traversal guard
        if not str(destination).startswith(str(self.upload_dir)):
            raise BadRequestError("Invalid file path.")

        destination.write_bytes(content)
        return filename, destination, file_size

    def get_file_path(self, stored_path_str: str) -> Path:
        """Resolves and validates that the file exists and is inside the upload directory."""
        path = Path(stored_path_str).resolve()
        if not str(path).startswith(str(self.upload_dir)) or not path.exists():
            raise NotFoundError("The requested document file could not be found.")
        return path
