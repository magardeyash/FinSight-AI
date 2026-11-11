from __future__ import annotations
from datetime import datetime, timezone
import redis
from asgiref.sync import async_to_sync
from celery import Task
from app.workers.celery_app import celery_app
from app.agents.graph import build_graph
from app.agents.state import InvoiceState
from app.agents.checkpointer import get_mongo_checkpointer
from app.config import get_settings
from app.database import get_database
from app.utils.logging import logger

settings = get_settings()
_redis_client = redis.from_url(settings.REDIS_URL)


async def _async_process_invoice(
    invoice_id: str,
    user_id: str,
    file_path: str,
    job_id: str,
) -> None:
    db = get_database()

    # Read current job state
    job = await db.processing_jobs.find_one({"_id": job_id})
    if job and job.get("status") in ("COMPLETED", "FAILED", "APPROVED", "REJECTED"):
        logger.info(f"Job {job_id} is already in terminal state '{job.get('status')}'. Skipping.")
        return

    now = datetime.now(timezone.utc)
    await db.processing_jobs.update_one(
        {"_id": job_id},
        {
            "$set": {"status": "PROCESSING", "started_at": now},
            "$inc": {"attempts": 1},
        },
    )
    await db.invoices.update_one(
        {"_id": invoice_id},
        {"$set": {"status": "PROCESSING", "updated_at": now}},
    )

    initial_state: InvoiceState = {
        "invoice_id": invoice_id,
        "user_id": user_id,
        "job_id": job_id,
        "file_path": file_path,
        "file_hash": "",
        "raw_text": "",
        "extracted": {},
        "extraction_retries": 0,
        "schema_error": None,
        "validation_errors": [],
        "is_duplicate": False,
        "duplicate_reason": None,
        "risk_score": 0.0,
        "risk_flags": [],
        "requires_human_review": False,
        "human_decision": None,
        "human_corrections": None,
        "final_status": "PROCESSING",
        "error_message": None,
        "trace_id": None,
    }

    config = {"configurable": {"thread_id": invoice_id}}

    checkpointer = get_mongo_checkpointer()
    graph = build_graph().compile(checkpointer=checkpointer)

    logger.info(f"Starting LangGraph workflow for invoice {invoice_id}...")
    await graph.ainvoke(initial_state, config)


@celery_app.task(
    bind=True,
    max_retries=3,
    name="finsight.process_invoice",
)
def process_invoice(
    self: Task,
    invoice_id: str,
    user_id: str,
    file_path: str,
    job_id: str,
) -> None:
    """
    Celery task that executes the LangGraph invoice processing workflow.
    Uses distributed Redis locking for strict idempotency.
    """
    lock_key = f"finsight:lock:invoice:{invoice_id}"
    # Acquire lock for up to 10 minutes (600s)
    has_lock = _redis_client.set(lock_key, "locked", nx=True, ex=600)

    if not has_lock:
        logger.warning(
            f"Could not acquire distributed lock for invoice {invoice_id}. "
            "Another worker is actively processing it. Skipping duplicate delivery."
        )
        return

    try:
        async_to_sync(_async_process_invoice)(invoice_id, user_id, file_path, job_id)
    except Exception as exc:
        logger.error(f"Task process_invoice failed for invoice {invoice_id}: {exc}")
        countdown = 2 ** self.request.retries * 15  # 15s, 30s, 60s exponential backoff
        raise self.retry(exc=exc, countdown=countdown)
    finally:
        try:
            _redis_client.delete(lock_key)
        except Exception:
            pass
