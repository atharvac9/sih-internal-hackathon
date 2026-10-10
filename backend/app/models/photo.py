"""
Photo ORM model — uploaded field photos stored in Supabase Storage.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Photo(Base):
    __tablename__ = "photos"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    site_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Original filename from the upload
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)

    # Path in Supabase Storage (bucket/key)
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)

    # Public URL for the stored image
    public_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    # MIME type
    content_type: Mapped[str] = mapped_column(String(50), default="image/jpeg")

    # File size in bytes
    file_size_bytes: Mapped[int | None] = mapped_column(nullable=True)

    # ── EXIF Metadata (extracted on upload) ──────────────────────────────────
    has_exif: Mapped[bool] = mapped_column(Boolean, default=False)
    has_gps: Mapped[bool] = mapped_column(Boolean, default=False)
    has_camera_model: Mapped[bool] = mapped_column(Boolean, default=False)
    has_timestamp: Mapped[bool] = mapped_column(Boolean, default=False)

    exif_gps_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    exif_gps_lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    exif_camera_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    exif_datetime: Mapped[str | None] = mapped_column(String(30), nullable=True)
    exif_warnings_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array

    # ── CLIP Classification (runs after upload) ──────────────────────────────
    classified: Mapped[bool] = mapped_column(Boolean, default=False)
    predicted_class: Mapped[str | None] = mapped_column(String(50), nullable=True)
    classification_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    classification_scores_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Who uploaded
    uploaded_by: Mapped[str | None] = mapped_column(String(36), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationship
    site: Mapped["Site"] = relationship(back_populates="photos")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Photo {self.id[:8]} site={self.site_id[:8]} class={self.predicted_class}>"
