from __future__ import annotations
import io
import uuid
from datetime import datetime, timezone
import pytest
from httpx import AsyncClient
from app.database import get_database


@pytest.mark.asyncio
async def test_invoice_upload_and_lifecycle_api(authenticated_client: dict, sample_pdf_bytes: bytes):
    client: AsyncClient = authenticated_client["client"]
    headers = authenticated_client["headers"]
    user_id = authenticated_client["user_id"]

    # 1. Upload Invoice PDF
    files = {"file": ("acme_invoice.pdf", sample_pdf_bytes, "application/pdf")}
    upload_res = await client.post("/api/v1/invoices/upload", files=files, headers=headers)
    assert upload_res.status_code == 202
    data = upload_res.json()
    assert "invoice_id" in data
    assert "job_id" in data
    assert data["status"] == "QUEUED"
    invoice_id = data["invoice_id"]

    # 2. Get Status Poll
    status_res = await client.get(f"/api/v1/invoices/{invoice_id}/status", headers=headers)
    assert status_res.status_code == 200
    assert status_res.json()["status"] == "QUEUED"

    # 3. Get Detail
    detail_res = await client.get(f"/api/v1/invoices/{invoice_id}", headers=headers)
    assert detail_res.status_code == 200
    assert detail_res.json()["original_filename"] == "acme_invoice.pdf"

    # 4. Stream PDF file
    file_res = await client.get(f"/api/v1/invoices/{invoice_id}/file", headers=headers)
    assert file_res.status_code == 200
    assert file_res.headers["content-type"] == "application/pdf"
    assert len(file_res.content) == len(sample_pdf_bytes)

    # 5. Patch Extracted Fields
    patch_res = await client.patch(
        f"/api/v1/invoices/{invoice_id}",
        json={"invoice_number": "INV-MODIFIED-001", "grand_total": 75000.0},
        headers=headers,
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["extracted"]["invoice_number"] == "INV-MODIFIED-001"
    assert patch_res.json()["extracted"]["grand_total"] == 75000.0

    # 6. List Invoices with filter
    list_res = await client.get("/api/v1/invoices?search=MODIFIED", headers=headers)
    assert list_res.status_code == 200
    items = list_res.json()["items"]
    assert any(item["id"] == invoice_id for item in items)

    # 7. Audit log exists
    audit_res = await client.get(f"/api/v1/invoices/{invoice_id}/audit", headers=headers)
    assert audit_res.status_code == 200
    logs = audit_res.json()
    assert len(logs) >= 2  # upload + patch


@pytest.mark.asyncio
async def test_invoice_approval_and_rejection_api(authenticated_client: dict, sample_pdf_bytes: bytes, mock_gemini):
    client: AsyncClient = authenticated_client["client"]
    headers = authenticated_client["headers"]
    user_id = authenticated_client["user_id"]
    db = get_database()

    # Create an invoice in REVIEW_REQUIRED state
    inv_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    await db.invoices.insert_one({
        "_id": inv_id,
        "user_id": user_id,
        "original_filename": "review_needed.pdf",
        "file_size_bytes": 1024,
        "status": "REVIEW_REQUIRED",
        "extracted": {"invoice_number": "REV-01", "grand_total": 1000.0},
        "risk_score": 0.65,
        "risk_flags": ["Validation mismatch"],
        "validation_errors": ["Subtotal mismatch"],
        "created_at": now,
        "updated_at": now,
    })

    # Cannot approve if invalid status (e.g. try non-existent id)
    not_found_res = await client.post(f"/api/v1/invoices/{uuid.uuid4()}/approve", headers=headers)
    assert not_found_res.status_code == 404

    # Reject invoice
    reject_res = await client.post(
        f"/api/v1/invoices/{inv_id}/reject",
        json={"comment": "Duplicate entry"},
        headers=headers,
    )
    assert reject_res.status_code == 200
    assert reject_res.json()["status"] == "REJECTED"

    # Cannot approve already REJECTED invoice (must return 409 Conflict)
    second_res = await client.post(f"/api/v1/invoices/{inv_id}/approve", headers=headers)
    assert second_res.status_code == 409


@pytest.mark.asyncio
async def test_dashboard_stats_and_activity_api(authenticated_client: dict):
    client: AsyncClient = authenticated_client["client"]
    headers = authenticated_client["headers"]

    stats_res = await client.get("/api/v1/dashboard/stats", headers=headers)
    assert stats_res.status_code == 200
    stats = stats_res.json()
    assert "total_invoices" in stats
    assert "status_distribution" in stats
    assert "total_approved_value" in stats

    activity_res = await client.get("/api/v1/dashboard/recent-activity", headers=headers)
    assert activity_res.status_code == 200
    assert isinstance(activity_res.json(), list)


@pytest.mark.asyncio
async def test_tenant_isolation_on_api(authenticated_client: dict, async_client: AsyncClient, sample_pdf_bytes: bytes):
    """User B cannot access or modify User A's invoices."""
    headers_a = authenticated_client["headers"]

    # User A uploads an invoice
    files = {"file": ("secret.pdf", sample_pdf_bytes, "application/pdf")}
    res = await authenticated_client["client"].post("/api/v1/invoices/upload", files=files, headers=headers_a)
    invoice_id = res.json()["invoice_id"]

    # Register User B
    email_b = f"user_b_{uuid.uuid4().hex[:8]}@finsight.ai"
    reg_b = await async_client.post(
        "/api/v1/auth/register",
        json={"email": email_b, "password": "Password12345!"},
    )
    headers_b = {"Authorization": f"Bearer {reg_b.json()['access_token']}"}

    # User B tries to view User A's invoice -> 404 Not Found (tenant isolated)
    get_res = await async_client.get(f"/api/v1/invoices/{invoice_id}", headers=headers_b)
    assert get_res.status_code == 404

    # User B tries to download User A's file -> 404
    file_res = await async_client.get(f"/api/v1/invoices/{invoice_id}/file", headers=headers_b)
    assert file_res.status_code == 404

    # User B tries to patch User A's invoice -> 404
    patch_res = await async_client.patch(
        f"/api/v1/invoices/{invoice_id}", json={"invoice_number": "HACKED"}, headers=headers_b
    )
    assert patch_res.status_code == 404
