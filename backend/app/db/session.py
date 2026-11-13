"""Database session management and engine configuration."""
import logging
from typing import AsyncGenerator, Tuple, Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from app.core.config import settings

logger = logging.getLogger(__name__)

# Configure Async Engine
engine_kwargs = {
    "echo": settings.DEBUG and settings.LOG_LEVEL.upper() == "DEBUG",
    "future": True,
}

# Handle pooling configurations
if "sqlite" not in settings.DATABASE_URL:
    engine_kwargs.update({
        "pool_pre_ping": True,
        "pool_size": 5,
        "max_overflow": 10,
        "connect_args": {"timeout": settings.DATABASE_CONNECT_TIMEOUT_SECONDS}
    })

engine = create_async_engine(
    settings.DATABASE_URL,
    **engine_kwargs
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for providing an async database session per request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_database_connection() -> Tuple[bool, Optional[str]]:
    """Test database connectivity with a lightweight ping."""
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            return True, "Connected successfully"
    except Exception as e:
        logger.warning(f"Database health check failed: {e}")
        return False, str(e)
