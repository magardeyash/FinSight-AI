from __future__ import annotations
from langgraph.graph import StateGraph, START, END
from app.agents.state import InvoiceState
from app.agents.nodes import (
    document_loader,
    text_extractor,
    invoice_extractor,
    validator,
    duplicate_checker,
    risk_assessor,
    human_review,
    finalizer,
    error_handler,
)

MAX_EXTRACTION_RETRIES = 2


def route_after_loader(state: InvoiceState) -> str:
    """Route to error_handler if document validation failed."""
    if state.get("error_message"):
        return "error_handler"
    return "text_extractor"


def route_after_text_extraction(state: InvoiceState) -> str:
    """Route to error_handler if text extraction failed (e.g. empty or scanned PDF)."""
    if state.get("error_message"):
        return "error_handler"
    return "invoice_extractor"


def route_after_validation(state: InvoiceState) -> str:
    """
    Controlled retry loop for schema extraction:
    - If schema_error is present and retries < MAX_EXTRACTION_RETRIES: retry invoice_extractor
    - If schema_error is present and retries >= MAX_EXTRACTION_RETRIES: route to error_handler
    - If validation succeeded: proceed to duplicate_checker
    """
    schema_err = state.get("schema_error")
    retries = state.get("extraction_retries", 0)

    if schema_err:
        if retries < MAX_EXTRACTION_RETRIES:
            return "invoice_extractor"  # Retry extraction
        return "error_handler"          # All extraction attempts exhausted

    return "duplicate_checker"


def route_after_risk(state: InvoiceState) -> str:
    """Route to human_review if risk score exceeds threshold; otherwise auto-approve via finalizer."""
    if state.get("requires_human_review"):
        return "human_review"
    return "finalizer"


def build_graph() -> StateGraph:
    """Constructs the FinSight AI StateGraph."""
    workflow = StateGraph(InvoiceState)

    # 1. Add all 9 nodes
    workflow.add_node("document_loader", document_loader.run)
    workflow.add_node("text_extractor", text_extractor.run)
    workflow.add_node("invoice_extractor", invoice_extractor.run)
    workflow.add_node("validator", validator.run)
    workflow.add_node("duplicate_checker", duplicate_checker.run)
    workflow.add_node("risk_assessor", risk_assessor.run)
    workflow.add_node("human_review", human_review.run)
    workflow.add_node("finalizer", finalizer.run)
    workflow.add_node("error_handler", error_handler.run)

    # 2. Add edges
    workflow.add_edge(START, "document_loader")

    workflow.add_conditional_edges(
        "document_loader",
        route_after_loader,
        {
            "text_extractor": "text_extractor",
            "error_handler": "error_handler",
        },
    )

    workflow.add_conditional_edges(
        "text_extractor",
        route_after_text_extraction,
        {
            "invoice_extractor": "invoice_extractor",
            "error_handler": "error_handler",
        },
    )

    workflow.add_edge("invoice_extractor", "validator")

    workflow.add_conditional_edges(
        "validator",
        route_after_validation,
        {
            "invoice_extractor": "invoice_extractor",
            "duplicate_checker": "duplicate_checker",
            "error_handler": "error_handler",
        },
    )

    workflow.add_edge("duplicate_checker", "risk_assessor")

    workflow.add_conditional_edges(
        "risk_assessor",
        route_after_risk,
        {
            "human_review": "human_review",
            "finalizer": "finalizer",
        },
    )

    workflow.add_edge("human_review", "finalizer")
    workflow.add_edge("finalizer", END)
    workflow.add_edge("error_handler", END)

    return workflow
