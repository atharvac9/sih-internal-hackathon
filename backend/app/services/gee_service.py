"""
Google Earth Engine service — service-account auth, coordinate-agnostic
Sentinel-2 queries, NDVI/NDWI computation.

Supports two modes:
- FULL: queries both T0 (baseline) and T_NOW (current) → returns deltas
- SNAPSHOT: queries T_NOW only → returns absolute indices

NO hardcoded bounding boxes or region filters. Any lat/lon works.
"""

import io
import json
import logging
import os
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

# Earth Engine is imported lazily to avoid import-time failures
_ee = None
_ee_initialized = False


def _get_ee():
    """Lazy-import ee module."""
    global _ee
    if _ee is None:
        try:
            import ee
            _ee = ee
        except ImportError:
            raise RuntimeError(
                "earthengine-api is not installed. "
                "Install it with: pip install earthengine-api"
            )
    return _ee


def initialize_gee() -> bool:
    """
    Initialize GEE with service-account credentials from env vars.
    Returns True if successful, False if credentials are not configured.

    NEVER falls back to mock data. If GEE is not configured, the caller
    must handle the "not configured" state explicitly.
    """
    global _ee_initialized

    if _ee_initialized:
        return True

    from app.config import settings

    if not settings.gee_configured:
        logger.warning(
            "GEE not configured: GEE_SERVICE_ACCOUNT_KEY and GEE_PROJECT_ID "
            "env vars are required. See docs/GEE_SETUP.md"
        )
        return False

    ee = _get_ee()

    try:
        key_data = json.loads(settings.gee_service_account_key)
        credentials = ee.ServiceAccountCredentials(
            settings.gee_service_account_email,
            key_data=key_data,
        )
        ee.Initialize(
            credentials=credentials,
            project=settings.gee_project_id,
        )
        _ee_initialized = True
        logger.info("GEE initialized successfully with service account")
        return True

    except Exception as e:
        logger.error(f"GEE initialization failed: {e}")
        return False


def _get_s2_composite(
    lat: float,
    lon: float,
    start_date: str,
    end_date: str,
    buffer_m: int = 500,
):
    """
    Fetch a Sentinel-2 median composite from GEE.
    Fully coordinate-agnostic — works for any lat/lon on Earth.

    Returns (ee.Image, ee.Geometry) tuple.
    """
    from app.config import settings
    ee = _get_ee()

    point = ee.Geometry.Point([lon, lat])
    roi = point.buffer(buffer_m)

    collection = (
        ee.ImageCollection(settings.gee_collection)
        .filterBounds(roi)
        .filterDate(start_date, end_date)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", settings.gee_cloud_cover_max))
        .select(settings.bands_analysis)
    )

    # Check if any images exist for this location/time window
    count = collection.size().getInfo()
    if count == 0:
        raise ValueError(
            f"No Sentinel-2 images found for ({lat}, {lon}) between "
            f"{start_date} and {end_date} with <{settings.gee_cloud_cover_max}% cloud cover. "
            f"Try a larger time window or check if this location has coverage."
        )

    composite = collection.median().clip(roi)
    return composite, roi, count


def _compute_indices_from_image(image, roi) -> dict:
    """
    Compute mean NDVI and NDWI from an ee.Image over a region.

    NDVI = (NIR - Red) / (NIR + Red) = (B8 - B4) / (B8 + B4)
    NDWI = (Green - NIR) / (Green + NIR) = (B3 - B8) / (B3 + B8)
    """
    from app.config import settings
    ee = _get_ee()

    nir = image.select(settings.band_nir)
    red = image.select(settings.band_red)
    green = image.select(settings.band_green)

    ndvi = nir.subtract(red).divide(nir.add(red)).rename("NDVI")
    ndwi = green.subtract(nir).divide(green.add(nir)).rename("NDWI")

    stats = ndvi.addBands(ndwi).reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=roi,
        scale=settings.gee_scale_m,
        maxPixels=1e6,
    ).getInfo()

    ndvi_val = stats.get("NDVI")
    ndwi_val = stats.get("NDWI")

    if ndvi_val is None or ndwi_val is None:
        raise ValueError("NDVI/NDWI computation returned null — region may have no valid pixels")

    return {
        "ndvi": round(float(ndvi_val), 4),
        "ndwi": round(float(ndwi_val), 4),
    }


