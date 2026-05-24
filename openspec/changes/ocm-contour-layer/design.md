# Design: OCM 等高线图层

## 架构决策

### 方案选择：半透明叠加 + 坐标修正
高德底图保持 GCJ-02 坐标系不变，OCM 作为 `MATileOverlay` 叠加。在瓦片请求时做坐标系转换（GCJ-02 → WGS-84），而不改变 MAMapView 的坐标系配置。

### 组件关系

```
MapLayerToggle (SwiftUI)
    │
    ├── AMapNavigationView ── MAMapView ── OCMTileOverlay
    └── RoutePreviewMap    ── MAMapView ── OCMTileOverlay
```

## 数据流

1. 用户点击图层按钮 → `selectedLayer` 状态变化
2. 父视图响应：`mapView.add(OCMTileOverlay())` 或 `mapView.remove(OCMTileOverlay)`
3. `MAMapView` 加载瓦片时调用 `OCMTileOverlay.loadTile(at:)` 
4. 瓦片路径 `(z, x_gcj, y_gcj)` → 反算 GCJ-02 经纬度 → 转换 WGS-84 → 正算 `(z, x_wgs, y_wgs)`
5. URL 请求：`tile.opencyclemap.org/{z}/{x_wgs}/{y_wgs}.png`
6. 返回 PNG Data 给 MAMapView 渲染

## 坐标转换算法

```
tile (z, x_gcj, y_gcj)
  → tileToLngLat(x_gcj, y_gcj, z) → (lng_gcj, lat_gcj)
  → gcj02ToWgs84(lng_gcj, lat_gcj) → (lng_wgs, lat_wgs)
  → lngLatToTile(lng_wgs, lat_wgs, z) → (x_wgs, y_wgs)
```

GCJ-02 逆变换使用公开公式，精度在 1 米以内。

## 图层切换逻辑

```
switch selectedLayer:
    case .standard:  mapView.remove(ocmOverlay)
    case .contour:   mapView.add(ocmOverlay)
```

导航中切换实时生效，不影响导航状态。

## 边界处理

| 场景 | 处理 |
|------|------|
| 网络不可用 | OCM 返回 nil，高德底图正常显示 |
| zoom < 0 或 > 18 | 直接返回 nil，不请求 |
| OCM 返回 404/5xx | 返回 nil，静默处理 |
| 图层切换按钮重复点击 | 去重处理（选中相同选项时不操作） |
