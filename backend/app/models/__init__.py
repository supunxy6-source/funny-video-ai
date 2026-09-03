"""
AI News Studio — Models Package

Import all models here so Alembic and the application can discover them.
"""

from app.models.user import User
from app.models.source import Source
from app.models.article import NewsArticle
from app.models.script import Script
from app.models.scene import Scene
from app.models.video import Video
from app.models.thumbnail import Thumbnail
from app.models.upload import Upload
from app.models.job import Job
from app.models.log import Log

__all__ = [
    "User",
    "Source",
    "NewsArticle",
    "Script",
    "Scene",
    "Video",
    "Thumbnail",
    "Upload",
    "Job",
    "Log",
]
