from __future__ import annotations
import uuid
from datetime import datetime, timezone
import pytest
from app.agents.nodes import duplicate_checker
from app.agents.state import InvoiceState
from app.database import get_database


@pytest.mark.asyncio
async def test_duplicate_file_hash_detection():
    db = get_database()
    user_id = str(uuid.uuid4())
    existing_id = str(uuid.uuid4())
    current_id = str(uuid.uuid4())
    test_hash = "abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789"

    # Insert existing invoice record with hash
    await db.invoices.insert_one({
        "_id": existing_id,
        "user_id": user_id,
        "file_hash": test_hash,
        "status": "APPROVED",
        "created_at": datetime.now(timezone.utc),
    })

    state: InvoiceState = {
        "invoice_id": current_id,
        "user_id": user_id,
        "job_id": "j1",
        "file_path": "new.pdf",
        "file_hash": test_hash,  # same hash!
        "raw_text": "",
        "extracted": {"invoice_number": "NEW-1", "vendor_name": "New Vendor"},
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

    result = await duplicate_checker.run(state)
    assert result["is_duplicate"] is True
    assert "Identical file already uploaded" in result["duplicate_reason"]


@pytest.mark.asyncio
async def test_duplicate_vendor_invoice_number_detection():
    db = get_database()
    user_id = str(uuid.uuid4())
    existing_id = str(uuid.uuid4())
    current_id = str(uuid.uuid4())

    await db.invoices.insert_one({
        "_id": existing_id,
        "user_id": user_id,
        "file_hash": "hash_different_1",
        "status": "APPROVED",
        "extracted": {
            "invoice_number": "INV-777",
            "vendor_name": "Unique Tech Services",
        },
        "created_at": datetime.now(timezone.utc),
    })

    state: InvoiceState = {
        "invoice_id": current_id,
        "user_id": user_id,
        "job_id": "j2",
        "file_path": "test.pdf",
        "file_hash": "hash_different_2",
        "raw_text": "",
        "extracted": {
            "invoice_number": "INV-777",
            "vendor_name": "Unique Tech Services",
        },
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

    result = await duplicate_checker.run(state)
    assert result["is_duplicate"] is True
    assert "Unique Tech Services" in result["duplicate_reason"]
    assert "INV-777" in result["duplicate_reason"]


@pytest.mark.asyncio
async def test_tenant_isolation_duplicate_checking():
    """Different users having same invoice number/hash must NOT flag duplicate."""
    db = get_database()
    user_a = str(uuid.uuid4())
    user_b = str(uuid.uuid4())

    await db.invoices.insert_one({
        "_id": str(uuid.uuid4()),
        "user_id": user_a,
        "file_hash": "shared_hash_123",
        "status": "APPROVED",
        "extracted": {"invoice_number": "INV-ISOLATION", "vendor_name": "Cross Vendor"},
        "created_at": datetime.now(timezone.utc),
    })

    state: InvoiceState = {
        "invoice_id": str(uuid.uuid4()),
        "user_id": user_b,  # User B!
        "job_id": "j3",
        "file_path": "test.pdf",
        "file_hash": "shared_hash_123",
        "raw_text": "",
        "extracted": {"invoice_number": "INV-ISOLATION", "vendor_name": "Cross Vendor"},
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

    result = await duplicate_checker.run(state)
    # Must NOT be marked duplicate because it belongs to a different tenant!
    assert result["is_duplicate"] is False
    assert result["duplicate_reason"] is None
