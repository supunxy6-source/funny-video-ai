"""
Add facebook_video_id column to uploads table.

Revision ID: 003_add_facebook_video_id
Revises: 002_widen_url_columns
Create Date: 2026-08-22
"""

from alembic import op
import sqlalchemy as sa

revision = "003_add_facebook_video_id"
down_revision = "002_widen_url_columns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "uploads",
        sa.Column("facebook_video_id", sa.String(50), nullable=True, unique=True),
    )


def downgrade() -> None:
    op.drop_column("uploads", "facebook_video_id")
