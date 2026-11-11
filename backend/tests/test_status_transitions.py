from __future__ import annotations
import uuid
from datetime import datetime, timezone
import pytest
from app.invoices.repository import atomic_status_transition
from app.database import get_database


@pytest.mark.asyncio
async def test_atomic_status_transition_success():
    db = get_database()
    invoice_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())

    await db.invoices.insert_one({
        "_id": invoice_id,
        "user_id": user_id,
        "status": "REVIEW_REQUIRED",
        "created_at": datetime.now(timezone.utc),
    })

    # Transition to APPROVING succeeds
    res = await atomic_status_transition(
        db,
        invoice_id=invoice_id,
        user_id=user_id,
        expected_status="REVIEW_REQUIRED",
        new_status="APPROVING",
    )
    assert res is not None
    assert res["status"] == "APPROVING"


@pytest.mark.asyncio
async def test_atomic_status_transition_prevents_duplicate_approval():
    db = get_database()
    invoice_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())

    await db.invoices.insert_one({
        "_id": invoice_id,
        "user_id": user_id,
        "status": "APPROVED",  # Already approved
        "created_at": datetime.now(timezone.utc),
    })

    # Second approval attempt expecting REVIEW_REQUIRED must fail (returns None)
    res = await atomic_status_transition(
        db,
        invoice_id=invoice_id,
        user_id=user_id,
        expected_status="REVIEW_REQUIRED",
        new_status="APPROVING",
    )
    assert res is None, "Should not allow transition if invoice is already APPROVED!"
