"""
AnalysisResult ORM model — stores satellite indices, classification,
cross-validation, and health score for a site at a point in time.

Supports two modes:
- FULL (before/after): has both T0 and T_NOW data + delta computations
- SNAPSHOT (current only): has T_NOW data only, no deltas, simplified health score
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

import enum


class AnalysisMode(str, enum.Enum):
    FULL = "full"          # Before/after with known baseline
    SNAPSHOT = "snapshot"   # Current-only for arbitrary points


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    site_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Analysis mode
    mode: Mapped[str] = mapped_column(
        String(10), default=AnalysisMode.SNAPSHOT.value
    )

    # ── Satellite Indices ────────────────────────────────────────────────────
    # T0 (baseline) — only populated in FULL mode
    ndvi_t0: Mapped[float | None] = mapped_column(Float, nullable=True)
    ndwi_t0: Mapped[float | None] = mapped_column(Float, nullable=True)
    t0_start_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    t0_end_date: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # T_NOW (current)
    ndvi_tnow: Mapped[float | None] = mapped_column(Float, nullable=True)
    ndwi_tnow: Mapped[float | None] = mapped_column(Float, nullable=True)
    tnow_start_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    tnow_end_date: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Deltas — only in FULL mode
    delta_ndvi: Mapped[float | None] = mapped_column(Float, nullable=True)
    delta_ndwi: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Data source indicator
    satellite_source: Mapped[str] = mapped_column(String(20), default="gee")

    # ── Photo Classification ─────────────────────────────────────────────────
    predicted_class: Mapped[str | None] = mapped_column(String(50), nullable=True)
    photo_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    classification_scores_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON

    # ── Cross-Validation ─────────────────────────────────────────────────────
    # Only populated if activity_type was provided
    satellite_agreement: Mapped[bool | None] = mapped_column(nullable=True)
    photo_agreement: Mapped[bool | None] = mapped_column(nullable=True)
    overall_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    flags_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array
    validation_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── Health Score ─────────────────────────────────────────────────────────
    health_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    health_grade: Mapped[str | None] = mapped_column(String(2), nullable=True)
    health_components_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON

    # ── Buffer radius used for this analysis ─────────────────────────────────
    buffer_radius_m: Mapped[int] = mapped_column(Integer, default=500)

    # ── Timestamps ───────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationship
    site: Mapped["Site"] = relationship(back_populates="analysis_results")  # noqa: F821

    def __repr__(self) -> str:
        return f"<AnalysisResult {self.id[:8]} mode={self.mode} score={self.health_score}>"
