from __future__ import annotations
import math
from datetime import datetime, timezone
from typing import Optional, Any
from motor.motor_asyncio import AsyncIOMotorDatabase


async def create_invoice(db: AsyncIOMotorDatabase, doc: dict[str, Any]) -> dict[str, Any]:
    await db.invoices.insert_one(doc)
    return doc


async def get_invoice(db: AsyncIOMotorDatabase, invoice_id: str, user_id: str) -> Optional[dict[str, Any]]:
    return await db.invoices.find_one({"_id": invoice_id, "user_id": user_id})


async def list_invoices(
    db: AsyncIOMotorDatabase,
    user_id: str,
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
    search: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    sort_by: str = "created_at",
    sort_order: int = -1,
) -> tuple[list[dict[str, Any]], int, int]:
    """
    Paginated query with user-level isolation and multi-field search.
    Returns: (items, total_count, total_pages)
    """
    query: dict[str, Any] = {"user_id": user_id}

    if status:
        query["status"] = status

    if search:
        search_re = {"$regex": search, "$options": "i"}
        query["$or"] = [
            {"original_filename": search_re},
            {"extracted.invoice_number": search_re},
            {"extracted.vendor_name": search_re},
            {"extracted.buyer_name": search_re},
        ]

    if date_from or date_to:
        query["created_at"] = {}
        if date_from:
            query["created_at"]["$gte"] = date_from
        if date_to:
            query["created_at"]["$lte"] = date_to

    total_count = await db.invoices.count_documents(query)
    total_pages = max(1, math.ceil(total_count / page_size))
    skip = (page - 1) * page_size

    cursor = db.invoices.find(query).sort(sort_by, sort_order).skip(skip).limit(page_size)
    items = await cursor.to_list(length=page_size)

    return items, total_count, total_pages


async def update_invoice_fields(
    db: AsyncIOMotorDatabase,
    invoice_id: str,
    user_id: str,
    fields: dict[str, Any],
) -> Optional[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    set_fields = {f"extracted.{k}": v for k, v in fields.items()}
    set_fields["updated_at"] = now

    result = await db.invoices.find_one_and_update(
        {"_id": invoice_id, "user_id": user_id},
        {"$set": set_fields},
        return_document=True,
    )
    return result


async def atomic_status_transition(
    db: AsyncIOMotorDatabase,
    invoice_id: str,
    user_id: str,
    expected_status: str | list[str],
    new_status: str,
    extra_fields: Optional[dict[str, Any]] = None,
) -> Optional[dict[str, Any]]:
    """
    Optimistic concurrency control:
    Atomically transitions invoice status ONLY if current status matches expected_status.
    Prevents race conditions / duplicate approval executions.
    """
    now = datetime.now(timezone.utc)
    status_filter = (
        {"$in": expected_status} if isinstance(expected_status, list) else expected_status
    )

    query = {
        "_id": invoice_id,
        "user_id": user_id,
        "status": status_filter,
    }

    set_fields = {"status": new_status, "updated_at": now}
    if extra_fields:
        set_fields.update(extra_fields)

    updated = await db.invoices.find_one_and_update(
        query,
        {"$set": set_fields},
        return_document=True,
    )
    return updated


async def create_processing_job(db: AsyncIOMotorDatabase, job_doc: dict[str, Any]) -> dict[str, Any]:
    await db.processing_jobs.insert_one(job_doc)
    return job_doc


async def get_processing_job(db: AsyncIOMotorDatabase, job_id: str) -> Optional[dict[str, Any]]:
    return await db.processing_jobs.find_one({"_id": job_id})


async def get_audit_logs(db: AsyncIOMotorDatabase, invoice_id: str, user_id: str) -> list[dict[str, Any]]:
    cursor = db.audit_logs.find({"invoice_id": invoice_id, "user_id": user_id}).sort("created_at", -1)
    return await cursor.to_list(length=100)
