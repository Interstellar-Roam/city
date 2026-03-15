# 🧪 搜索功能测试指南

## 快速测试步骤

### 1️⃣ 启动基础服务

```bash
# 启动 MongoDB 和 FalkorDB
docker-compose up -d

# 验证服务运行
docker-compose ps
```

### 2️⃣ 初始化数据（首次运行）

```bash
# 初始化 MongoDB 示例数据
uv run python scripts/init_db.py

# 初始化 FalkorDB 知识图谱
uv run python scripts/init_knowledge_graph.py
```

### 3️⃣ 启动应用服务

```bash
# 方式一：使用启动脚本（推荐）
./start.sh

# 方式二：手动启动
uv run uvicorn app.main:app --reload
```

### 4️⃣ 测试搜索功能

#### 方式一：运行完整测试（推荐）

```bash
# 测试知识图谱搜索和流式搜索
./scripts/test_search.sh
```

#### 方式二：单独测试

```bash
# 测试知识图谱搜索
uv run python scripts/test_search_stream.py kg

# 测试流式搜索（SSE）
uv run python scripts/test_search_stream.py stream

# 测试非流式搜索
uv run python scripts/test_search_stream.py non-stream
```

#### 方式三：使用 curl 测试

```bash
# 测试健康检查
curl http://localhost:8000/health

# 测试知识图谱统计
curl http://localhost:8000/api/v1/knowledge-graph/stats

# 测试知识图谱搜索
curl http://localhost:8000/api/v1/knowledge-graph/search/西湖

# 测试流式搜索（SSE）
curl -X POST http://localhost:8000/api/v1/search/stream \
  -H "Content-Type: application/json" \
  -d '{"query": "推荐一条适合周末的休闲路线"}' \
  --no-buffer
```

## 测试输出示例

### 知识图谱搜索

```
查询 '西湖':
  结果数量: 2
  - [route] 杭州西湖环湖漫步
  - [poi] 断桥残雪
```

### 流式搜索（SSE）

```
data: {"type": "text", "content": "根据您的需求"}
data: {"type": "text", "content": "，我推荐以下路线："}
data: {"type": "tool_call", "name": "search_routes", "arguments": "..."}
data: {"type": "tool_result", "name": "search_routes", "result": "..."}
data: {"type": "done"}
```

## 验证清单

- [ ] Docker 服务运行中
- [ ] MongoDB 数据已初始化
- [ ] FalkorDB 知识图谱已初始化
- [ ] 应用服务运行在 http://localhost:8000
- [ ] API 文档可访问 http://localhost:8000/docs
- [ ] 知识图谱搜索返回结果
- [ ] 流式搜索返回 SSE 流

## 故障排查

### 服务无法启动

```bash
# 检查端口占用
lsof -i:8000
lsof -i:27017
lsof -i:6379

# 重启 Docker 服务
docker-compose restart
```

### 搜索无结果

```bash
# 检查数据是否初始化
docker exec -it citywalk-mongo mongosh citywalk
> db.routes.countDocuments()

# 检查知识图谱
docker exec -it citywalk-falkordb redis-cli
> GRAPH.QUERY citywalk_kg "MATCH (n) RETURN COUNT(n)"
```

### 流式响应异常

```bash
# 检查 LLM 配置
cat .env | grep LLM

# 测试 LLM 连接
uv run python -c "
from openai import AsyncOpenAI
import asyncio

async def test():
    client = AsyncOpenAI()
    response = await client.chat.completions.create(
        model='gpt-4o-mini',
        messages=[{'role': 'user', 'content': 'Hello'}]
    )
    print(response.choices[0].message.content)

asyncio.run(test())
"
```

## 性能基准

- 知识图谱搜索: < 100ms
- 流式首字节响应: < 2s
- 完整流式响应: 5-15s（取决于 LLM）

## API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/api/v1/knowledge-graph/stats` | GET | 知识图谱统计 |
| `/api/v1/knowledge-graph/search/{query}` | GET | 知识图谱搜索 |
| `/api/v1/search/stream` | POST | 流式搜索（SSE） |
| `/api/v1/search` | POST | 非流式搜索 |

## 下一步

1. ✅ 测试基础功能
2. 🎯 测试自然语言查询
3. 📊 性能测试和优化
4. 🔄 集成到前端应用
