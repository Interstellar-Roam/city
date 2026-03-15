"""数据库初始化脚本 - 创建示例路线数据"""

import asyncio
import random
from datetime import datetime, timedelta

from motor.motor_asyncio import AsyncIOMotorClient

from app.config import get_settings


async def create_sample_routes():
    """创建示例路线数据"""
    settings = get_settings()
    client = AsyncIOMotorClient(settings.mongodb_url)
    db = client[settings.mongodb_db_name]

    # 示例路线数据
    sample_routes = [
        {
            "_id": "route_001",
            "name": "杭州西湖环湖漫步",
            "description": "环绕美丽的西湖，欣赏湖光山色，途径断桥、白堤、苏堤等经典景点。适合周末休闲漫步，全程平缓，老少皆宜。",
            "preview_image": "https://example.com/westlake.jpg",
            "images": [
                "https://example.com/westlake1.jpg",
                "https://example.com/westlake2.jpg",
                "https://example.com/westlake3.jpg"
            ],
            "points": _generate_lake_points(),
            "pois": [
                {
                    "id": "poi_001",
                    "name": "断桥残雪",
                    "location": {"type": "Point", "coordinates": [120.1498, 30.2599]},
                    "category": "景点",
                    "description": "西湖十景之一，白娘子传说的发源地",
                    "images": ["https://example.com/duanqiao.jpg"],
                    "rating": 4.8,
                    "tags": ["经典", "拍照打卡"]
                },
                {
                    "id": "poi_002",
                    "name": "平湖秋月",
                    "location": {"type": "Point", "coordinates": [120.1447, 30.2547]},
                    "category": "景点",
                    "description": "西湖十景之一，赏月胜地",
                    "images": ["https://example.com/pinghu.jpg"],
                    "rating": 4.6,
                    "tags": ["赏景", "夜景"]
                }
            ],
            "distance": 12000,
            "elevation_gain": 50,
            "estimated_duration": 180,
            "start_location": {"type": "Point", "coordinates": [120.1498, 30.2599]},
            "end_location": {"type": "Point", "coordinates": [120.1498, 30.2599]},
            "city": "杭州",
            "district": "西湖区",
            "favorites_count": 1523,
            "views_count": 8520,
            "completions_count": 342,
            "difficulty": "easy",
            "tags": ["环湖", "经典", "休闲", "拍照", "新手友好"],
            "created_at": datetime.now() - timedelta(days=30),
            "updated_at": datetime.now(),
            "is_published": True
        },
        {
            "_id": "route_002",
            "name": "上海外滩-南京路CityWalk",
            "description": "从外滩出发，漫步南京路步行街，感受上海的历史与现代交融。沿途可欣赏万国建筑群、外滩夜景、繁华商业街。",
            "preview_image": "https://example.com/bund.jpg",
            "images": [
                "https://example.com/bund1.jpg",
                "https://example.com/bund2.jpg"
            ],
            "points": _generate_city_points(),
            "pois": [
                {
                    "id": "poi_003",
                    "name": "外滩",
                    "location": {"type": "Point", "coordinates": [121.4903, 31.2397]},
                    "category": "景点",
                    "description": "上海的标志性地标，万国建筑博览群",
                    "images": ["https://example.com/waitan.jpg"],
                    "rating": 4.9,
                    "tags": ["地标", "夜景", "建筑"]
                }
            ],
            "distance": 5000,
            "elevation_gain": 10,
            "estimated_duration": 120,
            "start_location": {"type": "Point", "coordinates": [121.4903, 31.2397]},
            "end_location": {"type": "Point", "coordinates": [121.4765, 31.2345]},
            "city": "上海",
            "district": "黄浦区",
            "favorites_count": 2341,
            "views_count": 12300,
            "completions_count": 567,
            "difficulty": "easy",
            "tags": ["城市", "夜景", "购物", "美食", "新手友好"],
            "created_at": datetime.now() - timedelta(days=15),
            "updated_at": datetime.now(),
            "is_published": True
        },
        {
            "_id": "route_003",
            "name": "北京南锣鼓巷-什刹海漫步",
            "description": "探索老北京胡同文化，从南锣鼓巷出发，途径什刹海、后海，感受老北京的烟火气息。沿途有众多特色小店、酒吧、餐厅。",
            "preview_image": "https://example.com/nanluo.jpg",
            "images": [
                "https://example.com/nanluo1.jpg",
                "https://example.com/shichahai.jpg"
            ],
            "points": _generate_hutong_points(),
            "pois": [
                {
                    "id": "poi_004",
                    "name": "南锣鼓巷",
                    "location": {"type": "Point", "coordinates": [116.4039, 39.9373]},
                    "category": "景点",
                    "description": "北京最古老的街区之一，胡同文化代表",
                    "images": ["https://example.com/nanluoguxiang.jpg"],
                    "rating": 4.5,
                    "tags": ["胡同", "小吃", "文艺"]
                }
            ],
            "distance": 4500,
            "elevation_gain": 20,
            "estimated_duration": 150,
            "start_location": {"type": "Point", "coordinates": [116.4039, 39.9373]},
            "end_location": {"type": "Point", "coordinates": [116.3835, 39.9431]},
            "city": "北京",
            "district": "东城区",
            "favorites_count": 1892,
            "views_count": 9876,
            "completions_count": 423,
            "difficulty": "easy",
            "tags": ["胡同", "文化", "美食", "文艺", "新手友好"],
            "created_at": datetime.now() - timedelta(days=20),
            "updated_at": datetime.now(),
            "is_published": True
        }
    ]

    # 清空现有数据
    await db.routes.delete_many({})
    
    # 插入示例数据
    result = await db.routes.insert_many(sample_routes)
    print(f"已创建 {len(result.inserted_ids)} 条示例路线")

    # 创建索引
    await db.routes.create_index([("location", "2dsphere")])
    await db.routes.create_index([("name", "text"), ("description", "text")])
    await db.routes.create_index([("created_at", -1)])
    await db.routes.create_index([("favorites_count", -1)])
    print("索引创建完成")

    client.close()


def _generate_lake_points():
    """生成环湖路线点"""
    points = []
    base_lon, base_lat = 120.1498, 30.2599
    for i in range(20):
        angle = i * 18 * 3.14159 / 180
        lon = base_lon + 0.02 * math.cos(angle)
        lat = base_lat + 0.015 * math.sin(angle)
        points.append({
            "location": {"type": "Point", "coordinates": [lon, lat]},
            "elevation": 10 + random.random() * 5,
            "timestamp": (datetime.now() - timedelta(minutes=i * 10)).isoformat()
        })
    return points


def _generate_city_points():
    """生成城市路线点"""
    points = []
    start_lon, start_lat = 121.4903, 31.2397
    for i in range(15):
        lon = start_lon - i * 0.001
        lat = start_lat - i * 0.0005
        points.append({
            "location": {"type": "Point", "coordinates": [lon, lat]},
            "elevation": 5 + random.random() * 3,
            "timestamp": (datetime.now() - timedelta(minutes=i * 8)).isoformat()
        })
    return points


def _generate_hutong_points():
    """生成胡同路线点"""
    points = []
    start_lon, start_lat = 116.4039, 39.9373
    for i in range(12):
        lon = start_lon - i * 0.0015
        lat = start_lat + random.random() * 0.0005
        points.append({
            "location": {"type": "Point", "coordinates": [lon, lat]},
            "elevation": 45 + random.random() * 5,
            "timestamp": (datetime.now() - timedelta(minutes=i * 12)).isoformat()
        })
    return points


if __name__ == "__main__":
    import math
    asyncio.run(create_sample_routes())
