from __future__ import annotations
import os
from typing import Optional, Any
from app.config import get_settings
from app.utils.logging import logger

_tracer = None
_initialized = False


def get_tracer() -> Optional[Any]:
    """
    Returns the Langfuse v3 client if credentials are configured.
    Returns None safely if Langfuse is absent or unconfigured.
    """
    global _tracer, _initialized
    if _initialized:
        return _tracer

    settings = get_settings()
    if settings.LANGFUSE_PUBLIC_KEY and settings.LANGFUSE_SECRET_KEY:
        try:
            os.environ.setdefault("LANGFUSE_PUBLIC_KEY", settings.LANGFUSE_PUBLIC_KEY)
            os.environ.setdefault("LANGFUSE_SECRET_KEY", settings.LANGFUSE_SECRET_KEY)
            os.environ.setdefault("LANGFUSE_HOST", settings.LANGFUSE_HOST)
            from langfuse import get_client
            _tracer = get_client()
            logger.info("Langfuse observability initialized successfully.")
        except Exception as exc:
            logger.warning(f"Langfuse failed to initialize, continuing without tracing: {exc}")
            _tracer = None
    else:
        logger.debug("Langfuse credentials not configured; tracing is disabled.")
        _tracer = None

    _initialized = True
    return _tracer
