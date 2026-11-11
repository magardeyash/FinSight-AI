from __future__ import annotations
from datetime import datetime, timezone
from app.agents.state import InvoiceState
from app.database import get_database
from app.utils.logging import logger


async def run(state: InvoiceState) -> dict:
    """
    Finalizes the invoice lifecycle:
    - Merges human corrections if provided.
    - Persists final status (APPROVED or REJECTED).
    - Updates processing job status to COMPLETED.
    - Creates durable audit log record.
    """
    db = get_database()
    invoice_id = state["invoice_id"]
    user_id = state["user_id"]
    job_id = state.get("job_id")

    human_decision = state.get("human_decision")
    corrections = state.get("human_corrections") or {}

    extracted = state.get("extracted", {}).copy()
    if corrections and isinstance(corrections, dict):
        extracted.update(corrections)

    if human_decision == "rejected":
        final_status = "REJECTED"
        audit_action = "INVOICE_REJECTED"
        audit_detail = "Invoice was rejected during manual human review."
    else:
        final_status = "APPROVED"
        if human_decision == "approved":
            audit_action = "INVOICE_APPROVED"
            audit_detail = "Invoice was approved after manual human review."
            if corrections:
                audit_detail += f" Reviewer applied corrections to fields: {', '.join(corrections.keys())}."
        else:
            audit_action = "INVOICE_AUTO_APPROVED"
            audit_detail = "Invoice passed deterministic validation and risk assessment; auto-approved."

    now = datetime.now(timezone.utc)

    # 1. Update invoice in MongoDB
    await db.invoices.update_one(
        {"_id": invoice_id},
        {
            "$set": {
                "status": final_status,
                "extracted": extracted,
                "risk_score": state.get("risk_score", 0.0),
                "risk_flags": state.get("risk_flags", []),
                "validation_errors": state.get("validation_errors", []),
                "is_duplicate": state.get("is_duplicate", False),
                "duplicate_reason": state.get("duplicate_reason"),
                "human_decision": human_decision,
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
                    "status": "COMPLETED",
                    "final_invoice_status": final_status,
                    "completed_at": now,
                }
            },
        )

    # 3. Create audit log entry
    await db.audit_logs.insert_one({
        "invoice_id": invoice_id,
        "user_id": user_id,
        "action": audit_action,
        "detail": audit_detail,
        "metadata": {
            "risk_score": state.get("risk_score"),
            "risk_flags": state.get("risk_flags"),
            "has_corrections": bool(corrections),
        },
        "created_at": now,
    })

    logger.info(f"Invoice {invoice_id} successfully finalized with status: {final_status}")

    return {
        "final_status": final_status,
        "extracted": extracted,
    }
