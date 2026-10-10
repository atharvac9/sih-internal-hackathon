"""
Watershed health score computation — ported from original with two modes:

FULL MODE (has T0 baseline):
  score = W_ndvi × ndvi_delta_score + W_ndwi × ndwi_delta_score
        + W_agreement × agreement_score + W_confidence × confidence_score
  This is the original formula — ecologically sound, unchanged.

SNAPSHOT MODE (arbitrary point, no baseline):
  score = 0.40 × ndvi_absolute_score + 0.40 × ndwi_absolute_score
        + 0.20 × confidence_score (if photo exists, else 50)
  Based on absolute current NDVI/NDWI values only — no delta, no agreement.
  The UI must NOT imply an "intervention" occurred.
"""

import logging
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)


def _normalize_delta(delta: float, min_val: float = None, max_val: float = None) -> float:
    """Normalize a delta value from [min_val, max_val] to [0, 100]. Clamps outliers."""
    if min_val is None:
        min_val = settings.index_delta_min
    if max_val is None:
        max_val = settings.index_delta_max

    if max_val == min_val:
        return 50.0

    normalized = (delta - min_val) / (max_val - min_val) * 100
    return max(0.0, min(100.0, normalized))


def _absolute_ndvi_score(ndvi: float) -> float:
    """
    Score absolute NDVI for snapshot mode.
    NDVI ranges: -1 to 1. Typical land: 0.1-0.8.
      >= 0.5  → lush vegetation → 100
      0.3-0.5 → moderate → 60-100
      0.15-0.3 → sparse → 30-60
      < 0.15 → barren/water → 0-30
    """
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
    """
    Score absolute NDWI for snapshot mode.
    NDWI > 0 → water present; NDWI < 0 → dry.
    For general health, moderate positive NDWI is good (moisture availability).
      >= 0.3  → strong water presence → 100
      0.0-0.3 → moderate → 50-100
      -0.2-0.0 → dry → 20-50
      < -0.2  → very dry → 0-20
    """
    if ndwi >= 0.3:
        return 100.0
    elif ndwi >= 0.0:
        return 50.0 + ndwi / 0.3 * 50.0
    elif ndwi >= -0.2:
        return 20.0 + (ndwi + 0.2) / 0.2 * 30.0
    else:
        return max(0.0, 20.0 + (ndwi + 0.2) / 0.3 * 20.0)


def compute_health_score_full(
    satellite_data: dict,
    validation_result: dict,
) -> dict:
    """
    FULL MODE health score — original formula, uses deltas + cross-validation.

    Args:
        satellite_data: dict with delta_ndvi, delta_ndwi
        validation_result: dict with overall_status, details.photo_confidence

    Returns:
        dict with score (0-100), grade (A-F), mode ("full"), components
    """
    delta_ndvi = satellite_data.get("delta_ndvi", 0)
    delta_ndwi = satellite_data.get("delta_ndwi", 0)

    # Component 1: NDVI trend score
    ndvi_score = _normalize_delta(delta_ndvi)

    # Component 2: NDWI trend score
    ndwi_score = _normalize_delta(delta_ndwi)

    # Component 3: Agreement score
    status = validation_result.get("overall_status", "inconclusive")
    if status == "confirmed":
        agreement_score = 100.0
    elif status == "inconclusive":
        agreement_score = 50.0
    else:  # anomaly
        agreement_score = 0.0

    # Component 4: Classifier / Telemetry confidence
    photo_confidence = validation_result.get("details", {}).get("photo_confidence")
    if photo_confidence is None:
        photo_confidence = validation_result.get("confidence", 0.75)
    confidence_score = photo_confidence * 100

    # Weighted combination
    score = (
        settings.health_weight_ndvi * ndvi_score
        + settings.health_weight_ndwi * ndwi_score
        + settings.health_weight_agreement * agreement_score
        + settings.health_weight_confidence * confidence_score
    )

    score = max(0, min(100, round(score)))
    grade = _grade(score)

    return {
        "score": score,
        "grade": grade,
        "mode": "full",
        "components": {
            "ndvi_trend_score": round(ndvi_score, 1),
            "ndwi_trend_score": round(ndwi_score, 1),
            "agreement_score": round(agreement_score, 1),
            "confidence_score": round(confidence_score, 1),
        },
    }


def compute_health_score_snapshot(
    satellite_data: dict,
    classification_result: Optional[dict] = None,
) -> dict:
    """
    SNAPSHOT MODE health score — for arbitrary points without a baseline.
    Uses absolute NDVI/NDWI values. No implied "intervention" or "improvement."

    Args:
        satellite_data: dict with ndvi_tnow, ndwi_tnow
        classification_result: optional dict with confidence

    Returns:
        dict with score (0-100), grade (A-F), mode ("snapshot"), components
    """
    ndvi_tnow = satellite_data.get("ndvi_tnow", 0)
    ndwi_tnow = satellite_data.get("ndwi_tnow", 0)

    ndvi_score = _absolute_ndvi_score(ndvi_tnow)
    ndwi_score = _absolute_ndwi_score(ndwi_tnow)

    if classification_result is not None:
        confidence = classification_result.get("confidence", 0.5)
        confidence_score = confidence * 100
        # With photo: 35% NDVI + 35% NDWI + 30% confidence
        score = 0.35 * ndvi_score + 0.35 * ndwi_score + 0.30 * confidence_score
    else:
        # No photo: 50% NDVI + 50% NDWI
        score = 0.50 * ndvi_score + 0.50 * ndwi_score
        confidence_score = None

    score = max(0, min(100, round(score)))
    grade = _grade(score)

    components = {
        "ndvi_absolute_score": round(ndvi_score, 1),
        "ndwi_absolute_score": round(ndwi_score, 1),
    }
    if confidence_score is not None:
        components["confidence_score"] = round(confidence_score, 1)

    return {
        "score": score,
        "grade": grade,
        "mode": "snapshot",
        "components": components,
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
