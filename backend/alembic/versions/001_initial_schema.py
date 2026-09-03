"""
Initial database schema — Creates all tables.

Revision ID: 001
Create Date: 2026-08-07
"""

from alembic import op
import sqlalchemy as sa

revision = "001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Users ──────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False, server_default=""),
        sa.Column("role", sa.String(50), nullable=False, server_default="admin"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    # ── Sources ────────────────────────────────────────
    op.create_table(
        "sources",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("url", sa.String(500), nullable=False),
        sa.Column("rss_url", sa.String(500), nullable=True),
        sa.Column("trust_score", sa.Float(), nullable=False, server_default=sa.text("0.8")),
        sa.Column("category", sa.String(100), nullable=False, server_default="general"),
        sa.Column("country", sa.String(10), nullable=False, server_default="US"),
        sa.Column("language", sa.String(10), nullable=False, server_default="en"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("logo_url", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    # ── News Articles ──────────────────────────────────
    op.create_table(
        "news_articles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("headline", sa.String(500), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("url", sa.String(1000), nullable=False),
        sa.Column("image_url", sa.String(1000), nullable=True),
        sa.Column("author", sa.String(255), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("category", sa.String(100), nullable=False, server_default="general"),
        sa.Column("cluster_id", sa.Integer(), nullable=True),
        sa.Column("credibility_score", sa.Float(), nullable=False, server_default=sa.text("0.0")),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("keywords", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("url"),
    )
    op.create_index("ix_news_articles_source_id", "news_articles", ["source_id"])
    op.create_index("ix_news_articles_url", "news_articles", ["url"])
    op.create_index("ix_news_articles_published_at", "news_articles", ["published_at"])
    op.create_index("ix_news_articles_category", "news_articles", ["category"])
    op.create_index("ix_news_articles_cluster_id", "news_articles", ["cluster_id"])

    # ── Scripts ────────────────────────────────────────
    op.create_table(
        "scripts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("topic_summary", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_json", sa.Text(), nullable=True),
        sa.Column("article_ids", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("word_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("duration_estimate", sa.Float(), nullable=False, server_default=sa.text("0.0")),
        sa.Column("llm_provider", sa.String(50), nullable=False, server_default="openai"),
        sa.Column("llm_model", sa.String(100), nullable=False, server_default="gpt-4o"),
        sa.Column("status", sa.String(50), nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_scripts_status", "scripts", ["status"])

    # ── Scenes ─────────────────────────────────────────
    op.create_table(
        "scenes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("script_id", sa.Integer(), sa.ForeignKey("scripts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.Column("scene_type", sa.String(50), nullable=False, server_default="narration"),
        sa.Column("title", sa.String(255), nullable=False, server_default=""),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("visual_prompt", sa.Text(), nullable=True),
        sa.Column("visual_type", sa.String(50), nullable=False, server_default="image"),
        sa.Column("image_url", sa.String(1000), nullable=True),
        sa.Column("video_url", sa.String(1000), nullable=True),
        sa.Column("audio_url", sa.String(1000), nullable=True),
        sa.Column("duration", sa.Float(), nullable=False, server_default=sa.text("0.0")),
        sa.Column("word_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_scenes_script_id", "scenes", ["script_id"])

    # ── Videos ─────────────────────────────────────────
    op.create_table(
        "videos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("script_id", sa.Integer(), sa.ForeignKey("scripts.id"), nullable=False),
        sa.Column("file_path", sa.String(1000), nullable=False),
        sa.Column("subtitle_path", sa.String(1000), nullable=True),
        sa.Column("duration", sa.Float(), nullable=False, server_default=sa.text("0.0")),
        sa.Column("resolution", sa.String(20), nullable=False, server_default="1920x1080"),
        sa.Column("fps", sa.Integer(), nullable=False, server_default=sa.text("30")),
        sa.Column("file_size", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("codec", sa.String(20), nullable=False, server_default="h264"),
        sa.Column("status", sa.String(50), nullable=False, server_default="rendering"),
        sa.Column("ffmpeg_log", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_videos_script_id", "videos", ["script_id"])
    op.create_index("ix_videos_status", "videos", ["status"])

    # ── Thumbnails ─────────────────────────────────────
    op.create_table(
        "thumbnails",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("video_id", sa.Integer(), sa.ForeignKey("videos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("file_path", sa.String(1000), nullable=False),
        sa.Column("prompt", sa.String(1000), nullable=True),
        sa.Column("width", sa.Integer(), server_default=sa.text("1280")),
        sa.Column("height", sa.Integer(), server_default=sa.text("720")),
        sa.Column("predicted_ctr", sa.Float(), nullable=False, server_default=sa.text("0.0")),
        sa.Column("is_selected", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_thumbnails_video_id", "thumbnails", ["video_id"])

    # ── Uploads ────────────────────────────────────────
    op.create_table(
        "uploads",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("video_id", sa.Integer(), sa.ForeignKey("videos.id"), nullable=False),
        sa.Column("youtube_video_id", sa.String(50), nullable=True),
        sa.Column("title", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("tags", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("hashtags", sa.Text(), nullable=True),
        sa.Column("chapters", sa.Text(), nullable=True),
        sa.Column("pinned_comment", sa.Text(), nullable=True),
        sa.Column("category_id", sa.String(10), nullable=False, server_default="25"),
        sa.Column("privacy_status", sa.String(20), nullable=False, server_default="private"),
        sa.Column("playlist_id", sa.String(100), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("youtube_video_id"),
    )
    op.create_index("ix_uploads_video_id", "uploads", ["video_id"])
    op.create_index("ix_uploads_status", "uploads", ["status"])

    # ── Jobs ───────────────────────────────────────────
    op.create_table(
        "jobs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("pipeline_run_id", sa.String(100), nullable=False),
        sa.Column("step_name", sa.String(50), nullable=False),
        sa.Column("step_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("celery_task_id", sa.String(255), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("max_retries", sa.Integer(), nullable=False, server_default=sa.text("3")),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_jobs_pipeline_run_id", "jobs", ["pipeline_run_id"])
    op.create_index("ix_jobs_step_name", "jobs", ["step_name"])
    op.create_index("ix_jobs_status", "jobs", ["status"])

    # ── Logs ───────────────────────────────────────────
    op.create_table(
        "logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("job_id", sa.Integer(), sa.ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("pipeline_run_id", sa.String(100), nullable=True),
        sa.Column("level", sa.String(20), nullable=False, server_default="INFO"),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("module", sa.String(100), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_logs_job_id", "logs", ["job_id"])
    op.create_index("ix_logs_pipeline_run_id", "logs", ["pipeline_run_id"])
    op.create_index("ix_logs_level", "logs", ["level"])
    op.create_index("ix_logs_timestamp", "logs", ["timestamp"])

    # ── Seed default sources ───────────────────────────
    op.execute("""
        INSERT INTO sources (name, url, rss_url, trust_score, category) VALUES
        ('Reuters', 'https://www.reuters.com', 'https://www.reuters.com/rssfeed/topNews', 0.95, 'general'),
        ('Associated Press', 'https://apnews.com', 'https://rsshub.app/apnews/topics/apf-topnews', 0.95, 'general'),
        ('BBC News', 'https://www.bbc.com/news', 'http://feeds.bbci.co.uk/news/rss.xml', 0.92, 'general'),
        ('CNN', 'https://www.cnn.com', 'http://rss.cnn.com/rss/cnn_topstories.rss', 0.85, 'general'),
        ('Al Jazeera', 'https://www.aljazeera.com', 'https://www.aljazeera.com/xml/rss/all.xml', 0.88, 'general'),
        ('The Guardian', 'https://www.theguardian.com', 'https://www.theguardian.com/world/rss', 0.90, 'general'),
        ('NPR', 'https://www.npr.org', 'https://feeds.npr.org/1001/rss.xml', 0.90, 'general'),
        ('TechCrunch', 'https://techcrunch.com', 'https://techcrunch.com/feed/', 0.82, 'technology'),
        ('Bloomberg', 'https://www.bloomberg.com', 'https://feeds.bloomberg.com/markets/news.rss', 0.90, 'business'),
        ('NASA', 'https://www.nasa.gov', 'https://www.nasa.gov/rss/dyn/breaking_news.rss', 0.98, 'science'),
        ('WHO', 'https://www.who.int', 'https://www.who.int/rss-feeds/news-english.xml', 0.95, 'health'),
        ('Google News', 'https://news.google.com', 'https://news.google.com/rss', 0.75, 'general')
    """)

    # ── Seed default admin user (password: changeme) ───
    op.execute("""
        INSERT INTO users (email, password_hash, full_name, role)
        VALUES ('admin@ainewsstudio.com', '$2b$12$RTrJYUWdD7tECF5DWJqqQO8pn.SubZDkzLKwNZPGgRwS4x.PYvHgC', 'Admin', 'admin')
    """)


def downgrade() -> None:
    op.drop_table("logs")
    op.drop_table("jobs")
    op.drop_table("uploads")
    op.drop_table("thumbnails")
    op.drop_table("videos")
    op.drop_table("scenes")
    op.drop_table("scripts")
    op.drop_table("news_articles")
    op.drop_table("sources")
    op.drop_table("users")
