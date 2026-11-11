from __future__ import annotations
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.config import get_settings

# Loop-aware client singleton to prevent "Event loop is closed" across test runs and workers
_client: AsyncIOMotorClient | None = None
_client_loop: asyncio.AbstractEventLoop | None = None


def get_client() -> AsyncIOMotorClient:
    global _client, _client_loop
    current_loop = None
    try:
        current_loop = asyncio.get_running_loop()
    except RuntimeError:
        pass

    # If event loop changed (e.g. between pytest test functions or Celery tasks), recycle client
    if _client is None or (_client_loop is not None and current_loop is not None and _client_loop != current_loop):
        if _client is not None:
            try:
                _client.close()
            except Exception:
                pass
        settings = get_settings()
        _client = AsyncIOMotorClient(settings.MONGODB_URL)
        _client_loop = current_loop

    return _client


def get_database() -> AsyncIOMotorDatabase:
    settings = get_settings()
    return get_client()[settings.MONGODB_DB_NAME]


async def create_indexes() -> None:
    """Create all required compound and unique indexes."""
    db = get_database()
    await db.users.create_index("email", unique=True)
    await db.invoices.create_index([("user_id", 1), ("created_at", -1)])
    await db.invoices.create_index([("user_id", 1), ("status", 1)])
    await db.invoices.create_index([("file_hash", 1), ("user_id", 1)])
    await db.invoices.create_index(
        [("extracted.invoice_number", 1), ("extracted.vendor_name", 1), ("user_id", 1)]
    )
    await db.processing_jobs.create_index([("invoice_id", 1)])
    await db.audit_logs.create_index([("invoice_id", 1), ("created_at", -1)])
