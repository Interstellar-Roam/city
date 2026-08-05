# CityWalk Backend

面向城市漫步(CityWalk)的后端服务

## 功能特性

- 🗺️ 路线发现与探索
- 🧭 路线导航
- 🔍 智能路线检索（基于LLM Agent）
- 📍 GPS轨迹存储与管理
- 🧠 知识图谱管理（Graphiti）

## 技术栈

- **框架**: FastAPI
- **用户数据**: MongoDB
- **公域地理数据**: PostgreSQL + PostGIS
- **知识库**: Neo4j + Graphiti
- **LLM**: OpenAI 兼容 API（可选）

## 快速开始

### 方式一：使用 uv（推荐）

#### 1. 安装 uv

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# 或使用 pip
pip install uv
```

#### 2. 启动基础服务

```bash
# 启动MongoDB、PostGIS、FalkorDB和API
docker-compose up -d

# 查看服务状态
docker-compose ps
```

#### 3. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，填入实际配置
```

#### 4. 一键启动（自动安装依赖和初始化）

```bash
./start.sh
```

或手动执行：

```bash
# 安装依赖（自动创建 Python 3.12 虚拟环境）
uv sync

# 初始化数据
uv run python scripts/init_db.py
uv run python scripts/init_knowledge_graph.py
uv run python scripts/seed_geo_places.py

# 启动服务
uv run uvicorn app.main:app --reload
```

### 方式二：使用传统方式

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 启动基础服务
docker-compose up -d

# 配置环境变量
cp .env.example .env

# 初始化数据
python scripts/init_db.py
python scripts/init_knowledge_graph.py

# 启动服务
uvicorn app.main:app --reload
```

## API文档

启动服务后访问:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 地点与多地点路线规划

公域地点存储在 PostGIS，其中不保存用户 ID、贡献者或个性化属性。用户贡献关系、
当前位置、推荐文本和个人路线历史保存在 MongoDB。地点发布后即进入公域，
可被其他用户或未登录访客检索，并用于路线推荐。

内部坐标统一为 WGS-84，生产环境通过高德逐段验证步行可达性；本地 Docker
默认使用带 `is_simulated=true` 标记的确定性测试路由器。

主要接口：

- `POST /api/v1/places`：用户分享地点
- `GET /api/v1/places/search`：公开的 PostGIS 半径、文字、分类与标签搜索
- `POST /api/v1/route-plans`：连接多个指定地点
- `POST /api/v1/route-plans/recommend`：结合文字和 MongoDB 用户偏好生成路线
- `GET /api/v1/route-plans/{id}`：读取持久化路线规划

### Query 路线推荐 Agent

`/route-plans/recommend` 使用一个有界的工具调用 Agent，而不是从模型自由文本里解析
地点或路线：

1. 服务端从认证信息读取用户 ID，从 MongoDB 读取经过裁剪的历史偏好。
2. Agent 调用 `search_public_places`，在请求位置和半径内检索 PostGIS 公域地点；可在预算内细化检索。
3. Agent 只能把已检索返回的地点 ID 交给 `build_route_plan`，不能编造地点或坐标。
4. 服务端重新读取地点，并由路由服务逐段验证步行可达性、总距离和总时长后再持久化。
5. Agent 未配置、超时、模型异常或无法形成有效工具结果时，自动回退到本地意图解析与确定性排序。

精确起点和用户 ID 不发送给模型；模型只接收 query、路线约束、显式分类/标签和
匿名化的偏好摘要。Agent 最多执行有限轮次和有限次地点搜索，也没有修改用户偏好的工具权限。
成功路线的 `score_breakdown.planner_mode` 为 `agent`，回退路线为 `heuristic`。

生产环境配置：

```bash
POSTGRES_DSN=postgresql://citywalk:password@postgres:5432/citywalk
ROUTING_PROVIDER=amap
AMAP_API_KEY_BACKEND=your-web-service-key

# 或使用基于 OpenStreetMap 的 Valhalla 步行路网
# ROUTING_PROVIDER=valhalla
# VALHALLA_BASE_URL=https://your-valhalla.example.com/route

# 可选的 OpenAI 兼容路线推荐 Agent；密钥只放环境变量
RECOMMENDATION_AGENT_ENABLED=true
RECOMMENDATION_AGENT_MAX_ITERATIONS=4
RECOMMENDATION_AGENT_MAX_SEARCHES=3
RECOMMENDATION_AGENT_TIMEOUT_SECONDS=20
LLM_PROVIDER=deepseek
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-v4-flash
LLM_API_KEY=your-key

# 仅控制确定性回退路径中的旧版 LLM 意图解析，通常保持关闭以避免重复调用
RECOMMENDATION_USE_LLM=false
```

`amap` 与 `valhalla` 返回真实步行路网，响应中的 `is_simulated=false`；
`deterministic` 只用于本地单测和离线 E2E，会明确返回 `is_simulated=true`。
生产环境建议自建 Valhalla，公共 demo 端点只适合开发联调。

南山区小红书地点数据集通过 OSM 坐标快照生成并幂等导入：

```bash
python scripts/build_nanshan_xhs_dataset.py --overpass /path/to/nanshan-overpass.json
python scripts/import_nanshan_xhs_places.py
```

本地完整 E2E 会由一个用户贡献四个地点，再由另一个用户搜索并规划路线，
同时验证 PostGIS 不含用户字段、MongoDB 保留贡献归属和私有路线历史：

```bash
./scripts/test_geo_e2e.sh
```

该脚本在 Apple Silicon/ARM64 上会自动选用多架构 PostGIS 镜像；AMD64
服务器和部署配置默认使用官方 `postgis/postgis` 镜像。也可通过
`POSTGIS_IMAGE` 和 `POSTGIS_PLATFORM` 显式覆盖。

也可以在服务已经启动时单独运行：

```bash
E2E_BASE_URL=http://localhost:8000 uv run pytest tests/test_geo_e2e.py -v
```

## 项目结构

```
app/
├── main.py              # 应用入口
├── config.py            # 配置管理
├── database.py          # 数据库连接
├── models/              # 数据模型
├── schemas/             # API schemas
├── api/                 # API路由
├── services/            # 业务逻辑
├── agent/               # Agent系统
└── utils/               # 工具函数
```
