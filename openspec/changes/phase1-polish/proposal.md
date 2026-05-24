# Proposal: Phase 1 基础体验打磨

## 动机
当前 MVP 核心闭环完整，但交互细节和视觉品质不足：
- 路线卡片只有纯色渐变占位图，视觉单调
- 上传后无法编辑路线信息
- 空状态缺乏引导，用户不知道该做什么
- 没有分享能力，路线无法传播

## 变更内容

### 1.1 发现页视觉升级
- **Hero Banner**：`GET /routes/featured` 精选路线轮播（后端 is_featured 标记）
- **卡片重设计**：真实封面图（preview_image 非空时）+ 渐变色占位（根据 name 哈希取色）
- **按压动效**：卡片 scale 0.97 spring 回弹

### 1.2 路线编辑 & 分享
- **EditRouteView**：名称/描述/难度/标签/城市/封面图编辑
- **后端**：新建 `POST /routes/{id}/cover` 封面图上传端点
- **ShareCardView**：路线卡片截图 → 保存相册

### 1.3 空状态引导
- 个人中心：插画 + "去记录第一条路线"CTA 按钮
- 发现页搜索：无结果时展示"试试热门路线"

## 影响范围
- **后端**：`routes.py` +2 端点、`route.py` schema +1 字段、`route.py` model +1 字段
- **iOS**：`ExploreView.swift` 修改、新建 `EditRouteView.swift` + `ShareCardView.swift` + `EmptyStateView.swift`、`APIService.swift` +3 方法、`CityWalkApp.swift` 传递 tab binding
