from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

settings = get_settings()

engine: AsyncEngine = create_async_engine(
    str(settings.database_url),
    future=True,
    echo=settings.app_env == "local",
    pool_pre_ping=True,  # 연결 사용 전 유효성 검사
    pool_size=5,  # 연결 풀 크기
    max_overflow=10,  # 최대 추가 연결 수
    pool_recycle=3600,  # 1시간마다 연결 재생성
)

SessionLocal = async_sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    class_=AsyncSession,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a database session for request scope injections."""
    async with SessionLocal() as session:
        yield session

