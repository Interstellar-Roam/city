# Proposal: OCM 等高线/路网图层叠加

## 动机
当前 CityWalk 地图仅使用高德标准矢量图，缺少户外运动所需的等高线和路网信息。两步路等竞品通过叠加 OpenCycleMap (OCM) 瓦片解决了此问题。本变更为导航视图和路线预览图增加 OCM 等高线叠加层。

## 变更内容

### 1. OCM 瓦片叠加层 (`OCMTileOverlay`)
- `MATileOverlay` 子类，拦截高德地图的瓦片请求
- 将瓦片索引从 GCJ-02 坐标系转换为 WGS-84
- 从 `tile.opencyclemap.org` 加载瓦片数据
- zoom 范围限制 0-18

### 2. 坐标转换工具 (`CoordTransform`)
- GCJ-02 → WGS-84 经纬度转换
- 瓦片索引与经纬度双向映射
- 单元测试：已知坐标对验证精度

### 3. 图层切换 UI (`MapLayerToggle`)
- 浮动按钮（地图右下角）
- 弹出 sheet 选择：标准地图 / 等高线叠加
- 导航视图和路线预览图共用

### 4. 集成
- `AMapNavigationView` 添加图层切换按钮 + OCM overlay 管理
- `ExploreView.swift` 路线详情预览地图添加图层切换

## 影响范围
- **iOS 前端**：新建 3 个文件，修改 2 个视图文件
- **后端**：无变更
- **坐标系统**：引入 GCJ-02 → WGS-84 转换逻辑
