"""Upload model — YouTube and Facebook upload records and metadata."""

from datetime import datetime

from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Upload(TimestampMixin, Base):
    __tablename__ = "uploads"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("videos.id"), nullable=False, index=True)
    youtube_video_id: Mapped[str | None] = mapped_column(String(50), nullable=True, unique=True)
    facebook_video_id: Mapped[str | None] = mapped_column(String(50), nullable=True, unique=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False)  # YouTube 100 char limit
    description: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[str] = mapped_column(Text, nullable=False, default="[]")  # JSON array
    hashtags: Mapped[str | None] = mapped_column(Text, nullable=True)
    chapters: Mapped[str | None] = mapped_column(Text, nullable=True)  # Formatted chapter timestamps
    pinned_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    category_id: Mapped[str] = mapped_column(String(10), default="25", nullable=False)
    privacy_status: Mapped[str] = mapped_column(
        String(20), default="private", nullable=False
    )  # private, unlisted, public
    playlist_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="pending", index=True
    )  # pending, uploading, processing, published, failed, scheduled
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    video = relationship("Video", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Upload(id={self.id}, yt_id='{self.youtube_video_id}', fb_id='{self.facebook_video_id}', status='{self.status}')>"

