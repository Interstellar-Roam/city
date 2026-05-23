# Tasks: 多字段文字搜索增强

## Task 1: 更新文本索引
- 修改 `app/database.py` 的 `setup_indexes()`
- 添加覆盖 name, description, tags, city, district, pois.name, pois.tags 的 text 索引

## Task 2: 增强 RouteService.search_by_keyword
- 修改 `app/services/route_service.py`
- 扩展搜索字段到 tags, city, district
- 添加 $regex 降级兜底
- 返回 match_fields 信息

## Task 3: 新增搜索建议端点
- 修改 `app/api/routes.py` 添加 `/search/suggest` 端点
- 修改 `app/schemas/route.py` 添加 SearchSuggestion schema
- 修改 `RouteService` 添加 `suggest()` 方法

## Task 4: iOS 搜索防抖优化
- 修改 `iOS/CityWalk/CityWalk/ViewModels/ExploreViewModel.swift`
- 添加 300ms 防抖逻辑

## Task 5: 端到端测试
- 手动测试中英文搜索
- 验证 suggest 功能
- 验证索引生效
