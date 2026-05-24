# Tasks: OCM 等高线图层

## Task 1: 坐标转换工具
**文件**: `CoordTransform.swift`
- 实现 GCJ-02 → WGS-84 经纬度转换
- 实现瓦片索引 ↔ 经纬度互转
- 单元测试

## Task 2: OCM 瓦片叠加层
**文件**: `OCMTileOverlay.swift`
- `MATileOverlay` 子类
- 坐标转换 + 瓦片加载
- 错误处理（网络失败、zoom 越界）

## Task 3: 图层切换 UI
**文件**: `MapLayerToggle.swift`
- 浮动按钮组件
- Sheet 选择器组件
- 状态回调

## Task 4: 导航视图集成
**文件**: `AMapNavigationView.swift`
- 添加 `MapLayerToggle`
- 管理 `OCMTileOverlay` 的添加/移除

## Task 5: 路线预览图集成
**文件**: `ExploreView.swift` (RoutePreviewMap 部分)
- 添加 `MapLayerToggle`
- 管理 `OCMTileOverlay` 的添加/移除

## Task 6: 真机验证
- 真机构建 + 目测等高线对齐
- 网络异常测试
- zoom 边界测试
