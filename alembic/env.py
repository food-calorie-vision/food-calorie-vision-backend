from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.core.config import get_settings
from app.db import base  # noqa: F401 - ensures models are registered
from app.db import models  # noqa: F401 - import all models for Alembic

# Interpret the config file for Python logging.
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = base.Base.metadata
settings = get_settings()
config.set_main_option("sqlalchemy.url", str(settings.database_url))


def include_object(object, name, type_, reflected, compare_to):
    """
    Alembic이 무시할 테이블 설정
    - food_nutrients: 절대 수정 금지
    - ERDCloud 테이블들: 직접 SQL로 생성
    - users: Alembic으로 관리 (유일하게 Alembic이 관리하는 테이블)
    """
    # 절대 수정 금지 테이블
    if type_ == "table" and name == "food_nutrients":
        return False
    
    # ERDCloud 스키마 테이블들 (직접 SQL로 생성할 예정)
    erdcloud_tables = [
        "Food",
        "Nutrient", 
        "UserFoodHistory",
        "health_score",
        "HealthReport",
        "UserPreferences",
        "disease_allergy_profile"
    ]
    if type_ == "table" and name in erdcloud_tables:
        return False
    
    # users 테이블만 Alembic으로 관리
    return True


def _run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = str(settings.database_url)
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,  # 특정 테이블 무시
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_object=include_object,  # 특정 테이블 무시
    )

    with context.begin_transaction():
        context.run_migrations()


async def _run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable: AsyncEngine = create_async_engine(
        str(settings.database_url),
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    _run_migrations_offline()
else:
    asyncio.run(_run_migrations_online())
