"""
Tests for input validators — CSV schema, coordinate checks.
"""

import pytest
from app.utils.validators import validate_coordinates, validate_sites_csv


class TestCoordinateValidation:
    def test_valid_coordinates(self):
        assert validate_coordinates(19.05, 74.72) == []

    def test_lat_too_high(self):
        errors = validate_coordinates(91.0, 74.0)
        assert len(errors) == 1
        assert "Latitude" in errors[0]

    def test_lat_too_low(self):
        errors = validate_coordinates(-91.0, 74.0)
        assert len(errors) == 1

    def test_lon_too_high(self):
        errors = validate_coordinates(19.0, 200.0)
        assert len(errors) == 1
        assert "Longitude" in errors[0]

    def test_lon_too_low(self):
        errors = validate_coordinates(19.0, -181.0)
        assert len(errors) == 1

    def test_both_invalid(self):
        errors = validate_coordinates(95.0, 200.0)
        assert len(errors) == 2

    def test_boundary_values_valid(self):
        assert validate_coordinates(90, 180) == []
        assert validate_coordinates(-90, -180) == []
        assert validate_coordinates(0, 0) == []


class TestCSVValidation:
    def test_valid_csv(self):
        csv = (
            "site_id,lat,lon,activity_type\n"
            "S01,19.095,74.738,check_dam\n"
            "S02,19.140,74.685,farm_pond\n"
        )
        result = validate_sites_csv(csv)
        assert result["valid"] is True
        assert result["row_count"] == 2
        assert len(result["errors"]) == 0

    def test_missing_required_column(self):
        csv = "site_id,lat,lon\nS01,19.0,74.0\n"
        result = validate_sites_csv(csv)
        assert result["valid"] is False
        assert any("activity_type" in e for e in result["errors"])

    def test_duplicate_site_ids(self):
        csv = (
            "site_id,lat,lon,activity_type\n"
            "S01,19.0,74.0,check_dam\n"
            "S01,19.1,74.1,farm_pond\n"
        )
        result = validate_sites_csv(csv)
        assert result["valid"] is False
        assert any("duplicate" in e.lower() for e in result["errors"])

    def test_invalid_coordinates(self):
        csv = (
            "site_id,lat,lon,activity_type\n"
            "S01,999,74.0,check_dam\n"
        )
        result = validate_sites_csv(csv)
        assert result["valid"] is False
        assert any("Latitude" in e for e in result["errors"])

    def test_non_numeric_coordinates(self):
        csv = (
            "site_id,lat,lon,activity_type\n"
            "S01,abc,74.0,check_dam\n"
        )
        result = validate_sites_csv(csv)
        assert result["valid"] is False

    def test_empty_site_id(self):
        csv = (
            "site_id,lat,lon,activity_type\n"
            ",19.0,74.0,check_dam\n"
        )
        result = validate_sites_csv(csv)
        assert result["valid"] is False
        assert any("missing site_id" in e for e in result["errors"])

    def test_unknown_activity_type_warns(self):
        csv = (
            "site_id,lat,lon,activity_type\n"
            "S01,19.0,74.0,magic_fountain\n"
        )
        result = validate_sites_csv(csv)
        assert result["valid"] is True  # Warning, not error
        assert len(result["warnings"]) > 0

    def test_empty_csv(self):
        csv = "site_id,lat,lon,activity_type\n"
        result = validate_sites_csv(csv)
        assert result["valid"] is True
        assert result["row_count"] == 0

    def test_no_header(self):
        csv = ""
        result = validate_sites_csv(csv)
        assert result["valid"] is False
