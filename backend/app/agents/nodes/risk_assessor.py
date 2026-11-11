from __future__ import annotations
from app.agents.state import InvoiceState
from app.utils.logging import logger

REVIEW_THRESHOLD = 0.40


async def run(state: InvoiceState) -> dict:
    """
    Evaluates explainable risk signals deterministically without trusting LLM self-evaluation.
    Scores range from 0.0 to 1.0 (capped).
    If risk_score >= REVIEW_THRESHOLD (0.40), requires_human_review is set to True.
    """
    score = 0.0
    flags: list[str] = []
    extracted = state.get("extracted", {})

    # 1. Validation issues (business rule failures)
    validation_errors = state.get("validation_errors", [])
    if validation_errors:
        score += 0.25
        flags.append(f"Validation failure ({len(validation_errors)} error(s)): {validation_errors[0]}")

    # 2. Duplicate invoice flag
    if state.get("is_duplicate"):
        score += 0.35
        flags.append(f"Duplicate invoice: {state.get('duplicate_reason', 'Identical invoice recorded')}")

    # 3. Missing critical required fields
    critical_fields = ["invoice_number", "vendor_name", "grand_total"]
    missing_fields = [f for f in critical_fields if extracted.get(f) is None]
    if missing_fields:
        score += 0.20
        flags.append(f"Missing mandatory fields: {', '.join(missing_fields)}")

    # 4. Low-confidence fields (< 0.6)
    conf_dict = extracted.get("field_confidence", {})
    low_conf_keys = [
        k for k, v in conf_dict.items()
        if isinstance(v, (int, float)) and v < 0.6
    ]
    if low_conf_keys:
        conf_penalty = min(0.20, 0.10 * len(low_conf_keys))
        score += conf_penalty
        flags.append(f"Low extraction confidence on fields: {', '.join(low_conf_keys[:3])}")

    # 5. Missing GSTIN for Indian vendor
    if not extracted.get("vendor_gstin"):
        score += 0.10
        flags.append("Vendor GSTIN is missing or invalid format")

    final_score = min(round(score, 3), 1.0)
    requires_review = final_score >= REVIEW_THRESHOLD

    logger.info(
        f"Invoice {state['invoice_id']} risk evaluated: score={final_score}, "
        f"requires_human_review={requires_review}, flags={flags}"
    )

    return {
        "risk_score": final_score,
        "risk_flags": flags,
        "requires_human_review": requires_review,
    }
