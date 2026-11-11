from __future__ import annotations
from datetime import datetime, timezone
from langgraph.types import interrupt
from app.agents.state import InvoiceState
from app.database import get_database
from app.utils.logging import logger


async def run(state: InvoiceState) -> dict:
    """
    Human-in-the-Loop review node using LangGraph native interrupt/resume.

    First pass:
      - Marks invoice status in MongoDB as REVIEW_REQUIRED
      - interrupt() halts execution and persists checkpoint to MongoDB
    Second pass (on resume with Command(resume=...)):
      - Node re-executes from top and interrupt() returns the resume payload
      - Passes human_decision ("approved"|"rejected") and corrections down to finalizer
    """
    invoice_id = state["invoice_id"]
    db = get_database()

    # Update MongoDB status to REVIEW_REQUIRED before pausing
    now = datetime.now(timezone.utc)
    await db.invoices.update_one(
        {"_id": invoice_id, "status": {"$in": ["PROCESSING", "QUEUED"]}},
        {
            "$set": {
                "status": "REVIEW_REQUIRED",
                "risk_score": state["risk_score"],
                "risk_flags": state["risk_flags"],
                "validation_errors": state.get("validation_errors", []),
                "extracted": state.get("extracted", {}),
                "updated_at": now,
            }
        },
    )

    logger.info(f"LangGraph pausing at human_review for invoice {invoice_id}...")

    # LangGraph interrupt primitive
    resume_payload = interrupt({
        "invoice_id": invoice_id,
        "risk_score": state["risk_score"],
        "risk_flags": state["risk_flags"],
        "validation_errors": state.get("validation_errors", []),
        "extracted": state.get("extracted", {}),
        "message": "Invoice requires manual review and approval before finalization.",
    })

    # Resumed execution
    action = resume_payload.get("action", "approved") if isinstance(resume_payload, dict) else "approved"
    corrections = resume_payload.get("corrections") if isinstance(resume_payload, dict) else None

    logger.info(f"LangGraph resumed for invoice {invoice_id} with human decision: {action}")

    return {
        "human_decision": action,
        "human_corrections": corrections,
    }
