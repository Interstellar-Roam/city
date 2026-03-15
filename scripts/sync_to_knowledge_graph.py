"""将MongoDB路线数据同步到FalkorDB知识图谱"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from loguru import logger
import sys
sys.path.insert(0, '/Users/rob/CodeBuddy/walk')

from app.agent.memory import KnowledgeBaseClient


async def sync_routes_to_knowledge_graph():
    """同步路线数据到知识图谱"""
    
    # 连接MongoDB
    mongo_client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = mongo_client.citywalk
    routes_collection = db.routes
    
    # 连接FalkorDB
    knowledge_client = KnowledgeBaseClient()
    
    try:
        await knowledge_client.connect()
        print("✅ 已连接到FalkorDB")
        
        # 清空现有图谱数据
        await knowledge_client.clear_graph()
        print("🗑️ 已清空现有知识图谱")
        
        # 读取MongoDB中的所有路线
        routes = await routes_collection.find({}).to_list(length=100)
        print(f"📚 从MongoDB读取了 {len(routes)} 条路线")
        
        # 同步每条路线到知识图谱
        success_count = 0
        for route in routes:
            try:
                # 准备POI数据
                pois = []
                if "pois" in route:
                    for poi in route["pois"]:
                        pois.append({
                            "id": poi.get("id", str(hash(poi.get("name", "")))),
                            "name": poi.get("name", ""),
                            "description": poi.get("description", ""),
                            "category": poi.get("category", ""),
                            "rating": poi.get("rating", 0)
                        })
                
                # 添加到知识图谱
                await knowledge_client.add_route_knowledge(
                    route_id=route["_id"],
                    name=route["name"],
                    description=route.get("description", ""),
                    tags=route.get("tags", []),
                    metadata={
                        "distance": route.get("distance", 0),
                        "elevation_gain": route.get("elevation_gain", 0),
                        "difficulty": route.get("difficulty", "medium"),
                        "city": route.get("city", ""),
                        "pois": pois
                    }
                )
                success_count += 1
                print(f"  ✓ [{success_count}/{len(routes)}] {route['name']}")
                
            except Exception as e:
                print(f"  ✗ 同步失败: {route['name']} - {e}")
        
        # 获取统计信息
        stats = await knowledge_client.get_stats()
        print(f"\n📊 知识图谱统计:")
        print(f"   - 路线节点: {stats.get('routes', 0)}")
        print(f"   - POI节点: {stats.get('pois', 0)}")
        print(f"   - 标签节点: {stats.get('tags', 0)}")
        print(f"   - 城市节点: {stats.get('cities', 0)}")
        
        print(f"\n✅ 同步完成! 成功同步 {success_count}/{len(routes)} 条路线到知识图谱")
        
    except Exception as e:
        print(f"❌ 同步失败: {e}")
        raise
    finally:
        await knowledge_client.close()
        mongo_client.close()


async def test_knowledge_search():
    """测试知识图谱搜索"""
    knowledge_client = KnowledgeBaseClient()
    
    try:
        await knowledge_client.connect()
        print("\n🔍 测试知识图谱搜索...\n")
        
        # 测试搜索
        test_queries = [
            "咖啡",
            "周末",
            "上海",
            "商场",
            "西湖"
        ]
        
        for query in test_queries:
            print(f"搜索: '{query}'")
            results = await knowledge_client.search(query, limit=5)
            print(f"  找到 {len(results)} 条结果:")
            for r in results[:3]:
                print(f"    - [{r['type']}] {r['name']} (相关度: {r['relevance_score']})")
            print()
            
    finally:
        await knowledge_client.close()


async def main():
    """主函数"""
    print("=" * 60)
    print("🔄 开始同步路线数据到知识图谱")
    print("=" * 60)
    
    # 同步数据
    await sync_routes_to_knowledge_graph()
    
    # 测试搜索
    await test_knowledge_search()


if __name__ == "__main__":
    asyncio.run(main())
