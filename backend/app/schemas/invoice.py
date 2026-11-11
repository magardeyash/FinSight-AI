from __future__ import annotations
import re
from decimal import Decimal
from datetime import date
from typing import Optional, Any
from pydantic import BaseModel, Field, field_validator

# Indian GSTIN format: 2-digit state code + 10-char PAN + 1 entity num + 'Z' + 1 checksum char
GSTIN_RE = re.compile(r"^\d{2}[A-Z]{5}\d{4}[A-Z][A-Z\d]Z[A-Z\d]$")


class LineItem(BaseModel):
    description: str
    quantity: Optional[Decimal] = None
    unit_price: Optional[Decimal] = None
    tax_rate: Optional[Decimal] = None  # percentage e.g. 18.0
    amount: Optional[Decimal] = None
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class ExtractedInvoice(BaseModel):
    invoice_number: Optional[str] = None
    vendor_name: Optional[str] = None
    vendor_gstin: Optional[str] = None
    buyer_name: Optional[str] = None
    buyer_gstin: Optional[str] = None
    invoice_date: Optional[date] = None
    due_date: Optional[date] = None
    currency: str = "INR"
    subtotal: Optional[Decimal] = None
    cgst: Optional[Decimal] = None
    sgst: Optional[Decimal] = None
    igst: Optional[Decimal] = None
    total_tax: Optional[Decimal] = None
    grand_total: Optional[Decimal] = None
    payment_terms: Optional[str] = None
    line_items: list[LineItem] = Field(default_factory=list)
    field_confidence: dict[str, float] = Field(default_factory=dict)

    @field_validator("vendor_gstin", "buyer_gstin", mode="before")
    @classmethod
    def validate_gstin(cls, v: Any) -> Optional[str]:
        if not v or not isinstance(v, str):
            return None
        cleaned = v.strip().upper()
        return cleaned if GSTIN_RE.match(cleaned) else None
