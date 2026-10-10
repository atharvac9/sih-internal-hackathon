"""
Tests for cross_validator.validate_site() — REAL assertions.

Replaces the old test_pipeline.py which had zero assertions and
unconditionally printed "PASSED."
"""

import pytest
from app.services.cross_validator import validate_site


class TestSatelliteAgreement:
    """Test satellite trend validation against activity-type rules."""

    def test_check_dam_confirmed_when_ndvi_stable_ndwi_increase(self):
        """Check dam: NDVI stable/up + NDWI increase → satellite agrees."""
        result = validate_site(
            activity_type="check_dam",
            satellite_data={
                "ndvi_tnow": 0.30,
                "ndwi_tnow": 0.05,
                "delta_ndvi": 0.10,   # Positive — vegetation increase
                "delta_ndwi": 0.15,   # Positive — water increase
            },
        )
        assert result["satellite_agreement"] is True
        assert result["overall_status"] in ("confirmed", "inconclusive")

    def test_check_dam_anomaly_when_ndwi_drops(self):
        """Check dam: NDWI drops significantly → satellite disagrees."""
        result = validate_site(
            activity_type="check_dam",
            satellite_data={
                "ndvi_tnow": 0.25,
                "ndwi_tnow": -0.20,
                "delta_ndvi": 0.05,
                "delta_ndwi": -0.15,  # Negative — water DECREASED
            },
        )
        assert result["satellite_agreement"] is False
        assert len(result["flags"]) > 0

    def test_farm_pond_anomaly_no_water_signature(self):
        """Farm pond: very negative NDWI → no water detected → anomaly."""
        result = validate_site(
            activity_type="farm_pond",
            satellite_data={
                "ndvi_tnow": 0.10,
                "ndwi_tnow": -0.25,   # Very dry
                "delta_ndvi": -0.05,
                "delta_ndwi": -0.10,
            },
        )
        assert result["satellite_agreement"] is False
        assert any("water" in f.lower() or "NDWI" in f for f in result["flags"])

    def test_plantation_confirmed_with_high_ndvi(self):
        """Plantation: strong NDVI increase → satellite agrees."""
        result = validate_site(
            activity_type="plantation",
            satellite_data={
                "ndvi_tnow": 0.40,
                "ndwi_tnow": -0.10,
                "delta_ndvi": 0.20,   # Strong increase
                "delta_ndwi": -0.05,
            },
        )
        assert result["satellite_agreement"] is True

    def test_plantation_low_ndvi_flagged(self):
        """Plantation: low current NDVI → flagged regardless of delta."""
        result = validate_site(
            activity_type="plantation",
            satellite_data={
                "ndvi_tnow": 0.12,    # Below 0.20 threshold
                "ndwi_tnow": -0.15,
                "delta_ndvi": 0.06,
                "delta_ndwi": -0.05,
            },
        )
        assert result["satellite_agreement"] is False
        assert any("vegetation" in f.lower() or "NDVI" in f for f in result["flags"])

    def test_unknown_activity_type_flagged(self):
        """Unknown activity type → satellite agreement is False."""
        result = validate_site(
            activity_type="magic_fountain",
            satellite_data={
                "ndvi_tnow": 0.50,
                "ndwi_tnow": 0.30,
                "delta_ndvi": 0.20,
                "delta_ndwi": 0.20,
            },
        )
        assert result["satellite_agreement"] is False
        assert any("Unknown" in f for f in result["flags"])


