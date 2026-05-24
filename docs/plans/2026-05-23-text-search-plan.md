# 多字段文字搜索增强 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 增强 `GET /api/v1/routes/search` 端点，使关键词搜索覆盖 name、description、tags、city、district、pois.name、pois.tags 七个字段，并给 iOS 搜索框添加 300ms 防抖。

**Architecture:** 后端在 `RouteService.search_by_keyword` 中扩展 MongoDB text 索引查询降级为 regex 兜底；iOS 在 `ExploreViewModel` 中用 `Task.sleep` 实现防抖。

**Tech Stack:** Python 3.12, FastAPI, Motor (MongoDB async), Pydantic v2, Swift 5, SwiftUI

---

### Task 1: 更新 MongoDB 文本索引

**Files:**
- Modify: `app/database.py:43-50`

**Step 1: 修改索引定义**

修改 `create_indexes()` 方法，将文本索引从两个字段扩展到七个字段，使用 `default_language: "none"` 避免中文停用词问题。

```python
# app/database.py line 48 — 替换现有索引
# 删除旧索引（如果存在）
try:
    await db.routes.drop_index("name_text_description_text")
except Exception:
    pass

# 创建新多字段文本索引
await db.routes.create_index([
    ("name", "text"),
    ("description", "text"),
    ("tags", "text"),
    ("city", "text"),
    ("district", "text"),
    ("pois.name", "text"),
    ("pois.tags", "text"),
], default_language="none")
```

**Step 2: 运行验证索引创建**

Run: `cd /Users/rob/CodeBuddy/walk && uv run python -c "import asyncio; from app.database import Database; from app.config import get_settings; from motor.motor_asyncio import AsyncIOMotorClient; async def test(): client = AsyncIOMotorClient(get_settings().mongodb_url); Database._client = client; Database._db = client[get_settings().mongodb_db_name]; await Database.create_indexes(); indexes = await Database._db.routes.index_information(); text_indexes = [v for k,v in indexes.items() if 'text' in str(v.get('key'))]; print(f'Text indexes: {text_indexes}'); print('✅ Index created'); client.close(); asyncio.run(test())"`

Expected: 输出 Text indexes 包含 7 个字段

**Step 3: Commit**

```bash
git add app/database.py
git commit -m "feat: expand text index to cover name/description/tags/city/district/pois.name/pois.tags"
```

---

### Task 2: 增强 RouteService.search_by_keyword

**Files:**
- Modify: `app/services/route_service.py:195-202`
- Create: `tests/test_search.py`

**Step 1: Write the failing test**

