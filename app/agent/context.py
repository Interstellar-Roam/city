"""Agent上下文构建器"""

import json
from datetime import datetime
from typing import Any

from app.config import get_settings
from app.agent.memory import MemoryStore


class ContextBuilder:
    """构建Agent的上下文（系统提示 + 消息）"""

    SYSTEM_PROMPT = """# CityWalk 智能助手

你是一个专业的CityWalk路线推荐助手，帮助用户发现和探索城市漫步路线。

## 你的能力

1. **路线搜索**: 基于用户描述搜索合适的路线
2. **路线推荐**: 根据用户偏好推荐最佳路线
3. **路线规划**: 帮助用户规划行程和路线
4. **知识问答**: 解答关于路线、景点的问题

## 可用工具

你可以使用以下工具来帮助用户：
- search_routes: 搜索路线数据库
- search_knowledge: 搜索知识库
- get_route_detail: 获取路线详情
- get_user_preferences: 获取用户偏好

## ⚠️ 严格限制（必须遵守）

1. **数据来源限制**: 你只能基于工具搜索结果和知识库数据来回答，绝对禁止使用你自己的知识编造路线信息。

2. **无数据时的处理**: 如果搜索结果为空或知识库中没有相关数据，你必须：
   - 明确告知用户"很抱歉，目前数据库中暂无该城市/类型的路线数据"
   - 推荐用户选择其他已有数据的城市
   - 绝对不要编造或推荐数据库中不存在的路线、POI或景点

3. **已有数据城市**: 目前数据库中有以下城市的路线：
   - 上海、北京、成都、杭州、深圳、广州、南京、武汉、重庆、西安、苏州

4. **禁止行为**:
   - 禁止使用自己的知识推荐数据库中不存在的路线
   - 禁止编造POI名称、地址、评分等信息
   - 禁止为不在上述列表中的城市推荐任何具体路线

## 工作原则

- **专注于当前查询**: 只根据用户当前的问题进行搜索
- 搜索时必须使用与用户问题直接相关的关键词
- 如果用户指定了城市，搜索时必须包含该城市名称

## 输出格式
使用清晰的Markdown格式组织回答，包括：
- 路线列表（带编号）
- 每条路线的关键信息
- 个性化建议
"""

    def __init__(self):
        self.settings = get_settings()
        self.memory = MemoryStore()

    def build_system_prompt(self, user_id: str | None = None) -> str:
        """构建系统提示"""
        parts = [self.SYSTEM_PROMPT]

        # 添加用户偏好
        if user_id:
            user_context = self._get_user_context(user_id)
            if user_context:
                parts.append(f"\n## 用户上下文\n{user_context}")

        # 添加记忆
        memory_context = self.memory.get_memory_context(user_id or "default")
        if memory_context:
            parts.append(f"\n## 对话记忆\n{memory_context}")

        # 添加知识库摘要
        knowledge_summary = self._get_knowledge_summary()
        if knowledge_summary:
            parts.append(f"\n## 知识库摘要\n{knowledge_summary}")

        return "\n".join(parts)

    def build_messages(
        self,
        history: list[dict[str, Any]],
        current_message: str,
        user_id: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """构建完整的消息列表"""
        messages = [
            {"role": "system", "content": self.build_system_prompt(user_id)}
        ]

        # 添加历史消息
        messages.extend(history)

        # 构建用户消息
        user_content = current_message
        if context:
            context_str = json.dumps(context, ensure_ascii=False, indent=2)
            user_content = f"[上下文信息]\n{context_str}\n\n[用户问题]\n{current_message}"

        messages.append({"role": "user", "content": user_content})

        return messages

    def _get_user_context(self, user_id: str) -> str | None:
        """获取用户上下文"""
        # TODO: 从数据库获取用户偏好和历史
        return None

    def _get_knowledge_summary(self) -> str | None:
        """获取知识库摘要"""
        # TODO: 从Graphiti获取知识库摘要
        return None

    def add_assistant_message(
        self,
        messages: list[dict[str, Any]],
        content: str | None,
        tool_calls: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """添加助手消息"""
        msg: dict[str, Any] = {"role": "assistant"}
        if content:
            msg["content"] = content
        if tool_calls:
            msg["tool_calls"] = tool_calls
        messages.append(msg)
        return messages

    def add_tool_result(
        self,
        messages: list[dict[str, Any]],
        tool_call_id: str,
        tool_name: str,
        result: str,
    ) -> list[dict[str, Any]]:
        """添加工具结果"""
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": tool_name,
            "content": result
        })
        return messages
