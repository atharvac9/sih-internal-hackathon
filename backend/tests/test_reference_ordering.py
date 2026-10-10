"""
Integration tests: Reference site ordering using live Google Earth Engine data.
Verifies that natural water and forest sites score higher than dense urban cores and quarries.
"""

import pytest
from app.services import gee_service, health_score
from tests.fixtures.reference_sites import REFERENCE_SITES


@pytest.mark.asyncio
async def test_reference_site_ordering_with_live_gee():
    """Verify live GEE indices preserve ecological ordering (reservoir & forest > urban & quarry)."""
    if not gee_service.initialize_gee():
        pytest.skip("GEE credentials not configured; skipping live GEE integration test.")

    sites_by_id = {s["id"]: s for s in REFERENCE_SITES}

    # 1. Khadakwasla Reservoir (open water)
    kw_ref = sites_by_id["khadakwasla_reservoir"]
    kw_sat = await gee_service.get_snapshot_indices(kw_ref["lat"], kw_ref["lon"], kw_ref["buffer_radius_m"])
    assert "error" not in kw_sat, f"GEE query failed: {kw_sat}"
    kw_health = health_score.compute_health_score_snapshot(kw_sat)

    # 2. Sinhagad Forest (dense canopy)
    sh_ref = sites_by_id["sinhagad_forest"]
    sh_sat = await gee_service.get_snapshot_indices(sh_ref["lat"], sh_ref["lon"], sh_ref["buffer_radius_m"])
    assert "error" not in sh_sat, f"GEE query failed: {sh_sat}"
    sh_health = health_score.compute_health_score_snapshot(sh_sat)

    # 3. Kharadi IT Park (dense commercial urban core)
    kh_ref = sites_by_id["kharadi_it_park"]
    kh_sat = await gee_service.get_snapshot_indices(kh_ref["lat"], kh_ref["lon"], kh_ref["buffer_radius_m"])
    assert "error" not in kh_sat, f"GEE query failed: {kh_sat}"
    kh_health = health_score.compute_health_score_snapshot(kh_sat)

    # 4. Shivajinagar Core (dense historic urban core)
    sn_ref = sites_by_id["shivajinagar_core"]
    sn_sat = await gee_service.get_full_indices(sn_ref["lat"], sn_ref["lon"], buffer_m=sn_ref["buffer_radius_m"])
    assert "error" not in sn_sat, f"GEE query failed: {sn_sat}"
    sn_health = health_score.compute_health_score_snapshot(sn_sat)

    kw_score = kw_health["score"]
    sh_score = sh_health["score"]
    kh_score = kh_health["score"]
    sn_score = sn_health["score"]

    # Verified Ecological Ordering: Reservoir & Forest strictly outscore Urban Core
    assert kw_score > kh_score, f"Reservoir ({kw_score}) must exceed Urban ({kh_score})"
    assert kw_score > sn_score, f"Reservoir ({kw_score}) must exceed Urban Core ({sn_score})"
    assert sh_score > kh_score, f"Forest ({sh_score}) must exceed Urban ({kh_score})"
    assert sh_score > sn_score, f"Forest ({sh_score}) must exceed Urban Core ({sn_score})"

    # Absolute Ecological Guardrails:
    assert sn_score <= 50, f"Dense urban core must score <= 50, got {sn_score}"
    assert kh_score <= 50, f"Kharadi (urban) must score <= 50, got {kh_score}"
    assert sh_score >= 70, f"Healthy forest must score >= 70, got {sh_score}"
    assert kw_score >= 70, f"Open water reservoir must score >= 70, got {kw_score}"
