"""
Watershed health score computation — surface-type-aware scoring.

Replaces the delta-only formula with a surface-type classifier that uses
MNDWI, NDVI, NDBI, and per-pixel surface fractions to determine what kind
of surface is at a point, then scores it appropriately:

  - WATER: scored on surface-area stability (not NDVI)
  - LAND: 70% absolute NDVI condition + 30% same-season trend
  - URBAN: scored on green + blue cover fraction ("Green and blue cover")

When no photo/classification exists, agreement and confidence components
are dropped entirely and remaining weights are renormalized — not defaulted
to 50.

Grade bands (A/B/C/D/F) are configurable and returned in the API response
as heuristic thresholds, not scientific ones.
"""

import logging
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)


# ── Grade Configuration (heuristic thresholds, returned in API) ─────────────

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
    """Return the heuristic grade bands config for API transparency."""
    return GRADE_BANDS


def _clamp(x: float) -> float:
    """Clamp to [0.0, 1.0]."""
    return max(0.0, min(1.0, float(x)))


# ── Surface Type Classification ──────────────────────────────────────────────

def surface_type(f: dict) -> str:
    """
    Classify surface type with strict mutual exclusivity & precedence:
      water > built-up (urban) > vegetation (land) > barren.
    """
    water_frac = f.get("water_frac", 0.0)
    built_frac = f.get("built_frac", 0.0)
    veg_frac = f.get("veg_frac", 0.0)

    # 1. Water: water fraction >= 0.50
    if water_frac >= 0.50:
        return "water"
    # 2. Built-up / Urban: built fraction >= 0.35
    if built_frac >= 0.35:
        return "urban"
    # 3. Vegetation / Forest / Land: vegetation fraction >= 0.40
    if veg_frac >= 0.40:
        return "land"
    # 4. Barren: exposed rock, quarries, bare earth
    return "barren"


# Alias for backward compatibility
classify_surface_type = surface_type


# ── Satellite Score by Surface Type ──────────────────────────────────────────

def satellite_score(now: dict, base: Optional[dict] = None) -> tuple[str, int]:
    """
    Specification satellite score function:
    Returns (surface_type, score_0_to_100).
    """
    st, score, _ = compute_satellite_score(now, base)
    return st, score


def compute_satellite_score(
    now: dict,
    base: Optional[dict] = None,
) -> tuple[str, int, dict]:
    """
    Compute a surface-type-aware satellite score with full component breakdown.

    Rules:
      - WATER: judged on surface-area stability year-over-year.
        If baseline is absent or has low_data: score from current water extent,
        never assume stability = 100.
      - LAND: 0.85 NDVI ceiling so climax canopy doesn't saturate at 100:
        absolute = clamp((now["ndvi"] - 0.10) / 0.75)
        trend = clamp(((now["ndvi"] - base["ndvi"]) + 0.2) / 0.4)
        round(100 * (0.7 * absolute + 0.3 * trend))
      - URBAN: capped at 50 so built-up areas with street trees cannot score above 50:
        round(50 * clamp((now["veg_frac"] + now["water_frac"]) / 0.4))
      - BARREN: bare rock, quarries, dry soil capped at <= 35:
        round(35 * clamp((now["ndvi"] - 0.05) / 0.40))
    """
    t = surface_type(now)
    components = {
        "surface_type": t,
    }

    if t == "water":
        base_low_data = base.get("low_data", False) if base else True
        if base is not None and not base_low_data:
            base_water = max(base.get("water_frac", 0.0), 0.05)
            now_water = now.get("water_frac", 0.0)
            change = (now_water - base_water) / base_water
            stability = _clamp((change + 0.5) / 0.5)
            score = round(100 * stability)
            components["water_stability"] = round(100 * stability, 1)
            components["water_frac_now"] = round(now_water, 4)
            components["water_frac_base"] = round(base_water, 4)
            components["water_change_pct"] = round(change * 100, 1)
        else:
            # Low data or no baseline: score from current water extent only; never assume stable = 100
            now_water = now.get("water_frac", 0.0)
            score = round(70 * _clamp(now_water / 0.5))
            components["water_frac_now"] = round(now_water, 4)
            components["water_stability"] = None
            components["baseline_status"] = "no baseline"

        if now.get("ndti") is not None:
            components["turbidity_proxy_ndti"] = round(now["ndti"], 4)
        if now.get("ndci") is not None:
            components["chlorophyll_proxy_ndci"] = round(now["ndci"], 4)

    elif t == "land":
        ndvi_now = now.get("ndvi", 0.0)
        # 0.85 NDVI ceiling prevents dense canopy from saturating at 100
        absolute = _clamp((ndvi_now - 0.10) / 0.75)

        base_low_data = base.get("low_data", False) if base else True
        if base is not None and not base_low_data:
            ndvi_base = base.get("ndvi", 0.0)
            delta = ndvi_now - ndvi_base
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

    elif t == "urban":
        # Built-up area with street trees cannot score above about 50
        veg_frac = now.get("veg_frac", 0.0)
        water_frac = now.get("water_frac", 0.0)
        green_blue = veg_frac + water_frac
        score = round(50 * _clamp(green_blue / 0.4))
        components["green_blue_cover"] = round(green_blue, 4)
        components["veg_frac"] = round(veg_frac, 4)
        components["water_frac"] = round(water_frac, 4)

    else:  # barren (quarries, exposed rock, barren land)
        ndvi_now = now.get("ndvi", 0.0)
        score = round(35 * _clamp((ndvi_now - 0.05) / 0.40))
        components["barren_ndvi"] = round(ndvi_now, 4)
        components["barren_frac"] = round(now.get("barren_frac", 0.0), 4)

    return t, max(0, min(100, score)), components


