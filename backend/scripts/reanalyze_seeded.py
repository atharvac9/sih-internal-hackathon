"""
Re-analyze all seeded reference sites using the real Google Earth Engine pipeline.
Replaces stale database rows with schema_version=CURRENT_SCHEMA_VERSION.
"""

import asyncio
import json
import logging
import sys
from datetime import datetime as dt, timedelta
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import select
from app.config import settings
from app.database import async_session_factory, create_tables
from app.models.site import Site
from app.models.analysis import AnalysisResult, AnalysisMode, CURRENT_SCHEMA_VERSION
from app.services import gee_service, cross_validator, health_score
from tests.fixtures.reference_sites import REFERENCE_SITES

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("reanalyze_seeded")


async def main():
    logger.info("Initializing database...")
    await create_tables()

    logger.info("Checking GEE credentials...")
    if not gee_service.initialize_gee():
        err = gee_service.get_gee_init_error()
        logger.error(f"Cannot re-analyze sites: GEE is not initialized ({err})")
        return

    logger.info("GEE initialized successfully. Fetching seeded sites...")

    async with async_session_factory() as session:
        result = await session.execute(select(Site).where(Site.is_seeded_demo == True))
        seeded_sites = list(result.scalars().all())

        if not seeded_sites:
            logger.info("No seeded sites in DB. Populating from reference_sites fixture...")
            for ref in REFERENCE_SITES:
                s = Site(
                    id=ref["id"],
                    site_code=f"REF-{ref['id'][:8].upper()}",
                    lat=ref["lat"],
                    lon=ref["lon"],
                    buffer_radius_m=ref.get("buffer_radius_m", 250),
                    description=ref["description"],
                    activity_type=ref.get("expected_surface_type", "water_body"),
                    is_seeded_demo=True,
                )
                session.add(s)
                seeded_sites.append(s)
            await session.flush()

        # Purge all existing analyses so we have only pristine, median-computed GEE data
        from sqlalchemy import delete
        await session.execute(delete(AnalysisResult))
        logger.info("Purged all previous analysis rows.")

        for s in seeded_sites:
            logger.info(f"Querying GEE for site {s.id} ({s.description}) at ({s.lat}, {s.lon})...")
            has_baseline = s.baseline_date is not None
            mode = AnalysisMode.FULL if has_baseline else AnalysisMode.SNAPSHOT

            if has_baseline:
                base_dt = dt.strptime(s.baseline_date, "%Y-%m-%d")
                t0_start = (base_dt - timedelta(days=45)).strftime("%Y-%m-%d")
                t0_end = (base_dt + timedelta(days=45)).strftime("%Y-%m-%d")
                sat_data = await gee_service.get_full_indices(s.lat, s.lon, t0_start, t0_end, s.buffer_radius_m or 250)
            else:
                sat_data = await gee_service.get_snapshot_indices(s.lat, s.lon, s.buffer_radius_m or 250)

            if "error" in sat_data:
                logger.error(f"Failed GEE query for {s.id}: {sat_data}")
                continue

            val_res = cross_validator.validate_site(s.activity_type, sat_data) if s.activity_type else None
            if mode == AnalysisMode.FULL and val_res:
                hs_res = health_score.compute_health_score_full(sat_data, val_res)
            else:
                hs_res = health_score.compute_health_score_snapshot(sat_data)

            analysis = AnalysisResult(
                site_id=s.id,
                schema_version=CURRENT_SCHEMA_VERSION,
                mode=mode.value,
                ndvi_tnow=sat_data.get("ndvi_tnow"),
                ndwi_tnow=sat_data.get("ndwi_tnow"),
                mndwi_tnow=sat_data.get("mndwi_tnow"),
                tnow_start_date=sat_data.get("tnow_start_date"),
                tnow_end_date=sat_data.get("tnow_end_date"),
                ndvi_t0=sat_data.get("ndvi_t0"),
                ndwi_t0=sat_data.get("ndwi_t0"),
                mndwi_t0=sat_data.get("mndwi_t0"),
                t0_start_date=sat_data.get("t0_start_date"),
                t0_end_date=sat_data.get("t0_end_date"),
                delta_ndvi=sat_data.get("delta_ndvi"),
                delta_ndwi=sat_data.get("delta_ndwi"),
                satellite_source=sat_data.get("source", "gee"),
                satellite_agreement=val_res.get("satellite_agreement") if val_res else None,
                photo_agreement=val_res.get("photo_agreement") if val_res else None,
                overall_status=val_res.get("overall_status") if val_res else None,
                flags_json=json.dumps(val_res["flags"]) if val_res else None,
                validation_confidence=val_res.get("confidence") if val_res else None,
                health_score=hs_res["score"],
                health_grade=hs_res["grade"],
                health_components_json=json.dumps(hs_res["components"]),
                buffer_radius_m=s.buffer_radius_m or 250,
            )
            session.add(analysis)
            surface_type = hs_res.get("surface_type") or hs_res.get("components", {}).get("surface_type")
            logger.info(
                f" -> Saved {s.id}: Score={hs_res['score']}, Grade={hs_res['grade']}, "
                f"Surface={surface_type}, NDWI={sat_data.get('ndwi_tnow')}, MNDWI={sat_data.get('mndwi_tnow')}"
            )

        await session.commit()
        logger.info("Re-analysis complete! All stale rows replaced with schema_version=2.")


if __name__ == "__main__":
    asyncio.run(main())
