from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Optional, Any
from fastapi import UploadFile
from motor.motor_asyncio import AsyncIOMotorDatabase
from langgraph.types import Command
from app.invoices.schemas import (
    InvoiceStatus,
    InvoiceResponse,
    InvoiceListResponse,
    InvoiceStatusResponse,
    InvoiceUpdate,
    InvoiceReviewAction,
    UploadResponse,
    PaginationMeta,
    AuditLogResponse,
)
from app.invoices import repository
from app.services.storage import StorageService
from app.agents.graph import build_graph
from app.agents.checkpointer import get_mongo_checkpointer
from app.workers.tasks import process_invoice
from app.utils.exceptions import NotFoundError, ConflictError, BadRequestError
from app.utils.logging import logger


def _format_invoice_response(doc: dict[str, Any]) -> InvoiceResponse:
    extracted = doc.get("extracted", {})
    return InvoiceResponse(
        id=doc["_id"],
        user_id=doc["user_id"],
        original_filename=doc.get("original_filename", "invoice.pdf"),
        file_size_bytes=doc.get("file_size_bytes", 0),
        status=InvoiceStatus(doc.get("status", "UPLOADED")),
        extracted=extracted,
        risk_score=doc.get("risk_score", 0.0),
        risk_flags=doc.get("risk_flags", []),
        validation_errors=doc.get("validation_errors", []),
        is_duplicate=doc.get("is_duplicate", False),
        duplicate_reason=doc.get("duplicate_reason"),
        error_message=doc.get("error_message"),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
        completed_at=doc.get("completed_at"),
    )


async def upload_invoice(
    db: AsyncIOMotorDatabase,
    user_id: str,
    file: UploadFile,
) -> UploadResponse:
    storage = StorageService()
    original_filename, saved_path, file_size = await storage.save_upload(file)

    invoice_id = str(uuid.uuid4())
    job_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    invoice_doc = {
        "_id": invoice_id,
        "user_id": user_id,
        "job_id": job_id,
        "original_filename": original_filename,
        "file_path": str(saved_path),
        "file_size_bytes": file_size,
        "status": InvoiceStatus.QUEUED.value,
        "extracted": {},
        "risk_score": 0.0,
        "risk_flags": [],
        "validation_errors": [],
        "is_duplicate": False,
        "duplicate_reason": None,
        "error_message": None,
        "created_at": now,
        "updated_at": now,
    }
    await repository.create_invoice(db, invoice_doc)

    job_doc = {
        "_id": job_id,
        "invoice_id": invoice_id,
        "user_id": user_id,
        "status": "QUEUED",
        "attempts": 0,
        "created_at": now,
    }
    await repository.create_processing_job(db, job_doc)

    # Initial audit log
    await db.audit_logs.insert_one({
        "invoice_id": invoice_id,
        "user_id": user_id,
        "action": "INVOICE_UPLOADED",
        "detail": f"File '{original_filename}' uploaded and queued for agentic processing.",
        "created_at": now,
    })

    # Dispatch Celery background task
    try:
        process_invoice.delay(
            invoice_id=invoice_id,
            user_id=user_id,
            file_path=str(saved_path),
            job_id=job_id,
        )
    except Exception as exc:
        logger.warning(
            f"Could not enqueue Celery task automatically (Redis/Celery might be offline in test): {exc}. "
            "Job remains QUEUED in database."
        )

    return UploadResponse(
        invoice_id=invoice_id,
        job_id=job_id,
        status=InvoiceStatus.QUEUED,
        original_filename=original_filename,
        message="Invoice uploaded successfully and queued for AI extraction.",
    )


async def get_invoice(db: AsyncIOMotorDatabase, invoice_id: str, user_id: str) -> InvoiceResponse:
    doc = await repository.get_invoice(db, invoice_id, user_id)
    if not doc:
        raise NotFoundError("Invoice not found.")
    return _format_invoice_response(doc)


async def get_invoice_status(db: AsyncIOMotorDatabase, invoice_id: str, user_id: str) -> InvoiceStatusResponse:
    doc = await repository.get_invoice(db, invoice_id, user_id)
    if not doc:
        raise NotFoundError("Invoice not found.")
    return InvoiceStatusResponse(
        id=doc["_id"],
        status=InvoiceStatus(doc["status"]),
        risk_score=doc.get("risk_score", 0.0),
        requires_human_review=(doc.get("status") == InvoiceStatus.REVIEW_REQUIRED.value),
        error_message=doc.get("error_message"),
        updated_at=doc["updated_at"],
    )


