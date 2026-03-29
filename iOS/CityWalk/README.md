# CityWalk iOS 客户端

城市步行路线探索应用

## 项目结构

```
CityWalk/
├── CityWalkApp.swift      # App 入口
├── Models/                 # 数据模型
│   └── Route.swift         # 路线模型
├── Views/                  # 视图层
│   └── ExploreView.swift   # 发现页
├── ViewModels/             # 视图模型
│   └── ExploreViewModel.swift
├── Services/               # 服务层
│   └── APIService.swift    # API 服务
└── Resources/              # 资源文件
```

## 如何运行

### 方式一：使用 Xcode 创建项目

1. 打开 Xcode，创建新项目
   - 选择 **iOS** > **App**
   - Product Name: `CityWalk`
   - Interface: **SwiftUI**
   - Language: **Swift**

2. 将 `CityWalk/` 目录下的文件复制到 Xcode 项目中

3. 配置 App Transport Security
   - 已在 `Info.plist` 中配置允许 HTTP 请求（用于本地开发）

4. 运行项目

### 方式二：直接用 Xcode 打开

```bash
cd iOS/CityWalk
open Package.swift  # 或用 Xcode 打开整个文件夹
```

## 功能特性

### 发现页 ✅
- 顶部搜索栏
- 分类标签横向滚动
- 精选路线卡片
- 推荐路线列表
- 下拉刷新

### 待开发
- [ ] 路线详情页
- [ ] 地图导航
- [ ] 我的路线
- [ ] 个人中心

## API 配置

默认连接本地后端：`http://localhost:8080/api/v1`

修改 `APIService.swift` 中的 `baseURL` 切换环境。

## 依赖

- iOS 15.0+
- Swift 5.5+
- SwiftUI 3.0+
