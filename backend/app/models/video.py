"""Video model — Final rendered video files."""

from sqlalchemy import String, Text, Integer, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Video(TimestampMixin, Base):
    __tablename__ = "videos"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    script_id: Mapped[int] = mapped_column(ForeignKey("scripts.id"), nullable=False, index=True)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    subtitle_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    duration: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)  # seconds
    resolution: Mapped[str] = mapped_column(String(20), default="1080x1920", nullable=False)
    fps: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # bytes
    codec: Mapped[str] = mapped_column(String(20), default="h264", nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="rendering", index=True
    )  # rendering, ready, uploaded, failed
    ffmpeg_log: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    script = relationship("Script", lazy="selectin")
    thumbnails = relationship("Thumbnail", back_populates="video", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Video(id={self.id}, status='{self.status}', duration={self.duration}s)>"
