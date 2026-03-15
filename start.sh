#!/bin/bash
# CityWalk 项目启动脚本 - 使用 uv

set -e

echo "=========================================="
echo "CityWalk 后端服务启动"
echo "=========================================="

# 检查 uv 是否安装
if ! command -v uv &> /dev/null; then
    echo "❌ uv 未安装"
    echo ""
    echo "请先安装 uv:"
    echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo ""
    exit 1
fi

echo "✓ uv 已安装: $(uv --version)"

# 检查 Docker 是否运行
if ! docker info &> /dev/null; then
    echo "⚠️  Docker 未运行，跳过服务启动检查"
    echo "   请确保 MongoDB 和 FalkorDB 已启动"
else
    echo "✓ Docker 正在运行"
    
    # 检查 MongoDB 和 FalkorDB 是否运行
    if ! docker ps | grep -q citywalk-mongo; then
        echo "⚠️  MongoDB 容器未运行"
        read -p "是否启动所有服务? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            docker-compose up -d
            sleep 3
        fi
    else
        echo "✓ MongoDB 容器正在运行"
    fi
    
    if docker ps | grep -q citywalk-falkordb; then
        echo "✓ FalkorDB 容器正在运行"
    fi
fi

echo ""
echo "=========================================="
echo "安装依赖"
echo "=========================================="

# 使用 uv 同步依赖
uv sync

echo ""
echo "=========================================="
echo "检查环境配置"
echo "=========================================="

if [ ! -f .env ]; then
    echo "⚠️  .env 文件不存在，从模板创建..."
    cp .env.example .env
    echo "✓ 已创建 .env 文件，请编辑配置后重新启动"
    exit 1
fi

echo "✓ .env 文件存在"

# 检查必要的配置
if grep -q "your-api-key-here" .env; then
    echo "⚠️  请在 .env 文件中配置 LLM_API_KEY"
fi

echo ""
echo "=========================================="
echo "初始化数据（如果需要）"
echo "=========================================="

# 检查是否需要初始化数据库
read -p "是否需要初始化数据库? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "初始化 MongoDB 数据..."
    uv run python scripts/init_db.py
    
    echo "初始化 FalkorDB 知识图谱..."
    uv run python scripts/init_knowledge_graph.py
fi

echo ""
echo "=========================================="
echo "启动服务"
echo "=========================================="

# 获取调试模式配置
DEBUG=$(grep DEBUG .env | cut -d'=' -f2 | tr -d ' ')

if [ "$DEBUG" = "true" ]; then
    echo "🚀 启动开发服务器（自动重载）..."
    uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
else
    echo "🚀 启动生产服务器..."
    uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
fi