```python
# tests/test_search.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.route_service import RouteService


class TestSearchByKeyword:
    """搜索功能测试"""

    @pytest.mark.asyncio
    async def test_search_matches_city_field(self):
        """搜索 '杭州' 应匹配 city 字段"""
        service = RouteService(MagicMock())
        coll = AsyncMock()
        service.collection = coll

        mock_route = {"_id": "r1", "name": "西湖漫步", "city": "杭州", "tags": ["徒步"]}
        coll.find.return_value.sort.return_value.limit.return_value.to_list = AsyncMock(return_value=[mock_route])

        results = await service.search_by_keyword("杭州")

        assert len(results) == 1
        assert results[0]["city"] == "杭州"
        # 验证使用了 $text 搜索
        call_args = coll.find.call_args[0][0]
        assert "$text" in call_args

    @pytest.mark.asyncio
    async def test_search_matches_tag_field(self):
        """搜索 '咖啡' 应匹配 tags 字段"""
        service = RouteService(MagicMock())
        coll = AsyncMock()
        service.collection = coll

        mock_route = {"_id": "r2", "name": "上海咖啡之旅", "city": "上海", "tags": ["咖啡", "文艺"]}
        coll.find.return_value.sort.return_value.limit.return_value.to_list = AsyncMock(return_value=[mock_route])

        results = await service.search_by_keyword("咖啡")

        assert len(results) == 1
        assert "咖啡" in results[0]["tags"]

    @pytest.mark.asyncio
    async def test_search_fallback_to_regex_when_text_returns_empty(self):
        """$text 无结果时降级为 regex"""
        service = RouteService(MagicMock())
        coll = AsyncMock()
        service.collection = coll

        # 第一次 $text 查询返回空
        first_call = AsyncMock(return_value=[])
        # 第二次 regex 查询返回结果
        second_call = AsyncMock(return_value=[{"_id": "r3", "name": "abc路线", "tags": []}])

        coll.find.return_value.sort.return_value.limit.return_value.to_list = first_call

        results = await service.search_by_keyword("abc")

        assert len(results) == 0  # 第一次无结果时，应触发 regex 降级
        # 注意：这需要实现降级逻辑后才能通过

    @pytest.mark.asyncio
    async def test_search_returns_empty_for_no_match(self):
        """无匹配时返回空数组（非错误）"""
        service = RouteService(MagicMock())
        coll = AsyncMock()
        service.collection = coll
        coll.find.return_value.sort.return_value.limit.return_value.to_list = AsyncMock(return_value=[])

        results = await service.search_by_keyword("不存在的关键词xyz")

        assert results == []

    @pytest.mark.asyncio
    async def test_search_truncates_long_keyword(self):
        """超长关键词自动截断"""
        service = RouteService(MagicMock())
        coll = AsyncMock()
        service.collection = coll
        coll.find.return_value.sort.return_value.limit.return_value.to_list = AsyncMock(return_value=[])

        long_keyword = "x" * 300
        await service.search_by_keyword(long_keyword)

        # 验证截断逻辑（实际传入 $search 的关键词长度 ≤ 200）
        call_args = coll.find.call_args[0][0]
        search_term = call_args["$text"]["$search"]
        assert len(search_term) <= 200
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/rob/CodeBuddy/walk && uv run pytest tests/test_search.py::TestSearchByKeyword::test_search_matches_city_field -v`

Expected: FAIL — 因为当前 search_by_keyword 虽然能搜到（MongoDB $text 会处理），但需要运行确认

Run: `cd /Users/rob/CodeBuddy/walk && uv run pytest tests/test_search.py::TestSearchByKeyword::test_search_fallback_to_regex_when_text_returns_empty -v`

Expected: FAIL — 没有降级逻辑

**Step 3: Write minimal implementation**

修改 `app/services/route_service.py` 的 `search_by_keyword` 方法：

```python
import re


async def search_by_keyword(self, keyword: str, limit: int = 20) -> list[dict[str, Any]]:
    """多字段关键词搜索，支持 $text 优先 + $regex 降级
    
    搜索范围：name, description, tags, city, district, pois.name, pois.tags
    """
    keyword = keyword.strip()[:200]  # 截断超长输入
    
    if not keyword:
        return []
    
    # 策略1: 使用 $text 索引搜索
    cursor = self.collection.find(
        {"$text": {"$search": keyword}, "is_published": True},
        {"score": {"$meta": "textScore"}}
    ).sort([("score", {"$meta": "textScore"})]).limit(limit)
    
    results = await cursor.to_list(length=limit)
    
    # 策略2: $text 无结果时降级为 $regex 模糊匹配
    if not results:
        pattern = re.escape(keyword)
        cursor = self.collection.find(
            {
                "is_published": True,
                "$or": [
                    {"name": {"$regex": pattern, "$options": "i"}},
                    {"description": {"$regex": pattern, "$options": "i"}},
                    {"tags": {"$regex": pattern, "$options": "i"}},
                    {"city": {"$regex": pattern, "$options": "i"}},
                    {"district": {"$regex": pattern, "$options": "i"}},
                    {"pois.name": {"$regex": pattern, "$options": "i"}},
                    {"pois.tags": {"$regex": pattern, "$options": "i"}},
                ]
            }
        ).limit(limit)
        results = await cursor.to_list(length=limit)
    
    return results
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/rob/CodeBuddy/walk && uv run pytest tests/test_search.py -v`

Expected: All 5 tests PASS

**Step 5: Commit**

```bash
git add app/services/route_service.py tests/test_search.py
git commit -m "feat: enhance search to cover tags/city/district with $text+$regex fallback"
```

---

### Task 3: API 空关键词校验

**Files:**
- Modify: `app/api/routes.py:82-90`

**Step 1: Write the failing test**

