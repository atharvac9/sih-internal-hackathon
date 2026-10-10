"""
EXIF metadata extraction for photo authenticity checking.

Checks for GPS coordinates, camera model, and capture timestamp.
Returns soft warnings (not hard rejects) when metadata is missing.
"""

import io
import logging
from typing import Optional

from PIL import Image

logger = logging.getLogger(__name__)


def extract_exif(image_bytes: bytes) -> dict:
    """
    Extract EXIF metadata from image bytes.

    Returns:
        dict with:
            - has_exif: bool
            - has_gps: bool
            - has_camera_model: bool
            - has_timestamp: bool
            - gps_lat: float | None
            - gps_lon: float | None
            - camera_model: str | None
            - capture_datetime: str | None
            - warnings: list[str]
    """
    result = {
        "has_exif": False,
        "has_gps": False,
        "has_camera_model": False,
        "has_timestamp": False,
        "gps_lat": None,
        "gps_lon": None,
        "camera_model": None,
        "capture_datetime": None,
        "warnings": [],
    }

    try:
        img = Image.open(io.BytesIO(image_bytes))
    except Exception as e:
        result["warnings"].append(f"Could not open image: {e}")
        return result

    from PIL import ExifTags

    # Try to get EXIF data using Pillow's built-in APIs
    exif_data = None
    try:
        exif_data = img._getexif()
    except (AttributeError, Exception):
        pass

    raw_exif = None
    try:
        raw_exif = img.getexif()
    except (AttributeError, Exception):
        pass

    if exif_data is None and (raw_exif is None or len(raw_exif) == 0):
        # EXIF header is missing (e.g. stripped by WhatsApp, messaging apps, or downloads).
        # Check if the photo contains visual GPS/watermark geotags burned directly into the image pixels.
        visual_geo = _extract_visual_geotag(image_bytes, img=img)
        if visual_geo and visual_geo.get("has_gps"):
            result["has_exif"] = True
            result["has_gps"] = True
            result["gps_lat"] = visual_geo["gps_lat"]
            result["gps_lon"] = visual_geo["gps_lon"]
            if visual_geo.get("camera_model"):
                result["has_camera_model"] = True
                result["camera_model"] = visual_geo["camera_model"]
            if visual_geo.get("capture_datetime"):
                result["has_timestamp"] = True
                result["capture_datetime"] = visual_geo["capture_datetime"]
            loc_name = visual_geo.get("location_name")
            if loc_name:
                result["warnings"].append(f"Geotag extracted from visual watermark: {loc_name}")
            else:
                result["warnings"].append("GPS geotag extracted from visual camera watermark in photo")
            return result

        result["warnings"].append(
            "No EXIF metadata found — photo may have been screenshot, "
            "downloaded, or had metadata stripped by messaging/social platforms"
        )
        return result

    result["has_exif"] = True
    if exif_data is None:
        exif_data = dict(raw_exif)

    # ── Camera Model (tag 0x0110 = 272) ──────────────────────────────────
    camera_model = exif_data.get(272) or (raw_exif.get(272) if raw_exif else None)
    if not camera_model and raw_exif:
        camera_model = raw_exif.get(ExifTags.Base.Model) or raw_exif.get(ExifTags.Base.Make)
    if camera_model:
        result["has_camera_model"] = True
        result["camera_model"] = str(camera_model).replace("\x00", "").strip()
    else:
        result["warnings"].append("No camera model in EXIF — may not be a direct camera photo")

    # ── Timestamp (tag 0x9003 = 36867 = DateTimeOriginal) ────────────────
    datetime_original = exif_data.get(36867)
    datetime_digitized = exif_data.get(36868)
    datetime_basic = exif_data.get(306)
    if not (datetime_original or datetime_digitized or datetime_basic) and raw_exif:
        datetime_basic = raw_exif.get(306) or raw_exif.get(ExifTags.Base.DateTime)

    capture_dt = datetime_original or datetime_digitized or datetime_basic
    if capture_dt:
        result["has_timestamp"] = True
        result["capture_datetime"] = str(capture_dt).replace("\x00", "").strip()
    else:
        result["warnings"].append("No capture timestamp in EXIF")

    # ── GPS (tag 0x8825 = 34853 = GPSInfo) ───────────────────────────────
    gps_info = None
    # Method A: from _getexif() dict
    if isinstance(exif_data.get(34853), dict):
        gps_info = exif_data.get(34853)
    # Method B: from getexif().get_ifd(ExifTags.IFD.GPSInfo)
    if not gps_info and raw_exif:
        try:
            if hasattr(ExifTags, "IFD") and hasattr(ExifTags.IFD, "GPSInfo"):
                ifd_data = raw_exif.get_ifd(ExifTags.IFD.GPSInfo)
                if ifd_data:
                    gps_info = dict(ifd_data)
        except Exception:
            pass
    if not gps_info and raw_exif:
        try:
            ifd_data = raw_exif.get_ifd(0x8825)
            if ifd_data:
                gps_info = dict(ifd_data)
        except Exception:
            pass

    if gps_info:
        try:
            lat_ref = gps_info.get(1) or gps_info.get("GPSLatitudeRef")
            lat_val = gps_info.get(2) or gps_info.get("GPSLatitude")
            lon_ref = gps_info.get(3) or gps_info.get("GPSLongitudeRef")
            lon_val = gps_info.get(4) or gps_info.get("GPSLongitude")

            gps_lat = _convert_gps_to_decimal(lat_val, lat_ref)
            gps_lon = _convert_gps_to_decimal(lon_val, lon_ref)

            if gps_lat is not None and gps_lon is not None:
                result["has_gps"] = True
                result["gps_lat"] = round(gps_lat, 6)
                result["gps_lon"] = round(gps_lon, 6)
            else:
                result["warnings"].append(
                    "GPS tag present but coordinates could not be parsed"
                )
        except Exception as e:
            logger.warning(f"GPS parsing error: {e}")
            result["warnings"].append("GPS tag present but malformed")
    else:
        result["warnings"].append(
            "No GPS coordinates found in image EXIF. Camera location tagging may be disabled in device settings, or photo was downloaded/shared without metadata."
        )

    # Try piexif for more detailed extraction if available
    try:
        import piexif
        piexif_data = piexif.load(image_bytes)

        # Double-check GPS if Pillow missed it
        if not result["has_gps"] and piexif_data.get("GPS"):
            gps = piexif_data["GPS"]
            if piexif.GPSIFD.GPSLatitude in gps and piexif.GPSIFD.GPSLongitude in gps:
                lat = _piexif_gps_to_decimal(
                    gps[piexif.GPSIFD.GPSLatitude],
                    gps.get(piexif.GPSIFD.GPSLatitudeRef, b"N"),
                )
                lon = _piexif_gps_to_decimal(
                    gps[piexif.GPSIFD.GPSLongitude],
                    gps.get(piexif.GPSIFD.GPSLongitudeRef, b"E"),
                )
                if lat is not None and lon is not None:
                    result["has_gps"] = True
                    result["gps_lat"] = round(lat, 6)
                    result["gps_lon"] = round(lon, 6)
                    result["warnings"] = [
                        w for w in result["warnings"]
                        if "No GPS coordinates" not in w
                    ]
    except ImportError:
        pass
    except Exception as e:
        logger.debug(f"piexif extraction failed (non-critical): {e}")

    # Fallback to visual watermark OCR if EXIF header lacked GPS
    if not result["has_gps"]:
        visual_geo = _extract_visual_geotag(image_bytes, img=img)
        if visual_geo and visual_geo.get("has_gps"):
            result["has_gps"] = True
            result["gps_lat"] = visual_geo["gps_lat"]
            result["gps_lon"] = visual_geo["gps_lon"]
            result["warnings"] = [
                w for w in result["warnings"]
                if "No GPS coordinates" not in w
            ]
            loc_name = visual_geo.get("location_name")
            if loc_name:
                result["warnings"].append(f"Geotag extracted from visual watermark: {loc_name}")
            else:
                result["warnings"].append("GPS geotag extracted from visual camera watermark in photo")

            if not result["has_camera_model"] and visual_geo.get("camera_model"):
                result["has_camera_model"] = True
                result["camera_model"] = visual_geo["camera_model"]
            if not result["has_timestamp"] and visual_geo.get("capture_datetime"):
                result["has_timestamp"] = True
                result["capture_datetime"] = visual_geo["capture_datetime"]

    return result


