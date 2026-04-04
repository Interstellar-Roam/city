"""数据库连接模块"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from loguru import logger

from app.config import get_settings


class Database:
    """MongoDB数据库连接管理"""

    _client: AsyncIOMotorClient | None = None
    _db: AsyncIOMotorDatabase | None = None

    @classmethod
    async def connect(cls) -> None:
        """建立数据库连接"""
        settings = get_settings()
        cls._client = AsyncIOMotorClient(settings.mongodb_url)
        cls._db = cls._client[settings.mongodb_db_name]
        logger.info(f"已连接到MongoDB: {settings.mongodb_db_name}")

    @classmethod
    async def disconnect(cls) -> None:
        """断开数据库连接"""
        if cls._client:
            cls._client.close()
            cls._client = None
            cls._db = None
            logger.info("已断开MongoDB连接")

    @classmethod
    def get_db(cls) -> AsyncIOMotorDatabase:
        """获取数据库实例"""
        if cls._db is None:
            raise RuntimeError("数据库未连接，请先调用 Database.connect()")
        return cls._db

    @classmethod
    async def create_indexes(cls) -> None:
        """创建数据库索引"""
        db = cls.get_db()
        # 路线索引
        await db.routes.create_index([("location", "2dsphere")])
        await db.routes.create_index([("name", "text"), ("description", "text")])
        await db.routes.create_index([("created_at", -1)])
        await db.routes.create_index([("favorites_count", -1)])

        # GPS轨迹索引
        await db.gps_tracks.create_index([("route_id", 1)])
        await db.gps_tracks.create_index([("user_id", 1)])
        await db.gps_tracks.create_index([("created_at", -1)])

        # 会话索引
        await db.chat_sessions.create_index([("user_id", 1)])
        await db.chat_sessions.create_index([("user_id", 1), ("updated_at", -1)])
        await db.chat_sessions.create_index([("created_at", -1)])

        # 用户偏好索引
        await db.user_preferences.create_index([("user_id", 1)], unique=True)

        logger.info("数据库索引创建完成")


@asynccontextmanager
async def get_database() -> AsyncGenerator[AsyncIOMotorDatabase, None]:
    """获取数据库连接的上下文管理器"""
    db = Database.get_db()
    try:
        yield db
    except Exception as e:
        logger.error(f"数据库操作错误: {e}")
        raise
