from __future__ import annotations
from datetime import datetime, timezone
from app.agents.state import InvoiceState
from app.database import get_database
from app.utils.logging import logger


async def run(state: InvoiceState) -> dict:
    """
    Terminal failure node:
    - Marks invoice as FAILED
    - Updates processing_jobs with error detail
    - Adds audit log entry
    Ensures no job is ever left hanging in PROCESSING.
    """
    db = get_database()
    invoice_id = state.get("invoice_id")
    user_id = state.get("user_id")
    job_id = state.get("job_id")
    error_msg = state.get("error_message") or state.get("schema_error") or "Unknown processing failure"

    now = datetime.now(timezone.utc)
    logger.error(f"Routing invoice {invoice_id} to error_handler: {error_msg}")

    # 1. Update invoice if invoice_id is known
    if invoice_id:
        await db.invoices.update_one(
            {"_id": invoice_id},
            {
                "$set": {
                    "status": "FAILED",
                    "error_message": error_msg,
                    "updated_at": now,
                    "completed_at": now,
                }
            },
        )

    # 2. Update processing job
    if job_id:
        await db.processing_jobs.update_one(
            {"_id": job_id},
            {
                "$set": {
                    "status": "FAILED",
                    "error": error_msg,
                    "completed_at": now,
                }
            },
        )

    # 3. Create audit log
    if invoice_id and user_id:
        await db.audit_logs.insert_one({
            "invoice_id": invoice_id,
            "user_id": user_id,
            "action": "PROCESSING_FAILED",
            "detail": f"Invoice processing failed: {error_msg}",
            "metadata": {
                "retries": state.get("extraction_retries", 0),
                "file_path": state.get("file_path"),
            },
            "created_at": now,
        })

    return {
        "final_status": "FAILED",
        "error_message": error_msg,
    }