# ── Full Health Score (with optional photo/validation) ───────────────────────

def compute_health_score_full(
    satellite_data: dict,
    validation_result: dict,
) -> dict:
    """
    FULL MODE health score — surface-type-aware, with optional cross-validation.

    Weights:
      - If photo evidence exists: 60% satellite + 20% agreement + 20% confidence
      - If NO photo: 100% satellite (renormalized — NOT defaulted to 50!)
    """
    now = _extract_window(satellite_data, "tnow")
    base = _extract_window(satellite_data, "t0")

    if "delta_ndvi" in satellite_data and "ndvi_tnow" not in satellite_data:
        delta_v = satellite_data.get("delta_ndvi", 0.0)
        delta_w = satellite_data.get("delta_ndwi", 0.0)
        now["ndvi"] = 0.35 + delta_v / 2
        base["ndvi"] = 0.35 - delta_v / 2
        now["mndwi"] = delta_w / 2
        base["mndwi"] = -delta_w / 2

    surface, sat_score, sat_components = compute_satellite_score(now, base)

    photo_conf = validation_result.get("details", {}).get("photo_confidence")
    has_photo = photo_conf is not None

    if has_photo:
        status = validation_result.get("overall_status", "inconclusive")
        if status == "confirmed":
            agreement_score = 100.0
        elif status == "inconclusive":
            agreement_score = 50.0
        else:
            agreement_score = 0.0

        confidence_score = float(photo_conf) * 100.0
        score = round(
            0.60 * sat_score
            + 0.20 * agreement_score
            + 0.20 * confidence_score
        )
    else:
        score = sat_score
        agreement_score = None
        confidence_score = None

    score = max(0, min(100, score))
    grade = _grade(score)

    if surface == "urban":
        label = "Urban Watershed Health"
    elif surface == "water":
        label = "Water Body Health"
    elif surface == "barren":
        label = "Barren Land / Excavation"
    else:
        label = "Watershed Health"

    delta_ndvi_val = satellite_data.get("delta_ndvi", now.get("ndvi", 0) - base.get("ndvi", 0))
    delta_ndwi_val = satellite_data.get("delta_ndwi", now.get("mndwi", 0) - base.get("mndwi", 0))

    components = {
        "satellite_score": sat_score,
        **sat_components,
        "ndvi_trend_score": round(_normalize_delta(delta_ndvi_val), 1),
        "ndwi_trend_score": round(_normalize_delta(delta_ndwi_val), 1),
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
        "low_data_t0": satellite_data.get("low_data_t0", False),
        "low_data_tnow": satellite_data.get("low_data_tnow", False),
    }


# ── Snapshot Health Score ───────────────────────────────────────────────────

