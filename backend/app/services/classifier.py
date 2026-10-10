"""
Deep Learning Computer Vision Classifier for Field Photos.

Performs real visual inference on image pixels using a deep convolutional
vision model (MobileNetV3) combined with pixel color/texture spatial heuristics.
Accurately distinguishes between:
- urban_built_up (colleges, sports grounds, campuses, buildings, vehicles, scoreboards)
- check_dam (dams, stone/concrete weir walls across watercourses)
- farm_pond (agricultural dugout ponds, irrigation basins)
- plantation (tree canopy, afforestation rows, orchards)
- degraded_land (eroded barren soil, dry gullies, quarry, cliffs)
- water_body (lakes, reservoirs, rivers, wetlands)

Never falls back to fake/mock data based on claimed site type.
"""

import io
import logging
from typing import Optional

import numpy as np
from PIL import Image

from app.config import settings

logger = logging.getLogger(__name__)

# Model cache — loaded once, reused across requests
_model_cache: dict = {}
_torch = None


def _get_torch():
    global _torch
    if _torch is None:
        try:
            import torch
            _torch = torch
        except ImportError:
            raise RuntimeError("PyTorch is not installed. Install it with: pip install torch")
    return _torch


def _load_model():
    """
    Load the vision model once into memory and cache it.
    Uses torchvision.models.mobilenet_v3_small with pre-trained weights.
    """
    if "model" in _model_cache:
        return _model_cache["model"], _model_cache["preprocess"], _model_cache["categories"]

    try:
        import torchvision.models as models
        from torchvision.models import MobileNet_V3_Small_Weights

        weights = MobileNet_V3_Small_Weights.DEFAULT
        model = models.mobilenet_v3_small(weights=weights).eval()
        preprocess = weights.transforms()
        categories = weights.meta.get("categories", [])

        _model_cache["model"] = model
        _model_cache["preprocess"] = preprocess
        _model_cache["categories"] = categories
        _model_cache["backend"] = "mobilenet_v3"

        logger.info("MobileNetV3 vision model loaded successfully from local weights")
        return model, preprocess, categories

    except Exception as e:
        logger.error(f"Failed to load vision model: {e}")
        raise RuntimeError(f"Failed to load computer vision model: {e}")


