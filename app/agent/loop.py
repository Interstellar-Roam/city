"""Agent循环处理器"""

import json
from typing import Any, AsyncGenerator

from loguru import logger
from openai import AsyncOpenAI

from app.config import get_settings
from app.agent.context import ContextBuilder
from app.agent.memory import MemoryStore, KnowledgeBaseClient
from app.agent.tools import ToolRegistry
from app.database import Database
from app.services.session_service import SessionService


class AgentLoop:
    """Agent循环处理器"""

    def __init__(self):
        self.settings = get_settings()
        self.context = ContextBuilder()
        self.memory = MemoryStore()
        self.knowledge = KnowledgeBaseClient()
        self.tools = ToolRegistry()
        self.session_service: SessionService | None = None

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
        self.session_service = SessionService(Database.get_db())
        self._connected = True
        logger.info("Agent已初始化")

    async def process(
        self,
        query: str,
        user_id: str | None = None,
        session_id: str | None = None,
        context: dict[str, Any] | None = None,
        include_history: bool = True,  # 默认包含历史
    ) -> AsyncGenerator[str, None]:
        """
        处理用户查询（流式响应）

        Args:
            query: 用户查询
            user_id: 用户ID
            session_id: 会话ID（可选，不传则创建新会话）
            context: 额外上下文
            include_history: 是否包含历史消息

        Yields:
            str: 流式响应的文本片段
        """
        if not self._connected:
            await self.connect()

        user_id = user_id or "anonymous"

        # 获取或创建会话
        actual_session_id, db_history = await self.session_service.get_or_create_session(
            session_id, user_id
        )

        # 保存用户消息
        await self.session_service.add_message(actual_session_id, "user", query)

        # 获取历史消息
        history = db_history if include_history else []

        # 构建消息
        messages = self.context.build_messages(
            history=history,
            current_message=query,
            user_id=user_id,
            context=context
        )

        # 获取工具定义
        tool_defs = self.tools.get_definitions()

        # 调用LLM
        final_content = ""
        tool_calls_made = []  # 记录工具调用

        async for chunk in self._run_llm_loop(messages, tool_defs, user_id):
            if chunk.get("type") == "text":
                final_content += chunk["content"]
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
            elif chunk.get("type") == "tool_call":
                tool_calls_made.append({
                    "name": chunk.get("name"),
                    "arguments": chunk.get("arguments")
                })
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
            elif chunk.get("type") == "tool_result":
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
            elif chunk.get("type") == "route_recommendations":
                # 最终推荐的路线
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
            elif chunk.get("type") == "user_context":
                # 用户偏好上下文
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
            elif chunk.get("type") == "session":
                # 返回会话ID给客户端
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
            elif chunk.get("type") == "done":
                # 保存助手响应（包含工具调用元数据）
                metadata = {}
                if tool_calls_made:
                    metadata["tool_calls"] = tool_calls_made

                await self.session_service.add_message(
                    actual_session_id,
                    "assistant",
                    final_content,
                    metadata
                )

                # 返回完成事件和会话ID
                chunk["session_id"] = actual_session_id
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"

    async def _run_llm_loop(
        self,
        messages: list[dict[str, Any]],
        tool_defs: list[dict[str, Any]],
        user_id: str = "anonymous",
    ) -> AsyncGenerator[dict[str, Any], None]:
        """运行LLM循环"""
        # 先发送用户偏好上下文（如果有）
        if self.session_service and user_id != "anonymous":
            pref = await self.session_service.get_user_preference(user_id)
            if pref:
                yield {
                    "type": "user_context",
                    "preference": {
                        "cities": pref.preferred_cities,
                        "difficulty": pref.preferred_difficulty,
                        "tags": pref.preferred_tags
                    }
                }

        iteration = 0
        max_iterations = self.settings.max_iterations
        all_routes: list[dict[str, Any]] = []  # 收集所有路线数据
        final_content = ""  # 收集最终回复内容

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
                    final_content += delta.content
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

                    # 更新用户偏好（如果是搜索工具）
                    if func_name == "search_routes" and self.session_service and user_id != "anonymous":
                        try:
                            args = json.loads(func_args)
                            await self.session_service.update_user_preference(
                                user_id=user_id,
                                city=args.get("city"),
                                difficulty=args.get("difficulty"),
                                distance=args.get("max_distance"),
                                tags=args.get("tags")
                            )
                        except Exception as e:
                            logger.warning(f"更新用户偏好失败: {e}")

                    # 添加工具结果
                    messages = self.context.add_tool_result(
                        messages,
                        tc["id"],
                        func_name,
                        result
                    )

                    # 尝试解析为 JSON 以提取路线数据
                    routes_data = None
                    try:
                        parsed = json.loads(result)
                        if isinstance(parsed, dict) and "results" in parsed:
                            routes_data = parsed["results"]
                            all_routes.extend(routes_data)  # 收集路线数据
                            logger.info(f"提取到 {len(routes_data)} 条路线数据")
                    except Exception as e:
                        logger.error(f"解析路线数据失败: {e}")

                    logger.info(f"发送 tool_result 事件, routes={routes_data is not None}")
                    yield {
                        "type": "tool_result",
                        "name": func_name,
                        "result": result[:200] + "..." if len(result) > 200 else result,
                        "routes": routes_data  # 单独发送路线数据
                    }
            else:
                # 没有工具调用，结束循环
                break

        # 发送最终推荐的路线
        if all_routes:
            recommended_routes = self._extract_recommended_routes(final_content, all_routes)
            if recommended_routes:
                logger.info(f"发送 route_recommendations 事件, {len(recommended_routes)} 条路线")
                yield {
                    "type": "route_recommendations",
                    "routes": recommended_routes
                }

        yield {"type": "done"}

    def _extract_recommended_routes(
        self, 
        content: str, 
        all_routes: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """从 AI 回复中提取推荐的路线"""
        import re
        
        # 提取路线名称的多种格式：
        # 1. ### 数字️⃣ 名称（标题格式）
        # 2. | **名称** |（表格加粗格式）
        # 3. | 数字 | 名称 |（表格行格式）
        
        route_names = []
        
        # 方式1: 标题格式
        pattern1 = r'#{2,3}\s*\d+️⃣\s*([^\n|#]+?)(?=\n|\|)'
        matches1 = re.findall(pattern1, content)
        route_names.extend([m.strip() for m in matches1 if m.strip() and len(m.strip()) > 2])
        
        # 方式2: 表格加粗格式 | **名称** |
        pattern2 = r'\|\s*\*\*([^*|]+?)\*\*\s*\|'
        matches2 = re.findall(pattern2, content)
        # 过滤掉表头和无关内容
        table_names = []
        for m in matches2:
            name = m.strip()
            # 跳过表头（如"路线名称"、"距离"等）
            if name in ['路线名称', '距离', '预计时间', '特色', '项目', '信息', '名称', '类型', '难度', '累计爬升', '用时', '标签', '序号']:
                continue
            if name and len(name) > 2:
                table_names.append(name)
        route_names.extend(table_names)
        
        # 方式3: 表格行格式 | 数字 | 名称 |
        pattern3 = r'\|\s*\d+\s*\|\s*([^|]+?)\s*\|'
        matches3 = re.findall(pattern3, content)
        for m in matches3:
            name = m.strip()
            if name and len(name) > 2 and name not in route_names:
                route_names.append(name)
        
        # 去重
        route_names = list(dict.fromkeys(route_names))
        
        logger.info(f"📝 从 AI 回复中提取的路线名称: {route_names}")
        logger.info(f"📊 数据库中的路线: {[r.get('name') for r in all_routes]}")
        
        if not route_names:
            # 如果没有提取到，返回所有路线
            logger.warning("⚠️ 未提取到路线名称，返回所有路线")
            return all_routes
        
        # 匹配路线（使用已匹配集合避免重复）
        recommended = []
        matched_ids = set()  # 记录已匹配的路线ID
        
        for name in route_names:
            name_lower = name.lower()
            logger.info(f"🔍 尝试匹配: '{name}'")
            
            best_match = None
            best_score = 0
            
            for route in all_routes:
                route_id = route.get("id") or route.get("_id")
                if route_id in matched_ids:
                    continue
                
                route_name = route.get("name", "").lower()
                score = 0
                
                # 完全匹配
                if name_lower == route_name:
                    score = 100
                # 名称包含
                elif name_lower in route_name:
                    score = 80
                elif route_name in name_lower:
                    score = 70
                # 关键词匹配
                else:
                    # 提取关键词（包含地名、特色词等）
                    keywords = re.findall(r'[\u4e00-\u9fa5]{2,}', name_lower)
                    # 过滤掉泛词
                    generic_words = {'路线', '户外', '城市', '运动', '公园', '徒步', '跑步', '骑行', '散步', '休闲', '美食'}
                    specific_keywords = [kw for kw in keywords if kw not in generic_words]
                    
                    if specific_keywords:
                        # 关键词子串匹配
                        matched_count = 0
                        for kw in specific_keywords:
                            if kw in route_name:
                                matched_count += 1
                            else:
                                # 尝试关键词的前2-3个字符
                                for i in range(len(kw) - 1):
                                    sub_kw = kw[:i+2]
                                    if len(sub_kw) >= 2 and sub_kw in route_name:
                                        matched_count += 0.5
                                        break
                        
                        if matched_count >= 1:
                            score = int(50 + matched_count * 10)
                
                if score > best_score:
                    best_score = score
                    best_match = route
            
            if best_match and best_score >= 50:
                route_id = best_match.get("id") or best_match.get("_id")
                matched_ids.add(route_id)
                recommended.append(best_match)
                logger.info(f"  ✅ 匹配成功 (分数: {best_score}): '{best_match.get('name')}'")
            else:
                logger.warning(f"  ❌ 未找到匹配的路线 (最高分数: {best_score})")
        
        # 如果没有匹配到，返回所有路线
        result = recommended if recommended else all_routes
        logger.info(f"📤 最终推荐 {len(result)} 条路线: {[r.get('name') for r in result]}")
        return result

    async def search_routes(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """搜索路线（供工具调用）"""
        # 这里会在tools中实现
        return []

    async def close(self) -> None:
        """关闭连接"""
        await self.knowledge.close()
        self._connected = False
        logger.info("Agent已关闭")
