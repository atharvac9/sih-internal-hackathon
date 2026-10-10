"""
Application configuration via Pydantic Settings.
All secrets / deployment-specific values come from environment variables.
"""

from datetime import datetime, timedelta, timezone
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    """
    Central configuration. Every field can be overridden by an environment variable
    of the same name (case-insensitive).
    """

    # ── App ──────────────────────────────────────────────────────────────────
    app_name: str = "Clean Water Initiative"
    debug: bool = False
    api_prefix: str = "/api"
    demo_mode: bool = False  # If false, failed GEE calls return 503; if true, simulated data is allowed

    # Allowed frontend origins for CORS — comma-separated in env var
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:8000,http://127.0.0.1:8000"

    # ── Supabase ─────────────────────────────────────────────────────────────
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    database_url: str = ""  # Postgres connection string (Supabase pooler)

    # ── Google Earth Engine ──────────────────────────────────────────────────
    # JSON string of the GEE service account key (entire file contents)
    gee_service_account_key: str = ""
    gee_project_id: str = ""
    gee_service_account_email: str = ""

    # Sentinel-2 collection
    gee_collection: str = "COPERNICUS/S2_SR_HARMONIZED"
    gee_cloud_cover_max: int = 20  # max cloud cover percentage

    # Spatial defaults (overridable per-request)
    default_buffer_radius_m: int = 250  # 250m for ad-hoc, 500m for seeded sites
    gee_scale_m: int = 10  # Sentinel-2 native resolution

    # Sentinel-2 band names
    band_blue: str = "B2"
    band_green: str = "B3"
    band_red: str = "B4"
    band_red_edge: str = "B5"
    band_nir: str = "B8"
    band_swir1: str = "B11"

    # ── CLIP Classifier ──────────────────────────────────────────────────────
    clip_model_name: str = "ViT-B-32"
    clip_pretrained: str = "openai"

    # Zero-shot prompts (engineered for field-level watershed photos)
    clip_labels: list[str] = [
        "a photograph of a check dam built across a stream or river for water conservation",
        "a photograph of a farm pond or dugout pond used for irrigation and water harvesting",
        "a photograph of a tree plantation or afforestation area with rows of planted trees",
        "a photograph of degraded barren land with soil erosion and no vegetation",
        "a photograph of a water body such as a lake reservoir or large pond",
        "a photograph of an urban built-up area, college campus, sports ground, building, or road",
    ]
    class_names: list[str] = [
        "check_dam",
        "farm_pond",
        "plantation",
        "degraded_land",
        "water_body",
        "urban_built_up",
    ]

    # ── Cross-Validation Rules ───────────────────────────────────────────────
    # Kept from original — ecologically sound thresholds
    validation_rules: dict = {
        "check_dam": {
            "ndvi_trend": "stable_or_increase",
            "ndwi_trend": "increase",
            "ndvi_min": -0.05,
            "ndwi_min": 0.0,
        },
        "farm_pond": {
            "ndvi_trend": "stable",
            "ndwi_trend": "increase",
            "ndvi_min": -0.10,
            "ndwi_min": 0.0,
        },
        "plantation": {
            "ndvi_trend": "increase",
            "ndwi_trend": "stable",
            "ndvi_min": 0.05,
            "ndwi_min": -0.15,
        },
        "water_body": {
            "ndvi_trend": "stable_or_decrease",
            "ndwi_trend": "high",
            "ndvi_min": -0.20,
            "ndwi_min": -0.05,
        },
        "degraded_land": {
            "ndvi_trend": "low",
            "ndwi_trend": "low",
            "ndvi_min": -0.30,
            "ndwi_min": -0.30,
        },
        "urban_built_up": {
            "ndvi_trend": "low",
            "ndwi_trend": "low",
            "ndvi_min": -0.30,
            "ndwi_min": -0.30,
        },
    }

    # ── Health Score ─────────────────────────────────────────────────────────
    # Surface-type-aware scoring is now in health_score.py.
    # These legacy fields are kept for backward compatibility with old tests.
    health_weight_ndvi: float = 0.30
    health_weight_ndwi: float = 0.30
    health_weight_agreement: float = 0.25
    health_weight_confidence: float = 0.15
    index_delta_min: float = -0.3
    index_delta_max: float = 0.3

    # ── Cloud masking ───────────────────────────────────────────────────────
    cloud_score_threshold: float = 0.6  # cs_cdf >= this → clear pixel
    low_data_threshold: float = 0.30    # valid_fraction < this → low_data flag

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    # ── Computed Properties ──────────────────────────────────────────────────

    @property
    def cors_origin_list(self) -> list[str]:
        """Parse comma-separated CORS origins."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def bands_rgb(self) -> list[str]:
        return [self.band_red, self.band_green, self.band_blue]

    @property
    def bands_analysis(self) -> list[str]:
        return [self.band_blue, self.band_green, self.band_red, self.band_nir]

    @property
    def bands_all(self) -> list[str]:
        """All bands needed for NDVI + MNDWI + NDBI + water-quality proxies."""
        return [
            self.band_blue, self.band_green, self.band_red,
            self.band_red_edge, self.band_nir, self.band_swir1,
        ]

    @property
    def t_now_end(self) -> str:
        """Current date as ISO string."""
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    @property
    def t_now_start(self) -> str:
        """90 days before today as ISO string."""
        return (datetime.now(timezone.utc) - timedelta(days=90)).strftime("%Y-%m-%d")

    @property
    def gee_configured(self) -> bool:
        """True if GEE credentials are present."""
        return bool(self.gee_service_account_key and self.gee_project_id)


# Singleton — import this everywhere
settings = Settings()
