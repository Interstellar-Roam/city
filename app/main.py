"""FastAPI应用主入口"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from loguru import logger

from app.config import get_settings
from app.database import Database
from app.api import routes, gps, navigation, search, knowledge_graph, sessions, auth


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """应用生命周期管理"""
    settings = get_settings()

    # 启动时
    logger.info(f"启动 {settings.app_name} v{settings.app_version}")
    await Database.connect()
    await Database.create_indexes()

    yield

    # 关闭时
    logger.info("关闭应用")
    await Database.disconnect()


def create_app() -> FastAPI:
    """创建FastAPI应用实例"""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="""
## CityWalk 后端API

面向城市漫步(CityWalk)的后端服务，提供以下功能：

### 🗺️ 路线管理
- 创建、查询、更新、删除路线
- 分页列表、附近搜索、关键词搜索
- 路线收藏、浏览统计

### 🧭 导航功能
- 获取导航数据
- 高德地图集成
- POI信息展示

### 📍 GPS轨迹
- 记录用户步行轨迹
- 统计距离、爬升、时长
- 用户步行数据管理

### 🤖 智能搜索
- 基于LLM的自然语言搜索
- 流式响应（SSE）
- 知识图谱增强检索
        """,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc"
    )

    # CORS中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 生产环境应限制域名
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册路由
    app.include_router(routes.router, prefix="/api/v1")
    app.include_router(gps.router, prefix="/api/v1")
    app.include_router(navigation.router, prefix="/api/v1")
    app.include_router(search.router, prefix="/api/v1")
    app.include_router(knowledge_graph.router, prefix="/api/v1")
    app.include_router(sessions.router, prefix="/api/v1")
    app.include_router(auth.router, prefix="/api/v1")

    # 挂载静态文件
    import os
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    if os.path.exists(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

    # 健康检查
    @app.get("/health", tags=["健康检查"])
    async def health_check():
        """健康检查接口"""
        return {
            "status": "healthy",
            "app": settings.app_name,
            "version": settings.app_version
        }

    # 高德地图配置（供前端获取）
    @app.get("/api/v1/config/amap", tags=["配置"])
    async def get_amap_config():
        """获取高德地图配置"""
        return {
            "api_key": settings.amap_api_key,
            "security_key": settings.amap_security_key
        }

    # 根路径 - 返回编辑器页面
    @app.get("/", tags=["根路径"])
    async def root():
        """根路径，返回路线编辑器页面"""
        import os
        static_dir = os.path.join(os.path.dirname(__file__), "static")
        index_path = os.path.join(static_dir, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "docs": "/docs",
            "redoc": "/redoc"
        }

    return app


# 创建应用实例
app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )
