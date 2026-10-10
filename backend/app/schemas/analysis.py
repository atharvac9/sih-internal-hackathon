"""
Pydantic schemas for Analysis — including ad-hoc arbitrary-point requests.
"""

from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional


# ── Request Schemas ──────────────────────────────────────────────────────────

class AdHocAnalysisRequest(BaseModel):
    """
    Analyze any point on the globe — the core "click anywhere" feature.

    If claimed_activity_type is provided, cross-validation will run.
    Otherwise, returns raw satellite indices + optional photo classification.

    If baseline_date is provided, runs full before/after analysis.
    Otherwise, runs snapshot-only mode (current NDVI/NDWI).
    """
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    buffer_radius_m: int = Field(500, ge=100, le=5000)
    claimed_activity_type: Optional[str] = Field(
        None,
        description="If provided, cross-validation runs against this claim"
    )
    baseline_date: Optional[str] = Field(
        None,
        description="YYYY-MM-DD. If provided, runs full before/after analysis"
    )


class SiteAnalysisRequest(BaseModel):
    """Trigger analysis for an existing site (by site_id)."""
    force_refresh: bool = Field(False, description="Force re-fetch even if cached")


# ── Response Schemas ─────────────────────────────────────────────────────────

class SatelliteData(BaseModel):
    """Satellite indices for a location."""
    ndvi_tnow: Optional[float] = None
    ndwi_tnow: Optional[float] = None
    tnow_start_date: Optional[str] = None
    tnow_end_date: Optional[str] = None

    # Only in FULL (before/after) mode
    ndvi_t0: Optional[float] = None
    ndwi_t0: Optional[float] = None
    t0_start_date: Optional[str] = None
    t0_end_date: Optional[str] = None
    delta_ndvi: Optional[float] = None
    delta_ndwi: Optional[float] = None

    source: str = "gee"


class ClassificationResult(BaseModel):
    """CLIP zero-shot classification of a photo."""
    predicted_class: str
    confidence: float
    all_scores: dict[str, float]


class CrossValidationResult(BaseModel):
    """Cross-validation of claimed activity vs evidence."""
    satellite_agreement: Optional[bool] = None
    photo_agreement: Optional[bool] = None
    overall_status: str  # "confirmed", "anomaly", "inconclusive"
    flags: list[str] = []
    confidence: float = 0.0


class HealthScoreResult(BaseModel):
    """Computed health score for a site."""
    score: int = Field(..., ge=0, le=100)
    grade: str  # A, B, C, D, F
    mode: str   # "full" or "snapshot"
    components: dict[str, float]


class ExifInfo(BaseModel):
    """EXIF metadata extracted from an uploaded photo."""
    has_exif: bool = False
    has_gps: bool = False
    has_camera_model: bool = False
    has_timestamp: bool = False
    gps_lat: Optional[float] = None
    gps_lon: Optional[float] = None
    camera_model: Optional[str] = None
    capture_datetime: Optional[str] = None
    warnings: list[str] = []


class AnalysisResponse(BaseModel):
    """
    Complete analysis result for a site or ad-hoc point.
    The UI uses 'mode' to decide whether to show before/after or snapshot view.
    """
    id: str
    site_id: str
    mode: str  # "full" or "snapshot"

    satellite: SatelliteData
    classification: Optional[ClassificationResult] = None
    cross_validation: Optional[CrossValidationResult] = None
    health_score: Optional[HealthScoreResult] = None
    exif: Optional[ExifInfo] = None

    buffer_radius_m: int = 500
    created_at: datetime

    # For SNAPSHOT mode, this flag tells the UI not to show before/after language
    is_snapshot: bool = True

    model_config = {"from_attributes": True}
