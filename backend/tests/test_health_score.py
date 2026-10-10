"""
Tests for health_score — both full and snapshot modes.
"""

import pytest
from app.services.health_score import (
    compute_health_score_full,
    compute_health_score_snapshot,
    _grade,
)


class TestGradeBoundaries:
    """Grade boundaries should be exact and consistent."""

    def test_grade_a(self):
        assert _grade(80) == "A"
        assert _grade(100) == "A"

    def test_grade_b(self):
        assert _grade(65) == "B"
        assert _grade(79) == "B"

    def test_grade_c(self):
        assert _grade(50) == "C"
        assert _grade(64) == "C"

    def test_grade_d(self):
        assert _grade(35) == "D"
        assert _grade(49) == "D"

    def test_grade_f(self):
        assert _grade(0) == "F"
        assert _grade(34) == "F"


class TestFullMode:
    """Full mode (before/after with deltas)."""

    def test_score_in_valid_range(self):
        result = compute_health_score_full(
            satellite_data={"delta_ndvi": 0.15, "delta_ndwi": 0.10},
            validation_result={"overall_status": "confirmed",
                                "details": {"photo_confidence": 0.90}},
        )
        assert 0 <= result["score"] <= 100

    def test_mode_is_full(self):
        result = compute_health_score_full(
            satellite_data={"delta_ndvi": 0.0, "delta_ndwi": 0.0},
            validation_result={"overall_status": "confirmed",
                                "details": {"photo_confidence": 0.50}},
        )
        assert result["mode"] == "full"

    def test_confirmed_status_boosts_score(self):
        """Confirmed status should produce higher score than anomaly, all else equal."""
        confirmed = compute_health_score_full(
            satellite_data={"delta_ndvi": 0.10, "delta_ndwi": 0.10},
            validation_result={"overall_status": "confirmed",
                                "details": {"photo_confidence": 0.80}},
        )
        anomaly = compute_health_score_full(
            satellite_data={"delta_ndvi": 0.10, "delta_ndwi": 0.10},
            validation_result={"overall_status": "anomaly",
                                "details": {"photo_confidence": 0.80}},
        )
        assert confirmed["score"] > anomaly["score"]

    def test_positive_deltas_yield_higher_score(self):
        """Positive NDVI/NDWI deltas should score higher than negative ones."""
        positive = compute_health_score_full(
            satellite_data={"delta_ndvi": 0.20, "delta_ndwi": 0.20},
            validation_result={"overall_status": "confirmed",
                                "details": {"photo_confidence": 0.80}},
        )
        negative = compute_health_score_full(
            satellite_data={"delta_ndvi": -0.20, "delta_ndwi": -0.20},
            validation_result={"overall_status": "confirmed",
                                "details": {"photo_confidence": 0.80}},
        )
        assert positive["score"] > negative["score"]

    def test_all_zeros(self):
        """All zeros should still produce a valid score."""
        result = compute_health_score_full(
            satellite_data={"delta_ndvi": 0.0, "delta_ndwi": 0.0},
            validation_result={"overall_status": "inconclusive",
                                "details": {"photo_confidence": 0.0}},
        )
        assert 0 <= result["score"] <= 100
        assert result["grade"] in ("A", "B", "C", "D", "F")

    def test_extreme_positive_capped_at_100(self):
        result = compute_health_score_full(
            satellite_data={"delta_ndvi": 1.0, "delta_ndwi": 1.0},
            validation_result={"overall_status": "confirmed",
                                "details": {"photo_confidence": 1.0}},
        )
        assert result["score"] <= 100

    def test_extreme_negative_capped_at_0(self):
        result = compute_health_score_full(
            satellite_data={"delta_ndvi": -1.0, "delta_ndwi": -1.0},
            validation_result={"overall_status": "anomaly",
                                "details": {"photo_confidence": 0.0}},
        )
        assert result["score"] >= 0

    def test_components_present(self):
        result = compute_health_score_full(
            satellite_data={"delta_ndvi": 0.10, "delta_ndwi": 0.05},
            validation_result={"overall_status": "confirmed",
                                "details": {"photo_confidence": 0.80}},
        )
        assert "ndvi_trend_score" in result["components"]
        assert "ndwi_trend_score" in result["components"]
        assert "agreement_score" in result["components"]
        assert "confidence_score" in result["components"]


class TestSnapshotMode:
    """Snapshot mode (current only, no deltas)."""

    def test_score_in_valid_range(self):
        result = compute_health_score_snapshot(
            satellite_data={"ndvi_tnow": 0.35, "ndwi_tnow": 0.05},
        )
        assert 0 <= result["score"] <= 100

    def test_mode_is_snapshot(self):
        result = compute_health_score_snapshot(
            satellite_data={"ndvi_tnow": 0.35, "ndwi_tnow": 0.05},
        )
        assert result["mode"] == "snapshot"

    def test_high_ndvi_high_ndwi_yields_high_score(self):
        result = compute_health_score_snapshot(
            satellite_data={"ndvi_tnow": 0.55, "ndwi_tnow": 0.35},
        )
        assert result["score"] >= 80
        assert result["grade"] == "A"

    def test_low_ndvi_low_ndwi_yields_low_score(self):
        result = compute_health_score_snapshot(
            satellite_data={"ndvi_tnow": 0.05, "ndwi_tnow": -0.30},
        )
        assert result["score"] <= 30

    def test_negative_ndvi(self):
        """Negative NDVI (water/cloud) → should still produce valid score."""
        result = compute_health_score_snapshot(
            satellite_data={"ndvi_tnow": -0.10, "ndwi_tnow": 0.20},
        )
        assert 0 <= result["score"] <= 100

    def test_with_classification_adds_confidence(self):
        """With photo classification, score should include confidence component."""
        without = compute_health_score_snapshot(
            satellite_data={"ndvi_tnow": 0.35, "ndwi_tnow": 0.05},
        )
        with_class = compute_health_score_snapshot(
            satellite_data={"ndvi_tnow": 0.35, "ndwi_tnow": 0.05},
            classification_result={"confidence": 0.95},
        )
        assert "confidence_score" in with_class["components"]
        assert "confidence_score" not in without["components"]

    def test_snapshot_components_present(self):
        result = compute_health_score_snapshot(
            satellite_data={"ndvi_tnow": 0.30, "ndwi_tnow": 0.10},
        )
        assert "ndvi_absolute_score" in result["components"]
        assert "ndwi_absolute_score" in result["components"]
