# Spec Delta: 个人中心路线

## MODIFIED: 路线详情页统一
- 我的路线详情页不再使用独立 `MyRouteDetailView`，统一复用 `RouteDetailView`
- `RouteDetailView` 包含：地图、海拔图、路线数据统计、导航按钮

## ADDED: 最近路线展示
- 个人中心"我的路线" section 只展示最近 5 条
- 路线数 > 5 时，section 末尾显示"查看全部路线 →"
- 路线数 ≤ 5 时，不显示"查看全部"入口

## ADDED: 二级路线列表页
- 新建 `AllRoutesView`，按 `createdAt` 分三组：今天、本周、更早
- 每组显示路线名、距离、难度、创建时间
- 点击任意路线跳转 `RouteDetailView`

## ADDED: 登录自动跳转
- 登录成功后 `ContentView` 默认 tab 为 0（发现页），无需手动切换