def _convert_gps_to_decimal(
    dms_tuple: Optional[tuple],
    ref: Optional[str],
) -> Optional[float]:
    """Convert GPS DMS (degrees, minutes, seconds) tuple to decimal degrees."""
    if dms_tuple is None or ref is None:
        return None

    try:
        # Handle both IFDRational and plain tuple formats
        def _to_float(val):
            if hasattr(val, "numerator") and hasattr(val, "denominator"):
                return float(val.numerator) / float(val.denominator) if val.denominator else 0.0
            if isinstance(val, tuple) and len(val) == 2:
                return float(val[0]) / float(val[1]) if val[1] else 0.0
            return float(val)

        # Handle single float, 1-tuple, 2-tuple, or standard 3-tuple (deg, min, sec)
        if isinstance(dms_tuple, (int, float)):
            decimal = float(dms_tuple)
        elif len(dms_tuple) == 1:
            decimal = _to_float(dms_tuple[0])
        elif len(dms_tuple) == 2:
            decimal = _to_float(dms_tuple[0]) + _to_float(dms_tuple[1]) / 60.0
        else:
            degrees = _to_float(dms_tuple[0])
            minutes = _to_float(dms_tuple[1])
            seconds = _to_float(dms_tuple[2])
            decimal = degrees + minutes / 60.0 + seconds / 3600.0

        ref_str = ref if isinstance(ref, str) else ref.decode("utf-8", errors="ignore")
        if ref_str.upper() in ("S", "W"):
            decimal = -decimal

        return decimal

    except (IndexError, TypeError, ValueError) as e:
        logger.debug(f"GPS conversion error: {e}")
        return None


