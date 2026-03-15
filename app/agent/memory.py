"""Agent记忆系统 - 基于FalkorDB的知识图谱"""

from datetime import datetime
from typing import Any

from loguru import logger
from redis import Redis
from redis.commands.graph import Graph
from redis.commands.graph.node import Node

from app.config import get_settings


class MemoryStore:
    """对话记忆存储"""

    def __init__(self):
        # 在生产环境中，这应该存储在Redis或其他持久化存储中
        self._memories: dict[str, list[dict[str, Any]]] = {}
        self._max_history = 50

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None
    ) -> None:
        """添加消息到记忆"""
        if session_id not in self._memories:
            self._memories[session_id] = []

        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }

        self._memories[session_id].append(message)

        # 限制历史记录长度
        if len(self._memories[session_id]) > self._max_history:
            self._memories[session_id] = self._memories[session_id][-self._max_history:]

    def get_history(self, session_id: str, max_messages: int | None = None) -> list[dict[str, Any]]:
        """获取历史消息"""
        history = self._memories.get(session_id, [])
        if max_messages:
            return history[-max_messages:]
        return history

    def get_memory_context(self, session_id: str) -> str | None:
        """获取记忆上下文"""
        history = self.get_history(session_id, max_messages=10)
        if not history:
            return None

        lines = ["最近的对话:"]
        for msg in history[-5:]:
            role = "用户" if msg["role"] == "user" else "助手"
            content = msg["content"][:100] + "..." if len(msg["content"]) > 100 else msg["content"]
            lines.append(f"- {role}: {content}")

        return "\n".join(lines)

    def clear_session(self, session_id: str) -> None:
        """清除会话记忆"""
        self._memories.pop(session_id, None)
        logger.info(f"已清除会话记忆: {session_id}")

    def get_all_sessions(self) -> list[str]:
        """获取所有会话ID"""
        return list(self._memories.keys())


