# Design: Phase 2 用户体系 & 体验打磨

## 架构决策

### 1. 用户资料存储
- **方案**：扩展现有 User model，新增 `nickname: str | None`、`avatar: str | None`（存图片 URL）
- **头像上传**：复用现有 `POST /images/upload`，URL 写入 user.avatar 字段
- **统计数据**：实时计算（聚合 routes 集合），不单独存储统计表
  - 总里程：`sum(routes.distance)` where `created_by = user_id`
  - 总路线：`count(routes)` where `created_by = user_id`
  - 总收藏：`count(routes)` where `favorited_by` contains `user_id`

### 2. 收藏数据流
- **后端**：`POST /routes/{id}/favorite` 已实现（toggle 逻辑），新增 `GET /routes/favorites` 返回当前用户收藏的路线列表
- **前端**：Route model 新增 `isFavorited: Bool` + `favoriteCount: Int`
  - `GET /routes` 列表和详情返回 `is_favorited` + `favorite_count` 字段
  - 列表页 /mine 和 favorites 端点也返回这两个字段
- 收藏按钮交互：点击 → 乐观更新本地状态 → API 调用 → 成功则保持 / 失败则回滚

### 3. 难度配色方案
- easy = `Color.green.opacity(0.15)` 背景 + `.green` 文字
- medium = `Color.orange.opacity(0.15)` 背景 + `.orange` 文字
- hard = `Color.red.opacity(0.15)` 背景 + `.red` 文字
- RouteCardView 左上角 difficultyBadge 使用难度对应色
- HeroBannerView 和 MiniRouteCard 也同步更新难度角标颜色

### 4. 骨架屏实现
- 创建 `SkeletonView.swift` 可复用组件
- `SkeletonCardView`：模拟 RouteCardView 布局（100x100 占位 + 三行文字占位）
- `ShimmerModifier`：ViewModifier 使用 `LinearGradient` + `mask` + 位移动画
- 发现页在 `isLoading` 为 true 且 routes 为空时显示 3 个骨架卡片

### 5. 数据流总结

```
发现页卡片:
  GET /routes → { items: [{..., is_favorited, favorite_count}] }
  → RouteCardView 右上角心形按钮

路线详情:
  GET /routes/{id} → { ..., is_favorited, favorite_count }
  → 详情页收藏按钮

收藏操作:
  POST /routes/{id}/favorite → { favorited: bool, count: int }
  → 更新本地 Route.isFavorited + favoriteCount

我的收藏:
  GET /routes/favorites → { items: [...] }
  → 个人中心「我的收藏」列表

用户统计:
  GET /users/me → { nickname, avatar, stats: { total_distance, route_count, favorite_count } }
  → ProfileView StatsPanel

用户更新:
  PUT /users/me { nickname, avatar } → 更新用户文档
```

### 6. 涉及文件

**后端新增/修改：**
- `app/api/users.py` — 新增（GET/PUT /users/me）
- `app/api/routes.py` — 修改（favorites 列表端点）
- `app/models/user.py` — 修改（+nickname, +avatar）
- `app/schemas/user.py` — 新增（UserProfile, UserUpdate, UserStats）
- `app/schemas/route.py` — 修改（RouteListItem +is_favorited +favorite_count）

**iOS 新增/修改：**
- `iOS/CityWalk/CityWalk/Views/SkeletonView.swift` — 新增骨架屏组件
- `iOS/CityWalk/CityWalk/Views/ExploreView.swift` — 修改（收藏按钮 + 骨架屏 + 下拉刷新）
- `iOS/CityWalk/CityWalk/Views/RouteDetailView` — 修改（收藏按钮）
- `iOS/CityWalk/CityWalk/CityWalkApp.swift` — 重写 ProfileView（统计面板 + 头像昵称 + 收藏列表）
- `iOS/CityWalk/CityWalk/Models/Route.swift` — 修改（+isFavorited +favoriteCount）
- `iOS/CityWalk/CityWalk/Models/User.swift` — 新增
- `iOS/CityWalk/CityWalk/Services/APIService.swift` — 修改（+favorite 方法 +用户 API）