class TestPhotoAgreement:
    """Test photo classification agreement."""

    def test_matching_class_agrees(self):
        """Photo predicts same class as claimed → agrees."""
        result = validate_site(
            activity_type="check_dam",
            satellite_data={"ndvi_tnow": 0.30, "ndwi_tnow": 0.05,
                            "delta_ndvi": 0.10, "delta_ndwi": 0.15},
            classification_result={
                "predicted_class": "check_dam",
                "confidence": 0.90,
                "all_scores": {"check_dam": 0.90},
            },
        )
        assert result["photo_agreement"] is True
        assert result["overall_status"] == "confirmed"

    def test_mismatched_class_flags_anomaly(self):
        """Photo predicts different class → anomaly flag."""
        result = validate_site(
            activity_type="farm_pond",
            satellite_data={"ndvi_tnow": 0.10, "ndwi_tnow": -0.25,
                            "delta_ndvi": -0.05, "delta_ndwi": -0.10},
            classification_result={
                "predicted_class": "degraded_land",
                "confidence": 0.85,
                "all_scores": {"degraded_land": 0.85},
            },
        )
        assert result["photo_agreement"] is False
        assert result["overall_status"] == "anomaly"
        assert any("mismatch" in f.lower() for f in result["flags"])

    def test_no_photo_returns_none_agreement(self):
        """No classification result → photo_agreement is None."""
        result = validate_site(
            activity_type="check_dam",
            satellite_data={"ndvi_tnow": 0.30, "ndwi_tnow": 0.05,
                            "delta_ndvi": 0.10, "delta_ndwi": 0.15},
            classification_result=None,
        )
        assert result["photo_agreement"] is None

    def test_low_confidence_yields_inconclusive(self):
        """Mismatched class + low confidence → inconclusive, not anomaly."""
        result = validate_site(
            activity_type="check_dam",
            satellite_data={"ndvi_tnow": 0.30, "ndwi_tnow": 0.05,
                            "delta_ndvi": 0.10, "delta_ndwi": 0.15},
            classification_result={
                "predicted_class": "farm_pond",
                "confidence": 0.30,  # Very low
                "all_scores": {"farm_pond": 0.30},
            },
        )
        assert result["overall_status"] == "inconclusive"


class TestOverallStatus:
    """Test the combined status logic."""

    def test_both_agree_confirmed(self):
        result = validate_site(
            activity_type="check_dam",
            satellite_data={"ndvi_tnow": 0.30, "ndwi_tnow": 0.05,
                            "delta_ndvi": 0.10, "delta_ndwi": 0.15},
            classification_result={"predicted_class": "check_dam",
                                    "confidence": 0.90, "all_scores": {}},
        )
        assert result["overall_status"] == "confirmed"

    def test_both_disagree_anomaly(self):
        result = validate_site(
            activity_type="farm_pond",
            satellite_data={"ndvi_tnow": 0.10, "ndwi_tnow": -0.25,
                            "delta_ndvi": -0.15, "delta_ndwi": -0.20},
            classification_result={"predicted_class": "degraded_land",
                                    "confidence": 0.85, "all_scores": {}},
        )
        assert result["overall_status"] == "anomaly"

    def test_confidence_is_bounded(self):
        """Confidence should be between 0 and 1."""
        result = validate_site(
            activity_type="check_dam",
            satellite_data={"ndvi_tnow": 0.30, "ndwi_tnow": 0.05,
                            "delta_ndvi": 0.10, "delta_ndwi": 0.15},
            classification_result={"predicted_class": "check_dam",
                                    "confidence": 0.99, "all_scores": {}},
        )
        assert 0.0 <= result["confidence"] <= 1.0

    def test_flags_list_always_exists(self):
        """Flags should always be a list, even if empty."""
        result = validate_site(
            activity_type="check_dam",
            satellite_data={"ndvi_tnow": 0.30, "ndwi_tnow": 0.05,
                            "delta_ndvi": 0.10, "delta_ndwi": 0.15},
        )
        assert isinstance(result["flags"], list)

    def test_xss_in_activity_type_is_escaped(self):
        """User-supplied activity_type with XSS payload is HTML-escaped in flags."""
        result = validate_site(
            activity_type='<script>alert("xss")</script>',
            satellite_data={"ndvi_tnow": 0.30, "ndwi_tnow": 0.05,
                            "delta_ndvi": 0.10, "delta_ndwi": 0.15},
        )
        for flag in result["flags"]:
            assert "<script>" not in flag
