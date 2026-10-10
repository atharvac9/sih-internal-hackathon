"""
Async SQLAlchemy engine + session factory for Supabase Postgres.
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""
    pass


def _get_async_url(url: str) -> str:
    """Convert a postgres:// or postgresql:// URL to use asyncpg driver."""
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url


# Engine & session factory — created once at import time
# Falls back to project root SQLite if no DATABASE_URL is set
from pathlib import Path
_ROOT_DIR = Path(__file__).resolve().parent.parent.parent
_DEFAULT_DB_PATH = (_ROOT_DIR / "dev.db").as_posix()
_db_url = settings.database_url or f"sqlite+aiosqlite:///{_DEFAULT_DB_PATH}"
_async_url = _get_async_url(_db_url) if "postgresql" in _db_url or "postgres" in _db_url else _db_url

engine = create_async_engine(
    _async_url,
    echo=settings.debug,
    pool_pre_ping=True,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    """FastAPI dependency — yields an async session, auto-closes."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_tables():
    """Create all tables (dev/init only — use Alembic for production migrations)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        def migrate_schema(sync_conn):
            from sqlalchemy import inspect, text
            inspector = inspect(sync_conn)
            if "analysis_results" in inspector.get_table_names():
                cols = [c["name"] for c in inspector.get_columns("analysis_results")]
                if "schema_version" not in cols:
                    sync_conn.execute(text("ALTER TABLE analysis_results ADD COLUMN schema_version INTEGER DEFAULT 1"))
                if "mndwi_t0" not in cols:
                    sync_conn.execute(text("ALTER TABLE analysis_results ADD COLUMN mndwi_t0 FLOAT"))
                if "mndwi_tnow" not in cols:
                    sync_conn.execute(text("ALTER TABLE analysis_results ADD COLUMN mndwi_tnow FLOAT"))

        await conn.run_sync(migrate_schema)
