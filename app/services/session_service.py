"""会话服务 - 管理用户聊天会话和偏好"""

import json
from datetime import datetime
from typing import Any

from loguru import logger
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import Database
from app.schemas.session import ChatMessage, SessionDetail, SessionSummary, UserPreference


class SessionService:
    """会话服务"""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.sessions = db.chat_sessions
        self.preferences = db.user_preferences

    async def create_session(
        self,
        user_id: str,
        title: str | None = None,
        context: dict[str, Any] | None = None
    ) -> str:
        """创建新会话"""
        session = {
            "user_id": user_id,
            "title": title or f"会话 {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "messages": [],
            "context": context or {},
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "message_count": 0
        }

        result = await self.sessions.insert_one(session)
        logger.info(f"创建会话: {result.inserted_id}, 用户: {user_id}")
        return str(result.inserted_id)

    async def get_session(self, session_id: str) -> SessionDetail | None:
        """获取会话详情"""
        from bson import ObjectId
        
        session = await self.sessions.find_one({"_id": ObjectId(session_id)})
        if not session:
            return None

        session["id"] = str(session.pop("_id"))
        return SessionDetail(**session)

    async def get_user_sessions(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0
    ) -> list[SessionSummary]:
        """获取用户的会话列表"""
        cursor = self.sessions.find(
            {"user_id": user_id}
        ).sort("updated_at", -1).skip(offset).limit(limit)

        sessions = []
        async for doc in cursor:
            doc["id"] = str(doc.pop("_id"))
            # 获取最后一条消息
            last_msg = None
            if doc.get("messages"):
                last_msg = doc["messages"][-1].get("content", "")[:100]
            doc["last_message"] = last_msg
            sessions.append(SessionSummary(**doc))

        return sessions

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None
    ) -> None:
        """添加消息到会话"""
        from bson import ObjectId

        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now(),
            "metadata": metadata or {}
        }

        await self.sessions.update_one(
            {"_id": ObjectId(session_id)},
            {
                "$push": {"messages": message},
                "$inc": {"message_count": 1},
                "$set": {"updated_at": datetime.now()}
            }
        )

    async def update_session(
        self,
        session_id: str,
        title: str | None = None,
        context: dict[str, Any] | None = None
    ) -> bool:
        """更新会话信息"""
        from bson import ObjectId

        update_data = {"updated_at": datetime.now()}
        if title:
            update_data["title"] = title
        if context:
            update_data["context"] = context

        result = await self.sessions.update_one(
            {"_id": ObjectId(session_id)},
            {"$set": update_data}
        )
        return result.modified_count > 0

    async def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        from bson import ObjectId

        result = await self.sessions.delete_one({"_id": ObjectId(session_id)})
        return result.deleted_count > 0

    async def get_or_create_session(
        self,
        session_id: str | None,
        user_id: str
    ) -> tuple[str, list[dict[str, Any]]]:
        """获取或创建会话，返回 (session_id, 历史消息)"""
        if session_id:
            session = await self.get_session(session_id)
            if session:
                messages = [
                    {"role": msg.role, "content": msg.content}
                    for msg in session.messages
                ]
                return session_id, messages

        # 创建新会话
        new_session_id = await self.create_session(user_id)
        return new_session_id, []

    # ========== 用户偏好 ==========

    async def update_user_preference(
        self,
        user_id: str,
        city: str | None = None,
        difficulty: str | None = None,
        distance: float | None = None,
        tags: list[str] | None = None
    ) -> None:
        """更新用户偏好（基于搜索行为）"""
        pref = await self.preferences.find_one({"user_id": user_id})

        if not pref:
            pref = {
                "user_id": user_id,
                "preferred_cities": [],
                "preferred_difficulty": None,
                "preferred_distance_range": None,
                "preferred_tags": [],
                "search_count": 0,
                "last_active": datetime.now()
            }

        # 更新偏好
        if city:
            if city not in pref["preferred_cities"]:
                pref["preferred_cities"].append(city)
            # 保留最近5个城市
            pref["preferred_cities"] = pref["preferred_cities"][-5:]

        if difficulty:
            pref["preferred_difficulty"] = difficulty

        if distance:
            current_range = pref.get("preferred_distance_range")
            if current_range:
                # 平滑更新距离范围
                pref["preferred_distance_range"] = [
                    (current_range[0] + distance) / 2,
                    (current_range[1] + distance) / 2
                ]
            else:
                pref["preferred_distance_range"] = [distance, distance]

        if tags:
            for tag in tags:
                if tag not in pref["preferred_tags"]:
                    pref["preferred_tags"].append(tag)
            # 保留最近10个标签
            pref["preferred_tags"] = pref["preferred_tags"][-10:]

        pref["search_count"] += 1
        pref["last_active"] = datetime.now()

        await self.preferences.update_one(
            {"user_id": user_id},
            {"$set": pref},
            upsert=True
        )
        logger.debug(f"更新用户偏好: {user_id}")

    async def get_user_preference(self, user_id: str) -> UserPreference | None:
        """获取用户偏好"""
        pref = await self.preferences.find_one({"user_id": user_id})
        if pref:
            pref.pop("_id", None)
            return UserPreference(**pref)
        return None

    async def analyze_user_preference_from_history(
        self,
        user_id: str,
        limit: int = 10
    ) -> dict[str, Any]:
        """从历史会话分析用户偏好"""
        from bson import ObjectId

        # 获取最近会话中的工具调用
        cursor = self.sessions.find(
            {"user_id": user_id}
        ).sort("updated_at", -1).limit(limit)

        cities = []
        difficulties = []
        distances = []
        tags = []

        async for session in cursor:
            for msg in session.get("messages", []):
                metadata = msg.get("metadata", {})
                
                # 分析工具调用
                if "tool_call" in metadata:
                    tool_name = metadata["tool_call"].get("name")
                    args = metadata["tool_call"].get("arguments", "{}")
                    
                    if isinstance(args, str):
                        args = json.loads(args)

                    if tool_name == "search_routes":
                        if args.get("city"):
                            cities.append(args["city"])
                        if args.get("difficulty"):
                            difficulties.append(args["difficulty"])
                        if args.get("max_distance"):
                            distances.append(args["max_distance"])
                        if args.get("tags"):
                            tags.extend(args["tags"])

        return {
            "frequent_cities": list(set(cities))[:3],
            "preferred_difficulty": max(set(difficulties), key=difficulties.count) if difficulties else None,
            "average_distance": sum(distances) / len(distances) if distances else None,
            "interested_tags": list(set(tags))[:5]
        }
