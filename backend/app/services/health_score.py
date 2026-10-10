"""
Watershed health score computation — surface-type-aware scoring.

Replaces the delta-only formula with a surface-type classifier that uses
MNDWI, NDVI, NDBI, and per-pixel surface fractions to determine what kind
of surface is at a point, then scores it appropriately:

  - WATER: scored on surface-area stability (not NDVI)
  - LAND: 70% absolute NDVI condition + 30% same-season trend
  - URBAN: scored on green + blue cover fraction

When no photo/classification exists, agreement and confidence components
are dropped entirely and remaining weights are renormalized — not defaulted
to 50.

Grade bands (A/B/C/D/F) are configurable and returned in the API response
as heuristic thresholds, not scientific ones.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


# ── Grade Configuration (returned in API response) ──────────────────────────

GRADE_BANDS = {
    "A": {"min": 80, "label": "Excellent"},
    "B": {"min": 65, "label": "Good"},
    "C": {"min": 50, "label": "Fair"},
    "D": {"min": 35, "label": "Poor"},
    "F": {"min": 0, "label": "Critical"},
}


def _grade(score: int) -> str:
    """Assign letter grade from numeric score."""
    if score >= 80:
        return "A"
    elif score >= 65:
        return "B"
    elif score >= 50:
        return "C"
    elif score >= 35:
        return "D"
    else:
        return "F"


def get_grade_bands() -> dict:
    """Return the grade bands config for API response transparency."""
    return GRADE_BANDS


# ── Surface Type Classification ──────────────────────────────────────────────

def classify_surface_type(fractions: dict) -> str:
    """
    Classify the dominant surface type from per-pixel fractions.

    Args:
        fractions: dict with water_frac, veg_frac, built_frac

    Returns:
        "water", "urban", or "land"
    """
    water_frac = fractions.get("water_frac", 0)
    built_frac = fractions.get("built_frac", 0)

    if water_frac >= 0.5:
        return "water"
    if built_frac >= 0.4:
        return "urban"
    return "land"


# ── Satellite Score by Surface Type ──────────────────────────────────────────

def _clamp(x: float) -> float:
    """Clamp to [0.0, 1.0]."""
    return max(0.0, min(1.0, x))


def compute_satellite_score(
    now: dict,
    base: Optional[dict] = None,
) -> tuple[str, int, dict]:
    """
    Compute a surface-type-aware satellite score.

    Args:
        now: dict with ndvi, mndwi, ndbi, water_frac, veg_frac, built_frac
        base: optional dict with same keys (for trend computation).
              If None, only absolute condition is scored.

    Returns:
        (surface_type, score_0_to_100, components_dict)

    The scoring rules:
      - WATER: surface-area stability. A stable or expanding water body gets
        high scores. Never depends on NDVI.
      - LAND: 70% absolute NDVI condition (0.05→0.60 maps to 0→100) +
        30% same-season NDVI trend (delta from -0.2 to +0.2 maps to 0→100).
        If no baseline, 100% absolute.
      - URBAN: green + blue cover share. (veg_frac + water_frac) / 0.4 → 0-100.
        UI should label this "Green & Blue Cover", not "Watershed Health".
    """
    fractions_now = {
        "water_frac": now.get("water_frac", 0),
        "veg_frac": now.get("veg_frac", 0),
        "built_frac": now.get("built_frac", 0),
    }
    surface = classify_surface_type(fractions_now)
    components = {}

    if surface == "water":
        if base is not None:
            base_water = max(base.get("water_frac", 0), 0.05)
            change = (now.get("water_frac", 0) - base.get("water_frac", 0)) / base_water
            # -50% extent → 0, no loss → 100, growth capped at 100
            stability_score = _clamp((change + 0.5) / 0.5)
            score = round(100 * stability_score)
            components["water_stability"] = round(100 * stability_score, 1)
            components["water_frac_now"] = round(now.get("water_frac", 0), 4)
            components["water_frac_base"] = round(base.get("water_frac", 0), 4)
            components["water_change_pct"] = round(change * 100, 1)
        else:
            # No baseline — score based on absolute water presence
            # If water_frac >= 0.5, it IS a water body; score high for clear detection
            wf = now.get("water_frac", 0)
            score = round(100 * _clamp(wf / 0.7))
            components["water_frac_now"] = round(wf, 4)
            components["absolute_water_score"] = score

    elif surface == "land":
        ndvi_now = now.get("ndvi", 0)
        # Absolute condition: NDVI 0.05→0.60 maps to 0→100
        absolute = _clamp((ndvi_now - 0.05) / 0.55)

        if base is not None:
            ndvi_base = base.get("ndvi", 0)
            delta = ndvi_now - ndvi_base
            # Trend: delta from -0.2 to +0.2 maps to 0→100
            trend = _clamp((delta + 0.2) / 0.4)
            score = round(100 * (0.7 * absolute + 0.3 * trend))
            components["absolute_ndvi_condition"] = round(100 * absolute, 1)
            components["seasonal_trend"] = round(100 * trend, 1)
            components["ndvi_now"] = round(ndvi_now, 4)
            components["ndvi_base"] = round(ndvi_base, 4)
            components["ndvi_delta"] = round(delta, 4)
        else:
            score = round(100 * absolute)
            components["absolute_ndvi_condition"] = round(100 * absolute, 1)
            components["ndvi_now"] = round(ndvi_now, 4)

    else:  # urban
        veg_frac = now.get("veg_frac", 0)
        water_frac = now.get("water_frac", 0)
        green_blue = veg_frac + water_frac
        score = round(100 * _clamp(green_blue / 0.4))
        components["green_blue_cover"] = round(green_blue, 4)
        components["veg_frac"] = round(veg_frac, 4)
        components["water_frac"] = round(water_frac, 4)

    return surface, max(0, min(100, score)), components


# ── Full Health Score (with optional photo/validation) ───────────────────────

def compute_health_score_full(
    satellite_data: dict,
    validation_result: dict,
) -> dict:
    """
    FULL MODE health score — surface-type-aware, with optional cross-validation.

    Weights:
      - If photo classification exists: 60% satellite + 20% agreement + 20% confidence
      - If no photo: 100% satellite (renormalized — not defaulted to 50)

    Args:
        satellite_data: dict with all indices and fractions for both windows
        validation_result: dict with overall_status, details.photo_confidence

    Returns:
        dict with score (0-100), grade (A-F), surface_type, mode, components,
        grade_bands
    """
    # Build now/base dicts from satellite_data
    now = _extract_window(satellite_data, "tnow")
    base = _extract_window(satellite_data, "t0")

    surface, sat_score, sat_components = compute_satellite_score(now, base)

    # Check if photo evidence exists
    photo_confidence = validation_result.get("details", {}).get("photo_confidence")
    has_photo = photo_confidence is not None

    if has_photo:
        # Agreement score
        status = validation_result.get("overall_status", "inconclusive")
        if status == "confirmed":
            agreement_score = 100.0
        elif status == "inconclusive":
            agreement_score = 50.0
        else:
            agreement_score = 0.0

        confidence_score = photo_confidence * 100

        score = round(
            0.60 * sat_score
            + 0.20 * agreement_score
            + 0.20 * confidence_score
        )
    else:
        # No photo → satellite score is 100% of the grade
        score = sat_score

    score = max(0, min(100, score))
    grade = _grade(score)

    # Determine the UI label
    if surface == "urban":
        label = "Green & Blue Cover"
    elif surface == "water":
        label = "Water Body Health"
    else:
        label = "Watershed Health"

    components = {
        "satellite_score": sat_score,
        **sat_components,
    }
    if has_photo:
        components["agreement_score"] = round(agreement_score, 1)
        components["confidence_score"] = round(confidence_score, 1)

    return {
        "score": score,
        "grade": grade,
        "surface_type": surface,
        "label": label,
        "mode": "full",
        "components": components,
        "grade_bands": GRADE_BANDS,
        # Low data warnings
        "low_data_t0": satellite_data.get("low_data_t0", False),
        "low_data_tnow": satellite_data.get("low_data_tnow", False),
    }


def compute_health_score_snapshot(
    satellite_data: dict,
    classification_result: Optional[dict] = None,
) -> dict:
    """
    SNAPSHOT MODE health score — for arbitrary points without a baseline.
    Uses absolute indices and surface fractions. No implied "intervention."

    Weights:
      - If photo classification exists: 70% satellite + 30% confidence
      - If no photo: 100% satellite (renormalized)

    Args:
        satellite_data: dict with ndvi_tnow, mndwi_tnow, etc.
        classification_result: optional dict with confidence

    Returns:
        dict with score (0-100), grade (A-F), surface_type, mode, components,
        grade_bands
    """
    now = _extract_window(satellite_data, "tnow")

    surface, sat_score, sat_components = compute_satellite_score(now, base=None)

    if classification_result is not None:
        confidence = classification_result.get("confidence", 0.5)
        confidence_score = confidence * 100
        score = round(0.70 * sat_score + 0.30 * confidence_score)
    else:
        score = sat_score
        confidence_score = None

    score = max(0, min(100, score))
    grade = _grade(score)

    if surface == "urban":
        label = "Green & Blue Cover"
    elif surface == "water":
        label = "Water Body Health"
    else:
        label = "Watershed Health"

    components = {
        "satellite_score": sat_score,
        **sat_components,
    }
    if confidence_score is not None:
        components["confidence_score"] = round(confidence_score, 1)

    return {
        "score": score,
        "grade": grade,
        "surface_type": surface,
        "label": label,
        "mode": "snapshot",
        "components": components,
        "grade_bands": GRADE_BANDS,
        "low_data_tnow": satellite_data.get("low_data_tnow", False),
    }


# ── Helpers ──────────────────────────────────────────────────────────────────

def _extract_window(sat_data: dict, suffix: str) -> dict:
    """
    Extract a window's worth of data from satellite_data dict.

    For suffix="tnow", looks for ndvi_tnow, mndwi_tnow, water_frac_tnow, etc.
    For suffix="t0", looks for ndvi_t0, mndwi_t0, water_frac_t0, etc.

    Falls back to legacy keys (ndwi_tnow → mndwi if mndwi missing).
    """
    def _get(key):
        # Try the suffixed key first
        val = sat_data.get(f"{key}_{suffix}")
        if val is not None:
            return val
        # Legacy fallback
        if key == "mndwi":
            return sat_data.get(f"ndwi_{suffix}", 0)
        return 0

    return {
        "ndvi": _get("ndvi"),
        "mndwi": _get("mndwi"),
        "ndbi": _get("ndbi"),
        "water_frac": _get("water_frac"),
        "veg_frac": _get("veg_frac"),
        "built_frac": _get("built_frac"),
    }


def compute_watershed_summary(health_scores: list[dict]) -> dict:
    """
    Aggregate health scores across multiple sites.

    Returns overall score, count, grade distribution.
    """
    if not health_scores:
        return {"overall_score": 0, "site_count": 0, "grade_distribution": {}}

    scores = [h["score"] for h in health_scores]
    grades = [h["grade"] for h in health_scores]

    grade_dist = {}
    for g in ["A", "B", "C", "D", "F"]:
        grade_dist[g] = grades.count(g)

    return {
        "overall_score": round(sum(scores) / len(scores)),
        "site_count": len(scores),
        "min_score": min(scores),
        "max_score": max(scores),
        "grade_distribution": grade_dist,
    }
