# Tasks: 个人中心路线体验优化

## Task 1: 登录后自动跳到发现页
- 修改 `CityWalkApp.swift`：`ContentView.selectedTab` 确保初始化为 0
- **验证**：登录成功后自动显示发现页（而非我的页）

## Task 2: 删除 MyRouteDetailView，ProfileView 改用 RouteDetailView
- 删除 `CityWalkApp.swift` 中的 `MyRouteDetailView`、`StatBadge`、`InfoRow`
- `ProfileView` 中 `NavigationLink(destination: MyRouteDetailView(route:))` 改为 `NavigationLink(destination: RouteDetailView(route:))`
- **验证**：从我的页点击路线，进入带地图的完整详情页

## Task 3: 个人中心只展示最近 5 条 + 查看全部入口
- `ProfileView` 路线 section 改为只展示 `myRoutes.prefix(5)`
- 条件添加"查看全部路线 →"入口（仅 `count > 5`）
- **验证**：路线 ≤ 5 时不显示入口；> 5 时显示入口

## Task 4: 新建 AllRoutesView 二级列表页
- 新建 `Views/AllRoutesView.swift`
- 实现时间分组逻辑（今天/本周/更早）
- 每项可点击跳转 `RouteDetailView`
- **验证**：从 ProfileView 点击"查看全部"，进入分组列表，点击路线进详情
