from __future__ import annotations
import uuid
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import MagicMock
import pytest
from langgraph.types import Command
from app.agents.graph import build_graph
from app.agents.state import InvoiceState
from app.agents.checkpointer import get_mongo_checkpointer
from app.schemas.invoice import ExtractedInvoice
from app.database import get_database


@pytest.mark.asyncio
async def test_human_review_interrupt_and_resumption(tmp_path, sample_pdf_bytes, mock_gemini):
    """
    Critical Integration Test:
    1. An invoice with high risk (financial mismatch / low confidence) triggers interrupt().
    2. LangGraph pauses execution, state is checkpointed to real MongoDB.
    3. The invoice status in MongoDB is set to REVIEW_REQUIRED.
    4. Simulate process restart / new execution context with same checkpointer + thread_id.
    5. Call graph.ainvoke(Command(resume={"action": "approved", "corrections": {"vendor_name": "Corrected Vendor Corp"}})).
    6. Graph resumes, merges corrections, and finalizer marks status as APPROVED in MongoDB.
    """
    # Configure mock gemini to return risky invoice data (subtotal 500 != grand total 1000 -> mismatch error -> risk >= 0.40)
    risky_invoice = ExtractedInvoice(
        invoice_number="INV-RISKY-001",
        vendor_name="Risky Vendor Corp",
        subtotal=Decimal("500.00"),
        grand_total=Decimal("1000.00"),  # financial mismatch -> triggers validation error -> risk
        field_confidence={"invoice_number": 0.4, "vendor_name": 0.5},
    )
    mock_gemini.with_structured_output.return_value.invoke = MagicMock(return_value=risky_invoice)

    db = get_database()
    invoice_id = f"inv_hil_{uuid.uuid4().hex[:8]}"
    user_id = str(uuid.uuid4())
    job_id = str(uuid.uuid4())

    pdf_file = tmp_path / "review_invoice.pdf"
    pdf_file.write_bytes(sample_pdf_bytes)

    now = datetime.now(timezone.utc)
    await db.invoices.insert_one({
        "_id": invoice_id,
        "user_id": user_id,
        "job_id": job_id,
        "status": "PROCESSING",
        "file_path": str(pdf_file),
        "created_at": now,
        "updated_at": now,
    })
    await db.processing_jobs.insert_one({
        "_id": job_id,
        "invoice_id": invoice_id,
        "status": "PROCESSING",
        "created_at": now,
    })

    checkpointer = get_mongo_checkpointer()
    graph_instance_1 = build_graph().compile(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": invoice_id}}

    initial_state: InvoiceState = {
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

    # 1. First execution: runs until human_review node and interrupts
    result_interrupted = await graph_instance_1.ainvoke(initial_state, config)

    # 2. Verify invoice in MongoDB is now REVIEW_REQUIRED
    db_invoice_paused = await db.invoices.find_one({"_id": invoice_id})
    assert db_invoice_paused["status"] == "REVIEW_REQUIRED"
    assert db_invoice_paused["risk_score"] >= 0.40

    # 3. Simulate process restart: create a completely new graph instance with the same checkpointer
    graph_instance_2 = build_graph().compile(checkpointer=checkpointer)

    # 4. Resume via Command with human decision and corrections
    resume_payload = {
        "action": "approved",
        "corrections": {
            "vendor_name": "Corrected Vendor Corp",
            "grand_total": 500.0,
        },
    }
    resume_command = Command(resume=resume_payload)

    result_resumed = await graph_instance_2.ainvoke(resume_command, config)

    # 5. Verify final status is APPROVED and corrections are merged
    assert result_resumed["final_status"] == "APPROVED"
    assert result_resumed["extracted"]["vendor_name"] == "Corrected Vendor Corp"

    db_invoice_final = await db.invoices.find_one({"_id": invoice_id})
    assert db_invoice_final["status"] == "APPROVED"
    assert db_invoice_final["extracted"]["vendor_name"] == "Corrected Vendor Corp"
    assert db_invoice_final["extracted"]["grand_total"] == 500.0

    # 6. Verify audit log entry
    audit_entry = await db.audit_logs.find_one({"invoice_id": invoice_id, "action": "INVOICE_APPROVED"})
    assert audit_entry is not None
    assert "Reviewer applied corrections" in audit_entry["detail"]
