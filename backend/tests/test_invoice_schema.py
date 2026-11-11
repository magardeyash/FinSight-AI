from __future__ import annotations
from decimal import Decimal
from datetime import date
from app.schemas.invoice import ExtractedInvoice, LineItem


def test_extracted_invoice_valid_gstin():
    data = {
        "invoice_number": "INV-100",
        "vendor_name": "Acme Corp",
        "vendor_gstin": "27AAPFU0939F1ZV",  # Valid 15-char Indian GSTIN
        "buyer_gstin": "29AABCU9603R1ZM",   # Valid
        "grand_total": Decimal("1180.00"),
    }
    inv = ExtractedInvoice.model_validate(data)
    assert inv.vendor_gstin == "27AAPFU0939F1ZV"
    assert inv.buyer_gstin == "29AABCU9603R1ZM"
    assert inv.grand_total == Decimal("1180.00")


def test_extracted_invoice_invalid_gstin_returns_none():
    data = {
        "invoice_number": "INV-101",
        "vendor_name": "Acme Corp",
        "vendor_gstin": "INVALID_GST_123",  # Malformed GSTIN
    }
    inv = ExtractedInvoice.model_validate(data)
    # Must be set to None so risk assessor can flag it
    assert inv.vendor_gstin is None


def test_decimal_precision_preservation():
    data = {
        "subtotal": Decimal("1000.55"),
        "cgst": Decimal("90.05"),
        "sgst": Decimal("90.05"),
        "grand_total": Decimal("1180.65"),
    }
    inv = ExtractedInvoice.model_validate(data)
    assert inv.subtotal == Decimal("1000.55")
    assert (inv.cgst + inv.sgst) == Decimal("180.10")


def test_line_item_validation():
    item = LineItem(
        description="Engineering Consulting",
        quantity=Decimal("10.5"),
        unit_price=Decimal("2000.00"),
        tax_rate=Decimal("18.0"),
        amount=Decimal("21000.00"),
        confidence=0.99,
    )
    assert item.description == "Engineering Consulting"
    assert item.confidence == 0.99
    assert item.amount == Decimal("21000.00")


def test_model_dump_json_compatibility():
    inv = ExtractedInvoice(
        invoice_number="INV-999",
        invoice_date=date(2026, 3, 1),
        grand_total=Decimal("5000.50"),
    )
    dumped = inv.model_dump(mode="json")
    assert dumped["invoice_number"] == "INV-999"
    assert dumped["invoice_date"] == "2026-03-01"
    assert dumped["grand_total"] == "5000.50" or dumped["grand_total"] == 5000.5
