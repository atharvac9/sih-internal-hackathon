"""
Sites API — CRUD for monitored sites.
"""

import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.site import Site
from app.models.analysis import AnalysisResult
from app.schemas.site import SiteCreate, SiteUpdate, SiteResponse, SiteListResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sites", tags=["sites"])


def _serialize_analysis(latest: Optional[AnalysisResult]) -> Optional[dict]:
    if not latest:
        return None
    flags = json.loads(latest.flags_json) if latest.flags_json else []
    return {
        "id": latest.id,
        "site_id": latest.site_id,
        "mode": latest.mode,
        "health_score": latest.health_score,
        "health_grade": latest.health_grade,
        "delta_ndvi": latest.delta_ndvi,
        "delta_ndwi": latest.delta_ndwi,
        "ndvi_t0": latest.ndvi_t0,
        "ndvi_tnow": latest.ndvi_tnow,
        "ndwi_t0": latest.ndwi_t0,
        "ndwi_tnow": latest.ndwi_tnow,
        "satellite_agreement": latest.satellite_agreement,
        "photo_agreement": latest.photo_agreement,
        "overall_status": latest.overall_status,
        "flags": flags,
        "confidence_score": latest.validation_confidence,
        "classified_activity": latest.predicted_class,
        "classification_confidence": latest.photo_confidence,
        "satellite_source": latest.satellite_source,
        "buffer_radius_m": latest.buffer_radius_m,
        "analyzed_at": latest.created_at.isoformat() if latest.created_at else None,
    }


@router.get("", response_model=SiteListResponse)
async def list_sites(
    seeded_only: bool = Query(False, description="Only return seeded demo sites"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List all monitored sites with optional filtering and latest analysis."""
    query = select(Site)
    count_query = select(func.count(Site.id))

    if seeded_only:
        query = query.where(Site.is_seeded_demo == True)
        count_query = count_query.where(Site.is_seeded_demo == True)

    query = query.order_by(Site.created_at.desc()).offset(offset).limit(limit)

    result = await db.execute(query)
    sites = result.scalars().all()

    count_result = await db.execute(count_query)
    total = count_result.scalar_one()

    site_responses = []
    for s in sites:
        resp = SiteResponse.model_validate(s)
        ana_res = await db.execute(
            select(AnalysisResult)
            .where(AnalysisResult.site_id == s.id)
            .order_by(AnalysisResult.created_at.desc())
            .limit(1)
        )
        resp.latest_analysis = _serialize_analysis(ana_res.scalar_one_or_none())
        site_responses.append(resp)

    return SiteListResponse(
        sites=site_responses,
        total=total,
    )


@router.get("/{site_id}", response_model=SiteResponse)
async def get_site(site_id: str, db: AsyncSession = Depends(get_db)):
    """Get a single site by ID with its latest analysis."""
    result = await db.execute(select(Site).where(Site.id == site_id))
    site = result.scalar_one_or_none()
    if site is None:
        raise HTTPException(status_code=404, detail="Site not found")
    resp = SiteResponse.model_validate(site)
    ana_res = await db.execute(
        select(AnalysisResult)
        .where(AnalysisResult.site_id == site.id)
        .order_by(AnalysisResult.created_at.desc())
        .limit(1)
    )
    resp.latest_analysis = _serialize_analysis(ana_res.scalar_one_or_none())
    return resp


@router.post("", response_model=SiteResponse, status_code=201)
async def create_site(body: SiteCreate, db: AsyncSession = Depends(get_db)):
    """
    Create a new monitored site.
    Used when a user clicks a point on the map and wants to save it for tracking.
    """
    import uuid
    new_id = str(uuid.uuid4())
    site = Site(
        id=new_id,
        site_code=f"SITE-{new_id[:6].upper()}",
        lat=body.lat,
        lon=body.lon,
        activity_type=body.activity_type,
        description=body.description,
        baseline_date=body.baseline_date,
        intervention_date=body.intervention_date,
        buffer_radius_m=body.buffer_radius_m,
        is_seeded_demo=False,
    )
    db.add(site)
    await db.flush()
    await db.refresh(site)
    return SiteResponse.model_validate(site)


@router.patch("/{site_id}", response_model=SiteResponse)
async def update_site(
    site_id: str,
    body: SiteUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update an existing site."""
    result = await db.execute(select(Site).where(Site.id == site_id))
    site = result.scalar_one_or_none()
    if site is None:
        raise HTTPException(status_code=404, detail="Site not found")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(site, key, value)

    await db.flush()
    await db.refresh(site)
    return SiteResponse.model_validate(site)


@router.delete("/{site_id}", status_code=204)
async def delete_site(site_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a site and all associated data."""
    result = await db.execute(select(Site).where(Site.id == site_id))
    site = result.scalar_one_or_none()
    if site is None:
        raise HTTPException(status_code=404, detail="Site not found")

    await db.delete(site)
