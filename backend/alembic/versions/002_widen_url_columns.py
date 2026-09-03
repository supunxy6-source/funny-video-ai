"""
Widen URL and headline columns to prevent truncation errors.

Handles case where DB was created before model was updated to String(1000).

Revision ID: 002_widen_url_columns
Create Date: 2026-08-15
"""

from alembic import op
import sqlalchemy as sa

revision = "002_widen_url_columns"
down_revision = "001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Widen news_articles columns
    op.alter_column("news_articles", "url",
                    type_=sa.Text(), existing_nullable=False)
    op.alter_column("news_articles", "image_url",
                    type_=sa.Text(), existing_nullable=True)
    op.alter_column("news_articles", "headline",
                    type_=sa.String(500), existing_nullable=False)
    op.alter_column("news_articles", "author",
                    type_=sa.String(500), existing_nullable=True)

    # Widen sources columns
    op.alter_column("sources", "url",
                    type_=sa.Text(), existing_nullable=False)
    op.alter_column("sources", "rss_url",
                    type_=sa.Text(), existing_nullable=True)
    op.alter_column("sources", "logo_url",
                    type_=sa.Text(), existing_nullable=True)

    # Widen scenes columns
    op.alter_column("scenes", "image_url",
                    type_=sa.Text(), existing_nullable=True)
    op.alter_column("scenes", "video_url",
                    type_=sa.Text(), existing_nullable=True)
    op.alter_column("scenes", "audio_url",
                    type_=sa.Text(), existing_nullable=True)


def downgrade() -> None:
    # Revert news_articles
    op.alter_column("news_articles", "url",
                    type_=sa.String(1000), existing_nullable=False)
    op.alter_column("news_articles", "image_url",
                    type_=sa.String(1000), existing_nullable=True)
    op.alter_column("news_articles", "headline",
                    type_=sa.String(500), existing_nullable=False)
    op.alter_column("news_articles", "author",
                    type_=sa.String(255), existing_nullable=True)

    # Revert sources
    op.alter_column("sources", "url",
                    type_=sa.String(500), existing_nullable=False)
    op.alter_column("sources", "rss_url",
                    type_=sa.String(500), existing_nullable=True)
    op.alter_column("sources", "logo_url",
                    type_=sa.String(500), existing_nullable=True)

    # Revert scenes
    op.alter_column("scenes", "image_url",
                    type_=sa.String(1000), existing_nullable=True)
    op.alter_column("scenes", "video_url",
                    type_=sa.String(1000), existing_nullable=True)
    op.alter_column("scenes", "audio_url",
                    type_=sa.String(1000), existing_nullable=True)
