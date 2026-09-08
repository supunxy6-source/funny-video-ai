"""
Add tiktok_video_id column to uploads table.

Revision ID: 002_add_tiktok_video_id
Revises: 001_initial_schema
Create Date: 2026-09-08
"""

from alembic import op
import sqlalchemy as sa

revision = "002_add_tiktok_video_id"
down_revision = "001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "uploads",
        sa.Column("tiktok_video_id", sa.String(100), nullable=True, unique=True),
    )


def downgrade() -> None:
    op.drop_column("uploads", "tiktok_video_id")
