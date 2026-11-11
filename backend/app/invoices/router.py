from __future__ import annotations
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, UploadFile, File, Query, status
from fastapi.responses import FileResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.dependencies import get_db, get_current_user
from app.auth.schemas import UserResponse
from app.invoices.schemas import (
    InvoiceResponse,
    InvoiceListResponse,
    InvoiceStatusResponse,
    InvoiceUpdate,
    InvoiceReviewAction,
    UploadResponse,
    AuditLogResponse,
)
from app.invoices import service
from app.services.storage import StorageService
from app.utils.exceptions import NotFoundError

router = APIRouter(prefix="/invoices", tags=["Invoices"])


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_invoice(
    file: UploadFile = File(...),
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Upload an invoice PDF.
    Returns invoice ID and job ID immediately; processing occurs asynchronously via Celery.
    """
    return await service.upload_invoice(db, current_user.id, file)


@router.get("", response_model=InvoiceListResponse)
async def list_invoices(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    date_from: Optional[datetime] = Query(default=None),
    date_to: Optional[datetime] = Query(default=None),
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    List user's invoices with pagination, status filtering, and keyword search.
    Enforces strict user-level data isolation.
    """
    return await service.list_invoices(
        db,
        user_id=current_user.id,
        page=page,
        page_size=page_size,
        status=status,
        search=search,
        date_from=date_from,
        date_to=date_to,
    )


@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: str,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Get full details of a specific invoice."""
    return await service.get_invoice(db, invoice_id, current_user.id)


@router.get("/{invoice_id}/status", response_model=InvoiceStatusResponse)
async def get_invoice_status(
    invoice_id: str,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Lightweight endpoint for polling background processing status."""
    return await service.get_invoice_status(db, invoice_id, current_user.id)


@router.get("/{invoice_id}/file")
async def get_invoice_file(
    invoice_id: str,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Streams the original uploaded PDF document securely.
    Verifies authentication and tenant ownership before serving the file.
    """
    inv = await service.get_invoice(db, invoice_id, current_user.id)
    doc = await db.invoices.find_one({"_id": invoice_id, "user_id": current_user.id})
    if not doc or "file_path" not in doc:
        raise NotFoundError("Invoice file record not found.")

    storage = StorageService()
    path = storage.get_file_path(doc["file_path"])

    return FileResponse(
        path=str(path),
        media_type="application/pdf",
        filename=inv.original_filename,
    )


@router.patch("/{invoice_id}", response_model=InvoiceResponse)
async def update_invoice(
    invoice_id: str,
    update_data: InvoiceUpdate,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Edit extracted invoice fields manually."""
    return await service.update_invoice(db, invoice_id, current_user.id, update_data)


@router.post("/{invoice_id}/approve", response_model=InvoiceResponse)
async def approve_invoice(
    invoice_id: str,
    review_action: InvoiceReviewAction = InvoiceReviewAction(),
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Approves an invoice pending human review.
    Resumes the persisted LangGraph workflow with reviewer corrections.
    """
    return await service.approve_invoice(db, invoice_id, current_user.id, review_action)


@router.post("/{invoice_id}/reject", response_model=InvoiceResponse)
async def reject_invoice(
    invoice_id: str,
    review_action: InvoiceReviewAction = InvoiceReviewAction(),
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Rejects an invoice pending human review.
    Resumes the LangGraph workflow and marks invoice as REJECTED.
    """
    return await service.reject_invoice(db, invoice_id, current_user.id, review_action)


@router.post("/{invoice_id}/retry", response_model=UploadResponse)
async def retry_invoice(
    invoice_id: str,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Re-enqueues a failed or stuck invoice for processing."""
    return await service.retry_invoice(db, invoice_id, current_user.id)


@router.get("/{invoice_id}/audit", response_model=list[AuditLogResponse])
async def get_invoice_audit_logs(
    invoice_id: str,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Retrieve full audit history for an invoice."""
    return await service.get_audit_logs(db, invoice_id, current_user.id)
