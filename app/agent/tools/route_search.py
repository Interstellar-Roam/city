"""路线搜索工具"""

import json
from typing import Any

from loguru import logger

from app.agent.tools import BaseTool
from app.database import Database


class RouteSearchTool(BaseTool):
    """路线搜索工具"""

    name = "search_routes"
    description = "搜索路线数据库，根据关键词、位置、难度等条件查找路线"
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "搜索关键词，可以是路线名称、描述、特色等"
            },
            "city": {
                "type": "string",
                "description": "城市名称"
            },
            "difficulty": {
                "type": "string",
                "enum": ["easy", "medium", "hard"],
                "description": "难度等级"
            },
            "max_distance": {
                "type": "number",
                "description": "最大距离（米）"
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "标签列表"
            },
            "limit": {
                "type": "integer",
                "description": "返回结果数量限制",
                "default": 10
            }
        },
        "required": ["query"]
    }

    async def execute(
        self,
        query: str,
        city: str | None = None,
        difficulty: str | None = None,
        max_distance: float | None = None,
        tags: list[str] | None = None,
        limit: int = 10
    ) -> str:
        """执行路线搜索"""
        try:
            db = Database.get_db()

            # 构建查询条件
            search_query: dict[str, Any] = {
                "is_published": True,
                "$text": {"$search": query}
            }

            if city:
                search_query["city"] = city
            if difficulty:
                search_query["difficulty"] = difficulty
            if tags:
                search_query["tags"] = {"$in": tags}

            # 执行搜索
            cursor = db.routes.find(
                search_query,
                {"score": {"$meta": "textScore"}}
            ).sort([("score", {"$meta": "textScore"})]).limit(limit)

            results = await cursor.to_list(length=limit)

            # 格式化结果
            formatted_results = []
            for route in results:
                formatted_results.append({
                    "id": route["_id"],
                    "name": route["name"],
                    "description": route.get("description", "")[:100],
                    "distance": route.get("distance", 0),
                    "elevation_gain": route.get("elevation_gain", 0),
                    "estimated_duration": route.get("estimated_duration", 0),
                    "city": route.get("city"),
                    "difficulty": route.get("difficulty"),
                    "favorites_count": route.get("favorites_count", 0),
                    "preview_image": route.get("preview_image"),
                    "relevance_score": route.get("score", 0)
                })

            logger.info(f"路线搜索完成: 查询'{query}', 找到{len(formatted_results)}条结果")

            return json.dumps({
                "success": True,
                "query": query,
                "total": len(formatted_results),
                "results": formatted_results
            }, ensure_ascii=False)

        except Exception as e:
            logger.error(f"路线搜索错误: {e}")
            return json.dumps({
                "success": False,
                "error": str(e)
            }, ensure_ascii=False)


class GetRouteDetailTool(BaseTool):
    """获取路线详情工具"""

    name = "get_route_detail"
    description = "获取指定路线的详细信息，包括完整的路线点、POI、统计数据等"
    parameters = {
        "type": "object",
        "properties": {
            "route_id": {
                "type": "string",
                "description": "路线ID"
            }
        },
        "required": ["route_id"]
    }

    async def execute(self, route_id: str) -> str:
        """获取路线详情"""
        try:
            db = Database.get_db()
            route = await db.routes.find_one({"_id": route_id})

            if not route:
                return json.dumps({
                    "success": False,
                    "error": "路线不存在"
                }, ensure_ascii=False)

            # 移除敏感字段
            route.pop("created_by", None)

            logger.info(f"获取路线详情: {route_id}")

            return json.dumps({
                "success": True,
                "route": route
            }, ensure_ascii=False, default=str)

        except Exception as e:
            logger.error(f"获取路线详情错误: {e}")
            return json.dumps({
                "success": False,
                "error": str(e)
            }, ensure_ascii=False)