async def list_invoices(
    db: AsyncIOMotorDatabase,
    user_id: str,
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
    search: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> InvoiceListResponse:
    docs, total_count, total_pages = await repository.list_invoices(
        db,
        user_id=user_id,
        page=page,
        page_size=page_size,
        status=status,
        search=search,
        date_from=date_from,
        date_to=date_to,
    )
    items = [_format_invoice_response(d) for d in docs]
    return InvoiceListResponse(
        items=items,
        pagination=PaginationMeta(
            page=page,
            page_size=page_size,
            total_count=total_count,
            total_pages=total_pages,
        ),
    )


async def update_invoice(
    db: AsyncIOMotorDatabase,
    invoice_id: str,
    user_id: str,
    update_data: InvoiceUpdate,
) -> InvoiceResponse:
    fields = update_data.model_dump(exclude_unset=True)
    if not fields:
        raise BadRequestError("No fields provided to update.")

    updated_doc = await repository.update_invoice_fields(db, invoice_id, user_id, fields)
    if not updated_doc:
        raise NotFoundError("Invoice not found.")

    # Record edit in audit log
    await db.audit_logs.insert_one({
        "invoice_id": invoice_id,
        "user_id": user_id,
        "action": "FIELDS_EDITED",
        "detail": f"Manual field corrections saved for: {', '.join(fields.keys())}.",
        "created_at": datetime.now(timezone.utc),
    })

    return _format_invoice_response(updated_doc)


async def approve_invoice(
    db: AsyncIOMotorDatabase,
    invoice_id: str,
    user_id: str,
    review_action: InvoiceReviewAction,
) -> InvoiceResponse:
    """
    Approves an invoice in REVIEW_REQUIRED status.
    Uses atomic OCC transition to APPROVING state, resumes LangGraph workflow,
    and finalizer completes it as APPROVED.
    """
    # 1. Atomic transition guard: REVIEW_REQUIRED -> APPROVING
    locked_doc = await repository.atomic_status_transition(
        db,
        invoice_id=invoice_id,
        user_id=user_id,
        expected_status=InvoiceStatus.REVIEW_REQUIRED.value,
        new_status=InvoiceStatus.APPROVING.value,
    )
    if not locked_doc:
        existing = await repository.get_invoice(db, invoice_id, user_id)
        if not existing:
            raise NotFoundError("Invoice not found.")
        raise ConflictError(
            f"Cannot approve invoice. Current status is '{existing.get('status')}', but must be 'REVIEW_REQUIRED'."
        )

    # 2. Resume LangGraph execution via Command(resume=...) if a checkpoint exists
    checkpointer = get_mongo_checkpointer()
    config = {"configurable": {"thread_id": invoice_id}}
    checkpoint = checkpointer.get_tuple(config)

    resume_payload = {
        "action": "approved",
        "corrections": review_action.corrections or {},
        "comment": review_action.comment,
    }

    if checkpoint is not None:
        graph = build_graph().compile(checkpointer=checkpointer)
        try:
            await graph.ainvoke(Command(resume=resume_payload), config)
        except Exception as exc:
            logger.error(f"LangGraph resume failed for invoice {invoice_id}: {exc}. Rolling back to REVIEW_REQUIRED.")
            await repository.atomic_status_transition(
                db,
                invoice_id=invoice_id,
                user_id=user_id,
                expected_status=InvoiceStatus.APPROVING.value,
                new_status=InvoiceStatus.REVIEW_REQUIRED.value,
                extra_fields={"error_message": f"Resume failed: {exc}"},
            )
            raise RuntimeError(f"Workflow resumption error: {exc}") from exc
    else:
        # Direct finalization if no active paused checkpoint
        now = datetime.now(timezone.utc)
        extracted = (locked_doc.get("extracted") or {}).copy()
        if review_action.corrections:
            extracted.update(review_action.corrections)

        await db.invoices.update_one(
            {"_id": invoice_id},
            {
                "$set": {
                    "status": "APPROVED",
                    "extracted": extracted,
                    "updated_at": now,
                    "completed_at": now,
                }
            },
        )
        await db.audit_logs.insert_one({
            "invoice_id": invoice_id,
            "user_id": user_id,
            "action": "INVOICE_APPROVED",
            "detail": f"Invoice manually approved. Comment: {review_action.comment or 'None'}.",
            "created_at": now,
        })

    refetched = await repository.get_invoice(db, invoice_id, user_id)
    return _format_invoice_response(refetched)


async def reject_invoice(
    db: AsyncIOMotorDatabase,
    invoice_id: str,
    user_id: str,
    review_action: InvoiceReviewAction,
) -> InvoiceResponse:
    """
    Rejects an invoice in REVIEW_REQUIRED status.
    Resumes LangGraph workflow with action='rejected'.
    """
    locked_doc = await repository.atomic_status_transition(
        db,
        invoice_id=invoice_id,
        user_id=user_id,
        expected_status=InvoiceStatus.REVIEW_REQUIRED.value,
        new_status=InvoiceStatus.APPROVING.value,
    )
    if not locked_doc:
        existing = await repository.get_invoice(db, invoice_id, user_id)
        if not existing:
            raise NotFoundError("Invoice not found.")
        raise ConflictError(
            f"Cannot reject invoice. Current status is '{existing.get('status')}', but must be 'REVIEW_REQUIRED'."
        )

    checkpointer = get_mongo_checkpointer()
    config = {"configurable": {"thread_id": invoice_id}}
    checkpoint = checkpointer.get_tuple(config)

    resume_payload = {
        "action": "rejected",
        "corrections": None,
        "comment": review_action.comment,
    }

    if checkpoint is not None:
        graph = build_graph().compile(checkpointer=checkpointer)
        try:
            await graph.ainvoke(Command(resume=resume_payload), config)
        except Exception as exc:
            logger.error(f"LangGraph reject resume failed for invoice {invoice_id}: {exc}")
            await repository.atomic_status_transition(
                db,
                invoice_id=invoice_id,
                user_id=user_id,
                expected_status=InvoiceStatus.APPROVING.value,
                new_status=InvoiceStatus.REVIEW_REQUIRED.value,
            )
            raise RuntimeError(f"Workflow resumption error: {exc}") from exc
    else:
        now = datetime.now(timezone.utc)
        await db.invoices.update_one(
            {"_id": invoice_id},
            {
                "$set": {
                    "status": "REJECTED",
                    "updated_at": now,
                    "completed_at": now,
                }
            },
        )
        await db.audit_logs.insert_one({
            "invoice_id": invoice_id,
            "user_id": user_id,
            "action": "INVOICE_REJECTED",
            "detail": f"Invoice manually rejected. Comment: {review_action.comment or 'None'}.",
            "created_at": now,
        })

    refetched = await repository.get_invoice(db, invoice_id, user_id)
    return _format_invoice_response(refetched)


async def retry_invoice(db: AsyncIOMotorDatabase, invoice_id: str, user_id: str) -> UploadResponse:
    """
    Retries an invoice that previously failed (status=FAILED).
    """
    doc = await repository.get_invoice(db, invoice_id, user_id)
    if not doc:
        raise NotFoundError("Invoice not found.")

    if doc.get("status") not in (InvoiceStatus.FAILED.value, InvoiceStatus.PROCESSING.value):
        raise ConflictError(
            f"Only invoices in FAILED or stuck PROCESSING status can be retried (current: '{doc.get('status')}')."
        )

    now = datetime.now(timezone.utc)
    new_job_id = str(uuid.uuid4())

    await db.invoices.update_one(
        {"_id": invoice_id},
        {
            "$set": {
                "status": InvoiceStatus.QUEUED.value,
                "job_id": new_job_id,
                "error_message": None,
                "updated_at": now,
            }
        },
    )

    job_doc = {
        "_id": new_job_id,
        "invoice_id": invoice_id,
        "user_id": user_id,
        "status": "QUEUED",
        "attempts": 0,
        "created_at": now,
    }
    await repository.create_processing_job(db, job_doc)

    await db.audit_logs.insert_one({
        "invoice_id": invoice_id,
        "user_id": user_id,
        "action": "INVOICE_RETRIED",
        "detail": "Invoice processing manually re-triggered.",
        "created_at": now,
    })

    try:
        process_invoice.delay(
            invoice_id=invoice_id,
            user_id=user_id,
            file_path=doc["file_path"],
            job_id=new_job_id,
        )
    except Exception as exc:
        logger.warning(f"Could not re-queue Celery task automatically: {exc}")

    return UploadResponse(
        invoice_id=invoice_id,
        job_id=new_job_id,
        status=InvoiceStatus.QUEUED,
        original_filename=doc.get("original_filename", "invoice.pdf"),
        message="Invoice re-queued for processing.",
    )


async def get_audit_logs(
    db: AsyncIOMotorDatabase,
    invoice_id: str,
    user_id: str,
) -> list[AuditLogResponse]:
    # Ensure invoice exists and belongs to user
    await get_invoice(db, invoice_id, user_id)
    logs = await repository.get_audit_logs(db, invoice_id, user_id)
    return [
        AuditLogResponse(
            id=str(log["_id"]),
            invoice_id=log["invoice_id"],
            user_id=log["user_id"],
            action=log["action"],
            detail=log["detail"],
            metadata=log.get("metadata"),
            created_at=log["created_at"],
        )
        for log in logs
    ]