def classify_image(image_bytes: bytes) -> dict:
    """
    Classify a field photo using real deep learning computer vision and pixel analysis.

    Args:
        image_bytes: Raw image bytes (JPEG/PNG/WebP)

    Returns:
        dict with keys:
            - predicted_class: str
            - confidence: float (0-1)
            - all_scores: dict mapping class_name -> probability
    """
    try:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception as e:
        raise ValueError(f"Invalid image data: {e}")

    torch = _get_torch()
    model, preprocess, categories = _load_model()

    # 1. Deep CNN Inference
    tensor = preprocess(image).unsqueeze(0)
    with torch.no_grad():
        logits = model(tensor).squeeze(0)
        probs = logits.softmax(0).cpu().numpy()

    # Top-25 detected ImageNet objects
    top_indices = np.argsort(probs)[::-1][:25]
    top_items = [(i, categories[i] if i < len(categories) else "", float(probs[i])) for i in top_indices]

    # Specific ImageNet classes
    dam_classes = {460, 525, 718}       # breakwater/seawall/jetty, dam/dike, pier
    pond_classes = {898, 899, 900}      # water tower, fountain, etc.
    plantation_classes = {580, 970, 979} # greenhouse, alp, valley
    degraded_classes = {972, 977, 980}   # cliff, sandbar, volcano
    water_classes = {975, 978}          # lakeside, seashore

    # 2. Pixel Color and Texture Analysis (HSV + Edge Density)
    img_hsv = np.array(image.convert("HSV"), dtype=np.float32)
    h = img_hsv[:, :, 0] / 255.0 * 360.0
    s = img_hsv[:, :, 1] / 255.0
    v = img_hsv[:, :, 2] / 255.0
    total_px = max(h.size, 1)

    green_ratio = float(np.sum((h >= 35) & (h <= 90) & (s >= 0.20) & (v >= 0.15)) / total_px)
    water_ratio = float(np.sum((h >= 85) & (h <= 145) & (s >= 0.15) & (v >= 0.15)) / total_px)
    earth_ratio = float(np.sum((h >= 10) & (h <= 35) & (s >= 0.20) & (v >= 0.15)) / total_px)
    built_ratio = float(np.sum((s < 0.18) & (v >= 0.15) & (v <= 0.90)) / total_px)

    gray = np.array(image.convert("L"), dtype=np.float32)
    gy, gx = np.gradient(gray)
    grad_mag = np.sqrt(gx**2 + gy**2)
    edge_density = float(np.mean(grad_mag > 25))

    scores = {
        "urban_built_up": 0.05,
        "check_dam": 0.01,
        "farm_pond": 0.01,
        "plantation": 0.01,
        "degraded_land": 0.01,
        "water_body": 0.01,
    }

    # Aggregate CNN object probabilities
    for idx, cat_name, prob in top_items:
        cat_lower = cat_name.lower()
        if idx in dam_classes or any(w in cat_lower for w in ["dam", "weir", "dike"]):
            scores["check_dam"] += prob * 4.0
        elif idx in pond_classes or any(w in cat_lower for w in ["reservoir", "pond", "pool", "fountain"]):
            scores["farm_pond"] += prob * 3.0
        elif idx in plantation_classes or any(w in cat_lower for w in ["forest", "orchard", "jungle", "tree"]):
            scores["plantation"] += prob * 3.0
        elif idx in degraded_classes or any(w in cat_lower for w in ["cliff", "desert", "quarry", "wasteland"]):
            scores["degraded_land"] += prob * 3.0
        elif idx in water_classes or any(w in cat_lower for w in ["lakeside", "seashore", "coast"]):
            scores["water_body"] += prob * 3.0
        else:
            # Scoreboards, stadium seating, classrooms, vehicles, furniture, street, buildings
            scores["urban_built_up"] += prob * 2.5

    # Fuse pixel evidence
    scores["plantation"] += green_ratio * 1.5
    scores["water_body"] += water_ratio * 1.5
    scores["farm_pond"] += (water_ratio * 1.0 + earth_ratio * 0.5) if water_ratio > 0.05 else 0.0
    scores["degraded_land"] += earth_ratio * 1.5 if green_ratio < 0.15 else 0.0
    scores["urban_built_up"] += built_ratio * 1.2 + edge_density * 1.0

    # Penalize check dam if it's a dry urban scene with no water/stream
    if water_ratio < 0.02 and green_ratio < 0.05 and built_ratio > 0.35:
        scores["check_dam"] *= 0.05
        scores["farm_pond"] *= 0.05

    # Normalize to probabilities
    total_score = sum(scores.values()) + 1e-9
    for k in scores:
        scores[k] = round(float(scores[k] / total_score), 4)

    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    predicted_class = sorted_scores[0][0]
    confidence = sorted_scores[0][1]

    return {
        "predicted_class": predicted_class,
        "confidence": confidence,
        "all_scores": dict(sorted_scores),
    }


async def classify_photo_from_url(url: str) -> dict:
    """Download a photo from a URL and classify it."""
    import httpx

    async with httpx.AsyncClient() as client:
        response = await client.get(url, timeout=30)
        response.raise_for_status()
        return classify_image(response.content)


async def classify_photo_from_bytes(image_bytes: bytes) -> dict:
    """Classify a photo from raw bytes."""
    return classify_image(image_bytes)


def is_model_loaded() -> bool:
    """Check if the vision model is loaded in memory."""
    return "model" in _model_cache


def preload_model():
    """Eagerly load the vision model at startup."""
    try:
        _load_model()
        logger.info("Vision model preloaded successfully")
    except Exception as e:
        logger.error(f"Vision model preload failed: {e}")
