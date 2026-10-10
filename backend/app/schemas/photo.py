"""
Pydantic schemas for Photos.
"""

from datetime import datetime
from pydantic import BaseModel
from typing import Optional

from app.schemas.analysis import ExifInfo, ClassificationResult


class PhotoResponse(BaseModel):
    """Photo details returned from API."""
    id: str
    site_id: str
    original_filename: str
    public_url: Optional[str] = None
    content_type: str = "image/jpeg"
    file_size_bytes: Optional[int] = None

    # EXIF (nested object + flat convenience fields for client compatibility)
    exif: Optional[ExifInfo] = None
    exif_has_gps: bool = False
    exif_lat: Optional[float] = None
    exif_lon: Optional[float] = None
    exif_camera: Optional[str] = None
    exif_timestamp: Optional[str] = None
    exif_warnings: list[str] = []

    # Classification (nested object + flat convenience fields for client compatibility)
    classified: bool = False
    predicted_class: Optional[str] = None
    classification_confidence: Optional[float] = None
    all_scores: Optional[dict[str, float]] = None
    classification: Optional[ClassificationResult] = None

    uploaded_by: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PhotoListResponse(BaseModel):
    """List of photos for a site."""
    photos: list[PhotoResponse]
    total: int
