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
                "description": "搜索关键词，可以是路线名称、描述、特色等（可选）"
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
        "required": []
    }

    async def execute(
        self,
        query: str | None = None,
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
            search_query: dict[str, Any] = {"is_published": True}

            if city:
                search_query["city"] = city
            if difficulty:
                search_query["difficulty"] = difficulty
            if tags:
                search_query["tags"] = {"$in": tags}
            if max_distance:
                search_query["distance"] = {"$lte": max_distance}

            # 关键词搜索：在名称和描述中匹配
            if query:
                # 分词处理
                keywords = query.split()
                or_conditions = []
                for keyword in keywords:
                    or_conditions.append({"name": {"$regex": keyword, "$options": "i"}})
                    or_conditions.append({"description": {"$regex": keyword, "$options": "i"}})
                    or_conditions.append({"tags": {"$regex": keyword, "$options": "i"}})

                if or_conditions:
                    search_query["$or"] = or_conditions

            # 执行搜索
            cursor = db.routes.find(search_query).limit(limit)
            results = await cursor.to_list(length=limit)

            # 格式化结果
            formatted_results = []
            for route in results:
                # 跳过没有 id 或 name 的路线
                if not route.get("_id") or not route.get("name"):
                    continue
                formatted_results.append({
                    "id": str(route["_id"]),
                    "name": route["name"],
                    "description": route.get("description", "")[:100] if route.get("description") else "",
                    "distance": route.get("distance", 0) or 0,
                    "elevation_gain": route.get("elevation_gain", 0) or 0,
                    "estimated_duration": route.get("estimated_duration", 0) or 0,
                    "city": route.get("city"),
                    "difficulty": route.get("difficulty"),
                    "favorites_count": route.get("favorites_count", 0) or 0,
                    "preview_image": route.get("preview_image"),
                    "tags": route.get("tags", []) or []
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
