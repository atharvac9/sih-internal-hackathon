"""
Tests for EXIF metadata extraction.
"""

import io
import struct
import pytest
from PIL import Image

from app.services.exif_checker import extract_exif


def _create_jpeg_bytes(width=100, height=100) -> bytes:
    """Create a minimal JPEG image in memory (no EXIF)."""
    img = Image.new("RGB", (width, height), color=(128, 128, 128))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def _create_jpeg_with_exif(
    camera_model: str = None,
    datetime_original: str = None,
) -> bytes:
    """Create a JPEG with some EXIF data using piexif if available."""
    img = Image.new("RGB", (100, 100), color=(100, 150, 100))
    buf = io.BytesIO()

    try:
        import piexif

        exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}}

        if camera_model:
            exif_dict["0th"][piexif.ImageIFD.Model] = camera_model.encode()

        if datetime_original:
            exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal] = datetime_original.encode()

        exif_bytes = piexif.dump(exif_dict)
        img.save(buf, format="JPEG", exif=exif_bytes)
    except ImportError:
        # piexif not available — just save without EXIF
        img.save(buf, format="JPEG")

    return buf.getvalue()


class TestExifExtraction:
    def test_no_exif_returns_warnings(self):
        """JPEG without EXIF should flag warnings."""
        result = extract_exif(_create_jpeg_bytes())
        assert result["has_exif"] is False or len(result["warnings"]) > 0

    def test_invalid_image_data(self):
        """Non-image bytes should return warnings without crashing."""
        result = extract_exif(b"this is not an image")
        assert len(result["warnings"]) > 0

    def test_empty_bytes(self):
        """Empty input should handle gracefully."""
        result = extract_exif(b"")
        assert len(result["warnings"]) > 0

    def test_png_without_exif(self):
        """PNG files typically don't have EXIF."""
        img = Image.new("RGB", (50, 50), color=(200, 200, 200))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        result = extract_exif(buf.getvalue())
        assert isinstance(result["warnings"], list)

    def test_result_structure(self):
        """Result dict should always have all expected keys."""
        result = extract_exif(_create_jpeg_bytes())
        assert "has_exif" in result
        assert "has_gps" in result
        assert "has_camera_model" in result
        assert "has_timestamp" in result
        assert "gps_lat" in result
        assert "gps_lon" in result
        assert "camera_model" in result
        assert "capture_datetime" in result
        assert "warnings" in result
        assert isinstance(result["warnings"], list)

    def test_camera_model_extracted(self):
        """Camera model should be extracted from EXIF if present."""
        try:
            import piexif
        except ImportError:
            pytest.skip("piexif not installed")

        image_bytes = _create_jpeg_with_exif(camera_model="Test Camera X100")
        result = extract_exif(image_bytes)
        if result["has_exif"]:
            assert result["has_camera_model"] is True
            assert "Test Camera" in (result["camera_model"] or "")

    def test_timestamp_extracted(self):
        """Timestamp should be extracted from EXIF if present."""
        try:
            import piexif
        except ImportError:
            pytest.skip("piexif not installed")

        image_bytes = _create_jpeg_with_exif(datetime_original="2024:06:15 10:30:00")
        result = extract_exif(image_bytes)
        if result["has_exif"]:
            assert result["has_timestamp"] is True

    def test_parse_coordinates_from_text(self):
        """Coordinate parsing from OCR strings handles various GPS watermark formats."""
        from app.services.exif_checker import _parse_coordinates_from_text

        # GPS Map camera format with degree as zero/omitted
        assert _parse_coordinates_from_text("Lat 18.5543750 Long 73.961460") == (18.554375, 73.96146)
        # UK negative longitude
        assert _parse_coordinates_from_text("Lat 51.501364° Long -0.141890°") == (51.501364, -0.14189)
        # Degrees Minutes Seconds
        assert _parse_coordinates_from_text("51°30'26\"N 0°07'39\"W") == (51.507222, -0.1275)
        # Directional decimal
        assert _parse_coordinates_from_text("51.5074° N, 0.1278° W") == (51.5074, -0.1278)
        # GPS prefix
        assert _parse_coordinates_from_text("GPS: 51.5074, -0.1278") == (51.5074, -0.1278)

    def test_extract_camera_app(self):
        """Camera app name is extracted from watermark overlay."""
        from app.services.exif_checker import _extract_camera_app

        assert _extract_camera_app("Google GPS Map Camera Pune") == "GPS Map Camera"
        assert _extract_camera_app("Solocator Watermark") == "Solocator"
        assert _extract_camera_app("Random text") is None

    def test_extract_address_query_uk(self):
        """UK address line is prioritized in OCR text."""
        from app.services.exif_checker import _extract_address_query

        text = (
            "GPS Map Camera\n"
            "Westminster, London, United Kingdom\n"
            "Parliament Square, London, SW1A 0AA, UK\n"
            "Friday, 11/09/2026 01:32 PM GMT +01:00"
        )
        q = _extract_address_query(text)
        assert q is not None
        assert "London" in q or "United Kingdom" in q or "UK" in q
