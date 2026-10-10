"""
Site ORM model — represents a watershed monitoring location.

Sites can be:
- Seeded demo sites (is_seeded_demo=True) with a known baseline date (T0) for
  before/after intervention analysis
- User-created sites via the ad-hoc click-anywhere flow, which default to
  snapshot-only mode unless the user supplies a baseline date
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Site(Base):
    __tablename__ = "sites"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    # Human-readable site code (e.g. "S01") — optional for ad-hoc sites
    site_code: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True)

    lat: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    lon: Mapped[float] = mapped_column(Float, nullable=False, index=True)

    # Activity claimed by the submitter (check_dam, farm_pond, plantation, etc.)
    # NULL for arbitrary-point snapshot queries where user hasn't claimed anything yet
    activity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # The 8 hardcoded showcase sites have this set to True
    is_seeded_demo: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    # Baseline date for before/after analysis.
    # Only meaningful for seeded demos or user sites that explicitly set one.
    baseline_date: Mapped[str | None] = mapped_column(String(10), nullable=True)  # "YYYY-MM-DD"

    # Intervention date — when the activity was performed
    intervention_date: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Buffer radius in meters for satellite queries (default 500m)
    buffer_radius_m: Mapped[int] = mapped_column(Integer, default=500)

    # Who created this site
    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)  # user.id FK

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    analysis_results: Mapped[list["AnalysisResult"]] = relationship(  # noqa: F821
        back_populates="site", cascade="all, delete-orphan"
    )
    photos: Mapped[list["Photo"]] = relationship(  # noqa: F821
        back_populates="site", cascade="all, delete-orphan"
    )

    @property
    def has_baseline(self) -> bool:
        """Whether this site has a known T0 for before/after analysis."""
        return self.baseline_date is not None

    def __repr__(self) -> str:
        code = self.site_code or self.id[:8]
        return f"<Site {code} ({self.lat:.4f}, {self.lon:.4f})>"
