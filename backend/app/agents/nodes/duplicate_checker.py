from __future__ import annotations
from app.agents.state import InvoiceState
from app.database import get_database
from app.utils.logging import logger


async def run(state: InvoiceState) -> dict:
    """
    Checks for duplicates in MongoDB:
    1. Exact file duplicate by SHA-256 file_hash under same user_id.
    2. Business duplicate by (vendor_name + invoice_number) under same user_id.
    Enforces user-level tenant isolation.
    """
    db = get_database()
    user_id = state["user_id"]
    invoice_id = state["invoice_id"]
    file_hash = state.get("file_hash")
    extracted = state.get("extracted", {})

    is_duplicate = False
    duplicate_reason = None

    # 1. Exact file hash duplicate check
    if file_hash:
        existing_file = await db.invoices.find_one({
            "user_id": user_id,
            "file_hash": file_hash,
            "_id": {"$ne": invoice_id},
        })
        if existing_file:
            is_duplicate = True
            duplicate_reason = f"Identical file already uploaded on {existing_file.get('created_at')} (Invoice ID: {existing_file['_id']})"

    # 2. Business key duplicate check (vendor + invoice_number)
    if not is_duplicate:
        inv_num = extracted.get("invoice_number")
        vendor = extracted.get("vendor_name")
        if inv_num and vendor:
            existing_inv = await db.invoices.find_one({
                "user_id": user_id,
                "_id": {"$ne": invoice_id},
                "extracted.invoice_number": inv_num,
                "extracted.vendor_name": vendor,
                "status": {"$in": ["APPROVED", "REVIEW_REQUIRED", "APPROVING"]},
            })
            if existing_inv:
                is_duplicate = True
                duplicate_reason = (
                    f"Duplicate invoice detected: Vendor '{vendor}' with invoice number '{inv_num}' "
                    f"was already recorded on {existing_inv.get('created_at')} (Invoice ID: {existing_inv['_id']})"
                )

    if is_duplicate:
        logger.warning(f"Duplicate flagged for invoice {invoice_id}: {duplicate_reason}")
    else:
        logger.info(f"Duplicate check passed for invoice {invoice_id}.")

    return {
        "is_duplicate": is_duplicate,
        "duplicate_reason": duplicate_reason,
    }
