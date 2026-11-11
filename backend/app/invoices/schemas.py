from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, Field


class InvoiceStatus(str, Enum):
    UPLOADED = "UPLOADED"
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    APPROVING = "APPROVING"
    APPROVED = "APPROVED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    FAILED = "FAILED"
    REJECTED = "REJECTED"


class InvoiceItem(BaseModel):
    description: str
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    tax_rate: Optional[float] = None
    amount: Optional[float] = None
    confidence: Optional[float] = None


class InvoiceData(BaseModel):
    invoice_number: Optional[str] = None
    vendor_name: Optional[str] = None
    vendor_gstin: Optional[str] = None
    buyer_name: Optional[str] = None
    buyer_gstin: Optional[str] = None
    invoice_date: Optional[str] = None
    due_date: Optional[str] = None
    currency: Optional[str] = "INR"
    subtotal: Optional[float] = None
    cgst: Optional[float] = None
    sgst: Optional[float] = None
    igst: Optional[float] = None
    total_tax: Optional[float] = None
    grand_total: Optional[float] = None
    payment_terms: Optional[str] = None
    line_items: list[dict[str, Any]] = Field(default_factory=list)
    field_confidence: dict[str, float] = Field(default_factory=dict)


class InvoiceResponse(BaseModel):
    id: str
    user_id: str
    original_filename: str
    file_size_bytes: int
    status: InvoiceStatus
    extracted: InvoiceData = Field(default_factory=InvoiceData)
    risk_score: float = 0.0
    risk_flags: list[str] = Field(default_factory=list)
    validation_errors: list[str] = Field(default_factory=list)
    is_duplicate: bool = False
    duplicate_reason: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None


class InvoiceStatusResponse(BaseModel):
    id: str
    status: InvoiceStatus
    risk_score: float = 0.0
    requires_human_review: bool = False
    error_message: Optional[str] = None
    updated_at: datetime


class InvoiceUpdate(BaseModel):
    invoice_number: Optional[str] = None
    vendor_name: Optional[str] = None
    vendor_gstin: Optional[str] = None
    buyer_name: Optional[str] = None
    buyer_gstin: Optional[str] = None
    invoice_date: Optional[str] = None
    due_date: Optional[str] = None
    currency: Optional[str] = None
    subtotal: Optional[float] = None
    cgst: Optional[float] = None
    sgst: Optional[float] = None
    igst: Optional[float] = None
    total_tax: Optional[float] = None
    grand_total: Optional[float] = None
    payment_terms: Optional[str] = None
    line_items: Optional[list[dict[str, Any]]] = None


class InvoiceReviewAction(BaseModel):
    corrections: Optional[dict[str, Any]] = None
    comment: Optional[str] = None


class UploadResponse(BaseModel):
    invoice_id: str
    job_id: str
    status: InvoiceStatus
    original_filename: str
    message: str


class PaginationMeta(BaseModel):
    page: int
    page_size: int
    total_count: int
    total_pages: int


class InvoiceListResponse(BaseModel):
    items: list[InvoiceResponse]
    pagination: PaginationMeta


class AuditLogResponse(BaseModel):
    id: str
    invoice_id: str
    user_id: str
    action: str
    detail: str
    metadata: Optional[dict[str, Any]] = None
    created_at: datetime
