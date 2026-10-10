"""
Async SQLAlchemy engine + session factory for Supabase Postgres.
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""
    pass


def _get_async_url(url: str) -> str:
    """Convert a postgres:// or postgresql:// URL to use asyncpg driver."""
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url


# Engine & session factory — created once at import time
# Falls back to project root SQLite if no DATABASE_URL is set
from pathlib import Path
_ROOT_DIR = Path(__file__).resolve().parent.parent.parent
_DEFAULT_DB_PATH = (_ROOT_DIR / "dev.db").as_posix()
_db_url = settings.database_url or f"sqlite+aiosqlite:///{_DEFAULT_DB_PATH}"
_async_url = _get_async_url(_db_url) if "postgresql" in _db_url or "postgres" in _db_url else _db_url

engine = create_async_engine(
    _async_url,
    echo=settings.debug,
    pool_pre_ping=True,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    """FastAPI dependency — yields an async session, auto-closes."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_tables():
    """Create all tables (dev/init only — use Alembic for production migrations)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        def migrate_schema(sync_conn):
            from sqlalchemy import inspect, text
            inspector = inspect(sync_conn)
            if "analysis_results" in inspector.get_table_names():
                cols = [c["name"] for c in inspector.get_columns("analysis_results")]
                if "schema_version" not in cols:
                    sync_conn.execute(text("ALTER TABLE analysis_results ADD COLUMN schema_version INTEGER DEFAULT 1"))
                if "mndwi_t0" not in cols:
                    sync_conn.execute(text("ALTER TABLE analysis_results ADD COLUMN mndwi_t0 FLOAT"))
                if "mndwi_tnow" not in cols:
                    sync_conn.execute(text("ALTER TABLE analysis_results ADD COLUMN mndwi_tnow FLOAT"))

        await conn.run_sync(migrate_schema)

    # Automatically seed reference calibration sites if database is fresh
    await seed_initial_data_if_empty()


async def seed_initial_data_if_empty():
    """Ensure baseline reference sites and calibrated analyses exist on a fresh clone."""
    import json
    import uuid
    from datetime import datetime, timezone
    from sqlalchemy import select, func
    from app.models.site import Site
    from app.models.analysis import AnalysisResult, CURRENT_SCHEMA_VERSION

    INITIAL_SEEDED_SITES = [
        {
            "id": "khadakwasla_reservoir",
            "name": "Khadakwasla Reservoir",
            "lat": 18.4400,
            "lon": 73.7700,
            "buffer_radius_m": 250,
            "description": "Major perennial freshwater reservoir for Pune; permanent open water.",
            "activity_type": "water",
            "score": 70,
            "grade": "B",
            "ndvi": -0.2540,
            "ndwi": 0.4729,
            "mndwi": 0.4258,
            "components": {"satellite_score": 70, "surface_type": "water", "water_frac_now": 0.6656, "water_stability": None, "baseline_status": "no baseline", "turbidity_proxy_ndti": -0.2551, "chlorophyll_proxy_ndci": -0.0486, "ndvi_absolute_score": 0.0, "ndwi_absolute_score": 100.0},
        },
        {
            "id": "vetal_hill",
            "name": "Vetal Hill (Vetal Tekdi)",
            "lat": 18.5200,
            "lon": 73.8200,
            "buffer_radius_m": 250,
            "description": "Urban forested hill with dense tree cover and grassland.",
            "activity_type": "land",
            "score": 89,
            "grade": "A",
            "ndvi": 0.7638,
            "ndwi": -0.6778,
            "mndwi": -0.5295,
            "components": {"satellite_score": 89, "surface_type": "land", "absolute_ndvi_condition": 88.5, "ndvi_now": 0.7638, "ndvi_absolute_score": 100.0, "ndwi_absolute_score": 0.0},
        },
        {
            "id": "sinhagad_forest",
            "name": "Sinhagad Forest Ridge",
            "lat": 18.3667,
            "lon": 73.7558,
            "buffer_radius_m": 250,
            "description": "Protected mountain ridge in the Western Ghats with dense forest cover.",
            "activity_type": "land",
            "score": 79,
            "grade": "B",
            "ndvi": 0.6894,
            "ndwi": -0.5722,
            "mndwi": -0.4149,
            "components": {"satellite_score": 79, "surface_type": "land", "absolute_ndvi_condition": 78.6, "ndvi_now": 0.6894, "ndvi_absolute_score": 100.0, "ndwi_absolute_score": 5.7},
        },
        {
            "id": "kharadi_it_park",
            "name": "Kharadi IT Park Core",
            "lat": 18.5500,
            "lon": 73.9400,
            "buffer_radius_m": 250,
            "description": "High-density commercial IT park with concrete, asphalt, and low green cover.",
            "activity_type": "urban",
            "score": 21,
            "grade": "F",
            "ndvi": 0.1394,
            "ndwi": -0.2010,
            "mndwi": -0.2634,
            "components": {"satellite_score": 21, "surface_type": "urban", "green_blue_cover": 0.1714, "veg_frac": 0.1545, "water_frac": 0.0169, "ndvi_absolute_score": 27.9, "ndwi_absolute_score": 15.8},
        },
        {
            "id": "shivajinagar_core",
            "name": "Shivajinagar Dense Urban Core",
            "lat": 18.5300,
            "lon": 73.8500,
            "buffer_radius_m": 250,
            "description": "Historic dense downtown core with paved surfaces and negligible vegetation.",
            "activity_type": "urban",
            "score": 50,
            "grade": "C",
            "ndvi": 0.4122,
            "ndwi": -0.4126,
            "mndwi": -0.3537,
            "components": {"satellite_score": 50, "surface_type": "urban", "green_blue_cover": 0.5076, "veg_frac": 0.4838, "water_frac": 0.0238, "ndvi_absolute_score": 82.4, "ndwi_absolute_score": 9.8},
        },
        {
            "id": "wagholi_stone_quarry",
            "name": "Wagholi Basalt Stone Quarry",
            "lat": 18.5840,
            "lon": 73.9960,
            "buffer_radius_m": 250,
            "description": "Excavated open-cast basalt quarry and exposed barren bedrock.",
            "activity_type": "urban",
            "score": 50,
            "grade": "C",
            "ndvi": 0.3846,
            "ndwi": -0.3962,
            "mndwi": -0.3338,
            "components": {"satellite_score": 50, "surface_type": "urban", "green_blue_cover": 0.4947, "veg_frac": 0.4708, "water_frac": 0.0239, "ndvi_absolute_score": 76.9, "ndwi_absolute_score": 11.1},
        },
    ]

    try:
        async with async_session_factory() as session:
            site_count = await session.scalar(select(func.count(Site.id)))
            if site_count == 0:
                for seed in INITIAL_SEEDED_SITES:
                    s = Site(
                        id=seed["id"],
                        site_code=f"REF-{seed['id'][:8].upper()}",
                        lat=seed["lat"],
                        lon=seed["lon"],
                        buffer_radius_m=seed["buffer_radius_m"],
                        description=seed["description"],
                        activity_type=seed["activity_type"],
                        is_seeded_demo=True,
                    )
                    session.add(s)

                    ana = AnalysisResult(
                        id=str(uuid.uuid4()),
                        site_id=seed["id"],
                        schema_version=CURRENT_SCHEMA_VERSION,
                        mode="snapshot",
                        health_score=seed["score"],
                        health_grade=seed["grade"],
                        satellite_source="gee",
                        ndvi_tnow=seed["ndvi"],
                        ndwi_tnow=seed["ndwi"],
                        mndwi_tnow=seed["mndwi"],
                        overall_status="confirmed",
                        satellite_agreement="agree",
                        photo_agreement="none",
                        flags_json="[]",
                        health_components_json=json.dumps(seed["components"]),
                        buffer_radius_m=seed["buffer_radius_m"],
                        created_at=datetime.now(timezone.utc),
                    )
                    session.add(ana)

                await session.commit()
    except Exception as e:
        # Don't halt startup if seeding encounters an issue
        pass

