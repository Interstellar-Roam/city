"""FalkorDB连接测试脚本"""

import asyncio

from loguru import logger

from app.config import get_settings
from app.agent.memory import KnowledgeBaseClient


async def test_falkordb_connection():
    """测试FalkorDB连接"""
    settings = get_settings()
    
    logger.info("=" * 60)
    logger.info("FalkorDB 连接测试")
    logger.info("=" * 60)
    logger.info(f"主机: {settings.falkordb_host}")
    logger.info(f"端口: {settings.falkordb_port}")
    logger.info(f"图谱名称: {settings.falkordb_graph_name}")
    logger.info("=" * 60)
    
    try:
        # 创建客户端
        client = KnowledgeBaseClient()
        
        # 连接
        logger.info("\n1. 测试连接...")
        await client.connect()
        logger.info("✓ 连接成功")
        
        # 添加测试数据
        logger.info("\n2. 测试添加路线知识...")
        await client.add_route_knowledge(
            route_id="test_route_001",
            name="测试路线",
            description="这是一条测试路线",
            tags=["测试", "示例"],
            metadata={
                "distance": 5000,
                "elevation_gain": 100,
                "difficulty": "easy",
                "city": "测试城市",
                "pois": [
                    {
                        "id": "test_poi_001",
                        "name": "测试景点",
                        "description": "这是一个测试景点",
                        "category": "景点",
                        "rating": 4.5
                    }
                ]
            }
        )
        logger.info("✓ 添加成功")
        
        # 搜索测试
        logger.info("\n3. 测试搜索功能...")
        results = await client.search("测试", limit=5)
        logger.info(f"✓ 搜索结果: {len(results)} 条")
        for r in results:
            logger.info(f"  - [{r['type']}] {r['name']}")
        
        # 获取关系
        logger.info("\n4. 测试获取路线关系...")
        relations = await client.get_route_relations("test_route_001")
        logger.info(f"✓ 相似路线: {len(relations.get('similar_routes', []))} 条")
        logger.info(f"✓ 同城路线: {len(relations.get('nearby_routes', []))} 条")
        
        # 获取统计
        logger.info("\n5. 测试统计信息...")
        stats = await client.get_stats()
        logger.info(f"✓ 统计信息: {stats}")
        
        # 清理测试数据
        logger.info("\n6. 清理测试数据...")
        # 注意：这里不清空整个图谱，只是提示
        logger.info("✓ 测试完成（测试数据保留用于演示）")
        
        # 关闭连接
        await client.close()
        logger.info("\n✓ 连接已关闭")
        
        logger.info("\n" + "=" * 60)
        logger.info("所有测试通过! ✓")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_natural_language_search():
    """测试自然语言搜索"""
    logger.info("\n" + "=" * 60)
    logger.info("自然语言搜索测试")
    logger.info("=" * 60)
    
    client = KnowledgeBaseClient()
    await client.connect()
    
    # 先添加一些测试数据
    test_routes = [
        {
            "route_id": "easy_route_001",
            "name": "周末休闲漫步",
            "description": "适合周末放松的轻松路线",
            "tags": ["周末", "轻松", "休闲"],
            "metadata": {
                "difficulty": "easy",
                "distance": 3000,
                "city": "杭州"
            }
        },
        {
            "route_id": "hard_route_001",
            "name": "挑战者登山路线",
            "description": "适合喜欢挑战的登山爱好者",
            "tags": ["挑战", "登山", "困难"],
            "metadata": {
                "difficulty": "hard",
                "distance": 15000,
                "city": "北京"
            }
        }
    ]
    
    logger.info("添加测试路线...")
    for route in test_routes:
        await client.add_route_knowledge(**route)
        logger.info(f"  ✓ {route['name']}")
    
    # 测试自然语言搜索
    queries = [
        "适合周末的轻松路线",
        "挑战路线",
        "登山"
    ]
    
    logger.info("\n测试自然语言搜索:")
    for query in queries:
        logger.info(f"\n查询: '{query}'")
        results = await client.search(query, limit=5)
        logger.info(f"结果: {len(results)} 条")
        for r in results:
            logger.info(f"  - [{r.get('difficulty', 'N/A')}] {r['name']}")
    
    await client.close()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "nl":
        # 测试自然语言搜索
        asyncio.run(test_natural_language_search())
    else:
        # 基础连接测试
        asyncio.run(test_falkordb_connection())
