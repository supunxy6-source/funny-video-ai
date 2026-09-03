"""Script model — AI-generated video scripts."""

from sqlalchemy import String, Text, Integer, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Script(TimestampMixin, Base):
    __tablename__ = "scripts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    topic_summary: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)  # Full script text
    content_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # Structured scenes as JSON
    article_ids: Mapped[str] = mapped_column(Text, nullable=False, default="[]")  # JSON array of article IDs
    word_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duration_estimate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)  # minutes
    llm_provider: Mapped[str] = mapped_column(String(50), nullable=False, default="openai")
    llm_model: Mapped[str] = mapped_column(String(100), nullable=False, default="gpt-4o")
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="draft", index=True
    )  # draft, approved, used, rejected

    # Relationships
    scenes = relationship("Scene", back_populates="script", lazy="selectin", order_by="Scene.order")

    def __repr__(self) -> str:
        return f"<Script(id={self.id}, title='{self.title[:50]}...', status='{self.status}')>"
