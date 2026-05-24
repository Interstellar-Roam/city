# OCM 等高线图层 — 实现计划

> **Goal:** 在高德底图上叠加 OCM 等高线/路网图层，支持图层切换

**Architecture:** `MATileOverlay` 子类拦截瓦片请求 → 坐标转换 → OCM 服务器加载。SwiftUI 图层切换 UI 控制 overlay 添加/移除。

**Tech Stack:** Swift, MAMapKit, MATileOverlay, SwiftUI

---

### Task 1: CoordTransform 坐标转换工具

**文件:**
- Create: `iOS/CityWalk/CityWalk/Utils/CoordTransform.swift`

**Step 1: 编写 GCJ-02 → WGS-84 转换 + 瓦片索引互转**

**Step 2: 构建验证**

**Step 3: Commit**

---

### Task 2: OCMTileOverlay 瓦片加载

**文件:**
- Create: `iOS/CityWalk/CityWalk/Services/OCMTileOverlay.swift`

**Step 1: 编写 MATileOverlay 子类，包含坐标转换 + URL 构建**

**Step 2: 构建验证**

**Step 3: Commit**

---

### Task 3: MapLayerToggle UI 组件

**文件:**
- Create: `iOS/CityWalk/CityWalk/Views/MapLayerToggle.swift`

**Step 1: 编写浮动按钮 + Sheet 选择器**

**Step 2: 构建验证**

**Step 3: Commit**

---

### Task 4: 导航视图集成

**文件:**
- Modify: `iOS/CityWalk/CityWalk/Views/AMapNavigationView.swift`

**Step 1: 添加 MapLayerToggle + OCMTileOverlay 管理**

**Step 2: 构建验证**

**Step 3: Commit**

---

### Task 5: 路线预览图集成

**文件:**
- Modify: `iOS/CityWalk/CityWalk/Views/ExploreView.swift`

**Step 1: 在路线详情预览 MAMapView 添加图层切换**

**Step 2: 构建验证**

**Step 3: Commit**

---

### Task 6: 真机构建验证

**Step 1: xcodebuild clean build**

**Step 2: 目测验证（真机安装后检查）**
