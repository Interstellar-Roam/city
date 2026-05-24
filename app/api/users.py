"""用户管理 API"""

from fastapi import APIRouter, Depends

from app.database import Database
from app.middleware.auth import get_current_user
from app.schemas.common import APIResponse
from app.schemas.user import UserProfile, UserStats, UserUpdate

router = APIRouter(prefix="/users", tags=["用户管理"])


def get_db():
    return Database.get_db()


@router.get("/me", summary="获取当前用户信息")
async def get_me(
    user_id: str = Depends(get_current_user),
    db=Depends(get_db),
):
    """获取当前用户信息 + 统计数据（需登录）"""
    if not user_id:
        return APIResponse(code=2001, message="未登录").model_dump()

    user = await db.users.find_one({"_id": user_id})
    if not user:
        return APIResponse(code=3001, message="用户不存在").model_dump()

    # 统计路线数 & 总里程
    routes_cursor = db.routes.find({"created_by": user_id})
    routes = await routes_cursor.to_list(None)
    total_distance = sum(r.get("distance", 0) for r in routes) / 1000

    # 统计收藏数
    fav_cursor = db.routes.find({"favorites": {"$in": [user_id]}})
    fav_routes = await fav_cursor.to_list(None)

    nickname = user.get("nickname") or user.get("username")

    profile = UserProfile(
        phone=user.get("phone", ""),
        nickname=nickname,
        avatar=user.get("avatar"),
        stats=UserStats(
            total_distance_km=round(total_distance, 1),
            route_count=len(routes),
            favorite_count=len(fav_routes),
        ),
    )
    return APIResponse(data=profile.model_dump()).model_dump()


@router.put("/me", summary="更新用户信息")
async def update_me(
    data: UserUpdate,
    user_id: str = Depends(get_current_user),
    db=Depends(get_db),
):
    """更新昵称/头像（需登录）"""
    if not user_id:
        return APIResponse(code=2001, message="未登录").model_dump()

    update_doc: dict = {}
    if data.nickname is not None:
        update_doc["nickname"] = data.nickname
    if data.avatar is not None:
        update_doc["avatar"] = data.avatar

    if update_doc:
        await db.users.update_one({"_id": user_id}, {"$set": update_doc})

    user = await db.users.find_one({"_id": user_id})
    nickname = (user or {}).get("nickname") or (user or {}).get("username")

    return APIResponse(
        data={"nickname": nickname, "avatar": (user or {}).get("avatar")}
    ).model_dump()
