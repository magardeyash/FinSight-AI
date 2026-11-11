from __future__ import annotations
import os
import time
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from app.agents.state import InvoiceState
from app.schemas.invoice import ExtractedInvoice
from app.agents.prompts.extraction import (
    INVOICE_EXTRACTION_SYSTEM_PROMPT,
    INVOICE_EXTRACTION_USER_PROMPT,
)
from app.config import get_settings
from app.services.observability import get_tracer
from app.utils.logging import logger


async def run(state: InvoiceState) -> dict:
    """
    Extracts invoice data using Gemini 2.5 Flash with structured Pydantic schema.
    Traced with Langfuse when available.
    """
    settings = get_settings()
    raw_text = state.get("raw_text", "")
    retries = state.get("extraction_retries", 0)

    if not raw_text:
        return {
            "error_message": "No raw text available for invoice extraction.",
            "extracted": {},
            "schema_error": "Missing raw text",
        }

    # Verify API key
    api_key = settings.GOOGLE_API_KEY or os.environ.get("GOOGLE_API_KEY", "")
    if not api_key:
        err = "GOOGLE_API_KEY is not configured. Real invoice extraction requires a valid Gemini API key."
        logger.error(err)
        return {
            "error_message": err,
            "extracted": {},
            "schema_error": err,
        }

    tracer = get_tracer()
    trace_span = None
    if tracer:
        try:
            trace_span = tracer.start_as_current_span(
                name="gemini-invoice-extraction",
                input={
                    "invoice_id": state["invoice_id"],
                    "retry_attempt": retries,
                    "text_length": len(raw_text),
                },
            )
        except Exception as t_err:
            logger.debug(f"Could not start Langfuse span: {t_err}")

    start_time = time.time()
    try:
        llm = ChatGoogleGenerativeAI(
            model=settings.GEMINI_MODEL,
            google_api_key=api_key,
            temperature=0.0,
        )
        structured_llm = llm.with_structured_output(ExtractedInvoice, method="json_schema")

        user_content = INVOICE_EXTRACTION_USER_PROMPT.format(document_text=raw_text)
        if retries > 0 and state.get("schema_error"):
            user_content += f"\n\nNOTE: A previous extraction attempt failed with error: {state.get('schema_error')}. Please extract strictly according to the schema."

        messages = [
            SystemMessage(content=INVOICE_EXTRACTION_SYSTEM_PROMPT),
            HumanMessage(content=user_content),
        ]

        logger.info(
            f"Invoking Gemini ({settings.GEMINI_MODEL}) for invoice {state['invoice_id']} (attempt {retries + 1})..."
        )
        # Structured output invocation
        result = structured_llm.invoke(messages)

        duration = time.time() - start_time
        logger.info(f"Gemini extraction succeeded in {duration:.2f}s for invoice {state['invoice_id']}.")

        if isinstance(result, ExtractedInvoice):
            extracted_dict = result.model_dump(mode="json")
        elif isinstance(result, dict):
            extracted_dict = result
        else:
            extracted_dict = {}

        if trace_span:
            trace_span.update(
                output={"invoice_number": extracted_dict.get("invoice_number")},
                metadata={"duration_seconds": duration},
            )

        return {
            "extracted": extracted_dict,
            "schema_error": None,  # clear stale error
            "error_message": None,
        }

    except Exception as exc:
        duration = time.time() - start_time
        logger.error(f"Gemini extraction failed after {duration:.2f}s: {exc}")
        if trace_span:
            trace_span.update(level="ERROR", status_message=str(exc))

        return {
            "extracted": {},
            "schema_error": f"Extraction exception: {exc}",
            "error_message": f"LLM extraction error: {exc}",
        }
    finally:
        if trace_span:
            try:
                trace_span.end()
            except Exception:
                pass
