# Spec Delta: Phase 2 用户体系 & 体验打磨

## 新增需求

### REQ-201: 用户资料管理
- **GET /api/v1/users/me**：返回当前用户信息（手机号、昵称、头像 URL）+ 统计数据（总里程 km、总路线数、总收藏数）
- **PUT /api/v1/users/me**：更新昵称、头像 URL
- 昵称限 20 字符，头像需为合法 URL
- 需要 Bearer Token 认证

### REQ-202: 收藏功能前端接入
- 路线详情页显示收藏按钮（心形图标），显示当前收藏数
- 发现页路线卡片右上角显示心形按钮 + 收藏数
- 点击按钮调用 `POST /routes/{id}/favorite` toggle 收藏/取消
- 前端实现乐观更新：点击立即改变图标状态和计数，API 失败后回滚
- 个人中心「我的收藏」section，点击进入收藏路线列表

### REQ-203: 路线收藏数据暴露
- `GET /routes` 列表返回 `is_favorited`（当前用户是否收藏，未登录为 false）和 `favorite_count`
- `GET /routes/{id}` 详情返回 `is_favorited` 和 `favorite_count`
- `GET /routes/mine` 返回 `favorite_count`
- 新增 `GET /routes/favorites` 返回当前用户收藏的路线列表（需登录）

### REQ-204: 骨架屏加载态
- 发现页路线列表加载时显示 3 个骨架占位卡片
- 骨架卡片模拟真实卡片布局：100x100 图片占位 + 标题/副标题/标签占位条
- 闪烁动画（线性渐变遮罩水平位移，1.5s duration，无限循环）
- 数据加载完成后立即替换为真实列表

### REQ-205: 下拉刷新 + 触觉反馈
- 发现页支持下拉刷新（RefreshControl）
- 个人中心「我的路线」和「我的收藏」列表支持下拉刷新
- 开始记录：medium impact 触觉反馈
- 保存成功：notification success 触觉反馈
- 删除确认：warning 触觉反馈

### REQ-206: 难度视觉区分
- easy 路线卡片难度角标：绿色背景 + 绿色文字
- medium 路线卡片难度角标：橙色背景 + 橙色文字
- hard 路线卡片难度角标：红色背景 + 红色文字
- HeroBannerView 和 MiniRouteCard 同步使用难度配色

## 修改需求
无（Phase 1 需求不变）

## 废弃需求
无
