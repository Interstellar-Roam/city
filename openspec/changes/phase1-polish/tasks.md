# Tasks: Phase 1 基础体验打磨

## Task 1: 后端 — is_featured 字段 + featured 端点
- Route model 增加 `is_featured: bool = False`
- RouteDetail/RouteListItem schema 增加 `is_featured`
- 新增 `GET /routes/featured` 端点（limit=5）
- **验证**: curl 接口返回 is_featured 正确

## Task 2: 后端 — 封面图上传端点
- 新增 `CoverUpload` schema（image: Base64 string, max 500KB）
- 新增 `POST /routes/{id}/cover` 端点
- **验证**: curl 上传后 GET 路线详情返回 preview_image

## Task 3: iOS — Route 模型 + APIService 扩展
- Route 增加 `isFeatured` 字段
- APIService 新增 `fetchFeaturedRoutes()`、`updateRoute()`、`uploadCover()`
- **验证**: 编译通过

## Task 4: iOS — Hero Banner
- 在 ExploreView 搜索栏下新增 `HeroBannerView`
- 横滑 TabView 轮播，4 秒 timer，手动滑动打断
- 16:9 卡片 + 底部渐变遮罩 + 路线信息
- Shimmer 骨架屏加载态
- **验证**: 编译 + 真机 Banner 轮播正常

## Task 5: iOS — 路线卡片重设计
- `RouteCardView` 支持真实图片 / 渐变色占位
- 12 色调色板 + name.hashValue 取模
- 按压 scale 0.97 spring 动效
- **验证**: 有图路线显示图，无图路线显示渐变色

## Task 6: iOS — EditRouteView 编辑页
- 新建 `EditRouteView.swift`
- 封面图区域（点击 PHPicker 选图）
- 名称/描述/难度/标签/城市编辑
- 保存流程：PUT + POST cover
- 编辑入口：RouteDetailView 右上角（仅自己的路线）
- **验证**: 编辑后详情页自动刷新

## Task 7: iOS — ShareCardView 分享
- 新建 `ShareCardView.swift`：300pt 卡片
- ImageRenderer 截图
- PHPhotoLibrary 保存到相册
- Toast 提示
- 分享入口：RouteDetailView 右上角
- **验证**: 相册中出现分享卡片图

## Task 8: iOS — EmptyStateView 空状态引导
- 新建可复用 `EmptyStateView`
- ProfileView：插画 + "去记录第一条路线"按钮 → selectedTab = 1
- ExploreView 搜索空状态："试试热门路线"小卡片
- CityWalkApp：ProfileView 传入 $selectedTab binding
- **验证**: 无路线时个人中心显示引导，搜索无结果时显示推荐
