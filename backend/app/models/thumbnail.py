"""Thumbnail model — Generated video thumbnails with predicted CTR."""

from sqlalchemy import String, Float, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Thumbnail(TimestampMixin, Base):
    __tablename__ = "thumbnails"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    prompt: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    width: Mapped[int] = mapped_column(default=1280)
    height: Mapped[int] = mapped_column(default=720)
    predicted_ctr: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_selected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    video = relationship("Video", back_populates="thumbnails")

    def __repr__(self) -> str:
        return f"<Thumbnail(id={self.id}, video_id={self.video_id}, ctr={self.predicted_ctr}, selected={self.is_selected})>"
