"""测试流式搜索功能"""

import asyncio
import json

import httpx
from loguru import logger


async def test_search_stream():
    """测试流式搜索（SSE）"""
    
    # 测试查询
    test_queries = [
        "推荐一条适合周末的休闲路线",
        "杭州有什么好玩的citywalk路线",
        "适合拍照的轻松路线"
    ]
    
    base_url = "http://localhost:8000"
    
    logger.info("=" * 60)
    logger.info("测试流式搜索功能")
    logger.info("=" * 60)
    
    # 先检查服务是否运行
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{base_url}/health", timeout=5.0)
            if response.status_code != 200:
                logger.error("服务未运行，请先启动服务")
                return
            logger.info(f"✓ 服务运行正常: {response.json()}")
    except Exception as e:
        logger.error(f"❌ 无法连接到服务: {e}")
        logger.info("请先启动服务: uv run uvicorn app.main:app --reload")
        return
    
    # 测试每个查询
    for i, query in enumerate(test_queries, 1):
        logger.info(f"\n{'=' * 60}")
        logger.info(f"测试 {i}/{len(test_queries)}: {query}")
        logger.info("=" * 60)
        
        try:
            # 使用流式请求
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream(
                    "POST",
                    f"{base_url}/api/v1/search/stream",
                    json={
                        "query": query,
                        "user_id": "test_user_001",
                        "session_id": f"test_session_{i}"
                    },
                    headers={"Accept": "text/event-stream"}
                ) as response:
                    logger.info(f"响应状态: {response.status_code}")
                    logger.info(f"Content-Type: {response.headers.get('content-type')}")
                    
                    if response.status_code != 200:
                        error_text = await response.aread()
                        logger.error(f"请求失败: {error_text.decode()}")
                        continue
                    
                    logger.info("\n📝 流式响应:\n")
                    logger.info("-" * 60)
                    
                    # 读取流式响应
                    chunk_count = 0
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        
                        chunk_count += 1
                        
                        # 解析 SSE 格式
                        if line.startswith("data: "):
                            try:
                                data = json.loads(line[6:])
                                
                                # 根据类型显示不同的内容
                                event_type = data.get("type", "")
                                
                                if event_type == "text":
                                    # 文本内容
                                    print(data.get("content", ""), end="", flush=True)
                                
                                elif event_type == "tool_call":
                                    # 工具调用
                                    tool_name = data.get("name", "")
                                    tool_args = data.get("arguments", "")
                                    logger.info(f"\n🔧 调用工具: {tool_name}")
                                    logger.info(f"   参数: {tool_args[:100]}...")
                                
                                elif event_type == "tool_result":
                                    # 工具结果
                                    tool_name = data.get("name", "")
                                    result = data.get("result", "")
                                    logger.info(f"\n✓ 工具结果: {tool_name}")
                                    logger.info(f"   结果: {result}")
                                
                                elif event_type == "done":
                                    # 完成
                                    logger.info("\n\n✅ 响应完成")
                                
                                elif event_type == "error":
                                    # 错误
                                    logger.error(f"\n❌ 错误: {data.get('message', '')}")
                                
                                else:
                                    # 其他类型
                                    logger.debug(f"\n未知类型: {event_type}")
                                    logger.debug(f"数据: {data}")
                            
                            except json.JSONDecodeError as e:
                                logger.warning(f"无法解析 JSON: {line}")
                                logger.warning(f"错误: {e}")
                        
                        elif line.startswith(":"):
                            # SSE 注释
                            pass
                        
                        else:
                            # 其他行
                            logger.debug(f"原始行: {line}")
                    
                    logger.info(f"\n\n📊 统计:")
                    logger.info(f"   接收到 {chunk_count} 个数据块")
                    logger.info("-" * 60)
        
        except httpx.TimeoutException:
            logger.error(f"⏱️ 请求超时")
        except Exception as e:
            logger.error(f"❌ 请求失败: {e}")
            import traceback
            traceback.print_exc()
    
    logger.info("\n" + "=" * 60)
    logger.info("测试完成!")
    logger.info("=" * 60)


async def test_search_non_stream():
    """测试非流式搜索"""
    
    base_url = "http://localhost:8000"
    query = "推荐一条适合周末的休闲路线"
    
    logger.info("=" * 60)
    logger.info("测试非流式搜索")
    logger.info("=" * 60)
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{base_url}/api/v1/search",
                json={
                    "query": query,
                    "user_id": "test_user_001"
                }
            )
            
            logger.info(f"响应状态: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"查询: {data.get('query')}")
                logger.info(f"结果数量: {data.get('total')}")
                logger.info(f"消息: {data.get('message')}")
            else:
                logger.error(f"请求失败: {response.text}")
    
    except Exception as e:
        logger.error(f"请求失败: {e}")


async def test_knowledge_graph_search():
    """测试知识图谱搜索"""
    
    base_url = "http://localhost:8000"
    
    logger.info("=" * 60)
    logger.info("测试知识图谱搜索")
    logger.info("=" * 60)
    
    # 测试知识图谱统计
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{base_url}/api/v1/knowledge-graph/stats")
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✓ 知识图谱统计: {data.get('stats')}")
            else:
                logger.warning(f"知识图谱统计失败: {response.status_code}")
    except Exception as e:
        logger.warning(f"知识图谱可能未初始化: {e}")
    
    # 测试知识图谱搜索
    test_queries = ["西湖", "周末", "轻松"]
    
    for query in test_queries:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{base_url}/api/v1/knowledge-graph/search/{query}"
                )
                
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"\n查询 '{query}':")
                    logger.info(f"  结果数量: {data.get('total')}")
                    if data.get('results'):
                        for r in data['results'][:3]:
                            logger.info(f"  - [{r['type']}] {r['name']}")
                else:
                    logger.warning(f"  搜索失败: {response.status_code}")
        
        except Exception as e:
            logger.warning(f"  查询失败: {e}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        test_type = sys.argv[1]
        
        if test_type == "stream":
            asyncio.run(test_search_stream())
        elif test_type == "non-stream":
            asyncio.run(test_search_non_stream())
        elif test_type == "kg":
            asyncio.run(test_knowledge_graph_search())
        else:
            logger.error(f"未知的测试类型: {test_type}")
            logger.info("可用选项: stream, non-stream, kg")
    else:
        # 默认运行所有测试
        logger.info("运行所有测试...\n")
        asyncio.run(test_knowledge_graph_search())
        asyncio.run(test_search_stream())
