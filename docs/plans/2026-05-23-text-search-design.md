# 多字段文字搜索增强 - 设计文档

> 日期: 2026-05-23

## 目标

增强 `GET /api/v1/routes/search` 端点，使关键词搜索覆盖 name、description、tags、city、district、pois.name、pois.tags 七个字段。

## 架构决策

### 方案：纯增强搜索（无 suggest 端点）
- 扩大后端搜索字段覆盖
- iOS 加 300ms 防抖
- 保持输入即搜模式
- API 签名和响应格式不变

### 搜索策略：$text + $regex 双层
1. `$text` 优先（利用 MongoDB 分词索引）
2. `$regex` 降级兜底（保证短词/单字也有结果）

### 文本索引
```javascript
db.routes.createIndex({
  name: "text", description: "text", tags: "text",
  city: "text", district: "text",
  "pois.name": "text", "pois.tags": "text"
}, { default_language: "none" })
```

## 错误处理
- 空关键词 → 400 错误
- 超长输入(>200字符) → 自动截断
- 无结果 → 返回空数组，非错误
- 特殊字符 → 安全转义

## 涉及文件
| 文件 | 变更 |
|------|------|
| `app/database.py` | 文本索引更新 |
| `app/services/route_service.py` | search_by_keyword 增强 |
| `app/api/routes.py` | 空关键词校验 |
| `iOS/CityWalk/CityWalk/ViewModels/ExploreViewModel.swift` | 300ms 防抖 |
