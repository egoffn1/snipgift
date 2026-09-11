import os

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from config import settings
from db.models import Base
from utils.logger import get_logger

logger = get_logger("db.session")


def _build_database_url(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("postgres://"):
        raw = raw.replace("postgres://", "postgresql+asyncpg://", 1)
    elif raw.startswith("postgresql://"):
        raw = raw.replace("postgresql://", "postgresql+asyncpg://", 1)
    return raw


def _is_postgres(url: str) -> bool:
    return "postgresql" in url or "postgres" in url


def create_engine_and_sessionmaker():
    raw = settings.DATABASE_URL
    if raw:
        db_url = _build_database_url(raw)
        connect_args = {}
        if _is_postgres(db_url):
            connect_args = {
                "server_settings": {"statement_timeout": "30000"},
            }
        engine = create_async_engine(db_url, pool_pre_ping=True, connect_args=connect_args)
        logger.info("Using PostgreSQL database (Neon/Supabase/RDS)")
    else:
        sqlite_path = os.getenv("LOCAL_SQLITE_PATH", "/tmp/snipgift.db")
        db_url = f"sqlite+aiosqlite:///{sqlite_path}"
        engine = create_async_engine(db_url, connect_args={"check_same_thread": False})
        logger.warning(
            "DATABASE_URL not set — using ephemeral SQLite at %s. "
            "Data will be lost on restart. Use Neon.tech for production.",
            sqlite_path,
        )
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    return engine, session_factory


engine, session_factory = create_engine_and_sessionmaker()


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database schema is ready")


async def get_session() -> AsyncSession:
    async with session_factory() as session:
        yield session
