"""Source model — Trusted news sources and their RSS feeds."""

from sqlalchemy import String, Float, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Source(TimestampMixin, Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    rss_url: Mapped[str] = mapped_column(String(500), nullable=True)
    trust_score: Mapped[float] = mapped_column(Float, default=0.8, nullable=False)
    category: Mapped[str] = mapped_column(String(100), default="general", nullable=False)
    country: Mapped[str] = mapped_column(String(10), default="US", nullable=False)
    language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    def __repr__(self) -> str:
        return f"<Source(id={self.id}, name='{self.name}', trust={self.trust_score})>"
