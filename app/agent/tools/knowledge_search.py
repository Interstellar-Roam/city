"""知识库搜索工具"""

import json
from typing import Any

from loguru import logger

from app.agent.tools import BaseTool
from app.agent.memory import KnowledgeBaseClient


class KnowledgeSearchTool(BaseTool):
    """知识库搜索工具"""

    name = "search_knowledge"
    description = "搜索知识图谱，查找路线相关的深度信息和知识"
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "搜索查询，可以是自然语言问题或关键词"
            },
            "entity_type": {
                "type": "string",
                "enum": ["route", "poi", "city", "attraction"],
                "description": "实体类型"
            },
            "limit": {
                "type": "integer",
                "description": "返回结果数量限制",
                "default": 10
            }
        },
        "required": ["query"]
    }

    def __init__(self):
        self.client = KnowledgeBaseClient()

    async def execute(
        self,
        query: str,
        entity_type: str | None = None,
        limit: int = 10
    ) -> str:
        """执行知识库搜索"""
        try:
            # 确保连接
            if not self.client._connected:
                await self.client.connect()

            # 执行搜索
            results = await self.client.search(query, limit=limit)

            logger.info(f"知识库搜索完成: 查询'{query}', 找到{len(results)}条结果")

            return json.dumps({
                "success": True,
                "query": query,
                "total": len(results),
                "results": results
            }, ensure_ascii=False)

        except Exception as e:
            logger.error(f"知识库搜索错误: {e}")
            return json.dumps({
                "success": False,
                "error": str(e),
                "message": "知识库暂时不可用，请使用路线搜索工具"
            }, ensure_ascii=False)


class AddRouteKnowledgeTool(BaseTool):
    """添加路线知识到图谱"""

    name = "add_route_knowledge"
    description = "将路线信息添加到知识图谱，用于增强智能检索能力"
    parameters = {
        "type": "object",
        "properties": {
            "route_id": {
                "type": "string",
                "description": "路线ID"
            },
            "name": {
                "type": "string",
                "description": "路线名称"
            },
            "description": {
                "type": "string",
                "description": "路线描述"
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "标签列表"
            }
        },
        "required": ["route_id", "name"]
    }

    def __init__(self):
        self.client = KnowledgeBaseClient()

    async def execute(
        self,
        route_id: str,
        name: str,
        description: str | None = None,
        tags: list[str] | None = None
    ) -> str:
        """添加路线知识"""
        try:
            if not self.client._connected:
                await self.client.connect()

            await self.client.add_route_knowledge(
                route_id=route_id,
                name=name,
                description=description or "",
                tags=tags or []
            )

            logger.info(f"添加路线知识: {route_id}")

            return json.dumps({
                "success": True,
                "message": f"已将路线'{name}'添加到知识库"
            }, ensure_ascii=False)

        except Exception as e:
            logger.error(f"添加路线知识错误: {e}")
            return json.dumps({
                "success": False,
                "error": str(e)
            }, ensure_ascii=False)
