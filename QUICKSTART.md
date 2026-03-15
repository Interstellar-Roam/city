# 快速启动指南

## 环境要求

- **Python**: 3.12+（推荐使用 uv 自动管理）
- **Docker**: 用于运行 MongoDB 和 FalkorDB
- **uv**: Python 包管理工具（推荐）

## 安装 uv

uv 是一个极速的 Python 包管理工具，比 pip 快 10-100 倍。

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# 验证安装
uv --version
```

## 快速开始

### 方式一：一键启动（推荐）

```bash
# 1. 启动基础服务
docker-compose up -d

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 文件

# 3. 运行启动脚本（自动安装依赖、初始化数据、启动服务）
./start.sh
```

### 方式二：手动步骤

#### 1. 安装依赖

```bash
# uv 会自动创建 Python 3.12 虚拟环境并安装依赖
uv sync
```

#### 2. 启动基础服务（使用Docker Compose）

```bash
# 启动MongoDB和FalkorDB
docker-compose up -d

# 查看服务状态
docker-compose ps
```

#### 3. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，填入实际配置
```

必需配置：
- `MONGODB_URL`: MongoDB连接地址
- `LLM_API_KEY`: OpenAI API密钥（或其他兼容API）
- `FALKORDB_HOST`: FalkorDB主机地址（默认localhost）

#### 4. 启动FalkorDB

```bash
# 使用Docker启动FalkorDB（推荐）
docker run -d -p 6379:6379 --name citywalk-falkordb falkordb/falkordb:latest

# 或使用Redis Stack（包含RedisGraph模块）
docker run -d -p 6379:6379 --name citywalk-redis redis/redis-stack-server:latest
```

#### 5. 初始化数据库

```bash
# 初始化MongoDB示例数据
uv run python scripts/init_db.py

# 初始化FalkorDB知识图谱
uv run python scripts/init_knowledge_graph.py
```

#### 6. 启动服务

```bash
# 开发模式（自动重载）
uv run uvicorn app.main:app --reload --port 8000

# 生产模式
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

#### 7. 访问API文档

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 功能测试

### 测试基础API

```bash
# 安装测试依赖
pip install httpx

# 运行测试脚本
python scripts/test_api.py
```

### 测试智能搜索

```bash
# 使用curl测试流式搜索
curl -X POST "http://localhost:8000/api/v1/search/stream" \
  -H "Content-Type: application/json" \
  -d '{"query": "推荐一条适合周末的休闲路线"}' \
  --no-buffer
```

### 使用Python测试

```python
import httpx

# 流式搜索
with httpx.stream(
    "POST",
    "http://localhost:8000/api/v1/search/stream",
    json={"query": "杭州有什么好玩的路线"}
) as response:
    for line in response.iter_lines():
        if line.startswith("data: "):
            print(line[6:])
```

## API端点说明

### 路线管理 `/api/v1/routes`

- `GET /routes` - 获取路线列表（支持分页、筛选、附近搜索）
- `GET /routes/{id}` - 获取路线详情
- `POST /routes` - 创建路线
- `PUT /routes/{id}` - 更新路线
- `DELETE /routes/{id}` - 删除路线
- `POST /routes/{id}/favorite` - 收藏/取消收藏

### 导航功能 `/api/v1/navigation`

- `GET /navigation/{id}` - 获取导航数据
- `GET /navigation/amap/{id}` - 获取高德地图数据
- `GET /navigation/poi/{id}` - 获取POI信息

### GPS轨迹 `/api/v1/gps`

- `POST /gps` - 创建GPS轨迹
- `GET /gps/{id}` - 获取轨迹详情
- `GET /gps/user/{user_id}` - 获取用户轨迹列表
- `PUT /gps/{id}` - 更新轨迹
- `DELETE /gps/{id}` - 删除轨迹

### 智能搜索 `/api/v1/search`

- `POST /search` - 智能搜索（非流式）
- `POST /search/stream` - 智能搜索（流式SSE）
- `POST /search/quick` - 快速搜索

## 项目结构

```
app/
├── main.py              # FastAPI应用入口
├── config.py            # 配置管理
├── database.py          # MongoDB连接
├── models/              # 数据模型（Route, POI, User）
├── schemas/             # API schemas（请求/响应模型）
├── api/                 # API路由
│   ├── routes.py       # 路线API
│   ├── navigation.py   # 导航API
│   ├── gps.py          # GPS轨迹API
│   └── search.py       # 智能搜索API
├── services/            # 业务逻辑层
│   ├── route_service.py
│   ├── gps_service.py
│   └── navigation_service.py
├── agent/               # Agent系统（LLM + 知识库）
│   ├── context.py      # 上下文构建
│   ├── loop.py         # Agent循环
│   ├── memory.py       # 记忆管理
│   └── tools/          # Agent工具
│       ├── route_search.py
│       └── knowledge_search.py
└── utils/               # 工具函数
```

## 常见问题

### Q: MongoDB连接失败？
A: 检查MongoDB是否启动，连接地址是否正确

### Q: FalkorDB连接失败？
A: 
1. 确认FalkorDB容器是否运行：`docker ps | grep falkordb`
2. 检查端口是否被占用：`lsof -i:6379`
3. 查看容器日志：`docker logs citywalk-falkordb`

### Q: LLM调用失败？
A: 检查API密钥是否有效，网络是否可访问

### Q: 知识图谱搜索无结果？
A: 
1. 确认FalkorDB已启动
2. 运行 `python scripts/init_knowledge_graph.py` 初始化知识图谱
3. 检查知识图谱统计：`GET /api/v1/search/stats`

### Q: 如何添加自定义路线？
A: 使用POST `/api/v1/routes` 接口，或直接操作MongoDB

## 下一步

1. 配置高德地图API密钥以启用导航功能
2. 安装Neo4j并配置Graphiti以启用知识图谱
3. 根据需求调整LLM模型和参数
4. 添加用户认证和权限管理
5. 实现前端界面

## 技术支持

- 文档: http://localhost:8000/docs
- 问题反馈: 创建GitHub Issue
