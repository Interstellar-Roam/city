# Phase 2 用户体验打磨 实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 收藏功能前端接入、个人统计+头像昵称、难度配色、骨架屏+下拉刷新+触觉反馈

**Architecture:** 后端新增 /users/me API + /routes/favorites 端点，扩展 RouteListItem schema 增加 is_favorited/favorite_count；iOS 新增 SkeletonView、User model，重写 ProfileView，RouteCardView 增加收藏按钮和难度配色

**Tech Stack:** FastAPI + MongoDB (后端), SwiftUI + UIKit haptics (iOS)

---

### Task 1: 后端 — 用户模型扩展 + 用户 API

**Files:**
- Modify: `app/models/user.py` (+nickname 从 username 映射)
- Create: `app/schemas/user.py`
- Create: `app/api/users.py`
- Modify: `app/main.py` (注册路由)

**Step 1: 写测试**

```python
# tests/test_user_api.py
import pytest
from httpx import AsyncClient

async def test_get_my_profile(client: AsyncClient, auth_headers):
    res = await client.get("/api/v1/users/me", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["code"] == 0
    assert "nickname" in data["data"]
    assert "stats" in data["data"]
    assert "total_distance" in data["data"]["stats"]

async def test_update_profile(client: AsyncClient, auth_headers):
    res = await client.put("/api/v1/users/me", json={"nickname": "测试用户"}, headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["data"]["nickname"] == "测试用户"

async def test_update_profile_no_auth(client: AsyncClient):
    res = await client.put("/api/v1/users/me", json={"nickname": "xxx"})
    assert res.status_code == 200
    assert res.json()["code"] == 2001
```

**Step 2: Run test to verify it fails**
Run: `pytest tests/test_user_api.py -v`
Expected: FAIL (404 or import error)

**Step 3: 实现 users.py schemas + models + API**

1. `app/schemas/user.py`:
```python
from pydantic import BaseModel, Field

class UserStats(BaseModel):
    total_distance: float = 0.0
    route_count: int = 0
    favorite_count: int = 0

class UserProfile(BaseModel):
    phone: str
    nickname: str | None = None
    avatar: str | None = None
    stats: UserStats = Field(default_factory=UserStats)

class UserUpdate(BaseModel):
    nickname: str | None = Field(None, max_length=20)
    avatar: str | None = None
```

2. `app/api/users.py`:
```python
from fastapi import APIRouter, Depends
from app.database import Database
from app.middleware.auth import get_current_user
from app.schemas.common import APIResponse
from app.schemas.user import UserProfile, UserUpdate, UserStats

router = APIRouter(prefix="/users", tags=["用户管理"])

@router.get("/me")
async def get_me(user_id=Depends(get_current_user)):
    if not user_id:
        return APIResponse(code=2001, message="未登录").model_dump()
    db = Database.get_db()
    user = await db.users.find_one({"_id": user_id})
    routes_cursor = db.routes.find({"created_by": user_id})
    routes = await routes_cursor.to_list(None)
    total_distance = sum(r.get("distance", 0) for r in routes)
    fav_routes = await db.routes.find(
        {"favorites": {"$in": [user_id]}}
    ).to_list(None)
    profile = UserProfile(
        phone=user.get("phone", ""),
        nickname=user.get("nickname") or user.get("username"),
        avatar=user.get("avatar"),
        stats=UserStats(
            total_distance=round(total_distance / 1000, 1),
            route_count=len(routes),
            favorite_count=len(fav_routes)
        )
    )
    return APIResponse(data=profile.model_dump()).model_dump()

@router.put("/me")
async def update_me(data: UserUpdate, user_id=Depends(get_current_user)):
    if not user_id:
        return APIResponse(code=2001, message="未登录").model_dump()
    db = Database.get_db()
    update = {}
    if data.nickname is not None: update["nickname"] = data.nickname
    if data.avatar is not None: update["avatar"] = data.avatar
    if update:
        await db.users.update_one({"_id": user_id}, {"$set": update})
    user = await db.users.find_one({"_id": user_id})
    return APIResponse(data={"nickname": user.get("nickname") or user.get("username"), "avatar": user.get("avatar")}).model_dump()
```

3. 注册路由: `app/main.py` 添加 `from app.api import users` + `app.include_router(users.router, prefix="/api/v1")`

**Step 4: Run test to verify it passes**
Run: `pytest tests/test_user_api.py -v`
Expected: PASS

---

### Task 2: 后端 — 收藏列表 + 路线字段扩展

