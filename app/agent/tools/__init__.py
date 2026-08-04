"""Agent工具系统"""

import json
from abc import ABC, abstractmethod
from typing import Any

from loguru import logger


class BaseTool(ABC):
    """工具基类"""

    name: str = ""
    description: str = ""
    parameters: dict[str, Any] = {}

    @abstractmethod
    async def execute(self, **kwargs: Any) -> str:
        """执行工具"""
        pass

    def get_definition(self) -> dict[str, Any]:
        """获取工具定义"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }


class ToolRegistry:
    """工具注册表"""

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}
        self._register_default_tools()

    def _register_default_tools(self) -> None:
        """注册默认工具"""
        from app.agent.tools.knowledge_search import KnowledgeSearchTool
        from app.agent.tools.route_search import RouteSearchTool
        from app.agent.tools.user_preference import UserPreferenceTool

        self.register(RouteSearchTool())
        self.register(KnowledgeSearchTool())
        self.register(UserPreferenceTool())

    def register(self, tool: BaseTool) -> None:
        """注册工具"""
        self._tools[tool.name] = tool
        logger.debug(f"注册工具: {tool.name}")

    def get(self, name: str) -> BaseTool | None:
        """获取工具"""
        return self._tools.get(name)

    def get_definitions(self) -> list[dict[str, Any]]:
        """获取所有工具定义"""
        return [tool.get_definition() for tool in self._tools.values()]

    async def execute(self, name: str, arguments: dict[str, Any]) -> str:
        """执行工具"""
        tool = self._tools.get(name)
        if not tool:
            return json.dumps({"error": f"未知的工具: {name}"}, ensure_ascii=False)

        try:
            result = await tool.execute(**arguments)
            return result
        except Exception as e:
            logger.error(f"工具执行错误 {name}: {e}")
            return json.dumps({"error": str(e)}, ensure_ascii=False)
