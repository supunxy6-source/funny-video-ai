"""
Add video_format column to scripts table.

Supports dual pipeline: 'shorts' (9:16) and 'regular' (16:9) video production.

Revision ID: 004_add_script_video_format
Revises: 003_add_facebook_video_id
Create Date: 2026-09-17
"""

from alembic import op
import sqlalchemy as sa

revision = "004_add_script_video_format"
down_revision = "003_add_facebook_video_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "scripts",
        sa.Column("video_format", sa.String(20), nullable=False, server_default="shorts"),
    )


def downgrade() -> None:
    op.drop_column("scripts", "video_format")
