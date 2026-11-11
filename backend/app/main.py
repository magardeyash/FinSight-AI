from __future__ import annotations
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import get_settings
from app.database import create_indexes
from app.auth.router import router as auth_router
from app.invoices.router import router as invoices_router
from app.dashboard.router import router as dashboard_router
from app.utils.logging import setup_logging, logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    settings = get_settings()
    settings.validate_production()
    logger.info(f"Initializing {settings.APP_NAME} in {'DEBUG' if settings.DEBUG else 'PRODUCTION'} mode...")

    # Create MongoDB database indexes on startup
    try:
        await create_indexes()
        logger.info("MongoDB indexes verified and ready.")
    except Exception as exc:
        logger.warning(f"Could not initialize MongoDB indexes at startup: {exc}")

    yield

    logger.info("Shutting down FinSight AI...")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.APP_NAME,
        version="1.0.0",
        description="Production-Ready Agentic Invoice Processing Platform",
        lifespan=lifespan,
    )

    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Centralized exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled server error at {request.url.path}: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "An internal server error occurred. Please try again later.",
                "error_type": type(exc).__name__,
            },
        )

    # Health check endpoints
    @app.get("/health", tags=["Health"])
    async def health_check():
        return {
            "status": "healthy",
            "app": settings.APP_NAME,
            "version": "1.0.0",
        }

    @app.get("/", tags=["Health"])
    async def root():
        return {
            "message": f"Welcome to {settings.APP_NAME} API",
            "docs": "/docs",
            "version": "1.0.0",
        }

    # Mount versioned API routers
    prefix = settings.API_V1_PREFIX
    app.include_router(auth_router, prefix=prefix)
    app.include_router(invoices_router, prefix=prefix)
    app.include_router(dashboard_router, prefix=prefix)

    return app


app = create_app()
