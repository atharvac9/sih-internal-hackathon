"""
Google Earth Engine service — service-account auth, coordinate-agnostic
Sentinel-2 queries with Cloud Score+ pixel masking, MNDWI, NDBI, and
surface-fraction analysis.

Supports two modes:
- FULL: queries both baseline and current windows → returns deltas + fractions
- SNAPSHOT: queries current window only → returns absolute indices + fractions

NO hardcoded bounding boxes or region filters. Any lat/lon works.

Changes from original:
  - Cloud Score+ pixel masking (cs_cdf >= 0.6), SCL fallback
  - B11 (SWIR1) added; bands divided by 10000
  - MNDWI = (B3-B11)/(B3+B11) replaces McFeeters NDWI
  - NDBI = (B11-B8)/(B11+B8) for built-up detection
  - Surface fractions: water_frac, veg_frac, built_frac
  - Valid-pixel count + scene count; low_data flag when < 30% valid
  - Same-season baseline window builder (no dry-vs-monsoon comparison)
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# Earth Engine is imported lazily to avoid import-time failures
_ee = None
_ee_initialized = False
_ee_last_error = None


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


def get_gee_init_error() -> Optional[str]:
    """Return the last error message from ee.Initialize failure, if any."""
    return _ee_last_error


def is_gee_initialized() -> bool:
    """Return whether ee.Initialize has successfully run."""
    return _ee_initialized


def initialize_gee() -> bool:
    """
    Initialize GEE with service-account credentials from env vars.
    Supports either a direct JSON string or a file path (e.g. C:\\keys\\gee-key.json).
    Returns True if successful, False if credentials are not configured or failed.
    """
    global _ee_initialized, _ee_last_error

    if _ee_initialized:
        return True

    from app.config import settings

    if not settings.gee_configured:
        _ee_last_error = "GEE not configured: GEE_SERVICE_ACCOUNT_KEY env var is required"
        logger.warning(_ee_last_error)
        return False

    ee = _get_ee()

    try:
        import os
        key_raw = settings.gee_service_account_key.strip()
        if os.path.isfile(key_raw):
            with open(key_raw, "r", encoding="utf-8") as f:
                key_raw = f.read().strip()

        key_data = json.loads(key_raw)
        email = settings.gee_service_account_email or key_data.get("client_email")
        project_id = settings.gee_project_id or key_data.get("project_id")

        if not email or not project_id:
            _ee_last_error = "Missing client_email or project_id in GEE credentials"
            logger.error(_ee_last_error)
            return False

        credentials = ee.ServiceAccountCredentials(
            email,
            key_data=key_raw,
        )
        ee.Initialize(
            credentials=credentials,
            project=project_id,
        )
        _ee_initialized = True
        _ee_last_error = None
        logger.info(f"GEE initialized successfully for project '{project_id}'")
        return True

    except Exception as e:
        _ee_last_error = str(e)
        logger.error(f"GEE initialization failed: {e}")
        return False


# ── Window builders ──────────────────────────────────────────────────────────

def compute_windows(
    reference_date: Optional[str] = None,
    baseline_years_back: int = 1,
) -> dict:
    """
    Build same-season current and baseline windows.

    Current window: reference_date - 90d → reference_date
    Baseline window: same calendar months, `baseline_years_back` years earlier.

    If reference_date is None, uses today (UTC).

    Returns dict with current_start, current_end, baseline_start, baseline_end.
    """
    if reference_date:
        ref = datetime.strptime(reference_date, "%Y-%m-%d")
    else:
        ref = datetime.now(timezone.utc)

    current_end = ref
    current_start = ref - timedelta(days=90)

    # Same calendar months, N years back
    try:
        baseline_end = current_end.replace(year=current_end.year - baseline_years_back)
        baseline_start = current_start.replace(year=current_start.year - baseline_years_back)
    except ValueError:
        # Handle Feb 29 → Feb 28 for non-leap years
        baseline_end = current_end.replace(
            year=current_end.year - baseline_years_back,
            day=min(current_end.day, 28),
        )
        baseline_start = current_start.replace(
            year=current_start.year - baseline_years_back,
            day=min(current_start.day, 28),
        )

    return {
        "current_start": current_start.strftime("%Y-%m-%d"),
        "current_end": current_end.strftime("%Y-%m-%d"),
        "baseline_start": baseline_start.strftime("%Y-%m-%d"),
        "baseline_end": baseline_end.strftime("%Y-%m-%d"),
    }


def compute_intervention_windows(
    intervention_date: str,
    baseline_years_back: int = 1,
) -> dict:
    """
    For seeded intervention sites: baseline is same season in the year before
    the intervention. Current window is today-90d → today.

    Returns dict with current_start, current_end, baseline_start, baseline_end.
    """
    now = datetime.now(timezone.utc)
    current_end = now
    current_start = now - timedelta(days=90)

    # Baseline: same calendar months as current window, but in the year
    # before the intervention
    intervention_dt = datetime.strptime(intervention_date, "%Y-%m-%d")
    pre_intervention_year = intervention_dt.year - baseline_years_back

    try:
        baseline_start = current_start.replace(year=pre_intervention_year)
        baseline_end = current_end.replace(year=pre_intervention_year)
    except ValueError:
        baseline_start = current_start.replace(
            year=pre_intervention_year, day=min(current_start.day, 28)
        )
        baseline_end = current_end.replace(
            year=pre_intervention_year, day=min(current_end.day, 28)
        )

    return {
        "current_start": current_start.strftime("%Y-%m-%d"),
        "current_end": current_end.strftime("%Y-%m-%d"),
        "baseline_start": baseline_start.strftime("%Y-%m-%d"),
        "baseline_end": baseline_end.strftime("%Y-%m-%d"),
    }


# ── Cloud-masked composite ──────────────────────────────────────────────────

LOW_DATA_THRESHOLD = 0.30  # minimum fraction of valid pixels


def _build_s2_composite(roi, start_date: str, end_date: str):
    """
    Build a cloud-masked Sentinel-2 median composite.

    Strategy:
      1. Try Cloud Score+ (cs_cdf >= 0.6) — best quality
      2. Fallback to SCL mask (drop clouds, shadows, snow, saturated) if
         Cloud Score+ collection is empty or linkCollection fails

    Returns (composite_image, scene_count).
    Bands are divided by 10000 so indices use reflectance [0, 1].
    """
    ee = _get_ee()

    bands_to_select = ["B2", "B3", "B4", "B5", "B8", "B11", "SCL"]

    s2 = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(roi)
        .filterDate(start_date, end_date)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 80))
        .select(bands_to_select)
    )

    scene_count = s2.size().getInfo()
    if scene_count == 0:
        return None, 0

    # Try Cloud Score+ pixel masking
    try:
        cs = (
            ee.ImageCollection("GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED")
            .filterBounds(roi)
            .filterDate(start_date, end_date)
        )
        cs_count = cs.size().getInfo()

        if cs_count > 0:
            s2_masked = s2.linkCollection(cs, ["cs_cdf"]).map(
                lambda img: img.updateMask(img.select("cs_cdf").gte(0.6))
            )
            logger.info(
                f"Cloud Score+ masking: {scene_count} scenes, "
                f"{cs_count} CS+ scenes linked"
            )
        else:
            logger.warning("Cloud Score+ empty for this window, falling back to SCL")
            s2_masked = _apply_scl_mask(s2)
    except Exception as e:
        logger.warning(f"Cloud Score+ linkCollection failed ({e}), falling back to SCL")
        s2_masked = _apply_scl_mask(s2)

    # Compute median composite and scale to reflectance
    reflectance_bands = ["B2", "B3", "B4", "B5", "B8", "B11"]
    composite = s2_masked.select(reflectance_bands).median().divide(10000).clip(roi)

    return composite, scene_count


def _apply_scl_mask(collection):
    """
    Fallback cloud mask using the SCL (Scene Classification Layer) band.
    Drops: 1 (saturated/defective), 3 (cloud shadow), 8 (cloud medium),
           9 (cloud high), 10 (thin cirrus).
    """
    ee = _get_ee()

    def mask_scl(img):
        scl = img.select("SCL")
        mask = (
            scl.neq(1)
            .And(scl.neq(3))
            .And(scl.neq(8))
            .And(scl.neq(9))
            .And(scl.neq(10))
        )
        return img.updateMask(mask)

    return collection.map(mask_scl)


# ── Index and fraction computation ───────────────────────────────────────────

def _compute_indices_and_fractions(composite, roi, scale: int = 10) -> dict:
    """
    From a reflectance composite (bands already /10000), compute:
      - NDVI = (B8 - B4) / (B8 + B4)
      - MNDWI = (B3 - B11) / (B3 + B11)   (Modified NDWI — uses SWIR)
      - NDBI = (B11 - B8) / (B11 + B8)     (Normalized Difference Built-up)
      - Surface fractions: water_frac, veg_frac, built_frac
      - Valid pixel count and total pixel count

    Returns dict with all computed values plus a low_data flag.
    """
    ee = _get_ee()

    nir = composite.select("B8")
    red = composite.select("B4")
    green = composite.select("B3")
    swir1 = composite.select("B11")
    red_edge = composite.select("B5")

    # Spectral indices
    ndvi = nir.subtract(red).divide(nir.add(red)).rename("NDVI")
    mndwi = green.subtract(swir1).divide(green.add(swir1)).rename("MNDWI")
    ndbi = swir1.subtract(nir).divide(swir1.add(nir)).rename("NDBI")

    # Optional water-quality proxies
    ndti = red.subtract(green).divide(red.add(green)).rename("NDTI")
    ndci = red_edge.subtract(red).divide(red_edge.add(red)).rename("NDCI")

    # Mean indices over the buffer
    all_bands = ndvi.addBands(mndwi).addBands(ndbi).addBands(ndti).addBands(ndci)
    mean_stats = all_bands.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=roi,
        scale=scale,
        maxPixels=1e6,
    ).getInfo()

    # Surface fractions (per-pixel classification, then mean = fraction)
    is_water = mndwi.gt(0).rename("is_water")
    is_veg = ndvi.gt(0.3).And(mndwi.lte(0)).rename("is_veg")
    is_built = ndbi.gt(0).And(ndvi.lt(0.2)).And(mndwi.lte(0)).rename("is_built")

    fractions = is_water.addBands(is_veg).addBands(is_built)
    frac_stats = fractions.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=roi,
        scale=scale,
        maxPixels=1e6,
    ).getInfo()

    # Pixel counts for data-quality assessment
    valid_count = ndvi.reduceRegion(
        reducer=ee.Reducer.count(),
        geometry=roi,
        scale=scale,
        maxPixels=1e6,
    ).getInfo().get("NDVI", 0)

    # Total possible pixels (from unmasked geometry area / pixel area)
    area_m2 = roi.area().getInfo()
    total_pixels = max(1, int(area_m2 / (scale * scale)))
    valid_fraction = valid_count / total_pixels if total_pixels > 0 else 0

    ndvi_val = mean_stats.get("NDVI")
    mndwi_val = mean_stats.get("MNDWI")
    ndbi_val = mean_stats.get("NDBI")
    ndti_val = mean_stats.get("NDTI")
    ndci_val = mean_stats.get("NDCI")

    if ndvi_val is None or mndwi_val is None:
        raise ValueError(
            "Index computation returned null — region may have no valid pixels "
            "after cloud masking"
        )

    result = {
        "ndvi": round(float(ndvi_val), 4),
        "mndwi": round(float(mndwi_val), 4),
        "ndbi": round(float(ndbi_val), 4) if ndbi_val is not None else None,
        "ndti": round(float(ndti_val), 4) if ndti_val is not None else None,
        "ndci": round(float(ndci_val), 4) if ndci_val is not None else None,
        "water_frac": round(float(frac_stats.get("is_water", 0)), 4),
        "veg_frac": round(float(frac_stats.get("is_veg", 0)), 4),
        "built_frac": round(float(frac_stats.get("is_built", 0)), 4),
        "valid_pixels": int(valid_count),
        "total_pixels": total_pixels,
        "valid_fraction": round(valid_fraction, 4),
        "low_data": valid_fraction < LOW_DATA_THRESHOLD,
    }

    return result


# ── Public API ───────────────────────────────────────────────────────────────

async def get_snapshot_indices(
    lat: float,
    lon: float,
    buffer_m: int = 250,
) -> dict:
    """
    SNAPSHOT MODE: Get current indices + surface fractions for any point.
    Returns absolute indices, no deltas, no before/after.

    Used for arbitrary-point queries where no baseline date is known.
    """
    if not initialize_gee():
        return {
            "error": "gee_not_configured",
            "message": "Google Earth Engine credentials not configured. See docs/GEE_SETUP.md",
        }

    try:
        ee = _get_ee()
        point = ee.Geometry.Point([lon, lat])
        roi = point.buffer(buffer_m)

        windows = compute_windows()

        composite, scene_count = _build_s2_composite(
            roi, windows["current_start"], windows["current_end"],
        )

        if composite is None:
            return {
                "error": "no_imagery",
                "message": (
                    f"No Sentinel-2 images found for ({lat}, {lon}) between "
                    f"{windows['current_start']} and {windows['current_end']}."
                ),
            }

        indices = _compute_indices_and_fractions(composite, roi)

        return {
            "ndvi_tnow": indices["ndvi"],
            "mndwi_tnow": indices["mndwi"],
            "ndbi_tnow": indices["ndbi"],
            "ndti_tnow": indices["ndti"],
            "ndci_tnow": indices["ndci"],
            "water_frac_tnow": indices["water_frac"],
            "veg_frac_tnow": indices["veg_frac"],
            "built_frac_tnow": indices["built_frac"],
            "valid_pixels_tnow": indices["valid_pixels"],
            "total_pixels_tnow": indices["total_pixels"],
            "valid_fraction_tnow": indices["valid_fraction"],
            "low_data_tnow": indices["low_data"],
            "tnow_start_date": windows["current_start"],
            "tnow_end_date": windows["current_end"],
            "scene_count_tnow": scene_count,
            # Legacy compatibility
            "ndwi_tnow": indices["mndwi"],
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
    baseline_start: str = None,
    baseline_end: str = None,
    buffer_m: int = 500,
    intervention_date: str = None,
) -> dict:
    """
    FULL MODE: Get indices + fractions for both baseline and current windows.
    Returns absolute values, deltas, and surface fractions for both periods.

    Same-season comparison: baseline window has the same calendar months as
    the current window, but one year earlier. If intervention_date is provided,
    baseline is from the year before that intervention.

    If baseline_start/baseline_end are explicitly provided, those are used
    directly (for backward compatibility with seeded sites).
    """
    if not initialize_gee():
        return {
            "error": "gee_not_configured",
            "message": "Google Earth Engine credentials not configured.",
        }

    try:
        ee = _get_ee()
        point = ee.Geometry.Point([lon, lat])
        roi = point.buffer(buffer_m)

        # Build windows
        if baseline_start and baseline_end:
            # Legacy explicit windows — but we warn if they're cross-season
            windows = {
                "current_start": compute_windows()["current_start"],
                "current_end": compute_windows()["current_end"],
                "baseline_start": baseline_start,
                "baseline_end": baseline_end,
            }
        elif intervention_date:
            windows = compute_intervention_windows(intervention_date)
        else:
            windows = compute_windows()

        # Fetch baseline composite
        composite_t0, count_t0 = _build_s2_composite(
            roi, windows["baseline_start"], windows["baseline_end"],
        )
        if composite_t0 is None:
            return {
                "error": "no_imagery_baseline",
                "message": (
                    f"No Sentinel-2 images found for ({lat}, {lon}) in baseline "
                    f"window {windows['baseline_start']} to {windows['baseline_end']}."
                ),
            }
        indices_t0 = _compute_indices_and_fractions(composite_t0, roi)

        # Fetch current composite
        composite_tnow, count_tnow = _build_s2_composite(
            roi, windows["current_start"], windows["current_end"],
        )
        if composite_tnow is None:
            return {
                "error": "no_imagery_current",
                "message": (
                    f"No Sentinel-2 images found for ({lat}, {lon}) in current "
                    f"window {windows['current_start']} to {windows['current_end']}."
                ),
            }
        indices_tnow = _compute_indices_and_fractions(composite_tnow, roi)

        return {
            # T0 (baseline)
            "ndvi_t0": indices_t0["ndvi"],
            "mndwi_t0": indices_t0["mndwi"],
            "ndbi_t0": indices_t0["ndbi"],
            "water_frac_t0": indices_t0["water_frac"],
            "veg_frac_t0": indices_t0["veg_frac"],
            "built_frac_t0": indices_t0["built_frac"],
            "valid_pixels_t0": indices_t0["valid_pixels"],
            "valid_fraction_t0": indices_t0["valid_fraction"],
            "low_data_t0": indices_t0["low_data"],
            "t0_start_date": windows["baseline_start"],
            "t0_end_date": windows["baseline_end"],
            "scene_count_t0": count_t0,
            # T_NOW (current)
            "ndvi_tnow": indices_tnow["ndvi"],
            "mndwi_tnow": indices_tnow["mndwi"],
            "ndbi_tnow": indices_tnow["ndbi"],
            "ndti_tnow": indices_tnow["ndti"],
            "ndci_tnow": indices_tnow["ndci"],
            "water_frac_tnow": indices_tnow["water_frac"],
            "veg_frac_tnow": indices_tnow["veg_frac"],
            "built_frac_tnow": indices_tnow["built_frac"],
            "valid_pixels_tnow": indices_tnow["valid_pixels"],
            "valid_fraction_tnow": indices_tnow["valid_fraction"],
            "low_data_tnow": indices_tnow["low_data"],
            "tnow_start_date": windows["current_start"],
            "tnow_end_date": windows["current_end"],
            "scene_count_tnow": count_tnow,
            # Deltas
            "delta_ndvi": round(indices_tnow["ndvi"] - indices_t0["ndvi"], 4),
            "delta_mndwi": round(indices_tnow["mndwi"] - indices_t0["mndwi"], 4),
            "delta_ndbi": round(indices_tnow["ndbi"] - indices_t0["ndbi"], 4)
                if indices_tnow["ndbi"] is not None and indices_t0["ndbi"] is not None
                else None,
            # Legacy compatibility
            "ndwi_t0": indices_t0["mndwi"],
            "ndwi_tnow": indices_tnow["mndwi"],
            "delta_ndwi": round(indices_tnow["mndwi"] - indices_t0["mndwi"], 4),
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
