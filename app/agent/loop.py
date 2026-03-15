"""Agent循环处理器"""

import json
from typing import Any, AsyncGenerator

from loguru import logger
from openai import AsyncOpenAI

from app.config import get_settings
from app.agent.context import ContextBuilder
from app.agent.memory import MemoryStore, KnowledgeBaseClient
from app.agent.tools import ToolRegistry


class AgentLoop:
    """Agent循环处理器"""

    def __init__(self):
        self.settings = get_settings()
        self.context = ContextBuilder()
        self.memory = MemoryStore()
        self.knowledge = KnowledgeBaseClient()
        self.tools = ToolRegistry()

        # 初始化LLM客户端
        self.client = AsyncOpenAI(
            api_key=self.settings.llm_api_key,
            base_url=self.settings.llm_base_url
        )

        self._connected = False

    async def connect(self) -> None:
        """建立连接"""
        if self._connected:
            return

        await self.knowledge.connect()
        self._connected = True
        logger.info("Agent已初始化")

    async def process(
        self,
        query: str,
        user_id: str | None = None,
        session_id: str | None = None,
        context: dict[str, Any] | None = None,
        include_history: bool = False,
    ) -> AsyncGenerator[str, None]:
        """
        处理用户查询（流式响应）

        Args:
            query: 用户查询
            user_id: 用户ID
            session_id: 会话ID
            context: 额外上下文
            include_history: 是否包含历史消息（默认False，搜索API应为无状态）

        Yields:
            str: 流式响应的文本片段
        """
        if not self._connected:
            await self.connect()

        session_id = session_id or user_id or "default"

        # 获取历史消息（仅在需要时）
        history = self.memory.get_history(session_id) if include_history else []

        # 构建消息
        messages = self.context.build_messages(
            history=history,
            current_message=query,
            user_id=user_id,
            context=context
        )

        # 记录用户消息
        self.memory.add_message(session_id, "user", query)

        # 获取工具定义
        tool_defs = self.tools.get_definitions()

        # 调用LLM
        final_content = ""
        async for chunk in self._run_llm_loop(messages, tool_defs):
            if chunk.get("type") == "text":
                final_content += chunk["content"]
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
            elif chunk.get("type") == "tool_call":
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
            elif chunk.get("type") == "done":
                # 记录助手响应
                self.memory.add_message(session_id, "assistant", final_content)
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"

    async def _run_llm_loop(
        self,
        messages: list[dict[str, Any]],
        tool_defs: list[dict[str, Any]],
    ) -> AsyncGenerator[dict[str, Any], None]:
        """运行LLM循环"""
        iteration = 0
        max_iterations = self.settings.max_iterations

        while iteration < max_iterations:
            iteration += 1

            # 调用LLM
            response = await self.client.chat.completions.create(
                model=self.settings.llm_model,
                messages=messages,
                tools=tool_defs if tool_defs else None,
                stream=True
            )

            # 处理流式响应
            content_chunks = []
            tool_calls_data: dict[int, dict[str, Any]] = {}

            async for chunk in response:
                delta = chunk.choices[0].delta

                # 处理文本内容
                if delta.content:
                    content_chunks.append(delta.content)
                    yield {
                        "type": "text",
                        "content": delta.content
                    }

                # 处理工具调用
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        idx = tc.index
                        if idx not in tool_calls_data:
                            tool_calls_data[idx] = {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": "",
                                    "arguments": ""
                                }
                            }
                        if tc.function:
                            if tc.function.name:
                                tool_calls_data[idx]["function"]["name"] = tc.function.name
                            if tc.function.arguments:
                                tool_calls_data[idx]["function"]["arguments"] += tc.function.arguments

            # 检查是否有工具调用
            if tool_calls_data:
                tool_calls = list(tool_calls_data.values())
                
                # 构建助手消息
                messages = self.context.add_assistant_message(
                    messages,
                    content="".join(content_chunks) or None,
                    tool_calls=tool_calls
                )

                # 执行工具
                for tc in tool_calls:
                    func_name = tc["function"]["name"]
                    func_args = tc["function"]["arguments"]
                    
                    yield {
                        "type": "tool_call",
                        "name": func_name,
                        "arguments": func_args
                    }

                    # 执行工具
                    result = await self.tools.execute(
                        func_name,
                        json.loads(func_args)
                    )

                    # 添加工具结果
                    messages = self.context.add_tool_result(
                        messages,
                        tc["id"],
                        func_name,
                        result
                    )

                    yield {
                        "type": "tool_result",
                        "name": func_name,
                        "result": result[:200] + "..." if len(result) > 200 else result
                    }
            else:
                # 没有工具调用，结束循环
                break

        yield {"type": "done"}

    async def search_routes(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """搜索路线（供工具调用）"""
        # 这里会在tools中实现
        return []

    async def close(self) -> None:
        """关闭连接"""
        await self.knowledge.close()
        self._connected = False
        logger.info("Agent已关闭")
