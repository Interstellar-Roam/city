"""API测试脚本"""

import asyncio

import httpx


BASE_URL = "http://localhost:8000"


async def test_apis():
    """测试主要API端点"""
    async with httpx.AsyncClient() as client:
        print("=" * 60)
        print("开始测试 CityWalk API")
        print("=" * 60)

        # 1. 健康检查
        print("\n1. 健康检查")
        response = await client.get(f"{BASE_URL}/health")
        print(f"   状态: {response.status_code}")
        print(f"   响应: {response.json()}")

        # 2. 获取路线列表
        print("\n2. 获取路线列表")
        response = await client.get(f"{BASE_URL}/api/v1/routes", params={"page": 1, "page_size": 10})
        print(f"   状态: {response.status_code}")
        data = response.json()
        print(f"   总数: {data['total']}")
        if data['items']:
            print(f"   第一条路线: {data['items'][0]['name']}")

        # 3. 获取路线详情
        print("\n3. 获取路线详情")
        route_id = "route_001"
        response = await client.get(f"{BASE_URL}/api/v1/routes/{route_id}")
        print(f"   状态: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   路线名称: {data['name']}")
            print(f"   距离: {data['distance']}米")
            print(f"   预计时间: {data['estimated_duration']}分钟")

        # 4. 搜索路线
        print("\n4. 搜索路线（关键词：西湖）")
        response = await client.get(f"{BASE_URL}/api/v1/routes/search/西湖")
        print(f"   状态: {response.status_code}")
        data = response.json()
        print(f"   搜索结果: {data['total']}条")

        # 5. 获取导航数据
        print("\n5. 获取导航数据")
        response = await client.get(f"{BASE_URL}/api/v1/navigation/{route_id}")
        print(f"   状态: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   路线点数: {len(data['points'])}")
            print(f"   POI数: {len(data['pois'])}")

        # 6. 创建GPS轨迹
        print("\n6. 创建GPS轨迹")
        track_data = {
            "route_id": route_id,
            "user_id": "user_001",
            "points": [
                {
                    "location": {"type": "Point", "coordinates": [120.1498, 30.2599]},
                    "elevation": 10.5,
                    "timestamp": "2024-01-01T10:00:00"
                },
                {
                    "location": {"type": "Point", "coordinates": [120.1500, 30.2601]},
                    "elevation": 11.2,
                    "timestamp": "2024-01-01T10:05:00"
                }
            ],
            "started_at": "2024-01-01T10:00:00"
        }
        response = await client.post(f"{BASE_URL}/api/v1/gps", json=track_data)
        print(f"   状态: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   轨迹ID: {data['data']['_id']}")
            print(f"   距离: {data['data']['distance']:.2f}米")

        # 7. 知识图谱统计
        print("\n7. 知识图谱统计")
        response = await client.get(f"{BASE_URL}/api/v1/knowledge-graph/stats")
        print(f"   状态: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   统计信息: {data['stats']}")

        # 8. 知识图谱搜索
        print("\n8. 知识图谱搜索")
        response = await client.get(f"{BASE_URL}/api/v1/knowledge-graph/search/西湖")
        print(f"   状态: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   搜索结果: {data['total']}条")

        # 9. 智能搜索（流式）
        print("\n9. 智能搜索（流式）")
        print("   查询: '推荐一条适合周末的休闲路线'")
        print("   响应: ", end="")
        async with client.stream(
            "POST",
            f"{BASE_URL}/api/v1/search/stream",
            json={"query": "推荐一条适合周末的休闲路线"},
            timeout=30.0
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    print(line[6:], end="", flush=True)
        print("\n")

        print("=" * 60)
        print("测试完成!")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_apis())