**Files:**
- Modify: `app/schemas/route.py` (+is_favorited +favorite_count to RouteListItem/RouteDetail)
- Modify: `app/api/routes.py` (+GET /routes/favorites)
- Modify: `app/services/route_service.py` (list_routes 返回 is_favorited)

**Step 1: 写测试**
```python
# tests/test_favorites.py
async def test_favorite_toggle(client, auth_headers, route_id):
    res = await client.post(f"/api/v1/routes/{route_id}/favorite", headers=auth_headers)
    assert res.status_code == 200

async def test_my_favorites(client, auth_headers):
    res = await client.get("/api/v1/routes/favorites", headers=auth_headers)
    assert res.status_code == 200
    assert "items" in res.json()["data"]
```

**Step 2:** 实现:
1. RouteListItem 新增 `is_favorited: bool = False`
2. RouteDetail 新增 `is_favorited: bool = False`
3. route_service.py `list_routes` 和 `get_route_by_id` 支持传入 `current_user_id` 参数，注入 is_favorited
4. 新增 `GET /routes/favorites` which finds routes where `favorites` array contains user_id

---

### Task 3: iOS — 数据模型 + APIService 扩展

**Files:**
- Create: `iOS/CityWalk/CityWalk/Models/User.swift`
- Modify: `iOS/CityWalk/CityWalk/Models/Route.swift` (+isFavorited)
- Modify: `iOS/CityWalk/CityWalk/Services/APIService.swift`

**实现:**
1. User.swift: `UserProfile` struct (phone, nickname, avatar, stats)
2. Route.swift: 新增 `isFavorited: Bool?` + `CodingKeys.isFavorited = "is_favorited"`
3. APIService: `toggleFavorite(routeId:) -> Bool`, `fetchFavorites() -> [Route]`, `fetchUserProfile() -> UserProfile`, `updateUserProfile(nickname:avatar:)`
4. 编译验证

---

### Task 4: iOS — 骨架屏组件

**Files:**
- Create: `iOS/CityWalk/CityWalk/Views/SkeletonView.swift`
- Modify: `iOS/CityWalk/CityWalk/Views/ExploreView.swift`

**实现:**
1. `ShimmerModifier`: ViewModifier with LinearGradient mask animation (1.5s, infinite)
2. `SkeletonCardView`: RoundedRectangle 100x100 + 3 capsule text lines
3. ExploreView: if isLoading && routes.isEmpty → show 3 SkeletonCardView

---

### Task 5: iOS — 收藏功能

**Files:**
- Modify: `iOS/CityWalk/CityWalk/Views/ExploreView.swift` (RouteCardView 心形按钮)
- Modify: 对应 RouteDetailView (收藏按钮)
- Modify: `iOS/CityWalk/CityWalk/CityWalkApp.swift` (ProfileView 收藏 section)

**实现:**
1. RouteCardView 右上角 overlay: Heart icon + count, onTap → optimistic update → API call → rollback on fail
2. RouteDetailView: toolbar favorite button
3. ProfileView: "我的收藏" section → FavoriteRoutesView list

---

### Task 6: iOS — 个人中心重写

**Files:**
- Modify: `iOS/CityWalk/CityWalk/CityWalkApp.swift`

**实现:**
1. ProfileHeader section: avatar (AsyncImage + PhotosPicker) + nickname (onTap → alert with TextField)
2. StatsPanel: HStack of 3 cards (总里程 km / 总路线 / 收藏)
3. Avatar upload: PhotosPicker → optimizeImage → APIService.uploadImage → PUT /users/me

---

### Task 7: iOS — 难度配色

**Files:**
- Modify: RouteCardView (in ExploreView.swift), HeroBannerView, MiniRouteCard

**实现:**
Difficulty.difficultyColor computed property returns SwiftUI Color:
- easy → .green, medium → .orange, hard → .red
RouteCardView difficultyBadge uses difficultyColor as background (opacity 0.15) + foreground

---

### Task 8: iOS — 下拉刷新 + 触觉反馈

**Files:**
- Modify: `iOS/CityWalk/CityWalk/Views/ExploreView.swift`
- Modify: `iOS/CityWalk/CityWalk/CityWalkApp.swift`
- Modify: `iOS/CityWalk/CityWalk/Views/RouteRecordingView.swift`

**实现:**
1. ExploreView: `.refreshable { await loadRoutes() }`
2. ProfileView: `.refreshable { await loadMyRoutes() }` (already partially done)
3. Haptic: `UIImpactFeedbackGenerator(style: .medium).impactOccurred()` at key actions
