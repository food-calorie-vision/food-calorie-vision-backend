from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a database session for FastAPI dependency injection."""
    async for session in get_session():
        yield session