def compute_health_score_snapshot(
    satellite_data: dict,
    classification_result: Optional[dict] = None,
) -> dict:
    """
    SNAPSHOT MODE health score — for arbitrary points without a baseline.
    Uses absolute indices and surface fractions. No implied "intervention."

    Weights:
      - If photo classification exists: 70% satellite + 30% confidence
      - If NO photo: 100% satellite (renormalized)
    """
    now = _extract_window(satellite_data, "tnow")

    if "ndvi_tnow" in satellite_data and "veg_frac_tnow" not in satellite_data:
        ndvi_val = satellite_data.get("ndvi_tnow", 0.0)
        ndwi_val = satellite_data.get("ndwi_tnow", 0.0)
        now["ndvi"] = ndvi_val
        now["mndwi"] = ndwi_val
        if ndwi_val > 0.2 and ndvi_val <= 0.0:
            now["water_frac"] = 0.8
        elif ndvi_val > 0.3:
            now["veg_frac"] = 0.6
        elif ndvi_val < 0.2 and ndwi_val < -0.1:
            now["built_frac"] = 0.6

    base = _extract_window(satellite_data, "t0") if ("ndvi_t0" in satellite_data or "water_frac_t0" in satellite_data) else None
    surface, sat_score, sat_components = compute_satellite_score(now, base=base)

    if classification_result is not None:
        conf = classification_result.get("confidence", 0.5)
        confidence_score = float(conf) * 100.0
        score = round(0.70 * sat_score + 0.30 * confidence_score)
    else:
        score = sat_score
        confidence_score = None

    score = max(0, min(100, score))
    grade = _grade(score)

    if surface == "urban":
        label = "Urban Watershed Health"
    elif surface == "water":
        label = "Water Body Health"
    elif surface == "barren":
        label = "Barren Land / Excavation"
    else:
        label = "Watershed Health"

    ndvi_val = now.get("ndvi", 0.0)
    mndwi_val = now.get("mndwi", 0.0)

    components = {
        "satellite_score": sat_score,
        **sat_components,
        "ndvi_absolute_score": round(_absolute_ndvi_score(ndvi_val), 1),
        "ndwi_absolute_score": round(_absolute_ndwi_score(mndwi_val), 1),
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
    """Extract a window's data from satellite_data dict."""
    def _get(key):
        val = sat_data.get(f"{key}_{suffix}")
        if val is not None:
            return float(val)
        if key == "mndwi":
            legacy = sat_data.get(f"ndwi_{suffix}")
            if legacy is not None:
                return float(legacy)
        val = sat_data.get(key)
        if val is not None:
            return float(val)
        return 0.0

    return {
        "ndvi": _get("ndvi"),
        "mndwi": _get("mndwi"),
        "ndbi": _get("ndbi"),
        "water_frac": _get("water_frac"),
        "veg_frac": _get("veg_frac"),
        "built_frac": _get("built_frac"),
        "ndti": sat_data.get(f"ndti_{suffix}"),
        "ndci": sat_data.get(f"ndci_{suffix}"),
    }


def _normalize_delta(delta: float, min_val: float = None, max_val: float = None) -> float:
    """Normalize a delta value from [min_val, max_val] to [0, 100]."""
    if min_val is None:
        min_val = settings.index_delta_min
    if max_val is None:
        max_val = settings.index_delta_max
    if max_val == min_val:
        return 50.0
    normalized = (delta - min_val) / (max_val - min_val) * 100
    return max(0.0, min(100.0, normalized))


def _absolute_ndvi_score(ndvi: float) -> float:
    """Legacy absolute NDVI scorer for backwards compatibility."""
    if ndvi >= 0.5:
        return 100.0
    elif ndvi >= 0.3:
        return 60.0 + (ndvi - 0.3) / 0.2 * 40.0
    elif ndvi >= 0.15:
        return 30.0 + (ndvi - 0.15) / 0.15 * 30.0
    elif ndvi >= 0.0:
        return ndvi / 0.15 * 30.0
    else:
        return 0.0


def _absolute_ndwi_score(ndwi: float) -> float:
    """Legacy absolute NDWI scorer for backwards compatibility."""
    if ndwi >= 0.3:
        return 100.0
    elif ndwi >= 0.0:
        return 50.0 + ndwi / 0.3 * 50.0
    elif ndwi >= -0.2:
        return 20.0 + (ndwi + 0.2) / 0.2 * 30.0
    else:
        return max(0.0, 20.0 + (ndwi + 0.2) / 0.3 * 20.0)


def compute_watershed_summary(health_scores: list[dict]) -> dict:
    """Aggregate health scores across multiple sites."""
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
