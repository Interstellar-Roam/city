# Proposal: 个人中心路线体验优化

## 动机
当前个人中心"我的路线"存在三个问题：
1. 点击路线跳转到纯文字详情页（`MyRouteDetailView`），缺少地图展示
2. 所有路线平铺展示，用户路线多时（30+）页面过长
3. 登录成功后停留在登录页，需手动切换到发现页

## 变更内容
1. **路线详情统一**：删除 `MyRouteDetailView`，我的路线点击跳转复用发现页的 `RouteDetailView`（带地图+海拔图+导航）
2. **大列表适配**：个人中心只展示最近 5 条路线；提供"查看全部路线 →"入口进入二级时间分组列表页 `AllRoutesView`
3. **登录自动跳转**：`ContentView` 初始化 `selectedTab = 0`（发现页）

## 影响范围
- `CityWalkApp.swift`：`ContentView.selectedTab` 初始值、`ProfileView` 路线 section 改造
- `Views/ExploreView.swift`：无需改动（`RouteDetailView` 已是 public struct）
- `Views/AllRoutesView.swift`：新建文件
- 后端：无变更
