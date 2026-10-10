"""
Photos API — upload, classify, and manage field photos.

Upload flow: file input → POST multipart → EXIF extract → Supabase Storage → CLIP classify → persist
"""

import json
import logging

from typing import Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.photo import Photo
from app.models.site import Site
from app.schemas.analysis import ExifInfo, ClassificationResult
from app.schemas.photo import PhotoResponse, PhotoListResponse
from app.models.analysis import AnalysisResult, AnalysisMode
from app.services import classifier, exif_checker, storage, gee_service, cross_validator, health_score
from app.routers.analysis import _generate_simulated_telemetry

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/photos", tags=["photos"])

# Max upload size: 25MB
MAX_UPLOAD_BYTES = 25 * 1024 * 1024
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}


@router.post("/auto-audit")
async def auto_audit_photo(
    file: UploadFile = File(...),
    claimed_activity_type: Optional[str] = Form("check_dam"),
    client_lat: Optional[float] = Form(None),
    client_lon: Optional[float] = Form(None),
    site_id: Optional[str] = Form(None),
    site_name: Optional[str] = Form(None),
    buffer_radius_m: int = Form(500),
    db: AsyncSession = Depends(get_db),
):
    """
    Unified 1-Step Photo-to-Satellite Audit.
    1. Extracts embedded GPS coordinates from the photo (with client/device fallback).
    2. Runs deep computer vision classification on photo pixels.
    3. Uses or creates the monitored site at the photo's GPS coordinates.
    4. Automatically queries Sentinel-2 satellite imagery (NDVI/NDWI) for the exact location.
    5. Cross-validates satellite evidence against photo visual evidence.
    6. Calculates health score and grade.
    7. Persists records and returns the comparison report + PDF download URL.
    """
    # 1. Validate file type and size
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type '{file.content_type}'. Allowed: JPEG, PNG, WebP",
        )

    image_bytes = await file.read()
    if len(image_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty file uploaded")
    if len(image_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"File too large ({len(image_bytes) / 1024 / 1024:.1f}MB). Max: 25MB",
        )

    # 2. Extract EXIF metadata
    exif_data = exif_checker.extract_exif(image_bytes)

    target_lat = None
    target_lon = None
    if exif_data["has_gps"]:
        target_lat = exif_data["gps_lat"]
        target_lon = exif_data["gps_lon"]
    elif client_lat is not None and client_lon is not None:
        target_lat = round(float(client_lat), 6)
        target_lon = round(float(client_lon), 6)
        exif_data["has_gps"] = True
        exif_data["gps_lat"] = target_lat
        exif_data["gps_lon"] = target_lon
        exif_data["warnings"] = [w for w in exif_data.get("warnings", []) if "No GPS" not in w]
        exif_data["warnings"].append("GPS coordinates synchronized from device/user input")

    existing_site = None
    if site_id:
        res = await db.execute(select(Site).where(Site.id == site_id))
        existing_site = res.scalar_one_or_none()
        if existing_site and target_lat is None:
            target_lat = existing_site.lat
            target_lon = existing_site.lon
            exif_data["has_gps"] = True
            exif_data["gps_lat"] = target_lat
            exif_data["gps_lon"] = target_lon

    if target_lat is None or target_lon is None:
        raise HTTPException(
            status_code=400,
            detail="This photograph contains no embedded EXIF GPS tags. Please specify coordinates or allow device GPS location.",
        )

    # 3. Run Computer Vision on photo pixels
    classification = None
    try:
        classification = await classifier.classify_photo_from_bytes(image_bytes)
    except Exception as e:
        logger.error(f"Visual classification failed: {e}")
        classification = {
            "predicted_class": "unknown",
            "confidence": 0.0,
            "all_scores": {},
        }

    # 4. Resolve or create Site
    site = existing_site
    claimed = claimed_activity_type or (existing_site.activity_type if existing_site else "check_dam") or "check_dam"

    if site is None:
        desc = site_name or f"Auto-Audit: {file.filename or 'Field Photo'} ({target_lat:.4f}°N, {target_lon:.4f}°E)"
        site = Site(
            lat=target_lat,
            lon=target_lon,
            activity_type=claimed,
            description=desc,
            buffer_radius_m=buffer_radius_m,
            is_seeded_demo=False,
        )
        db.add(site)
        await db.flush()
        await db.refresh(site)

    # 5. Upload photo and persist Photo record
    storage_result = await storage.upload_photo(
        image_bytes=image_bytes,
        original_filename=file.filename or "photo.jpg",
        site_id=site.id,
        content_type=file.content_type or "image/jpeg",
    )

    photo = Photo(
        site_id=site.id,
        original_filename=file.filename or "photo.jpg",
        storage_path=storage_result["storage_path"],
        public_url=storage_result.get("public_url"),
        content_type=file.content_type or "image/jpeg",
        file_size_bytes=len(image_bytes),
        has_exif=exif_data["has_exif"],
        has_gps=exif_data["has_gps"],
        has_camera_model=exif_data["has_camera_model"],
        has_timestamp=exif_data["has_timestamp"],
        exif_gps_lat=exif_data.get("gps_lat"),
        exif_gps_lon=exif_data.get("gps_lon"),
        exif_camera_model=exif_data.get("camera_model"),
        exif_datetime=exif_data.get("capture_datetime"),
        exif_warnings_json=json.dumps(exif_data.get("warnings", [])),
        classified=True,
        predicted_class=classification["predicted_class"],
        classification_confidence=classification["confidence"],
        classification_scores_json=json.dumps(classification["all_scores"]),
    )
    db.add(photo)
    await db.flush()
    await db.refresh(photo)

    # 6. Synchronize Sentinel-2 satellite telemetry for these exact coordinates
    sat_data = await gee_service.get_snapshot_indices(target_lat, target_lon, buffer_radius_m)
    if "error" in sat_data:
        sat_data = _generate_simulated_telemetry(
            lat=target_lat,
            lon=target_lon,
            activity_type=claimed,
            has_baseline=False,
            buffer_radius_m=buffer_radius_m,
        )

    # 7. Cross-Validate: Compare satellite evidence against photo visual evidence
    validation_result = cross_validator.validate_site(
        activity_type=claimed,
        satellite_data=sat_data,
        classification_result=classification,
    )

    # 8. Compute Health Score
    health_result = health_score.compute_health_score_snapshot(sat_data, classification)

    # 9. Persist AnalysisResult
    analysis = AnalysisResult(
        site_id=site.id,
        mode=AnalysisMode.SNAPSHOT.value,
        ndvi_tnow=sat_data.get("ndvi_tnow"),
        ndwi_tnow=sat_data.get("ndwi_tnow"),
        tnow_start_date=sat_data.get("tnow_start_date"),
        tnow_end_date=sat_data.get("tnow_end_date"),
        satellite_source=sat_data.get("source", "gee"),
        predicted_class=classification["predicted_class"],
        photo_confidence=classification["confidence"],
        classification_scores_json=json.dumps(classification["all_scores"]),
        satellite_agreement=validation_result.get("satellite_agreement"),
        photo_agreement=validation_result.get("photo_agreement"),
        overall_status=validation_result["overall_status"],
        flags_json=json.dumps(validation_result["flags"]),
        health_score=health_result["score"],
        health_grade=health_result["grade"],
        health_components_json=json.dumps(health_result["components"]),
        validation_confidence=validation_result.get("confidence", 0.0),
        buffer_radius_m=buffer_radius_m,
    )
    db.add(analysis)
    await db.flush()
    await db.refresh(analysis)

    # 10. Format return payload
    photo_response = _build_photo_response(photo, exif_data, classification)
    site_response = {
        "id": site.id,
        "site_code": site.site_code or f"SITE-{site.id[:6].upper()}",
        "lat": site.lat,
        "lon": site.lon,
        "activity_type": site.activity_type,
        "description": site.description,
        "baseline_date": site.baseline_date,
        "intervention_date": site.intervention_date,
        "buffer_radius_m": site.buffer_radius_m,
        "is_seeded_demo": site.is_seeded_demo,
        "created_at": site.created_at.isoformat(),
        "updated_at": site.updated_at.isoformat(),
        "photo_count": 1,
    }
    analysis_response = {
        "id": analysis.id,
        "site_id": site.id,
        "mode": "snapshot",
        "health_score": health_result["score"],
        "health_grade": health_result["grade"],
        "delta_ndvi": None,
        "delta_ndwi": None,
        "ndvi_t0": None,
        "ndwi_t0": None,
        "ndvi_tnow": sat_data.get("ndvi_tnow"),
        "ndwi_tnow": sat_data.get("ndwi_tnow"),
        "satellite_agreement": validation_result.get("satellite_agreement"),
        "photo_agreement": validation_result.get("photo_agreement"),
        "overall_status": validation_result["overall_status"],
        "flags": validation_result["flags"],
        "confidence_score": validation_result.get("confidence", 0.0),
        "classified_activity": classification["predicted_class"],
        "classification_confidence": classification["confidence"],
        "satellite_source": sat_data.get("source", "gee"),
        "buffer_radius_m": buffer_radius_m,
        "analyzed_at": analysis.created_at.isoformat(),
    }
    site_response["latest_analysis"] = analysis_response

    return {
        "site": site_response,
        "photo": photo_response,
        "analysis": analysis_response,
        "cross_validation": validation_result,
        "health_score": health_result,
        "satellite_data": sat_data,
        "report_download_url": f"/api/reports/{site.id}/pdf",
    }


@router.post("/{site_id}", response_model=PhotoResponse, status_code=201)
async def upload_photo(
    site_id: str,
    file: UploadFile = File(...),
    client_lat: Optional[float] = Form(None),
    client_lon: Optional[float] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a field photo for a site.

    Flow:
    1. Validate file type and size
    2. Extract EXIF metadata (GPS, camera, timestamp)
    3. Apply device/site geolocation fallback if camera GPS is absent
    4. Upload to Storage
    5. Run CLIP classification on the actual image
    6. Persist photo record with EXIF + classification results
    """
    # 1. Validate site exists
    result = await db.execute(select(Site).where(Site.id == site_id))
    site = result.scalar_one_or_none()
    if site is None:
        raise HTTPException(status_code=404, detail="Site not found")

    # 2. Validate file
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type '{file.content_type}'. Allowed: JPEG, PNG, WebP",
        )

    image_bytes = await file.read()
    if len(image_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"File too large ({len(image_bytes) / 1024 / 1024:.1f}MB). Max: 25MB",
        )

    if len(image_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty file")

    # 3. Extract EXIF metadata
    exif_data = exif_checker.extract_exif(image_bytes)

    # If photo lacks hardware EXIF GPS, check if client provided live device coordinates
    if not exif_data["has_gps"] and client_lat is not None and client_lon is not None:
        exif_data["has_gps"] = True
        exif_data["gps_lat"] = round(float(client_lat), 6)
        exif_data["gps_lon"] = round(float(client_lon), 6)
        exif_data["warnings"] = [w for w in exif_data["warnings"] if "No GPS" not in w]
        exif_data["warnings"].append("GPS coordinates synchronized from device/site location")

    # 4. Upload to Storage
    try:
        storage_result = await storage.upload_photo(
            image_bytes=image_bytes,
            original_filename=file.filename or "photo.jpg",
            site_id=site_id,
            content_type=file.content_type or "image/jpeg",
        )
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    # 5. Run real computer vision classification on the actual image pixels
    classification = None
    try:
        classification = await classifier.classify_photo_from_bytes(image_bytes)
    except Exception as e:
        logger.error(f"Visual classification error: {e}", exc_info=True)
        # Do not fabricate high-confidence false matches; leave unclassified or record error
        classification = None

    # 6. Persist photo record
    photo = Photo(
        site_id=site_id,
        original_filename=file.filename or "photo.jpg",
        storage_path=storage_result["storage_path"],
        public_url=storage_result.get("public_url"),
        content_type=file.content_type or "image/jpeg",
        file_size_bytes=len(image_bytes),
        # EXIF
        has_exif=exif_data["has_exif"],
        has_gps=exif_data["has_gps"],
        has_camera_model=exif_data["has_camera_model"],
        has_timestamp=exif_data["has_timestamp"],
        exif_gps_lat=exif_data.get("gps_lat"),
        exif_gps_lon=exif_data.get("gps_lon"),
        exif_camera_model=exif_data.get("camera_model"),
        exif_datetime=exif_data.get("capture_datetime"),
        exif_warnings_json=json.dumps(exif_data.get("warnings", [])),
        # Classification
        classified=classification is not None,
        predicted_class=classification["predicted_class"] if classification else None,
        classification_confidence=classification["confidence"] if classification else None,
        classification_scores_json=json.dumps(classification["all_scores"]) if classification else None,
    )
    db.add(photo)
    await db.flush()
    await db.refresh(photo)

    return _build_photo_response(photo, exif_data, classification)


@router.get("/{site_id}", response_model=PhotoListResponse)
async def list_photos(site_id: str, db: AsyncSession = Depends(get_db)):
    """List all photos for a site."""
    result = await db.execute(
        select(Photo)
        .where(Photo.site_id == site_id)
        .order_by(Photo.created_at.desc())
    )
    photos = result.scalars().all()

    return PhotoListResponse(
        photos=[_build_photo_response_from_model(p) for p in photos],
        total=len(photos),
    )


@router.post("/{photo_id}/reclassify", response_model=PhotoResponse)
async def reclassify_photo(photo_id: str, db: AsyncSession = Depends(get_db)):
    """Re-run CLIP classification on an existing photo."""
    result = await db.execute(select(Photo).where(Photo.id == photo_id))
    photo = result.scalar_one_or_none()
    if photo is None:
        raise HTTPException(status_code=404, detail="Photo not found")

    if not photo.public_url:
        raise HTTPException(status_code=400, detail="Photo has no public URL")

    try:
        classification = await classifier.classify_photo_from_url(photo.public_url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Classification failed: {e}")

    photo.classified = True
    photo.predicted_class = classification["predicted_class"]
    photo.classification_confidence = classification["confidence"]
    photo.classification_scores_json = json.dumps(classification["all_scores"])

    await db.flush()
    await db.refresh(photo)

    return _build_photo_response_from_model(photo)


@router.delete("/{photo_id}", status_code=204)
async def delete_photo(photo_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a photo from storage and database."""
    result = await db.execute(select(Photo).where(Photo.id == photo_id))
    photo = result.scalar_one_or_none()
    if photo is None:
        raise HTTPException(status_code=404, detail="Photo not found")

    # Delete from storage
    if photo.storage_path:
        await storage.delete_photo(photo.storage_path)

    await db.delete(photo)


@router.patch("/{photo_id}/geotag", response_model=PhotoResponse)
async def update_photo_geotag(
    photo_id: str,
    lat: float = Form(...),
    lon: float = Form(...),
    db: AsyncSession = Depends(get_db),
):
    """Manually update or sync the geotagged coordinates for a photo."""
    result = await db.execute(select(Photo).where(Photo.id == photo_id))
    photo = result.scalar_one_or_none()
    if photo is None:
        raise HTTPException(status_code=404, detail="Photo not found")

    photo.has_gps = True
    photo.exif_gps_lat = round(float(lat), 6)
    photo.exif_gps_lon = round(float(lon), 6)
    warnings = json.loads(photo.exif_warnings_json) if photo.exif_warnings_json else []
    warnings = [w for w in warnings if "No GPS" not in w]
    warnings.append("GPS location tagged via device/site coordinate synchronization")
    photo.exif_warnings_json = json.dumps(warnings)

    await db.flush()
    await db.refresh(photo)
    return _build_photo_response_from_model(photo)


# ── Response Builders ────────────────────────────────────────────────────────

def _build_photo_response(
    photo: Photo,
    exif_data: dict,
    classification: dict = None,
) -> PhotoResponse:
    """Build response from fresh data."""
    exif_info = ExifInfo(
        has_exif=exif_data["has_exif"],
        has_gps=exif_data["has_gps"],
        has_camera_model=exif_data["has_camera_model"],
        has_timestamp=exif_data["has_timestamp"],
        gps_lat=exif_data.get("gps_lat"),
        gps_lon=exif_data.get("gps_lon"),
        camera_model=exif_data.get("camera_model"),
        capture_datetime=exif_data.get("capture_datetime"),
        warnings=exif_data.get("warnings", []),
    )

    classification_result = None
    if classification:
        classification_result = ClassificationResult(
            predicted_class=classification["predicted_class"],
            confidence=classification["confidence"],
            all_scores=classification.get("all_scores", {}),
        )

    return PhotoResponse(
        id=photo.id,
        site_id=photo.site_id,
        original_filename=photo.original_filename,
        public_url=photo.public_url,
        content_type=photo.content_type,
        file_size_bytes=photo.file_size_bytes,
        # Nested schemas
        exif=exif_info,
        classification=classification_result,
        # Flat convenience fields for direct client access
        exif_has_gps=exif_info.has_gps,
        exif_lat=exif_info.gps_lat,
        exif_lon=exif_info.gps_lon,
        exif_camera=exif_info.camera_model,
        exif_timestamp=exif_info.capture_datetime,
        exif_warnings=exif_info.warnings,
        classified=photo.classified,
        predicted_class=photo.predicted_class,
        classification_confidence=photo.classification_confidence,
        all_scores=classification.get("all_scores", {}) if classification else (
            json.loads(photo.classification_scores_json) if photo.classification_scores_json else None
        ),
        uploaded_by=photo.uploaded_by,
        created_at=photo.created_at,
    )


def _build_photo_response_from_model(photo: Photo) -> PhotoResponse:
    """Build response from persisted model."""
    warnings = json.loads(photo.exif_warnings_json) if photo.exif_warnings_json else []
    exif_info = ExifInfo(
        has_exif=photo.has_exif,
        has_gps=photo.has_gps,
        has_camera_model=photo.has_camera_model,
        has_timestamp=photo.has_timestamp,
        gps_lat=photo.exif_gps_lat,
        gps_lon=photo.exif_gps_lon,
        camera_model=photo.exif_camera_model,
        capture_datetime=photo.exif_datetime,
        warnings=warnings,
    )

    classification_result = None
    all_scores = json.loads(photo.classification_scores_json) if photo.classification_scores_json else None
    if photo.classified and photo.predicted_class:
        classification_result = ClassificationResult(
            predicted_class=photo.predicted_class,
            confidence=photo.classification_confidence or 0.0,
            all_scores=all_scores or {},
        )

    return PhotoResponse(
        id=photo.id,
        site_id=photo.site_id,
        original_filename=photo.original_filename,
        public_url=photo.public_url,
        content_type=photo.content_type,
        file_size_bytes=photo.file_size_bytes,
        # Nested schemas
        exif=exif_info,
        classification=classification_result,
        # Flat convenience fields for direct client access
        exif_has_gps=photo.has_gps,
        exif_lat=photo.exif_gps_lat,
        exif_lon=photo.exif_gps_lon,
        exif_camera=photo.exif_camera_model,
        exif_timestamp=photo.exif_datetime,
        exif_warnings=warnings,
        classified=photo.classified,
        predicted_class=photo.predicted_class,
        classification_confidence=photo.classification_confidence,
        all_scores=all_scores,
        uploaded_by=photo.uploaded_by,
        created_at=photo.created_at,
    )
