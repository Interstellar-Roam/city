"""知识图谱API路由"""

from typing import Any

from fastapi import APIRouter, HTTPException
from loguru import logger

from app.agent.memory import KnowledgeBaseClient

router = APIRouter(prefix="/knowledge-graph", tags=["知识图谱"])


@router.get("/stats", summary="获取知识图谱统计信息")
async def get_kg_stats() -> dict[str, Any]:
    """
    获取知识图谱的统计信息
    
    包括：
    - 路线节点数量
    - POI节点数量
    - 标签数量
    - 城市数量
    """
    try:
        client = KnowledgeBaseClient()
        await client.connect()
        stats = await client.get_stats()
        await client.close()
        
        return {
            "success": True,
            "stats": stats
        }
    except Exception as e:
        logger.error(f"获取知识图谱统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search/{query}", summary="搜索知识图谱")
async def search_kg(
    query: str,
    limit: int = 10
) -> dict[str, Any]:
    """
    搜索知识图谱
    
    支持搜索：
    - 路线名称和描述
    - POI名称和描述
    - 标签关联
    """
    try:
        client = KnowledgeBaseClient()
        await client.connect()
        results = await client.search(query, limit=limit)
        await client.close()
        
        return {
            "success": True,
            "query": query,
            "total": len(results),
            "results": results
        }
    except Exception as e:
        logger.error(f"搜索知识图谱失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/route/{route_id}/relations", summary="获取路线关联信息")
async def get_route_relations(route_id: str) -> dict[str, Any]:
    """
    获取路线的关联信息
    
    包括：
    - 相似路线（基于标签）
    - 同城路线
    - 相关POI
    """
    try:
        client = KnowledgeBaseClient()
        await client.connect()
        relations = await client.get_route_relations(route_id)
        await client.close()
        
        return {
            "success": True,
            "route_id": route_id,
            "relations": relations
        }
    except Exception as e:
        logger.error(f"获取路线关联失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync/{route_id}", summary="同步路线到知识图谱")
async def sync_route_to_kg(route_id: str) -> dict[str, Any]:
    """
    将指定路线同步到知识图谱
    
    用于更新或添加路线知识
    """
    try:
        from app.database import Database
        from motor.motor_asyncio import AsyncIOMotorDatabase
        
        db = Database.get_db()
        route = await db.routes.find_one({"_id": route_id})
        
        if not route:
            raise HTTPException(status_code=404, detail="路线不存在")
        
        client = KnowledgeBaseClient()
        await client.connect()
        
        await client.add_route_knowledge(
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
        
        await client.close()
        
        return {
            "success": True,
            "message": f"路线 '{route['name']}' 已同步到知识图谱"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"同步路线到知识图谱失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