class KnowledgeBaseClient:
    """知识库客户端（基于FalkorDB）"""

    def __init__(self):
        self.settings = get_settings()
        self._redis: Redis | None = None
        self._graph: Graph | None = None
        self._connected = False

    async def connect(self) -> None:
        """连接FalkorDB"""
        if self._connected:
            return

        try:
            # 创建Redis连接
            self._redis = Redis(
                host=self.settings.falkordb_host,
                port=self.settings.falkordb_port,
                password=self.settings.falkordb_password or None,
                decode_responses=True
            )

            # 测试连接
            self._redis.ping()

            # 获取图实例
            self._graph = self._redis.graph(self.settings.falkordb_graph_name)

            # 创建索引（如果不存在）
            await self._create_indices()

            self._connected = True
            logger.info(f"已连接到FalkorDB: {self.settings.falkordb_host}:{self.settings.falkordb_port}")

        except Exception as e:
            logger.error(f"连接FalkorDB失败: {e}")
            raise

    async def _create_indices(self) -> None:
        """创建图索引以提高查询性能"""
        try:
            # 为Route节点创建索引
            self._graph.query(
                "CREATE INDEX ON :Route(id) IF NOT EXISTS"
            )
            self._graph.query(
                "CREATE INDEX ON :Route(name) IF NOT EXISTS"
            )
            self._graph.query(
                "CREATE INDEX ON :POI(id) IF NOT EXISTS"
            )
            self._graph.query(
                "CREATE INDEX ON :Tag(name) IF NOT EXISTS"
            )
            self._graph.query(
                "CREATE INDEX ON :City(name) IF NOT EXISTS"
            )
            logger.debug("图索引创建完成")
        except Exception as e:
            logger.warning(f"创建索引时出错（可能已存在）: {e}")

    async def search(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """
        搜索知识图谱

        支持自然语言查询和关键词搜索
        """
        if not self._connected:
            await self.connect()

        results = []

        try:
            # 1. 搜索路线节点（名称和描述）
            cypher = f"""
                MATCH (r:Route)
                WHERE r.name CONTAINS $query OR r.description CONTAINS $query
                RETURN r.id as id, r.name as name, r.description as description,
                       r.distance as distance, r.elevation_gain as elevation_gain,
                       r.difficulty as difficulty, r.city as city
                LIMIT {limit}
            """
            route_results = self._graph.query(cypher, {"query": query})
            for record in route_results.result_set:
                results.append({
                    "type": "route",
                    "id": record[0],
                    "name": record[1],
                    "description": record[2],
                    "distance": record[3],
                    "elevation_gain": record[4],
                    "difficulty": record[5],
                    "city": record[6],
                    "relevance_score": 1.0
                })

            # 2. 搜索POI节点
            cypher = f"""
                MATCH (p:POI)
                WHERE p.name CONTAINS $query OR p.description CONTAINS $query
                RETURN p.id as id, p.name as name, p.description as description,
                       p.category as category, p.rating as rating
                LIMIT {limit}
            """
            poi_results = self._graph.query(cypher, {"query": query})
            for record in poi_results.result_set:
                results.append({
                    "type": "poi",
                    "id": record[0],
                    "name": record[1],
                    "description": record[2],
                    "category": record[3],
                    "rating": record[4],
                    "relevance_score": 0.9
                })

            # 3. 通过标签关联搜索
            cypher = f"""
                MATCH (t:Tag)-[:TAGGED]->(r:Route)
                WHERE t.name CONTAINS $query
                RETURN r.id as id, r.name as name, r.description as description,
                       r.distance as distance, r.difficulty as difficulty
                LIMIT {limit}
            """
            tag_results = self._graph.query(cypher, {"query": query})
            for record in tag_results.result_set:
                # 避免重复
                if not any(r["id"] == record[0] for r in results):
                    results.append({
                        "type": "route",
                        "id": record[0],
                        "name": record[1],
                        "description": record[2],
                        "distance": record[3],
                        "difficulty": record[4],
                        "relevance_score": 0.8
                    })

            logger.info(f"搜索知识库完成: 查询'{query}', 找到{len(results)}条结果")
            return results[:limit]

        except Exception as e:
            logger.error(f"搜索知识库失败: {e}")
            return []

    async def add_route_knowledge(
        self,
        route_id: str,
        name: str,
        description: str,
        tags: list[str],
        metadata: dict[str, Any] | None = None
    ) -> None:
        """添加路线知识到图谱"""
        if not self._connected:
            await self.connect()

        try:
            metadata = metadata or {}

            # 1. 创建Route节点
            cypher = """
                MERGE (r:Route {id: $route_id})
                SET r.name = $name,
                    r.description = $description,
                    r.distance = $distance,
                    r.elevation_gain = $elevation_gain,
                    r.difficulty = $difficulty,
                    r.city = $city,
                    r.created_at = $created_at
            """
            self._graph.query(cypher, {
                "route_id": route_id,
                "name": name,
                "description": description,
                "distance": metadata.get("distance", 0),
                "elevation_gain": metadata.get("elevation_gain", 0),
                "difficulty": metadata.get("difficulty", "medium"),
                "city": metadata.get("city", ""),
                "created_at": datetime.now().isoformat()
            })

            # 2. 创建City节点并建立关系
            if city := metadata.get("city"):
                cypher = """
                    MERGE (c:City {name: $city})
                    WITH c
                    MATCH (r:Route {id: $route_id})
                    MERGE (r)-[:LOCATED_IN]->(c)
                """
                self._graph.query(cypher, {"city": city, "route_id": route_id})

            # 3. 创建Tag节点并建立关系
            for tag in tags:
                cypher = """
                    MERGE (t:Tag {name: $tag})
                    WITH t
                    MATCH (r:Route {id: $route_id})
                    MERGE (t)-[:TAGGED]->(r)
                """
                self._graph.query(cypher, {"tag": tag, "route_id": route_id})

            # 4. 创建POI节点（如果有）
            if pois := metadata.get("pois"):
                for poi in pois:
                    cypher = """
                        MERGE (p:POI {id: $poi_id})
                        SET p.name = $name,
                            p.description = $description,
                            p.category = $category,
                            p.rating = $rating
                        WITH p
                        MATCH (r:Route {id: $route_id})
                        MERGE (r)-[:CONTAINS]->(p)
                    """
                    self._graph.query(cypher, {
                        "poi_id": poi.get("id"),
                        "name": poi.get("name", ""),
                        "description": poi.get("description", ""),
                        "category": poi.get("category", ""),
                        "rating": poi.get("rating", 0),
                        "route_id": route_id
                    })

            logger.info(f"添加路线知识到图谱: {route_id}")

        except Exception as e:
            logger.error(f"添加路线知识失败: {e}")
            raise

    async def get_route_relations(self, route_id: str) -> dict[str, Any]:
        """获取路线的相关关系（相似路线、附近的POI等）"""
        if not self._connected:
            await self.connect()

        try:
            # 查找相似路线（基于标签）
            cypher = """
                MATCH (r:Route {id: $route_id})<-[:TAGGED]-(t:Tag)-[:TAGGED]->(similar:Route)
                WHERE similar.id <> $route_id
                RETURN similar.id, similar.name, COUNT(t) as common_tags
                ORDER BY common_tags DESC
                LIMIT 5
            """
            similar_results = self._graph.query(cypher, {"route_id": route_id})
            similar_routes = [
                {
                    "id": record[0],
                    "name": record[1],
                    "common_tags": record[2]
                }
                for record in similar_results.result_set
            ]

            # 查找同城市的路线
            cypher = """
                MATCH (r:Route {id: $route_id})-[:LOCATED_IN]->(c:City)<-[:LOCATED_IN]-(other:Route)
                WHERE other.id <> $route_id
                RETURN other.id, other.name, other.distance, other.difficulty
                LIMIT 10
            """
            city_results = self._graph.query(cypher, {"route_id": route_id})
            nearby_routes = [
                {
                    "id": record[0],
                    "name": record[1],
                    "distance": record[2],
                    "difficulty": record[3]
                }
                for record in city_results.result_set
            ]

            return {
                "similar_routes": similar_routes,
                "nearby_routes": nearby_routes
            }

        except Exception as e:
            logger.error(f"获取路线关系失败: {e}")
            return {}

    async def search_by_natural_language(self, query: str) -> list[dict[str, Any]]:
        """
        使用图遍历进行更智能的搜索

        例如："适合周末的轻松路线" -> 查找difficulty=easy, tags包含"周末"等
        """
        if not self._connected:
            await self.connect()

        results = []

        # 解析查询意图
        difficulty_map = {
            "轻松": "easy",
            "简单": "easy",
            "中等": "medium",
            "困难": "hard",
            "挑战": "hard"
        }

        # 检测难度关键词
        detected_difficulty = None
        for keyword, diff in difficulty_map.items():
            if keyword in query:
                detected_difficulty = diff
                break

        # 构建查询
        if detected_difficulty:
            cypher = f"""
                MATCH (r:Route)
                WHERE r.difficulty = $difficulty
                AND (r.name CONTAINS $query OR r.description CONTAINS $query)
                RETURN r.id, r.name, r.description, r.distance, r.difficulty, r.city
                LIMIT 10
            """
            query_results = self._graph.query(cypher, {
                "difficulty": detected_difficulty,
                "query": query
            })

            for record in query_results.result_set:
                results.append({
                    "type": "route",
                    "id": record[0],
                    "name": record[1],
                    "description": record[2],
                    "distance": record[3],
                    "difficulty": record[4],
                    "city": record[5],
                    "relevance_score": 1.0
                })

        return results

    async def clear_graph(self) -> None:
        """清空知识图谱（谨慎使用）"""
        if not self._connected:
            await self.connect()

        try:
            # 删除所有节点和关系
            cypher = "MATCH (n) DETACH DELETE n"
            self._graph.query(cypher)
            logger.warning("已清空知识图谱")

        except Exception as e:
            logger.error(f"清空知识图谱失败: {e}")

    async def get_stats(self) -> dict[str, int]:
        """获取知识图谱统计信息"""
        if not self._connected:
            await self.connect()

        try:
            # 统计各类型节点数量
            route_count = self._graph.query("MATCH (r:Route) RETURN COUNT(r)").result_set[0][0]
            poi_count = self._graph.query("MATCH (p:POI) RETURN COUNT(p)").result_set[0][0]
            tag_count = self._graph.query("MATCH (t:Tag) RETURN COUNT(t)").result_set[0][0]
            city_count = self._graph.query("MATCH (c:City) RETURN COUNT(c)").result_set[0][0]

            return {
                "routes": route_count,
                "pois": poi_count,
                "tags": tag_count,
                "cities": city_count
            }

        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {}

    async def close(self) -> None:
        """关闭连接"""
        if self._redis:
            self._redis.close()
            self._redis = None
            self._graph = None
        self._connected = False
        logger.info("已断开FalkorDB连接")
