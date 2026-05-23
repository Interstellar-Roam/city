# Design: 多字段文字搜索增强

## 架构决策

### 搜索策略：MongoDB $text → $regex 降级

```
┌─────────────────────────────────────────────────────┐
│           search_by_keyword(keyword, limit)           │
├─────────────────────────────────────────────────────┤
│  1. 优先使用 $text 索引（中英文分词）                  │
│  2. 若 $text 无结果，降级为 $regex 模糊匹配            │
│  3. 返回按相关度排序的结果 + match 字段信息             │
└─────────────────────────────────────────────────────┘
```

#### 为什么双层策略？
- `$text` 基于 MongoDB 分词索引，对中英文自然语言查询效果好，但短词/单字可能无结果
- `$regex` 作为降级方案，保证至少给出模糊匹配结果

### 文本索引设计

```javascript
db.routes.createIndex({
    name: "text",
    description: "text", 
    tags: "text",
    city: "text",
    district: "text",
    "pois.name": "text",
    "pois.tags": "text"
}, { default_language: "none" })
```

`default_language: "none"` 使用简单分词器，避免中文停用词问题。

### 搜索建议端点 (Auto-Complete)

```
GET /api/v1/routes/search/suggest?q=杭&limit=5
```

返回：
```json
{
  "success": true,
  "data": [
    {"type": "city", "value": "杭州", "count": 2},
    {"type": "tag", "value": "网红打卡", "count": 15},
    {"type": "route", "value": "杭州咖啡漫步", "count": 1}
  ]
}
```

支持 prefix 匹配，快速返回城市/标签/路线三类候选。

## 数据流

```
iOS搜索框输入 "杭州"
     ↓ (300ms 防抖)
GET /api/v1/routes/search/suggest?q=杭州
     ↓ 返回候选建议
用户选择或回车确认
     ↓
GET /api/v1/routes/search?keyword=杭州
     ↓
后台: $text search across {name, description, tags, city, district, pois.name, pois.tags}
     ↓
返回: {success, total, data: [RouteListItem, ...]}
```

## 响应格式（不变）

现有 iOS 已解析的 `SearchResponse<T>` 格式保持不变：
```json
{
  "success": true,
  "total": 3,
  "data": [
    {
      "_id": "...",
      "name": "杭州咖啡漫步",
      "city": "杭州",
      "tags": ["咖啡", "周末休闲"],
      ...
    }
  ]
}
```

## 索引运维策略

在 `database.py` 的 `setup_indexes()` 中统一管理索引创建：

```python
# 删除旧索引 (name+description only)
try:
    await db.routes.drop_index("name_text_description_text")
except: pass

# 创建新索引
await db.routes.create_index([
    ("name", "text"), ("description", "text"),
    ("tags", "text"), ("city", "text"), ("district", "text"),
    ("pois.name", "text"), ("pois.tags", "text")
], default_language="none")
```
