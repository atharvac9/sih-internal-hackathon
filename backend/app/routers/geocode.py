"""
Geocoding API — robust proxy for Nominatim OpenStreetMap and local site resolution.
Bypasses browser CORS / 403 restrictions by sending proper User-Agent headers,
with fallback to local monitored sites and curated watershed landmarks.
"""

import logging
import re
import urllib.parse
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.site import Site

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/geocode", tags=["Geocoding"])

_GEOCODE_CACHE: dict[str, list[dict]] = {}

# Built-in watershed landmarks and Maharashtra/India reference coordinates
CURATED_LANDMARKS = [
    {"name": "Khadakwasla Reservoir", "displayName": "Khadakwasla Dam & Reservoir, Pune, Maharashtra", "lat": 18.4400, "lon": 73.7700, "type": "reservoir"},
    {"name": "Sinhagad Forest Ridge", "displayName": "Sinhagad Fort & Forest Ridge, Western Ghats, Pune", "lat": 18.3667, "lon": 73.7558, "type": "forest"},
    {"name": "Vetal Hill (Vetal Tekdi)", "displayName": "Vetal Tekdi Forest Hill, Pune, Maharashtra", "lat": 18.5200, "lon": 73.8200, "type": "hill"},
    {"name": "Kharadi IT Park Core", "displayName": "EON IT Park, Kharadi, Pune, Maharashtra", "lat": 18.5500, "lon": 73.9400, "type": "urban"},
    {"name": "Shivajinagar Urban Core", "displayName": "Shivajinagar Downtown Core, Pune, Maharashtra", "lat": 18.5300, "lon": 73.8500, "type": "urban"},
    {"name": "Wagholi Stone Quarry", "displayName": "Wagholi Basalt Quarry Region, East Pune, Maharashtra", "lat": 18.5840, "lon": 73.9960, "type": "quarry"},
    {"name": "Pune City", "displayName": "Pune, Maharashtra, India", "lat": 18.5204, "lon": 73.8567, "type": "city"},
    {"name": "Mumbai", "displayName": "Mumbai, Maharashtra, India", "lat": 19.0760, "lon": 72.8777, "type": "city"},
    {"name": "Nashik", "displayName": "Nashik, Maharashtra, India", "lat": 19.9975, "lon": 73.7898, "type": "city"},
    {"name": "Panshet Reservoir", "displayName": "Panshet Dam, Velhe, Pune, Maharashtra", "lat": 18.3739, "lon": 73.6192, "type": "reservoir"},
    {"name": "Mulshi Lake", "displayName": "Mulshi Dam Lake, Pune, Maharashtra", "lat": 18.5034, "lon": 73.5135, "type": "reservoir"},
    {"name": "Pawna Lake", "displayName": "Pawna Dam Reservoir, Maval, Maharashtra", "lat": 18.6728, "lon": 73.4862, "type": "reservoir"},
]