async def get_snapshot_indices(
    lat: float,
    lon: float,
    buffer_m: int = 500,
) -> dict:
    """
    SNAPSHOT MODE: Get current NDVI/NDWI for any point on Earth.
    Returns absolute indices, no deltas, no before/after.

    Used for arbitrary-point queries where no baseline date is known.
    """
    from app.config import settings

    if not initialize_gee():
        return {
            "error": "gee_not_configured",
            "message": "Google Earth Engine credentials not configured. See docs/GEE_SETUP.md",
        }

    try:
        composite, roi, image_count = _get_s2_composite(
            lat, lon,
            settings.t_now_start,
            settings.t_now_end,
            buffer_m,
        )

        indices = _compute_indices_from_image(composite, roi)

        return {
            "ndvi_tnow": indices["ndvi"],
            "ndwi_tnow": indices["ndwi"],
            "tnow_start_date": settings.t_now_start,
            "tnow_end_date": settings.t_now_end,
            "image_count": image_count,
            "source": "gee",
        }

    except Exception as e:
        logger.error(f"GEE snapshot query failed for ({lat}, {lon}): {e}")
        return {
            "error": "gee_query_failed",
            "message": str(e),
        }


async def get_full_indices(
    lat: float,
    lon: float,
    baseline_start: str,
    baseline_end: str,
    buffer_m: int = 500,
) -> dict:
    """
    FULL MODE: Get NDVI/NDWI for both baseline (T0) and current (T_NOW) periods.
    Returns absolute values + deltas.

    Used for seeded demo sites and user sites with a known baseline date.

    baseline_start/baseline_end define the T0 window (e.g. "2024-01-01" to "2024-03-31").
    T_NOW is always computed dynamically as today-90d → today.
    """
    from app.config import settings

    if not initialize_gee():
        return {
            "error": "gee_not_configured",
            "message": "Google Earth Engine credentials not configured.",
        }

    try:
        # Fetch T0 (baseline)
        composite_t0, roi_t0, count_t0 = _get_s2_composite(
            lat, lon, baseline_start, baseline_end, buffer_m,
        )
        indices_t0 = _compute_indices_from_image(composite_t0, roi_t0)

        # Fetch T_NOW (current)
        composite_tnow, roi_tnow, count_tnow = _get_s2_composite(
            lat, lon, settings.t_now_start, settings.t_now_end, buffer_m,
        )
        indices_tnow = _compute_indices_from_image(composite_tnow, roi_tnow)

        return {
            "ndvi_t0": indices_t0["ndvi"],
            "ndwi_t0": indices_t0["ndwi"],
            "t0_start_date": baseline_start,
            "t0_end_date": baseline_end,
            "ndvi_tnow": indices_tnow["ndvi"],
            "ndwi_tnow": indices_tnow["ndwi"],
            "tnow_start_date": settings.t_now_start,
            "tnow_end_date": settings.t_now_end,
            "delta_ndvi": round(indices_tnow["ndvi"] - indices_t0["ndvi"], 4),
            "delta_ndwi": round(indices_tnow["ndwi"] - indices_t0["ndwi"], 4),
            "image_count_t0": count_t0,
            "image_count_tnow": count_tnow,
            "source": "gee",
        }

    except Exception as e:
        logger.error(f"GEE full query failed for ({lat}, {lon}): {e}")
        return {
            "error": "gee_query_failed",
            "message": str(e),
        }


def is_gee_configured() -> bool:
    """Check if GEE credentials are present (without initializing)."""
    from app.config import settings
    return settings.gee_configured