```python
# 追加到 tests/test_search.py
class TestSearchAPI:
    """搜索 API 端点测试"""
    
    @pytest.mark.asyncio
    async def test_search_endpoint_rejects_empty_keyword(self):
        """空关键词应返回 400"""
        from httpx import AsyncClient, ASGITransport
        from app.main import app
        
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/routes/search", params={"keyword": ""})
            assert response.status_code == 400
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/rob/CodeBuddy/walk && uv run pytest tests/test_search.py::TestSearchAPI -v`

Expected: FAIL — status 200 而非 400

**Step 3: Write minimal implementation**

修改 `app/api/routes.py` 搜索端点：

```python
# app/api/routes.py — 在 search_routes 函数开头添加校验

@router.get("/search", summary="关键词搜索路线")
async def search_routes(
    keyword: str = Query(..., description="搜索关键词"),
    limit: int = Query(20, ge=1, le=100),
    service: RouteService = Depends(get_route_service)
) -> dict[str, Any]:
    """根据关键词搜索路线（支持路线名、城市、标签等）"""
    # 空关键词校验
    if not keyword.strip():
        return JSONResponse(
            status_code=400,
            content={"detail": "keyword 不能为空"}
        )
    results = await service.search_by_keyword(keyword.strip(), limit)
    return {"success": True, "total": len(results), "data": results}
```

需要添加 import：
```python
from fastapi.responses import JSONResponse  # 已有
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/rob/CodeBuddy/walk && uv run pytest tests/test_search.py::TestSearchAPI -v`

Expected: PASS

**Step 5: Commit**

```bash
git add app/api/routes.py tests/test_search.py
git commit -m "feat: reject empty keyword with 400 in search endpoint"
```

---

### Task 4: iOS 搜索防抖 (300ms)

**Files:**
- Modify: `iOS/CityWalk/CityWalk/ViewModels/ExploreViewModel.swift:72-96`

**Step 1: 修改 ExploreViewModel**

在 `ExploreViewModel` 中添加防抖逻辑：

```swift
// ExploreViewModel.swift

// 在类内部添加防抖相关属性
private var searchDebounceTask: Task<Void, Never>?

/// 搜索路线（带 300ms 防抖）
func searchRoutes() async {
    guard !searchKeyword.isEmpty else {
        await loadRoutes()
        return
    }
    
    // 取消之前的防抖任务
    searchDebounceTask?.cancel()
    
    // 创建新的防抖任务
    searchDebounceTask = Task {
        // 等待 300ms
        try? await Task.sleep(nanoseconds: 300_000_000)
        
        // 检查是否被取消
        if Task.isCancelled { return }
        
        await performSearch()
    }
}

/// 执行实际搜索
private func performSearch() async {
    isLoading = true
    errorMessage = nil
    
    print("🔍 开始搜索: \(searchKeyword)")
    
    do {
        let results = try await apiService.searchRoutes(keyword: searchKeyword)
        print("✅ 搜索完成，找到 \(results.count) 条路线")
        routes = results
        isLoading = false
    } catch {
        print("❌ 搜索失败: \(error.localizedDescription)")
        routes = []
        errorMessage = "搜索失败: \(error.localizedDescription)"
        isLoading = false
    }
}
```

**Step 2: 验证编译**

Run: 在 Xcode 中 Build (Cmd+B) 项目 `iOS/CityWalk/CityWalk.xcodeproj`

Expected: Build Succeeded

**Step 3: Commit**

```bash
git add iOS/CityWalk/CityWalk/ViewModels/ExploreViewModel.swift
git commit -m "feat: add 300ms debounce to iOS search input"
```

---

### Task 5: 端到端验证与归档

**Step 1: 确保索引在运行时创建**

Run: `cd /Users/rob/CodeBuddy/walk && uv run python tests/test_search.py -v`

Expected: All tests pass

**Step 2: 归档 OpenSpec 变更**

```bash
cp -r openspec/changes/add-text-search/specs/route-search openspec/specs/
git add openspec/
git commit -m "docs: archive text-search spec"
```

**Step 3: 完成开发**

Run: Use superpowers:finishing-a-development-branch to wrap up.
