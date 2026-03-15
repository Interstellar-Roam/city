"""知识图谱初始化脚本 - 将MongoDB路线数据同步到FalkorDB"""

import asyncio

from loguru import logger
from motor.motor_asyncio import AsyncIOMotorClient

from app.config import get_settings
from app.agent.memory import KnowledgeBaseClient


async def init_knowledge_graph():
    """初始化知识图谱"""
    settings = get_settings()
    
    # 连接MongoDB
    mongo_client = AsyncIOMotorClient(settings.mongodb_url)
    db = mongo_client[settings.mongodb_db_name]
    
    # 连接FalkorDB
    kg_client = KnowledgeBaseClient()
    await kg_client.connect()
    
    logger.info("开始初始化知识图谱...")
    
    # 获取所有已发布的路线
    routes = await db.routes.find({"is_published": True}).to_list(length=None)
    logger.info(f"找到 {len(routes)} 条路线")
    
    success_count = 0
    error_count = 0
    
    for route in routes:
        try:
            # 添加路线知识到图谱
            await kg_client.add_route_knowledge(
                route_id=route["_id"],
                name=route["name"],
                description=route.get("description", ""),
                tags=route.get("tags", []),
                metadata={
                    "distance": route.get("distance", 0),
                    "elevation_gain": route.get("elevation_gain", 0),
                    "difficulty": route.get("difficulty", "medium"),
                    "city": route.get("city", ""),
                    "pois": route.get("pois", [])
                }
            )
            success_count += 1
            logger.info(f"✓ 添加路线: {route['name']}")
            
        except Exception as e:
            error_count += 1
            logger.error(f"✗ 添加路线失败 {route['_id']}: {e}")
    
    # 获取统计信息
    stats = await kg_client.get_stats()
    
    logger.info("=" * 60)
    logger.info("知识图谱初始化完成!")
    logger.info(f"成功: {success_count} 条路线")
    logger.info(f"失败: {error_count} 条路线")
    logger.info(f"图谱统计: {stats}")
    logger.info("=" * 60)
    
    # 关闭连接
    await kg_client.close()
    mongo_client.close()


async def test_knowledge_graph():
    """测试知识图谱搜索"""
    settings = get_settings()
    
    kg_client = KnowledgeBaseClient()
    await kg_client.connect()
    
    # 测试搜索
    test_queries = [
        "西湖",
        "周末",
        "轻松",
        "北京"
    ]
    
    logger.info("\n测试知识图谱搜索:")
    logger.info("=" * 60)
    
    for query in test_queries:
        results = await kg_client.search(query, limit=5)
        logger.info(f"\n查询: '{query}'")
        logger.info(f"结果: {len(results)} 条")
        for r in results[:3]:
            logger.info(f"  - [{r['type']}] {r['name']}")
    
    # 测试获取路线关系
    logger.info("\n\n测试获取路线关系:")
    logger.info("=" * 60)
    
    relations = await kg_client.get_route_relations("route_001")
    logger.info(f"相似路线: {len(relations.get('similar_routes', []))} 条")
    logger.info(f"同城路线: {len(relations.get('nearby_routes', []))} 条")
    
    await kg_client.close()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # 运行测试
        asyncio.run(test_knowledge_graph())
    else:
        # 初始化知识图谱
        asyncio.run(init_knowledge_graph())
