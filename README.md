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
- **数据库**: MongoDB
- **知识库**: Neo4j + Graphiti
- **LLM**: OpenAI API

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
