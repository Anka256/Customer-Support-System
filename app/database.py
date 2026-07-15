from collections.abc import AsyncGenerator, Generator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


def _to_asyncpg_url(url: str) -> str:
    """Normalize a postgres:// or postgresql:// URL to the asyncpg driver (used by FastAPI's
    async read routes)."""
    if url.startswith("postgresql+asyncpg://"):
        return url
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url


def _to_psycopg2_url(url: str) -> str:
    """Normalize to the sync psycopg2 driver. Used by the LangGraph pipeline, whose nodes
    call the synchronous OpenAI SDK and are simplest kept fully synchronous end to end —
    the FastAPI route offloads the whole graph run to a thread instead of mixing sync LLM
    calls with an async DB session."""
    if url.startswith("postgresql+psycopg2://"):
        return url
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg2://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url


settings = get_settings()

engine = create_async_engine(_to_asyncpg_url(settings.database_url), pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)

sync_engine = create_engine(_to_psycopg2_url(settings.database_url), pool_pre_ping=True)
SyncSessionLocal = sessionmaker(bind=sync_engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — yields a request-scoped async session for read routes."""
    async with AsyncSessionLocal() as session:
        yield session


@contextmanager
def sync_session_scope() -> Generator[Session, None, None]:
    """Context-managed sync session for use inside the LangGraph pipeline."""
    session = SyncSessionLocal()
    try:
        yield session
    finally:
        session.close()