def _piexif_gps_to_decimal(
    dms_tuple: tuple,
    ref: bytes,
) -> Optional[float]:
    """Convert piexif GPS format to decimal degrees."""
    try:
        def _rational_to_float(r):
            return float(r[0]) / float(r[1]) if r[1] else 0.0

        degrees = _rational_to_float(dms_tuple[0])
        minutes = _rational_to_float(dms_tuple[1])
        seconds = _rational_to_float(dms_tuple[2])

        decimal = degrees + minutes / 60 + seconds / 3600

        ref_str = ref.decode("utf-8") if isinstance(ref, bytes) else str(ref)
        if ref_str.upper() in ("S", "W"):
            decimal = -decimal

        return decimal

    except (IndexError, TypeError, ValueError, ZeroDivisionError):
        return None


# ── Visual Geotag OCR Extraction (GPS Map Camera / Watermark Fallback) ───────

_GEOCODE_CACHE: dict = {}


def _run_winocr(img: Image.Image) -> dict:
    """Run winocr safely in a dedicated worker thread (avoids conflict with running event loops)."""
    import winocr
    from concurrent.futures import ThreadPoolExecutor

    try:
        import asyncio
        loop = asyncio.get_running_loop()
    except (RuntimeError, AttributeError):
        loop = None

    if loop and loop.is_running():
        with ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(winocr.recognize_pil_sync, img, "en").result()
    else:
        return winocr.recognize_pil_sync(img, lang="en")


