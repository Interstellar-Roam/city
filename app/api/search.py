"""智能搜索API路由"""

from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from loguru import logger

from app.schemas.search import SearchRequest, SearchResponse
from app.agent.loop import AgentLoop

router = APIRouter(prefix="/search", tags=["智能搜索"])

# Agent实例（单例）
_agent: AgentLoop | None = None


async def get_agent() -> AgentLoop:
    """获取Agent实例"""
    global _agent
    if _agent is None:
        _agent = AgentLoop()
        await _agent.connect()
    return _agent


@router.post("", response_model=SearchResponse, summary="智能搜索路线")
async def search_routes(request: SearchRequest) -> SearchResponse:
    """
    基于自然语言的智能路线搜索

    示例查询：
    - "我想找个适合周末散步的路线，不要太远"
    - "推荐一条有咖啡店的citywalk路线"
    - "适合拍照的路线，长度5公里左右"
    """
    # TODO: 实现非流式搜索
    return SearchResponse(
        query=request.query,
        results=[],
        total=0,
        has_more=False,
        message="请使用流式搜索接口"
    )


@router.post("/stream", summary="流式智能搜索（SSE）")
async def search_routes_stream(request: SearchRequest) -> StreamingResponse:
    """
    流式智能搜索（Server-Sent Events）

    返回SSE格式的流式响应，包括：
    - 思考过程
    - 工具调用
    - 搜索结果
    - 最终答案
    """
    agent = await get_agent()

    async def event_stream():
        try:
            async for chunk in agent.process(
                query=request.query,
                user_id=request.user_id,
                session_id=request.session_id,
                context=request.context
            ):
                yield chunk
        except Exception as e:
            logger.error(f"搜索错误: {e}")
            yield f"data: {{\"type\": \"error\", \"message\": \"{str(e)}\"}}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/quick", summary="快速搜索（仅返回结果）")
async def quick_search(request: SearchRequest) -> dict[str, Any]:
    """
    快速搜索，直接返回路线结果，不包含AI解释

    适合需要快速获取结果的场景
    """
    # TODO: 实现快速搜索逻辑
    # 直接调用RouteService的搜索方法
    return {
        "success": True,
        "query": request.query,
        "results": [],
        "message": "快速搜索功能开发中"
    }


@router.on_event("shutdown")
async def shutdown_event():
    """关闭Agent连接"""
    global _agent
    if _agent:
        await _agent.close()
        _agent = None
