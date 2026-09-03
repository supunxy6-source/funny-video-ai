"""Scene model — Individual scenes within a video script."""

from sqlalchemy import String, Text, Integer, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Scene(TimestampMixin, Base):
    __tablename__ = "scenes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    script_id: Mapped[int] = mapped_column(ForeignKey("scripts.id", ondelete="CASCADE"), nullable=False, index=True)
    order: Mapped[int] = mapped_column(Integer, nullable=False)
    scene_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="narration"
    )  # hook, intro, narration, facts, context, impact, conclusion, cta
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    text: Mapped[str] = mapped_column(Text, nullable=False)  # Narration text for this scene
    visual_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)  # Prompt for image/video generation
    visual_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="image"
    )  # image, video, map, chart, animation, stock
    image_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    video_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    audio_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    duration: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)  # seconds
    word_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    script = relationship("Script", back_populates="scenes")

    def __repr__(self) -> str:
        return f"<Scene(id={self.id}, script_id={self.script_id}, order={self.order}, type='{self.scene_type}')>"
