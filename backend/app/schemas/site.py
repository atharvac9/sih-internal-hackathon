"""
Pydantic schemas for Sites — request/response models.
"""

from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from typing import Optional


# ── Request Schemas ──────────────────────────────────────────────────────────

class SiteCreate(BaseModel):
    """Create a new monitored site."""
    lat: float = Field(..., ge=-90, le=90, description="Latitude")
    lon: float = Field(..., ge=-180, le=180, description="Longitude")
    activity_type: Optional[str] = Field(
        None,
        description="Claimed activity: check_dam, farm_pond, plantation, degraded_land, water_body"
    )
    description: Optional[str] = Field(None, max_length=500)
    baseline_date: Optional[str] = Field(
        None, description="Baseline date for before/after analysis (YYYY-MM-DD)"
    )
    intervention_date: Optional[str] = Field(None, description="YYYY-MM-DD")
    buffer_radius_m: int = Field(500, ge=100, le=5000, description="Buffer radius in meters")

    @field_validator("activity_type")
    @classmethod
    def validate_activity_type(cls, v):
        valid = {"check_dam", "farm_pond", "plantation", "degraded_land", "water_body", None}
        if v is not None and v not in valid:
            raise ValueError(
                f"Invalid activity_type '{v}'. Must be one of: "
                f"check_dam, farm_pond, plantation, degraded_land, water_body"
            )
        return v


class SiteUpdate(BaseModel):
    """Update an existing site."""
    activity_type: Optional[str] = None
    description: Optional[str] = Field(None, max_length=500)
    baseline_date: Optional[str] = None
    intervention_date: Optional[str] = None
    buffer_radius_m: Optional[int] = Field(None, ge=100, le=5000)

    @field_validator("activity_type")
    @classmethod
    def validate_activity_type(cls, v):
        valid = {"check_dam", "farm_pond", "plantation", "degraded_land", "water_body", None}
        if v is not None and v not in valid:
            raise ValueError(f"Invalid activity_type '{v}'.")
        return v


# ── Response Schemas ─────────────────────────────────────────────────────────

class SiteResponse(BaseModel):
    """Site details returned from API."""
    id: str
    site_code: Optional[str] = None
    lat: float
    lon: float
    activity_type: Optional[str] = None
    description: Optional[str] = None
    is_seeded_demo: bool = False
    baseline_date: Optional[str] = None
    intervention_date: Optional[str] = None
    buffer_radius_m: int = 500
    has_baseline: bool = False
    created_by: Optional[str] = None
    created_at: datetime
    latest_analysis: Optional[dict] = None
    photo_count: int = 0

    model_config = {"from_attributes": True}


class SiteListResponse(BaseModel):
    """Paginated list of sites."""
    sites: list[SiteResponse]
    total: int
