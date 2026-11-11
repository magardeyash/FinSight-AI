from __future__ import annotations
from contextlib import contextmanager
from typing import Iterator
from pymongo import MongoClient
from langgraph.checkpoint.mongodb import MongoDBSaver
from app.config import get_settings

_sync_client: MongoClient | None = None
_saver_instance: MongoDBSaver | None = None


def get_sync_mongo_client() -> MongoClient:
    """Returns synchronous MongoClient singleton for MongoDBSaver."""
    global _sync_client
    if _sync_client is None:
        settings = get_settings()
        _sync_client = MongoClient(settings.MONGODB_URL)
    return _sync_client


def get_mongo_checkpointer() -> MongoDBSaver:
    """
    Returns a MongoDBSaver instance using the synchronous MongoClient.
    MongoDBSaver natively supports async calls (aget, aput) as well as sync calls.
    """
    global _saver_instance
    if _saver_instance is None:
        settings = get_settings()
        client = get_sync_mongo_client()
        _saver_instance = MongoDBSaver(client=client, db_name=settings.MONGODB_DB_NAME)
    return _saver_instance


@contextmanager
def mongo_checkpointer_context() -> Iterator[MongoDBSaver]:
    """Context manager for obtaining a checkpointer."""
    settings = get_settings()
    with MongoDBSaver.from_conn_string(
        conn_string=settings.MONGODB_URL,
        db_name=settings.MONGODB_DB_NAME,
    ) as saver:
        yield saver
