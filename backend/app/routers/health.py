"""
Health check and system status endpoint.
"""

from fastapi import APIRouter

from app.services.gee_service import is_gee_configured
from app.services.classifier import is_model_loaded
from app.services.storage import is_storage_configured

router = APIRouter(tags=["system"])


@router.get("/health")
async def health_check():
    """System health check — shows which services are configured/ready."""
    return {
        "status": "ok",
        "services": {
            "gee_configured": is_gee_configured(),
            "clip_model_loaded": is_model_loaded(),
            "storage_configured": is_storage_configured(),
        },
    }
