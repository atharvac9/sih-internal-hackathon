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

    # 4. Wagholi Stone Quarry (barren open quarry)
    wq_ref = sites_by_id["wagholi_stone_quarry"]
    wq_sat = await gee_service.get_snapshot_indices(wq_ref["lat"], wq_ref["lon"], wq_ref["buffer_radius_m"])
    assert "error" not in wq_sat, f"GEE query failed: {wq_sat}"
    wq_health = health_score.compute_health_score_snapshot(wq_sat)

    # Verified Ecological Ordering: Reservoir & Forest strictly outscore Urban Core & Quarry
    assert kw_health["score"] > kh_health["score"], f"Reservoir ({kw_health['score']}) must exceed Urban ({kh_health['score']})"
    assert kw_health["score"] > wq_health["score"], f"Reservoir ({kw_health['score']}) must exceed Quarry ({wq_health['score']})"
    assert sh_health["score"] > kh_health["score"], f"Forest ({sh_health['score']}) must exceed Urban ({kh_health['score']})"
    assert sh_health["score"] > wq_health["score"], f"Forest ({sh_health['score']}) must exceed Quarry ({wq_health['score']})"
