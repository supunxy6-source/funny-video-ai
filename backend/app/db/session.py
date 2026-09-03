"""
AI News Studio — Database Session

Async session factory and FastAPI dependency for database access.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.base import get_engine

_session_factory = None

def get_session_factory():
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    return _session_factory


def reset_session_factory():
    """Reset the cached session factory (call after engine disposal)."""
    global _session_factory
    _session_factory = None

# For backward compatibility where it's used as a factory (e.g. `async with async_session_factory() as db:`)
class _SessionFactoryProxy:
    def __call__(self, *args, **kwargs):
        return get_session_factory()(*args, **kwargs)

async_session_factory = _SessionFactoryProxy()

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async database session."""
    async with get_session_factory()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
