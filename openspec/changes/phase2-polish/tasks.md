# Tasks: Phase 2 用户体系 & 体验打磨

## Task 1: 后端 — 用户模型扩展 + 用户 API
- User model 新增 `nickname: str | None`, `avatar: str | None`
- 新建 `app/schemas/user.py`（UserProfile, UserUpdate, UserStats）
- 新建 `app/api/users.py`（GET /users/me, PUT /users/me）
- 实时统计聚合：总里程/总路线/总收藏
- **验证**: curl 测试完整 CRUD

## Task 2: 后端 — 收藏列表端点 + 路线字段扩展
- RouteListItem/RouteDetail schema 新增 `is_favorited: bool`, `favorite_count: int`
- 新增 `GET /routes/favorites` 端点（获取当前用户收藏列表）
- `GET /routes/mine` 也返回 `favorite_count`
- **验证**: curl 收藏后查 favorites 列表包含该路线

## Task 3: iOS — 数据模型 + APIService 扩展
- Route model 新增 `isFavorited: Bool`, `favoriteCount: Int`
- 新建 `User.swift` 模型（UserProfile 含 stats）
- APIService 新增：`toggleFavorite()`, `fetchFavorites()`, `fetchUserProfile()`, `updateUserProfile()`
- **验证**: 编译通过

## Task 4: iOS — 骨架屏组件
- 新建 `SkeletonView.swift`（SkeletonCardView + ShimmerModifier）
- 发现页 isLoading + routes 为空时显示 3 个骨架卡片
- 闪烁动画（1.5s duration, repeat forever）
- **验证**: 刷新发现页 → 先看到骨架屏 → 数据加载后切换为真实列表

## Task 5: iOS — 收藏功能前端接入
- RouteCardView 右上角心形按钮（乐观更新 + API 调用 + 失败回滚）
- RouteDetailView 收藏按钮（同理）
- 个人中心新增「我的收藏」section → 收藏列表页
- **验证**: 点击收藏 → 心形变红 + 计数更新 → 我的收藏可见

## Task 6: iOS — 个人中心重写
- ProfileHeader：头像 + 昵称（点击编辑）
- StatsPanel：3 指标并排卡片
- 头像上传（PhotosPicker → optimizeImage → uploadImage → PUT /users/me）
- 昵称编辑弹窗
- **验证**: 头像编辑生效、统计数字准确

## Task 7: iOS — 难度配色
- RouteCardView difficultyBadge 颜色随难度变化
- HeroBannerView/MiniRouteCard 同步更新
- **验证**: easy/medium/hard 路线显示不同颜色角标

## Task 8: iOS — 下拉刷新 + 触觉反馈
- 发现页 RefreshControl
- 个人中心路线列表 RefreshControl + 收藏列表 RefreshControl
- 关键操作触觉反馈（UIImpactFeedbackGenerator）
- **验证**: 下拉刷新动画正常，触觉反馈可感知
