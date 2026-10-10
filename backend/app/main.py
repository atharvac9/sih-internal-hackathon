"""
FastAPI application — main entry point.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import create_tables
from app.routers import sites, analysis, photos, reports, health

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    logger.info("Starting Clean Water Initiative backend...")

    # Create database tables (dev convenience — use Alembic for production)
    await create_tables()
    logger.info("Database tables ready")

    # Preload CLIP model to avoid first-request latency
    try:
        from app.services.classifier import preload_model
        preload_model()
    except Exception as e:
        logger.warning(f"CLIP model preload failed (will retry on first request): {e}")

    # Check GEE configuration
    from app.services.gee_service import is_gee_configured
    if is_gee_configured():
        logger.info("GEE credentials configured ✓")
    else:
        logger.warning("GEE credentials NOT configured — satellite queries will return errors")

    yield

    logger.info("Shutting down...")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="Watershed health monitoring dashboard — satellite indices + CLIP photo classification",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — only allow configured frontend origins, NOT wildcard
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Register routers
app.include_router(health.router, prefix=settings.api_prefix)
app.include_router(sites.router, prefix=settings.api_prefix)
app.include_router(analysis.router, prefix=settings.api_prefix)
app.include_router(photos.router, prefix=settings.api_prefix)
app.include_router(reports.router, prefix=settings.api_prefix)


@app.get("/")
async def root():
    return {
        "name": settings.app_name,
        "version": "1.0.0",
        "docs": "/docs",
    }
