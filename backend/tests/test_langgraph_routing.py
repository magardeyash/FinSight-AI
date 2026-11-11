from __future__ import annotations
import uuid
import pytest
from app.agents.graph import build_graph, route_after_loader, route_after_validation, route_after_risk
from app.agents.state import InvoiceState
from app.database import get_database


def test_routing_functions():
    # 1. Loader routing
    assert route_after_loader({"error_message": "File not found"}) == "error_handler"
    assert route_after_loader({"error_message": None}) == "text_extractor"

    # 2. Validation retry routing
    # Schema error with retries < 2 -> loops back to invoice_extractor
    state_retry: InvoiceState = {"schema_error": "Invalid format", "extraction_retries": 1}
    assert route_after_validation(state_retry) == "invoice_extractor"

    # Schema error with retries >= 2 -> terminal error_handler
    state_exhausted: InvoiceState = {"schema_error": "Invalid format", "extraction_retries": 2}
    assert route_after_validation(state_exhausted) == "error_handler"

    # Validation passed -> duplicate_checker
    state_ok: InvoiceState = {"schema_error": None, "extraction_retries": 0}
    assert route_after_validation(state_ok) == "duplicate_checker"

    # 3. Risk routing
    assert route_after_risk({"requires_human_review": True}) == "human_review"
    assert route_after_risk({"requires_human_review": False}) == "finalizer"


@pytest.mark.asyncio
async def test_end_to_end_graph_auto_approval(mock_gemini, sample_pdf_bytes, tmp_path):
    """End-to-end graph execution when invoice is low-risk (auto-approved)."""
    db = get_database()
    invoice_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    job_id = str(uuid.uuid4())

    pdf_file = tmp_path / "valid_invoice.pdf"
    pdf_file.write_bytes(sample_pdf_bytes)

    # Insert initial DB records
    await db.invoices.insert_one({
        "_id": invoice_id,
        "user_id": user_id,
        "status": "PROCESSING",
        "file_path": str(pdf_file),
    })
    await db.processing_jobs.insert_one({
        "_id": job_id,
        "invoice_id": invoice_id,
        "status": "PROCESSING",
    })

    graph = build_graph().compile()

    state: InvoiceState = {
        "invoice_id": invoice_id,
        "user_id": user_id,
        "job_id": job_id,
        "file_path": str(pdf_file),
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

    result = await graph.ainvoke(state)
    assert result["final_status"] == "APPROVED"
    assert result["extracted"]["invoice_number"] == "INV-2026-001"

    # Verify MongoDB persistence
    db_invoice = await db.invoices.find_one({"_id": invoice_id})
    assert db_invoice["status"] == "APPROVED"
    assert db_invoice["extracted"]["vendor_name"] == "Antigravity Cloud Technologies Pvt Ltd"

    db_job = await db.processing_jobs.find_one({"_id": job_id})
    assert db_job["status"] == "COMPLETED"

    audit_entry = await db.audit_logs.find_one({"invoice_id": invoice_id})
    assert audit_entry is not None
    assert audit_entry["action"] in ("INVOICE_AUTO_APPROVED", "INVOICE_APPROVED")
