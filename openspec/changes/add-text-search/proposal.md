# Proposal: 多字段文字搜索增强

## 动机

当前 `GET /api/v1/routes/search?keyword=xxx` 端点仅使用 MongoDB `$text` 索引搜索 `name` 和 `description` 字段。实际种子数据（`scripts/seed_routes.py`）已建立覆盖 `name`、`description`、`tags`、`city`、`district` 五个字段的文本索引，但 API 层未充分利用。

iOS App 的 `ExploreView` 顶部搜索框调用此端点进行实时搜索，用户输入城市名、标签词（如"咖啡"、"商场"）、路线名等都应返回结果，但目前只有 name/description 匹配。

## 变更内容

### 后端
1. 增强 `RouteService.search_by_keyword()` 支持多字段搜索
2. 添加 `GET /api/v1/routes/search/suggest` 搜索建议端点（自动补全）
3. 确保文本索引覆盖 name、description、tags、city、district
4. 搜索结果按相关度排序并返回 match 字段信息

### iOS
5. 搜索框增加防抖（300ms），避免频繁请求
6. 搜索结果展示高亮匹配字段

## 涉及文件

| 文件 | 变更 |
|------|------|
| `app/services/route_service.py` | 增强 search_by_keyword，新增 suggest |
| `app/api/routes.py` | 新增 suggest 端点，兼容现有 search |
| `app/schemas/route.py` | 新增 SearchSuggestion schema |
| `app/database.py` | 确保文本索引覆盖所有字段 |
| `iOS/CityWalk/CityWalk/ViewModels/ExploreViewModel.swift` | 搜索防抖 |
| `iOS/CityWalk/CityWalk/Services/APIService.swift` | 新增 suggest API 调用 |

## 影响范围

- **无破坏性变更**：现有 API 签名不变，只增强内部搜索逻辑
- **向后兼容**：iOS 现有 `searchRoutes(keyword:)` 无需改动即可受益
- **新增端点**：`GET /routes/search/suggest` 为可选增强
