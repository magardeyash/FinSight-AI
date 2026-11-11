from __future__ import annotations
import uuid
from datetime import datetime, timezone
import pytest
import redis
from app.config import get_settings
from app.database import get_database
from app.workers.tasks import process_invoice


def test_redis_distributed_locking_prevents_concurrent_runs(monkeypatch):
    """Simulates two worker processes trying to pick up the same invoice simultaneously."""
    settings = get_settings()
    r = redis.from_url(settings.REDIS_URL)

    test_invoice_id = f"inv_lock_{uuid.uuid4().hex[:8]}"
    lock_key = f"finsight:lock:invoice:{test_invoice_id}"

    # Pre-acquire the lock to simulate Worker A is busy with this invoice
    r.set(lock_key, "locked_by_worker_a", ex=60)

    # Worker B tries to process invoice
    executed = False

    def fake_async_process(*args, **kwargs):
        nonlocal executed
        executed = True

    monkeypatch.setattr("app.workers.tasks._async_process_invoice", fake_async_process)

    # Calling process_invoice should skip execution because lock is held
    process_invoice(
        invoice_id=test_invoice_id,
        user_id="u1",
        file_path="dummy.pdf",
        job_id="j1",
    )

    assert executed is False, "Task should have skipped execution because lock was held!"

    # Clean up lock
    r.delete(lock_key)


@pytest.mark.asyncio
async def test_terminal_job_is_skipped(monkeypatch):
    """Task ignores redelivery if job is already marked COMPLETED or APPROVED."""
    db = get_database()
    invoice_id = str(uuid.uuid4())
    job_id = str(uuid.uuid4())

    await db.processing_jobs.insert_one({
        "_id": job_id,
        "invoice_id": invoice_id,
        "status": "COMPLETED",
        "created_at": datetime.now(timezone.utc),
    })

    from app.workers.tasks import _async_process_invoice
    # Running this on a completed job should return early without modifying invoice
    await _async_process_invoice(invoice_id, "u1", "dummy.pdf", job_id)

    # Invoice was not touched
    doc = await db.invoices.find_one({"_id": invoice_id})
    assert doc is None
