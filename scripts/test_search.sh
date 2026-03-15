#!/bin/bash

# 测试搜索功能的完整脚本

set -e

echo "=========================================="
echo "CityWalk 搜索功能测试"
echo "=========================================="

# 检查 uv 是否安装
if ! command -v uv &> /dev/null; then
    echo "❌ uv 未安装，使用 ~/.local/bin/uv"
    UV_CMD="$HOME/.local/bin/uv"
else
    UV_CMD="uv"
fi

# 检查 Docker 服务
echo ""
echo "1️⃣  检查 Docker 服务..."
if ! docker info &> /dev/null; then
    echo "❌ Docker 未运行"
    echo "   请先启动 Docker Desktop"
    exit 1
fi
echo "✓ Docker 运行正常"

# 检查 MongoDB 和 FalkorDB
echo ""
echo "2️⃣  检查数据库服务..."
if ! docker ps | grep -q citywalk-mongo; then
    echo "⚠️  MongoDB 未运行，正在启动..."
    docker-compose up -d mongodb
    sleep 3
fi

if ! docker ps | grep -q citywalk-falkordb; then
    echo "⚠️  FalkorDB 未运行，正在启动..."
    docker-compose up -d falkordb
    sleep 3
fi

echo "✓ 数据库服务正常"

# 检查 API 服务
echo ""
echo "3️⃣  检查 API 服务..."
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✓ API 服务运行正常"
else
    echo "⚠️  API 服务未启动"
    read -p "是否启动 API 服务? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "正在后台启动 API 服务..."
        $UV_CMD run uvicorn app.main:app --host 0.0.0.0 --port 8000 > /tmp/citywalk.log 2>&1 &
        API_PID=$!
        echo "API 服务启动中 (PID: $API_PID)..."
        sleep 5
        
        # 再次检查
        if curl -s http://localhost:8000/health > /dev/null 2>&1; then
            echo "✓ API 服务启动成功"
        else
            echo "❌ API 服务启动失败"
            echo "   查看日志: tail -f /tmp/citywalk.log"
            exit 1
        fi
    else
        echo "请手动启动服务: $UV_CMD run uvicorn app.main:app --reload"
        exit 0
    fi
fi

# 测试搜索功能
echo ""
echo "=========================================="
echo "4️⃣  开始测试搜索功能"
echo "=========================================="

# 测试知识图谱搜索
echo ""
echo "📊 测试知识图谱搜索..."
$UV_CMD run python scripts/test_search_stream.py kg

# 测试流式搜索
echo ""
echo "🌊 测试流式搜索..."
$UV_CMD run python scripts/test_search_stream.py stream

echo ""
echo "=========================================="
echo "✅ 测试完成!"
echo "=========================================="
