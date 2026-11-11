from __future__ import annotations
import io
from pathlib import Path
from typing import AsyncGenerator
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
import pymupdf
from unittest.mock import MagicMock, patch

from app.main import create_app
from app.config import get_settings
from app.database import get_database


SAMPLE_EXTRACTED_DATA = {
    "invoice_number": "INV-2026-001",
    "vendor_name": "Antigravity Cloud Technologies Pvt Ltd",
    "vendor_gstin": "27AAPFU0939F1ZV",
    "buyer_name": "FinSight Enterprise Ltd",
    "buyer_gstin": "29AABCU9603R1ZM",
    "invoice_date": "2026-03-15",
    "due_date": "2026-04-15",
    "currency": "INR",
    "subtotal": 50000.00,
    "cgst": 4500.00,
    "sgst": 4500.00,
    "igst": None,
    "total_tax": 9000.00,
    "grand_total": 59000.00,
    "payment_terms": "Net 30 Days",
    "line_items": [
        {
            "description": "Cloud Architecture & AI Agent Automation Services",
            "quantity": 1.0,
            "unit_price": 50000.0,
            "tax_rate": 18.0,
            "amount": 50000.0,
            "confidence": 0.98,
        }
    ],
    "field_confidence": {
        "invoice_number": 0.99,
        "vendor_name": 0.98,
        "vendor_gstin": 0.99,
        "invoice_date": 0.95,
        "grand_total": 0.99,
        "subtotal": 0.97,
        "total_tax": 0.97,
    },
}


@pytest.fixture
def sample_pdf_bytes() -> bytes:
    """Generates a valid digital text-based invoice PDF in memory."""
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)  # A4 size
    text = """
    TAX INVOICE
    
    Vendor: Antigravity Cloud Technologies Pvt Ltd
    GSTIN: 27AAPFU0939F1ZV
    Address: Tech Hub, Bangalore, India
    
    Billed To: FinSight Enterprise Ltd
    Buyer GSTIN: 29AABCU9603R1ZM
    
    Invoice Number: INV-2026-001
    Invoice Date: 2026-03-15
    Due Date: 2026-04-15
    Payment Terms: Net 30 Days
    
    Item Description: Cloud Architecture & AI Agent Automation Services
    Qty: 1 | Rate: 50,000.00 | Amount: 50,000.00
    
    Subtotal: INR 50,000.00
    CGST (9%): INR 4,500.00
    SGST (9%): INR 4,500.00
    Total Tax: INR 9,000.00
    Grand Total: INR 59,000.00
    """
    page.insert_text((50, 80), text, fontsize=12)
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()


@pytest.fixture
def empty_pdf_bytes() -> bytes:
    """Generates an empty PDF with no extractable text."""
    doc = pymupdf.open()
    doc.new_page(width=595, height=842)
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Test client for FastAPI ASGI endpoints."""
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        yield client


@pytest_asyncio.fixture
async def authenticated_client(async_client: AsyncClient) -> dict:
    """Registers a fresh test user and returns auth headers."""
    email = f"tester_{pytest_asyncio.__name__}_{id(async_client)}@finsight.ai"
    reg_res = await async_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "SecurePassword123!", "full_name": "Test Engineer"},
    )
    assert reg_res.status_code == 201
    data = reg_res.json()
    token = data["access_token"]
    user_id = data["user"]["id"]
    headers = {"Authorization": f"Bearer {token}"}
    return {
        "client": async_client,
        "token": token,
        "user_id": user_id,
        "headers": headers,
    }


@pytest.fixture
def mock_gemini():
    """Mocks Gemini extraction so test suite never requires API credits."""
    import os
    from app.schemas.invoice import ExtractedInvoice
    mock_invoice = ExtractedInvoice.model_validate(SAMPLE_EXTRACTED_DATA)

    with patch.dict(os.environ, {"GOOGLE_API_KEY": "mock-test-key-for-tests"}), patch(
        "app.agents.nodes.invoice_extractor.ChatGoogleGenerativeAI"
    ) as MockLLM:
        mock_instance = MagicMock()
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = mock_invoice
        mock_instance.with_structured_output.return_value = mock_chain
        MockLLM.return_value = mock_instance
        yield mock_instance
