# Design: 个人中心路线体验优化

## 架构决策

### 1. RouteDetailView 共享
- `RouteDetailView` 在 `ExploreView.swift` 中定义为 `struct`，SwiftUI 中同一 module 内可直接引用
- `ProfileView` 和 `AllRoutesView` 中直接用 `NavigationLink(destination: RouteDetailView(route: route))`
- 删除 `MyRouteDetailView`，同时删除 `StatBadge` 和 `InfoRow`（仅被 `MyRouteDetailView` 使用）

### 2. 最近展示 + 二级列表
- `ProfileView.loadMyRoutes()` 不变，始终拉取全量数据
- UI 展示：`myRoutes.prefix(5)` 在个人中心首页
- 条件显示：`myRoutes.count > 5` 时才出现"查看全部路线 →"
- `AllRoutesView` 接收完整 `[Route]` 数组，按 `createdAt` 分组

### 3. 时间分组规则
- **今天**：`Calendar.current.isDateInToday(createdAt)`
- **本周**：`Calendar.current.isDate(createdAt, equalTo: Date(), toGranularity: .weekOfYear)` 且非今天
- **更早**：其余

### 4. 登录自动跳转
- `ContentView` 中 `@State private var selectedTab = 0` 已默认 0
- 之前的问题在于 `LoginView` → `ContentView` 切换时可能未触发 TabView 重建
- 方案：确保 `authVM.isLoggedIn` 变化导致视图完全重建，`selectedTab` 自然为 0

## 数据流
```
用户上传路线 → POST /routes → 返回 RouteDetail
ProfileView.task → GET /routes/mine → [Route]
  → 首页显示 prefix(5)
  → "查看全部" → NavigationLink → AllRoutesView(routes: myRoutes)
    → 时间分组 → 点击路线 → NavigationLink → RouteDetailView(route:)
```

## 文件清单
| 文件 | 操作 |
|------|------|
| `iOS/CityWalk/CityWalk/CityWalkApp.swift` | 修改 ProfileView、删除 MyRouteDetailView/StatBadge/InfoRow |
| `iOS/CityWalk/CityWalk/Views/AllRoutesView.swift` | 新建 |
| `iOS/CityWalk/CityWalk/Views/ExploreView.swift` | 无需改动 |

## 测试策略
- 后端 API 测试：`tests/test_routes_api.py`（已有，继续使用）
- iOS 端：构建部署目测验证（三个场景：空路线、1-5条、6+条）
