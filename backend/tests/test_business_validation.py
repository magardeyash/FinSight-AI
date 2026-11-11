from __future__ import annotations
import pytest
from app.agents.nodes import validator
from app.agents.state import InvoiceState


@pytest.mark.asyncio
async def test_business_validation_valid_invoice():
    state: InvoiceState = {
        "invoice_id": "test-1",
        "user_id": "u1",
        "job_id": "j1",
        "file_path": "test.pdf",
        "file_hash": "hash1",
        "raw_text": "text",
        "extracted": {
            "invoice_number": "INV-100",
            "vendor_name": "Acme",
            "invoice_date": "2026-03-01",
            "due_date": "2026-03-31",
            "subtotal": 1000.00,
            "cgst": 90.00,
            "sgst": 90.00,
            "total_tax": 180.00,
            "grand_total": 1180.00,
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
    result = await validator.run(state)
    assert result["schema_error"] is None
    assert len(result["validation_errors"]) == 0


@pytest.mark.asyncio
async def test_business_validation_detects_math_mismatch():
    state: InvoiceState = {
        "invoice_id": "test-2",
        "user_id": "u1",
        "job_id": "j1",
        "file_path": "test.pdf",
        "file_hash": "hash1",
        "raw_text": "text",
        "extracted": {
            "invoice_number": "INV-100",
            "vendor_name": "Acme",
            "invoice_date": "2026-03-01",
            "subtotal": 1000.00,
            "cgst": 90.00,
            "sgst": 90.00,
            "grand_total": 1500.00,  # 1000 + 180 = 1180 != 1500!
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
    result = await validator.run(state)
    assert any("Financial mismatch" in err for err in result["validation_errors"])


@pytest.mark.asyncio
async def test_business_validation_detects_due_date_before_invoice_date():
    state: InvoiceState = {
        "invoice_id": "test-3",
        "user_id": "u1",
        "job_id": "j1",
        "file_path": "test.pdf",
        "file_hash": "hash1",
        "raw_text": "text",
        "extracted": {
            "invoice_number": "INV-100",
            "vendor_name": "Acme",
            "invoice_date": "2026-04-15",
            "due_date": "2026-03-01",  # Due date is before invoice date!
            "grand_total": 500.00,
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
    result = await validator.run(state)
    assert any("earlier than invoice date" in err for err in result["validation_errors"])
