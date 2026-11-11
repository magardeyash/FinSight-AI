from __future__ import annotations
from decimal import Decimal
from app.agents.state import InvoiceState
from app.schemas.invoice import ExtractedInvoice
from app.utils.logging import logger

TOLERANCE = Decimal("0.50")


async def run(state: InvoiceState) -> dict:
    """
    Two-stage deterministic validation:
    Stage 1: Pydantic schema validation (parse raw dict -> ExtractedInvoice).
             If failed, set schema_error and increment extraction_retries.
    Stage 2: Deterministic business rules (financial math, date sanity, required fields).
             Errors are added to validation_errors (do not trigger re-extraction, but feed into risk).
    """
    extracted_raw = state.get("extracted", {})

    # Stage 1: Pydantic schema parsing
    try:
        inv = ExtractedInvoice.model_validate(extracted_raw)
    except Exception as exc:
        retries = state.get("extraction_retries", 0) + 1
        err_msg = f"Schema validation error (attempt {retries}): {exc}"
        logger.warning(f"Invoice {state['invoice_id']} schema invalid: {exc}")
        return {
            "schema_error": err_msg,
            "extraction_retries": retries,
            "validation_errors": [err_msg],
        }

    # Stage 2: Deterministic business rules
    errors: list[str] = []

    # Required fields
    required_fields = ["invoice_number", "vendor_name", "grand_total", "invoice_date"]
    for field in required_fields:
        if getattr(inv, field) is None:
            errors.append(f"Missing required field: {field}")

    # Financial math sanity
    if inv.subtotal is not None and inv.grand_total is not None:
        taxes = Decimal("0")
        for tax_val in [inv.cgst, inv.sgst, inv.igst]:
            if tax_val is not None:
                taxes += tax_val

        # If total_tax was explicitly provided, also verify it
        if inv.total_tax is not None and taxes > Decimal("0") and abs(taxes - inv.total_tax) > TOLERANCE:
            errors.append(
                f"Tax breakdown sum ({taxes}) does not match declared total_tax ({inv.total_tax})."
            )

        expected_grand_total = inv.subtotal + taxes
        if abs(expected_grand_total - inv.grand_total) > TOLERANCE:
            errors.append(
                f"Financial mismatch: subtotal ({inv.subtotal}) + taxes ({taxes}) = {expected_grand_total}, "
                f"which does not match grand_total ({inv.grand_total})."
            )

    # Date sanity
    if inv.invoice_date is not None and inv.due_date is not None:
        if inv.due_date < inv.invoice_date:
            errors.append(
                f"Due date ({inv.due_date}) is earlier than invoice date ({inv.invoice_date})."
            )

    logger.info(
        f"Validation for invoice {state['invoice_id']} completed with {len(errors)} business validation errors."
    )

    return {
        "schema_error": None,
        "validation_errors": errors,
        "extraction_retries": state.get("extraction_retries", 0),
        "extracted": inv.model_dump(mode="json"),
    }