def _extract_visual_geotag(image_bytes: bytes, img: Optional[Image.Image] = None) -> dict:
    """
    Extract visual geotag, location address, timestamp, and camera watermark
    stamped directly into the image pixels using fast Windows Media OCR (winocr).

    This recovers GPS coordinates from photos where EXIF headers were stripped
    during WhatsApp, messaging, or web browser transfer, but the photo displays
    burned-in location stamps (e.g. GPS Map Camera, Solocator, Timestamp Camera).
    """
    result = {
        "has_gps": False,
        "gps_lat": None,
        "gps_lon": None,
        "location_name": None,
        "camera_model": None,
        "capture_datetime": None,
    }

    try:
        import winocr
    except ImportError:
        logger.debug("winocr package not installed, skipping visual OCR geotag extraction")
        return result

    try:
        if img is None:
            img = Image.open(io.BytesIO(image_bytes))

        # Ensure RGB mode for OCR
        if img.mode != "RGB":
            img = img.convert("RGB")

        # 1. First attempt OCR on the full image
        ocr_res = _run_winocr(img)
        full_lines = [l.get("text", "").strip() for l in (ocr_res.get("lines") or []) if l.get("text")]
        if not full_lines and ocr_res and ocr_res.get("text"):
            full_lines = [l.strip() for l in ocr_res["text"].split("\n") if l.strip()]
        full_text = "\n".join(full_lines)

        # 2. Check for explicit coordinates in full text
        coords = _parse_coordinates_from_text(full_text)

        # If no coordinates found and image is large enough, try focused banner crops
        # (GPS Map Camera & Solocator typically stamp on the bottom 35% or top 25%)
        w, h = img.size
        banner_text = ""
        if coords is None and h >= 300:
            # Crop bottom 35%
            try:
                bottom_crop = img.crop((0, int(h * 0.65), w, h))
                bottom_res = _run_winocr(bottom_crop)
                bottom_lines = [l.get("text", "").strip() for l in (bottom_res.get("lines") or []) if l.get("text")]
                banner_text = "\n".join(bottom_lines)
                coords = _parse_coordinates_from_text(banner_text)
            except Exception as e:
                logger.debug(f"Bottom crop OCR failed: {e}")

        if coords is None and h >= 300:
            # Crop top 25%
            try:
                top_crop = img.crop((0, 0, w, int(h * 0.25)))
                top_res = _run_winocr(top_crop)
                top_lines = [l.get("text", "").strip() for l in (top_res.get("lines") or []) if l.get("text")]
                top_text = "\n".join(top_lines)
                coords = _parse_coordinates_from_text(top_text)
                if coords:
                    banner_text = top_text
            except Exception as e:
                logger.debug(f"Top crop OCR failed: {e}")

        combined_text = f"{full_text}\n{banner_text}".strip()

        # 3. If explicit numeric coordinates were found:
        if coords is not None:
            result["has_gps"] = True
            result["gps_lat"] = round(coords[0], 6)
            result["gps_lon"] = round(coords[1], 6)

        # 4. If no numeric coordinates found, check for location / address text (e.g. UK locations)
        if not result["has_gps"] and combined_text:
            address_query = _extract_address_query(combined_text)
            if address_query:
                geocoded = _geocode_address(address_query)
                if geocoded:
                    result["has_gps"] = True
                    result["gps_lat"] = round(geocoded[0], 6)
                    result["gps_lon"] = round(geocoded[1], 6)
                    result["location_name"] = geocoded[2]

        # 5. Extract camera app branding (e.g. GPS Map Camera, Solocator)
        app_name = _extract_camera_app(combined_text)
        if app_name:
            result["camera_model"] = f"{app_name} (Visual Stamp)"

        # 6. Extract capture timestamp if present in visual text
        dt_str = _extract_timestamp_from_text(combined_text)
        if dt_str:
            result["capture_datetime"] = dt_str

    except Exception as e:
        logger.warning(f"Visual watermark OCR extraction error: {e}")

    return result


