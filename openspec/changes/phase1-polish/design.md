# Design: Phase 1 基础体验打磨

## 架构

### 封面图策略
- 不上传时：客户端根据 `route.name.hashValue % 12` 从预定义 12 色调色板取渐变色，纯本地计算，无后端交互
- 用户编辑换图：PHPicker 选图 → JPEG 压缩 → Base64 → `POST /routes/{id}/cover`
- `preview_image` 字段：`null` 表示无图，有值时为 Base64 编码的 JPEG 数据

### Hero Banner
- 独立 `GET /routes/featured` 端点，返回 `is_featured=true` 的路线（最多 5 条）
- 16:9 横滑卡片轮播，4 秒自动滑动，手动可打断
- 无精选路线时隐藏整块区域
- 加载中显示 Shimmer 骨架屏

### 编辑页
- `EditRouteView` 独立页面，预填当前路线数据
- 保存时：先 PUT /routes/{id}，如有新封面图再 POST /routes/{id}/cover
- 仅路线创建者可编辑（`createdBy == 当前用户ID`）

### 分享卡片
- `ShareCardView`：300pt 宽卡片，含封面图/路线名/距离/时长/难度
- `ImageRenderer` 渲染 → `PHPhotoLibrary` 保存 → Toast 提示

### 空状态
- `EmptyStateView` 可复用组件
- ProfileView 需要 `$selectedTab` 绑定实现"去记录"切换 Tab

## 数据流
```
编辑: EditRouteView → PUT /routes/{id} + POST /routes/{id}/cover → dismiss → RouteDetail 自动刷新
分享: RouteDetail → ShareCardView(off-screen) → ImageRenderer → PHPhotoLibrary → Toast
Banner: ExploreView → GET /routes/featured → HeroBannerView 轮播
空状态: ProfileView → EmptyStateView → CTA 按钮 → selectedTab = 1 (记录Tab)
```

## 文件清单
| 文件 | 操作 |
|------|------|
| `app/api/routes.py` | +2 端点 |
| `app/schemas/route.py` | +1 字段 |
| `app/models/route.py` | +1 字段 |
| `iOS/.../Views/ExploreView.swift` | HeroBanner + 卡片重设计 + 搜索空状态 |
| `iOS/.../Views/EditRouteView.swift` | **新建** |
| `iOS/.../Views/ShareCardView.swift` | **新建** |
| `iOS/.../Views/EmptyStateView.swift` | **新建** |
| `iOS/.../Services/APIService.swift` | +3 方法 |
| `iOS/.../Models/Route.swift` | +isFeatured |
| `iOS/.../CityWalkApp.swift` | ProfileView 传 selectedTab binding |