@router.get("")
async def geocode_location(
    q: str = Query(..., description="Location name, address, or coordinates"),
    limit: int = Query(6, ge=1, le=10),
    db: AsyncSession = Depends(get_db),
):
    """
    Geocode a query into coordinates with name and display label.
    Supports:
      1. Direct coordinates (e.g. '18.44, 73.77')
      2. Monitored database sites
      3. Upstream OpenStreetMap Nominatim with proper User-Agent
      4. Curated watershed landmarks fallback
    """
    clean_q = q.strip()
    if not clean_q or len(clean_q) < 2:
        return []

    # 1. Direct coordinate check
    coord_match = re.match(r"^([-+]?\d{1,2}(?:\.\d+)?)[,\s]+([-+]?\d{1,3}(?:\.\d+)?)$", clean_q)
    if coord_match:
        lat = float(coord_match.group(1))
        lon = float(coord_match.group(2))
        if -90 <= lat <= 90 and -180 <= lon <= 180:
            return [{
                "name": f"Coordinates ({lat:.4f}°, {lon:.4f}°)",
                "displayName": f"Direct Coordinates: {lat:.4f}°N, {lon:.4f}°E",
                "lat": lat,
                "lon": lon,
                "type": "coordinate",
            }]

    # Check memory cache
    cache_key = clean_q.lower()
    if cache_key in _GEOCODE_CACHE:
        return _GEOCODE_CACHE[cache_key][:limit]

    results = []

    # 2. Check local database sites
    try:
        query_pattern = f"%{clean_q}%"
        stmt = select(Site).where(
            (Site.description.ilike(query_pattern))
            | (Site.site_code.ilike(query_pattern))
            | (Site.id.ilike(query_pattern))
        ).limit(3)
        db_res = await db.execute(stmt)
        matched_sites = db_res.scalars().all()
        for s in matched_sites:
            results.append({
                "name": s.description or s.site_code or s.id,
                "displayName": f"Monitored Site: {s.description or s.site_code} ({s.lat:.4f}°N, {s.lon:.4f}°E)",
                "lat": s.lat,
                "lon": s.lon,
                "type": "site",
            })
    except Exception as e:
        logger.debug(f"DB search failed: {e}")

    # 3. Check curated landmarks
    for lm in CURATED_LANDMARKS:
        if clean_q.lower() in lm["name"].lower() or clean_q.lower() in lm["displayName"].lower():
            if not any(r["name"] == lm["name"] for r in results):
                results.append(lm)

    # 4. Upstream Nominatim Query with proper User-Agent
    try:
        url = f"https://nominatim.openstreetmap.org/search?format=json&q={urllib.parse.quote(clean_q)}&limit={limit}&addressdetails=1"
        headers = {
            "User-Agent": "NeerDrishtiWatershedApp/1.0 (water-survey@cleanwater.org)",
            "Accept-Language": "en",
        }
        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                for item in data:
                    item_name = item.get("display_name", "").split(",")[0]
                    lat = float(item["lat"])
                    lon = float(item["lon"])
                    if not any(abs(r["lat"] - lat) < 0.001 and abs(r["lon"] - lon) < 0.001 for r in results):
                        results.append({
                            "name": item_name,
                            "displayName": item.get("display_name", item_name),
                            "lat": lat,
                            "lon": lon,
                            "type": item.get("type") or item.get("class", "place"),
                        })
    except Exception as e:
        logger.warning(f"Nominatim geocoding proxy failed: {e}")

    final_results = results[:limit]
    if final_results:
        _GEOCODE_CACHE[cache_key] = final_results

    return final_results


@router.get("/reverse")
async def reverse_geocode_location(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
):
    """
    Reverse geocode coordinates into a human-readable place name.
    Proxies to Nominatim with custom User-Agent to avoid browser CORS/403 blocks.
    """
    # 1. Check curated landmarks first
    for lm in CURATED_LANDMARKS:
        if abs(lm["lat"] - lat) < 0.01 and abs(lm["lon"] - lon) < 0.01:
            return {
                "name": lm["name"],
                "displayName": lm["displayName"],
                "lat": lat,
                "lon": lon,
                "type": lm.get("type", "landmark"),
            }

    # 2. Nominatim reverse geocode
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}"
        headers = {
            "User-Agent": "NeerDrishtiWatershedApp/1.0 (water-survey@cleanwater.org)",
            "Accept-Language": "en",
        }
        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                display_name = data.get("display_name", f"{lat:.4f}°N, {lon:.4f}°E")
                place_name = display_name.split(",")[0].strip()
                return {
                    "name": place_name,
                    "displayName": display_name,
                    "lat": lat,
                    "lon": lon,
                    "type": data.get("type", "reverse"),
                }
    except Exception as e:
        logger.warning(f"Nominatim reverse proxy failed: {e}")

    return {
        "name": f"Location ({lat:.4f}, {lon:.4f})",
        "displayName": f"Coordinates: {lat:.4f}°N, {lon:.4f}°E",
        "lat": lat,
        "lon": lon,
        "type": "coordinate",
    }

