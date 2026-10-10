"""
Input validation utilities — CSV schema validation, coordinate checks.
"""

import csv
import io
from typing import Optional


REQUIRED_CSV_COLUMNS = {"site_id", "lat", "lon", "activity_type"}
VALID_ACTIVITY_TYPES = {"check_dam", "farm_pond", "plantation", "degraded_land", "water_body"}


def validate_coordinates(lat: float, lon: float) -> list[str]:
    """Validate lat/lon and return list of error messages (empty = valid)."""
    errors = []
    if lat < -90 or lat > 90:
        errors.append(f"Latitude {lat} out of range [-90, 90]")
    if lon < -180 or lon > 180:
        errors.append(f"Longitude {lon} out of range [-180, 180]")
    return errors


def validate_sites_csv(csv_content: str) -> dict:
    """
    Validate a sites CSV file content.

    Returns:
        dict with:
            - valid: bool
            - errors: list[str]
            - warnings: list[str]
            - row_count: int
    """
    errors = []
    warnings = []
    seen_ids = set()

    try:
        reader = csv.DictReader(io.StringIO(csv_content))
    except Exception as e:
        return {"valid": False, "errors": [f"Invalid CSV format: {e}"], "warnings": [], "row_count": 0}

    # Check required columns
    if reader.fieldnames is None:
        return {"valid": False, "errors": ["CSV has no header row"], "warnings": [], "row_count": 0}

    missing_cols = REQUIRED_CSV_COLUMNS - set(reader.fieldnames)
    if missing_cols:
        errors.append(f"Missing required columns: {', '.join(sorted(missing_cols))}")
        return {"valid": False, "errors": errors, "warnings": [], "row_count": 0}

    row_count = 0
    for i, row in enumerate(reader, start=2):  # Row 2 = first data row
        row_count += 1

        # Check for empty site_id
        site_id = row.get("site_id", "").strip()
        if not site_id:
            errors.append(f"Row {i}: missing site_id")
            continue

        # Check for duplicate IDs
        if site_id in seen_ids:
            errors.append(f"Row {i}: duplicate site_id '{site_id}'")
        seen_ids.add(site_id)

        # Validate coordinates
        try:
            lat = float(row.get("lat", ""))
            lon = float(row.get("lon", ""))
        except (ValueError, TypeError):
            errors.append(f"Row {i} ({site_id}): invalid lat/lon values")
            continue

        coord_errors = validate_coordinates(lat, lon)
        for e in coord_errors:
            errors.append(f"Row {i} ({site_id}): {e}")

        # Validate activity_type
        activity = row.get("activity_type", "").strip()
        if activity and activity not in VALID_ACTIVITY_TYPES:
            warnings.append(
                f"Row {i} ({site_id}): unknown activity_type '{activity}'. "
                f"Valid types: {', '.join(sorted(VALID_ACTIVITY_TYPES))}"
            )

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "row_count": row_count,
    }
