from __future__ import annotations
from typing import Optional
from typing_extensions import TypedDict


class InvoiceState(TypedDict):
    # Identity
    invoice_id: str
    user_id: str
    job_id: str

    # File
    file_path: str
    file_hash: str

    # Extraction
    raw_text: str
    extracted: dict
    extraction_retries: int

    # Validation
    schema_error: Optional[str]
    validation_errors: list[str]

    # Duplicate checking
    is_duplicate: bool
    duplicate_reason: Optional[str]

    # Risk assessment
    risk_score: float
    risk_flags: list[str]
    requires_human_review: bool

    # Human review
    human_decision: Optional[str]      # "approved" | "rejected"
    human_corrections: Optional[dict]

    # Terminal state
    final_status: str
    error_message: Optional[str]

    # Tracing / observability
    trace_id: Optional[str]
