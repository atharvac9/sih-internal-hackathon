"""
Tests for Vision Classifier (OpenCLIP / Deep CNN).
Verifies that classification produces positive confidence scores (never 0.0%),
and that failures return an explicit error state.
"""

import io
import pytest
from PIL import Image
from app.services.classifier import classify_image


def _generate_test_image(color=(34, 139, 34), size=(128, 128)) -> bytes:
    """Generate in-memory test JPEG image."""
    img = Image.new("RGB", size, color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


class TestClassifierInference:
    """Tests for real model inference on known images."""

    def test_known_image_classification_positive_confidence(self):
        """Top prediction for a valid photo must always produce positive confidence (never 0.0%)."""
        # Known green canopy / vegetation image
        image_bytes = _generate_test_image(color=(34, 139, 34))
        result = classify_image(image_bytes)

        assert "predicted_class" in result
        assert isinstance(result["predicted_class"], str)
        assert len(result["predicted_class"]) > 0

        # Confidence must be strictly positive and normalized (0 < c <= 1.0)
        assert result["confidence"] > 0.0, f"Confidence was {result['confidence']}, expected > 0.0"
        assert result["confidence"] <= 1.0

        # All scores distribution must be valid
        assert "all_scores" in result
        scores = result["all_scores"]
        assert len(scores) >= 5
        assert result["predicted_class"] in scores
        assert scores[result["predicted_class"]] == result["confidence"]
        assert abs(sum(scores.values()) - 1.0) < 0.05

    def test_water_image_classification_positive_confidence(self):
        """Known blue water body image must classify with positive confidence."""
        image_bytes = _generate_test_image(color=(15, 82, 186))
        result = classify_image(image_bytes)

        assert result["confidence"] > 0.0
        assert result["predicted_class"] in ("water_body", "farm_pond", "check_dam", "urban_built_up")

    def test_empty_bytes_raises_explicit_error(self):
        """Empty or invalid image data must raise ValueError, not return 0.0% confidence."""
        with pytest.raises(ValueError):
            classify_image(b"")

    def test_corrupted_bytes_raises_explicit_error(self):
        """Corrupted image bytes must raise ValueError."""
        with pytest.raises(ValueError):
            classify_image(b"not_a_valid_image_header_123456789")
