"""Async PostgreSQL/PostGIS connection and migration management."""

from __future__ import annotations

from pathlib import Path

import asyncpg
from asyncpg import Pool
from loguru import logger

from app.config import get_settings


class GeoDatabase:
    """Connection pool for geographic data stored in PostgreSQL/PostGIS."""

    _pool: Pool | None = None

    @classmethod
    async def connect(cls) -> None:
        if cls._pool is not None:
            return

        settings = get_settings()
        dsn = settings.postgres_dsn.replace("postgresql+asyncpg://", "postgresql://", 1)
        cls._pool = await asyncpg.create_pool(
            dsn=dsn,
            min_size=settings.postgres_min_pool_size,
            max_size=settings.postgres_max_pool_size,
            command_timeout=30,
        )
        logger.info("已连接到 PostgreSQL/PostGIS")

        if settings.geo_auto_migrate:
            await cls.apply_migrations()

    @classmethod
    async def disconnect(cls) -> None:
        if cls._pool is not None:
            await cls._pool.close()
            cls._pool = None
            logger.info("已断开 PostgreSQL/PostGIS")

    @classmethod
    def get_pool(cls) -> Pool:
        if cls._pool is None:
            raise RuntimeError("PostgreSQL/PostGIS 未连接")
        return cls._pool

    @classmethod
    async def apply_migrations(cls) -> None:
        pool = cls.get_pool()
        migration_dir = Path(__file__).parent / "migrations"
        migration_files = sorted(migration_dir.glob("*.sql"))

        async with pool.acquire() as connection:
            await connection.execute(
                """
                CREATE TABLE IF NOT EXISTS geo_schema_migrations (
                    version TEXT PRIMARY KEY,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
            applied = {
                row["version"]
                for row in await connection.fetch("SELECT version FROM geo_schema_migrations")
            }

            for migration_file in migration_files:
                if migration_file.name in applied:
                    continue
                if migration_file.name == "002_public_geo_boundary.sql":
                    from app.geo.private_data_migration import (
                        migrate_legacy_private_geo_data,
                    )

                    await migrate_legacy_private_geo_data(connection)
                sql = migration_file.read_text(encoding="utf-8")
                async with connection.transaction():
                    await connection.execute(sql)
                    await connection.execute(
                        "INSERT INTO geo_schema_migrations(version) VALUES($1)",
                        migration_file.name,
                    )
                logger.info(f"已应用 PostGIS 迁移: {migration_file.name}")
