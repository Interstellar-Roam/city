"""用户偏好检索工具"""

import json

from loguru import logger

from app.agent.tools import BaseTool
from app.database import Database
from app.services.session_service import SessionService


class UserPreferenceTool(BaseTool):
    """用户偏好检索工具"""

    name = "get_user_preference"
    description = "获取用户的历史偏好和搜索习惯，包括喜欢的城市、难度偏好、距离偏好等，用于个性化推荐"
    parameters = {
        "type": "object",
        "properties": {
            "include_history": {
                "type": "boolean",
                "description": "是否包含历史会话分析",
                "default": False
            }
        },
        "required": []
    }

    async def execute(self, user_id: str, include_history: bool = False) -> str:
        """执行用户偏好检索"""
        try:
            db = Database.get_db()
            service = SessionService(db)

            # 获取用户偏好
            preference = await service.get_user_preference(user_id)

            result = {
                "success": True,
                "user_id": user_id,
                "preference": preference.model_dump() if preference else None
            }

            # 可选：分析历史会话
            if include_history:
                analysis = await service.analyze_user_preference_from_history(user_id)
                result["history_analysis"] = analysis

            logger.info(f"获取用户偏好: {user_id}")
            return json.dumps(result, ensure_ascii=False)

        except Exception as e:
            logger.error(f"获取用户偏好错误: {e}")
            return json.dumps({
                "success": False,
                "error": str(e)
            }, ensure_ascii=False)
