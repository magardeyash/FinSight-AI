from __future__ import annotations
from typing import Any
from motor.motor_asyncio import AsyncIOMotorDatabase


async def get_dashboard_stats(db: AsyncIOMotorDatabase, user_id: str) -> dict[str, Any]:
    """
    Computes aggregate metrics for the current user's invoices.
    Enforces tenant isolation.
    """
    # 1. Status counts
    pipeline = [
        {"$match": {"user_id": user_id}},
        {"$group": {"_id": "$status", "count": {"$sum": 1}}},
    ]
    status_counts_cursor = db.invoices.aggregate(pipeline)
    status_counts: dict[str, int] = {}
    total_invoices = 0

    async for item in status_counts_cursor:
        status_name = item["_id"]
        c = item["count"]
        status_counts[status_name] = c
        total_invoices += c

    approved_count = status_counts.get("APPROVED", 0)
    pending_review_count = status_counts.get("REVIEW_REQUIRED", 0)
    failed_count = status_counts.get("FAILED", 0)
    processing_count = status_counts.get("PROCESSING", 0) + status_counts.get("QUEUED", 0)

    # 2. Total invoice value (sum of grand_total for approved invoices)
    val_pipeline = [
        {"$match": {"user_id": user_id, "status": "APPROVED"}},
        {"$group": {"_id": None, "total_value": {"$sum": "$extracted.grand_total"}}},
    ]
    val_cursor = db.invoices.aggregate(val_pipeline)
    total_value = 0.0
    async for item in val_cursor:
        val = item.get("total_value")
        if val is not None:
            try:
                total_value = float(val)
            except (ValueError, TypeError):
                total_value = 0.0

    return {
        "total_invoices": total_invoices,
        "approved_invoices": approved_count,
        "pending_reviews": pending_review_count,
        "failed_jobs": failed_count,
        "processing_invoices": processing_count,
        "total_approved_value": round(total_value, 2),
        "status_distribution": [
            {"name": "Approved", "value": approved_count, "color": "#10b981"},
            {"name": "Pending Review", "value": pending_review_count, "color": "#f59e0b"},
            {"name": "Processing", "value": processing_count, "color": "#3b82f6"},
            {"name": "Failed", "value": failed_count, "color": "#ef4444"},
            {"name": "Rejected", "value": status_counts.get("REJECTED", 0), "color": "#6b7280"},
        ],
    }


async def get_recent_activity(db: AsyncIOMotorDatabase, user_id: str, limit: int = 15) -> list[dict[str, Any]]:
    """Returns the latest audit events for the user's invoices."""
    cursor = db.audit_logs.find({"user_id": user_id}).sort("created_at", -1).limit(limit)
    items = await cursor.to_list(length=limit)
    return [
        {
            "id": str(item["_id"]),
            "invoice_id": item["invoice_id"],
            "action": item["action"],
            "detail": item["detail"],
            "created_at": item["created_at"],
        }
        for item in items
    ]
