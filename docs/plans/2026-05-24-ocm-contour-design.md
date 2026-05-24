# OCM 等高线/路网叠加 — 技术设计

**日期**: 2026-05-24
**状态**: 已确认

## 摘要

使用 OpenCycleMap (OCM) 瓦片服务，在高德底图上叠加等高线和户外路网图层。用户通过浮动图层按钮手动切换"标准地图/等高线叠加"模式。导航视图和路线详情预览图均支持。

## 技术架构

### 组件

| 组件 | 类型 | 职责 |
|------|------|------|
| `OCMTileOverlay` | `MATileOverlay` 子类 | 拦截瓦片请求，做 GCJ-02→WGS-84 坐标转换，从 OCM 服务器下载瓦片 |
| `CoordTransform` | 工具类 | GCJ-02 / WGS-84 双向坐标转换 + 瓦片索引正反算 |
| `MapLayerToggle` | SwiftUI View | 浮动按钮 + 图层选择 sheet |

### 数据流

```
用户点击图层按钮
  ↓
MapLayerToggle 发出 selectedLayer 变化
  ↓
父视图给 MAMapView 添加/移除 OCMTileOverlay
  ↓
MAMapView 请求瓦片 (z, x, y in GCJ-02)
  ↓
OCMTileOverlay.loadTile()
  ↓ 反算 GCJ-02 tile → GCJ-02 经纬度
  ↓ GCJ-02 → WGS-84 转换
  ↓ WGS-84 经纬度 → WGS-84 tile index
  ↓
请求 tile.opencyclemap.org/{z}/{x_wgs}/{y_wgs}.png
  ↓ 返回 PNG 瓦片
MAMapView 渲染到图面
```

## 坐标转换

### 策略

方案 A：半透明叠加 + 坐标修正。高德底图保持 GCJ-02，OCM 图层通过 `MATileOverlay` 叠加，在瓦片请求时做坐标转换。

### GCJ-02 → WGS-84

使用公开的 GCJ-02 逆变换算法，通过一次正算+减去偏移实现。

### 瓦片索引映射

```
MAMapView tile (z, x_gcj, y_gcj)
  → 反算 GCJ-02 经纬度
  → GCJ-02 → WGS-84
  → 正算 WGS-84 tile (x_wgs, y_wgs)
  → 请求 OCM
```

每次 `loadTile` 调用时实时计算，计算量 < 1ms。

## UI/UX

### 图层切换按钮

- 浮动按钮位于地图右下角（🗺 图标）
- 点击弹出 sheet：`标准地图` / `等高线叠加`
- 默认选中"标准地图"
- 导航视图和路线预览图共用 `MapLayerToggle` 组件

### 边界处理

| 场景 | 处理 |
|------|------|
| OCM 服务器无响应 | 瓦片透明，高德底图正常 |
| zoom 超出 0-18 | 不请求 OCM |
| 快速滑动 | MAMapView 自动管理队列 |
| 导航中切换 | 实时生效 |

## 涉及文件

| 文件 | 操作 |
|------|------|
| `OCMTileOverlay.swift` | 新建 |
| `CoordTransform.swift` | 新建 |
| `MapLayerToggle.swift` | 新建 |
| `ExploreView.swift` | 修改 - 集成图层切换 |
| `AMapNavigationView.swift` | 修改 - 集成图层切换 |

## 验证

1. **视觉**：真机运行，户外路线切换图层，目测对齐
2. **单元测试**：已知 GCJ-02/WGS-84 坐标对验证转换精度
3. **边界**：无网络不崩溃，zoom 边界正常