def _parse_coordinates_from_text(text: str) -> Optional[tuple[float, float]]:
    """Parse latitude and longitude coordinates from OCR text."""
    if not text:
        return None

    import re
    text_clean = text.replace("\n", " ").replace("\r", " ")

    # 1. Degree Minutes Seconds format: 51°30'26"N 0°07'39"W
    dms_pattern = (
        r"(\d+)\s*[°ºo]?\s*(\d+)\s*[\'′]\s*(\d+(?:\.\d+)?)\s*[\"″]?\s*([NSns])"
        r"[\s,;/|]+"
        r"(\d+)\s*[°ºo]?\s*(\d+)\s*[\'′]\s*(\d+(?:\.\d+)?)\s*[\"″]?\s*([EWew])"
    )
    m_dms = re.search(dms_pattern, text_clean)
    if m_dms:
        try:
            d1, m1, s1, ref1, d2, m2, s2, ref2 = m_dms.groups()
            lat = float(d1) + float(m1) / 60.0 + float(s1) / 3600.0
            if ref1.upper() == "S":
                lat = -lat
            lon = float(d2) + float(m2) / 60.0 + float(s2) / 3600.0
            if ref2.upper() == "W":
                lon = -lon
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                return round(lat, 6), round(lon, 6)
        except (ValueError, TypeError):
            pass

    # 2. Lat / Long with explicit labels
    # Handles degree symbol as °, o, 0, or omitted, plus space or dot separators:
    # "Lat 18.5543750 Long 73.961460"
    # "Lat 51.501364° Long -0.141890°"
    # "Lat: 51.5074 N, Long: 0.1278 W"
    # "Latitude: 51.5074, Longitude: -0.1278"
    lat_lon_pattern = (
        r"Lat(?:itude)?\s*[:=\s]?\s*([+-]?\d+(?:\.\d+)?)\s*([°ºo])?\s*([NSns])?"
        r"[\s,;/|]+(?:and\s+)?"
        r"Long(?:itude)?\s*[:=\s]?\s*([+-]?\d+(?:\.\d+)?)\s*([°ºo])?\s*([EWew])?"
    )
    m_latlon = re.search(lat_lon_pattern, text_clean, re.IGNORECASE)
    if m_latlon:
        try:
            val1, deg1, ref1, val2, deg2, ref2 = m_latlon.groups()
            lat, lon = float(val1), float(val2)
            if ref1 and ref1.upper() == "S":
                lat = -abs(lat)
            if ref2 and ref2.upper() == "W":
                lon = -abs(lon)
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                return round(lat, 6), round(lon, 6)
        except (ValueError, TypeError):
            pass

    # 3. Standard decimal with direction: 51.5074° N, 0.1278° W
    dir_pattern = (
        r"([+-]?\d+\.\d{3,})\s*[°ºo]?\s*([NSns])"
        r"[\s,;/|]+"
        r"([+-]?\d+\.\d{3,})\s*[°ºo]?\s*([EWew])"
    )
    m_dir = re.search(dir_pattern, text_clean)
    if m_dir:
        try:
            val1, ref1, val2, ref2 = m_dir.groups()
            lat = float(val1) * (-1 if ref1.upper() == "S" else 1)
            lon = float(val2) * (-1 if ref2.upper() == "W" else 1)
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                return round(lat, 6), round(lon, 6)
        except (ValueError, TypeError):
            pass

    # 4. GPS / Location / Coords prefix: GPS: 51.5074, -0.1278
    gps_pattern = (
        r"(?:GPS|Location|Coords?)\s*[:=\s]?\s*([+-]?\d+\.\d{3,})"
        r"[\s,;/|]+"
        r"([+-]?\d+\.\d{3,})"
    )
    m_gps = re.search(gps_pattern, text_clean, re.IGNORECASE)
    if m_gps:
        try:
            lat, lon = float(m_gps.group(1)), float(m_gps.group(2))
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                return round(lat, 6), round(lon, 6)
        except (ValueError, TypeError):
            pass

    return None


