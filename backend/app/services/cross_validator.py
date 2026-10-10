"""
Cross-validation logic — ported from the original codebase.

The math here was already correct; the only change is:
- Input validation on dict keys
- HTML-safe string outputs (no raw user data in flag strings)
- Only runs when activity_type is provided (arbitrary points without a claim skip this)
"""

import html
import logging
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)


def validate_site(
    activity_type: str,
    satellite_data: dict,
    classification_result: Optional[dict] = None,
) -> dict:
    """
    Cross-validate a site's claimed intervention against satellite + photo evidence.

    Args:
        activity_type: Claimed activity (check_dam, farm_pond, etc.)
        satellite_data: dict with delta_ndvi, delta_ndwi (full mode)
                        or ndvi_tnow, ndwi_tnow (snapshot mode)
        classification_result: dict with predicted_class, confidence, all_scores
                               (None if no photo uploaded)

    Returns:
        dict with keys:
            - satellite_agreement: bool
            - photo_agreement: bool | None (None if no photo)
            - overall_status: "confirmed" | "anomaly" | "inconclusive"
            - flags: list[str] (HTML-escaped diagnostic messages)
            - confidence: float (0-1)
    """
    flags: list[str] = []
    details: dict = {}

    # ── 1. Satellite trend validation ─────────────────────────────────────
    rules = settings.validation_rules.get(activity_type, None)
    satellite_agreement = True

    if rules is None:
        # Escape user-supplied activity_type to prevent XSS
        safe_activity = html.escape(str(activity_type))
        flags.append(f"Unknown activity type: {safe_activity}")
        satellite_agreement = False
    else:
        delta_ndvi = satellite_data.get("delta_ndvi", 0)
        delta_ndwi = satellite_data.get("delta_ndwi", 0)
        ndvi_tnow = satellite_data.get("ndvi_tnow", 0)
        ndwi_tnow = satellite_data.get("ndwi_tnow", 0)

        details["delta_ndvi"] = delta_ndvi
        details["delta_ndwi"] = delta_ndwi

        # Check if we have delta data (full mode) or only current (snapshot)
        has_deltas = (
            satellite_data.get("delta_ndvi") is not None
            and satellite_data.get("delta_ndwi") is not None
        )

        if has_deltas:
            # Full mode — check trends against thresholds
            ndvi_min = rules.get("ndvi_min", -1.0)
            if delta_ndvi < ndvi_min:
                satellite_agreement = False
                trend_name = rules.get("ndvi_trend", "expected")
                flags.append(
                    f"NDVI trend mismatch: delta={delta_ndvi:+.3f} "
                    f"(expected {trend_name}, min delta={ndvi_min:+.3f}) "
                    f"contradicts {html.escape(activity_type)} claim"
                )

            ndwi_min = rules.get("ndwi_min", -1.0)
            if delta_ndwi < ndwi_min:
                satellite_agreement = False
                trend_name = rules.get("ndwi_trend", "expected")
                flags.append(
                    f"NDWI trend mismatch: delta={delta_ndwi:+.3f} "
                    f"(expected {trend_name}, min delta={ndwi_min:+.3f}) "
                    f"contradicts {html.escape(activity_type)} claim"
                )

        # Additional absolute-value checks (apply in both modes)
        if activity_type == "farm_pond" and ndwi_tnow < -0.15:
            satellite_agreement = False
            flags.append(
                f"No water signature detected: NDWI={ndwi_tnow:.3f} "
                f"(expected > -0.15 for farm pond)"
            )

        if activity_type == "plantation" and ndvi_tnow < 0.20:
            satellite_agreement = False
            flags.append(
                f"Low vegetation signal: NDVI={ndvi_tnow:.3f} "
                f"(expected > 0.20 for plantation)"
            )

        if activity_type == "water_body" and ndwi_tnow < 0.0:
            satellite_agreement = False
            flags.append(
                f"Weak water signature: NDWI={ndwi_tnow:.3f} "
                f"(expected > 0.0 for water body)"
            )

    # ── 2. Photo classification validation ────────────────────────────────
    photo_agreement = None  # None = no photo provided
    photo_confidence = 0.0

    if classification_result is not None:
        predicted_class = classification_result.get("predicted_class", "unknown")
        photo_confidence = classification_result.get("confidence", 0.0)

        photo_agreement = (predicted_class == activity_type)

        if not photo_agreement:
            safe_predicted = html.escape(str(predicted_class))
            safe_activity = html.escape(str(activity_type))
            flags.append(
                f"Photo classification mismatch: classified as '{safe_predicted}' "
                f"({photo_confidence:.0%} confidence), but claimed as '{safe_activity}'"
            )

        details["predicted_class"] = predicted_class
        details["photo_confidence"] = photo_confidence

    # ── 3. Determine overall status ───────────────────────────────────────
    if photo_agreement is None:
        # No photo — decision based on satellite only
        if satellite_agreement:
            overall_status = "confirmed"
        else:
            overall_status = "inconclusive"
            flags.append("No photo evidence available — satellite-only assessment")
    elif satellite_agreement and photo_agreement:
        overall_status = "confirmed"
    elif not satellite_agreement and not photo_agreement:
        # Both disagree — strong anomaly
        overall_status = "anomaly"
    else:
        # One disagrees
        if photo_confidence < 0.5:
            overall_status = "inconclusive"
            flags.append("Low classifier confidence — result is inconclusive")
        else:
            overall_status = "anomaly"

    # Overall confidence
    sat_conf = 1.0 if satellite_agreement else 0.0
    if photo_agreement is not None:
        overall_confidence = sat_conf * 0.5 + photo_confidence * 0.5
    else:
        overall_confidence = sat_conf * 0.7  # lower confidence without photo

    return {
        "satellite_agreement": satellite_agreement,
        "photo_agreement": photo_agreement,
        "overall_status": overall_status,
        "flags": flags,
        "confidence": round(overall_confidence, 3),
        "details": details,
    }
