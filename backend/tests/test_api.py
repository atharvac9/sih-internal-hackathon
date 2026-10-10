"""
Integration tests for FastAPI endpoints.
Tests /api/health, /api/sites, and /api/analysis/adhoc.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.database import Base, get_db

# Use in-memory SQLite for testing
engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db():
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="module")
def client():
    # Pre-create tables using the engine
    import asyncio

    async def init_models():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(init_models())

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c

    async def clean_models():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    asyncio.run(clean_models())


def test_health_check(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "services" in data
    assert "gee_configured" in data["services"]
    assert "clip_model_loaded" in data["services"]
    assert "storage_configured" in data["services"]


def test_create_and_get_site(client):
    payload = {
        "lat": 19.05,
        "lon": 74.72,
        "activity_type": "farm_pond",
        "description": "Test farm pond site",
        "buffer_radius_m": 500,
    }
    create_resp = client.post("/api/sites", json=payload)
    assert create_resp.status_code == 201
    created = create_resp.json()
    assert created["lat"] == 19.05
    assert created["lon"] == 74.72
    assert created["activity_type"] == "farm_pond"
    assert "id" in created

    site_id = created["id"]
    get_resp = client.get(f"/api/sites/{site_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == site_id


def test_list_sites(client):
    list_resp = client.get("/api/sites")
    assert list_resp.status_code == 200
    data = list_resp.json()
    assert data["total"] >= 1
    assert len(data["sites"]) >= 1


def test_get_nonexistent_site(client):
    resp = client.get("/api/sites/non-existent-id")
    assert resp.status_code == 404


def test_create_site_invalid_coords(client):
    payload = {
        "lat": 95.0,  # Invalid latitude > 90
        "lon": 74.72,
        "activity_type": "check_dam",
    }
    resp = client.post("/api/sites", json=payload)
    assert resp.status_code == 422


def test_adhoc_analysis_gee_failure_returns_503(client, monkeypatch):
    """When GEE fails and DEMO_MODE is False, adhoc analysis returns 503 explicit error, not simulated data."""
    from app.config import settings

    async def mock_get_snapshot(*args, **kwargs):
        return {"error": "Earth Engine unavailable"}

    monkeypatch.setattr("app.services.gee_service.get_snapshot_indices", mock_get_snapshot)
    prev_demo = settings.demo_mode
    settings.demo_mode = False
    try:
        payload = {
            "lat": 19.05,
            "lon": 74.72,
            "claimed_activity_type": "farm_pond",
            "buffer_radius_m": 500,
        }
        resp = client.post("/api/analysis/adhoc", json=payload)
        assert resp.status_code == 503
        data = resp.json()
        assert "Satellite analysis failed" in data.get("detail", "")
    finally:
        settings.demo_mode = prev_demo


def test_adhoc_analysis_demo_mode_returns_simulated_source(client, monkeypatch):
    """When GEE fails and DEMO_MODE is True, adhoc analysis returns 200 with source='simulated'."""
    from app.config import settings

    async def mock_get_snapshot(*args, **kwargs):
        return {"error": "Earth Engine unavailable"}

    monkeypatch.setattr("app.services.gee_service.get_snapshot_indices", mock_get_snapshot)
    prev_demo = settings.demo_mode
    settings.demo_mode = True
    try:
        payload = {
            "lat": 19.05,
            "lon": 74.72,
            "claimed_activity_type": "farm_pond",
            "buffer_radius_m": 500,
        }
        resp = client.post("/api/analysis/adhoc", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["satellite"]["source"] == "simulated"
    finally:
        settings.demo_mode = prev_demo


def test_photo_upload_and_geotag(client):
    """Test photo upload with client geotag and subsequent patch."""
    import io
    from PIL import Image

    # Create a site
    site_payload = {
        "lat": 19.9975,
        "lon": 73.7898,
        "activity_type": "check_dam",
        "description": "Test Site for Photo Upload",
    }
    site_res = client.post("/api/sites", json=site_payload)
    assert site_res.status_code == 201
    site_id = site_res.json()["id"]

    # Create dummy image in memory
    img = Image.new("RGB", (64, 64), color="blue")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)

    # Upload with client_lat and client_lon
    files = {"file": ("test_photo.jpg", buf, "image/jpeg")}
    data = {"client_lat": "19.9975", "client_lon": "73.7898"}
    upload_res = client.post(f"/api/photos/{site_id}", files=files, data=data)
    assert upload_res.status_code == 201
    photo_data = upload_res.json()
    assert photo_data["exif_has_gps"] is True
    assert photo_data["exif_lat"] == 19.9975
    assert photo_data["exif_lon"] == 73.7898
    assert photo_data["predicted_class"] is not None
    assert photo_data["classification_confidence"] > 0

    # Patch geotag
    photo_id = photo_data["id"]
    patch_res = client.patch(f"/api/photos/{photo_id}/geotag", data={"lat": "20.0001", "lon": "73.8000"})
    assert patch_res.status_code == 200
    patched_data = patch_res.json()
    assert patched_data["exif_lat"] == 20.0001
    assert patched_data["exif_lon"] == 73.8


def test_stale_analysis_never_served(client):
    """Rows with old schema_version or simulated data (while DEMO_MODE=False) count as stale and must never be served."""
    import asyncio
    import uuid
    from app.models.analysis import AnalysisResult
    from app.config import settings

    settings.demo_mode = False

    site_res = client.post("/api/sites", json={"lat": 18.5, "lon": 73.8, "description": "Stale Row Test Site"})
    site_id = site_res.json()["id"]

    # Insert a row with old schema_version=1 directly into test DB
    async def insert_stale_row():
        async with SessionLocal() as session:
            stale_ana = AnalysisResult(
                id=str(uuid.uuid4()),
                site_id=site_id,
                schema_version=1,  # Old version
                mode="snapshot",
                health_score=75,
                health_grade="B",
                satellite_source="gee",
            )
            session.add(stale_ana)
            await session.commit()

    asyncio.run(insert_stale_row())

    # GET /latest must return 404 (needs reanalysis), not the stale row
    resp = client.get(f"/api/analysis/{site_id}/latest")
    assert resp.status_code == 404
    assert "stale" in resp.json().get("detail", "").lower()

    # GET /api/sites must return site with latest_analysis = None
    site_get = client.get(f"/api/sites/{site_id}")
    assert site_get.status_code == 200
    assert site_get.json()["latest_analysis"] is None


def test_latest_analysis_get_never_500s_on_old_row(client):
    """GET /api/sites and GET /api/analysis/{id}/latest must never 500 on corrupted or old-schema rows."""
    import asyncio
    import uuid
    from app.models.analysis import AnalysisResult

    site_res = client.post("/api/sites", json={"lat": 18.6, "lon": 73.9, "description": "Tolerant Test Site"})
    site_id = site_res.json()["id"]

    async def insert_corrupt_row():
        async with SessionLocal() as session:
            corrupt_ana = AnalysisResult(
                id=str(uuid.uuid4()),
                site_id=site_id,
                schema_version=2,
                mode="unknown_mode",
                health_score=60,
                health_grade="C",
                flags_json="INVALID_JSON{broken",
                satellite_source="gee",
            )
            session.add(corrupt_ana)
            await session.commit()

    asyncio.run(insert_corrupt_row())

    # Tolerant latest GET: must return 404, never 500
    resp = client.get(f"/api/analysis/{site_id}/latest")
    assert resp.status_code == 404

    # Tolerant sites GET: must return 200, never 500
    sites_resp = client.get("/api/sites")
    assert sites_resp.status_code == 200