def _extract_address_query(text: str) -> Optional[str]:
    """
    Extract location or address from GPS camera watermark text if no explicit coordinates were found.
    Looks for UK / United Kingdom locations, cities, postal codes, and places.
    """
    import re
    lines = [line.strip() for line in text.split("\n") if line.strip()]

    filtered = []
    for raw_line in lines:
        # Strip camera app prefixes from line rather than discarding entire line
        line = re.sub(
            r"\b(?:Google|GPS Map Camera|Timestamp Camera|Solocator|SpotGeo|SurveyCam|Open Camera)\b",
            "",
            raw_line,
            flags=re.I,
        )
        line = re.sub(r"^[,\s:;|-]+", "", line)
        line = re.sub(r"[,\s:;|-]+$", "", line).strip()

        if not line or len(line) < 4:
            continue
        if re.search(r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|\d{1,2}/\d{1,2}/\d{2,4}|GMT)", line, re.I):
            continue
        if re.search(r"Lat.*Long", line, re.I):
            continue
        if re.match(r"^[\d\s.,:;/-]+$", line):
            continue
        filtered.append(line)

    # Check for UK-specific locations first
    for line in filtered:
        if re.search(r"\b(?:UK|United Kingdom|England|Scotland|Wales|London|Manchester|Birmingham|Leeds|Glasgow|Bristol|Oxford|Cambridge|Edinburgh|Westminster)\b", line, re.I):
            return line

    # Check for lines containing commas (typical address structure)
    for line in filtered:
        if "," in line and len(line) >= 8:
            return line

    if filtered:
        return max(filtered, key=len)

    return None


def _geocode_address(query: str) -> Optional[tuple[float, float, str]]:
    """Resolve an address query to (latitude, longitude, display_name) via Nominatim."""
    if not query:
        return None

    query_clean = query.strip()
    if query_clean in _GEOCODE_CACHE:
        return _GEOCODE_CACHE[query_clean]

    import urllib.request
    import urllib.parse
    import json

    try:
        url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(query_clean)}&format=json&limit=1"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "CleanWaterInitiative/1.0 (water-survey@cleanwater.org)"}
        )
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            data = json.loads(resp.read().decode())
            if data and len(data) > 0:
                lat = float(data[0]["lat"])
                lon = float(data[0]["lon"])
                display = data[0].get("display_name", query_clean)
                short_display = display.split(",")[0] if "," in display else display
                res = (lat, lon, short_display)
                _GEOCODE_CACHE[query_clean] = res
                return res
    except Exception as e:
        logger.debug(f"Geocoding address '{query_clean}' failed: {e}")

    _GEOCODE_CACHE[query_clean] = None
    return None


def _extract_camera_app(text: str) -> Optional[str]:
    """Detect known GPS camera or timestamp camera app signatures from OCR text."""
    if not text:
        return None
    import re
    app_patterns = [
        ("GPS Map Camera", r"GPS Map Camera"),
        ("Solocator", r"Solocator"),
        ("Timestamp Camera", r"Timestamp Camera"),
        ("SpotGeo Camera", r"SpotGeo"),
        ("SurveyCam", r"SurveyCam"),
        ("Open Camera", r"Open Camera"),
    ]
    for app_name, pattern in app_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return app_name
    return None


def _extract_timestamp_from_text(text: str) -> Optional[str]:
    """Detect capture timestamp printed in watermark overlay."""
    if not text:
        return None
    import re
    ts_pattern = r"((?:(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)[a-z]*[,\s]+)?(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})\s+\d{1,2}:\d{2}(?::\d{2})?(?:\s*[APap][Mm])?(?:\s*GMT\s*[+-]\d{2}:\d{2})?)"
    m = re.search(ts_pattern, text)
    if m:
        return m.group(1).strip()
    return None
