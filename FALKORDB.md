# FalkorDB 使用指南

## 什么是 FalkorDB？

FalkorDB 是一个基于 Redis 的图数据库，提供高性能的知识图谱存储和查询能力。相比 Neo4j，它具有以下优势：

- 🚀 **性能优异**：基于 Redis 的内存存储，查询速度更快
- 🐳 **部署简单**：Docker 一键启动，无需复杂配置
- 💰 **成本低**：开源免费，资源占用更少
- 🔗 **兼容性好**：支持 Cypher 查询语言（部分）

## 安装和启动

### 方式一：Docker Compose（推荐）

```bash
# 启动所有服务（MongoDB + FalkorDB）
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs falkordb
```

### 方式二：单独启动 FalkorDB

```bash
# 使用官方镜像
docker run -d -p 6379:6379 --name citywalk-falkordb falkordb/falkordb:latest

# 或使用 Redis Stack（包含 RedisGraph 模块）
docker run -d -p 6379:6379 --name citywalk-redis redis/redis-stack-server:latest
```

### 方式三：本地安装

```bash
# macOS
brew install redis
# 安装 RedisGraph 模块

# Linux
# 参考 FalkorDB 官方文档
```

## 配置

在 `.env` 文件中配置 FalkorDB 连接：

```bash
# FalkorDB配置
FALKORDB_HOST=localhost
FALKORDB_PORT=6379
FALKORDB_PASSWORD=        # 如果设置了密码
FALKORDB_GRAPH_NAME=citywalk_kg
```

## 数据模型

CityWalk 的知识图谱包含以下节点类型：

### 1. Route（路线）节点

```cypher
(r:Route {
  id: "route_001",
  name: "杭州西湖环湖漫步",
  description: "...",
  distance: 12000,
  elevation_gain: 50,
  difficulty: "easy",
  city: "杭州",
  created_at: "2024-01-01"
})
```

### 2. POI（兴趣点）节点

```cypher
(p:POI {
  id: "poi_001",
  name: "断桥残雪",
  description: "...",
  category: "景点",
  rating: 4.8
})
```

### 3. Tag（标签）节点

```cypher
(t:Tag {
  name: "周末"
})
```

### 4. City（城市）节点

```cypher
(c:City {
  name: "杭州"
})
```

### 关系类型

- `(Route)-[:LOCATED_IN]->(City)` - 路线所在城市
- `(Tag)-[:TAGGED]->(Route)` - 标签关联
- `(Route)-[:CONTAINS]->(POI)` - 路线包含的POI

## 查询示例

### 1. 搜索路线

```cypher
MATCH (r:Route)
WHERE r.name CONTAINS "西湖" OR r.description CONTAINS "西湖"
RETURN r.id, r.name, r.description
LIMIT 10
```

### 2. 查找相似路线（基于标签）

```cypher
MATCH (r:Route {id: "route_001"})<-[:TAGGED]-(t:Tag)-[:TAGGED]->(similar:Route)
WHERE similar.id <> "route_001"
RETURN similar.id, similar.name, COUNT(t) as common_tags
ORDER BY common_tags DESC
LIMIT 5
```

### 3. 查找同城市的路线

```cypher
MATCH (r:Route {id: "route_001"})-[:LOCATED_IN]->(c:City)<-[:LOCATED_IN]-(other:Route)
WHERE other.id <> "route_001"
RETURN other.id, other.name, other.distance
LIMIT 10
```

### 4. 查找路线的POI

```cypher
MATCH (r:Route {id: "route_001"})-[:CONTAINS]->(p:POI)
RETURN p.id, p.name, p.category, p.rating
```

## API 使用

### 获取知识图谱统计

```bash
curl http://localhost:8000/api/v1/knowledge-graph/stats
```

### 搜索知识图谱

```bash
curl http://localhost:8000/api/v1/knowledge-graph/search/西湖
```

### 获取路线关联信息

```bash
curl http://localhost:8000/api/v1/knowledge-graph/route/route_001/relations
```

### 同步路线到知识图谱

```bash
curl -X POST http://localhost:8000/api/v1/knowledge-graph/sync/route_001
```

## 初始化数据

### 从 MongoDB 同步到 FalkorDB

```bash
# 同步所有路线数据到知识图谱
python scripts/init_knowledge_graph.py
```

### 测试 FalkorDB 连接

```bash
# 基础连接测试
python scripts/test_falkordb.py

# 自然语言搜索测试
python scripts/test_falkordb.py nl
```

## 性能优化

### 1. 创建索引

系统会自动创建以下索引：

```cypher
CREATE INDEX ON :Route(id)
CREATE INDEX ON :Route(name)
CREATE INDEX ON :POI(id)
CREATE INDEX ON :Tag(name)
CREATE INDEX ON :City(name)
```

### 2. 查询优化建议

- 使用索引字段进行查询
- 避免全图扫描
- 合理使用 LIMIT 限制结果数量
- 使用参数化查询（防止注入）

## 监控和调试

### 查看 FalkorDB 状态

```bash
# 连接 Redis CLI
docker exec -it citywalk-falkordb redis-cli

# 查看图信息
GRAPH.QUERY citywalk_kg "MATCH (n) RETURN COUNT(n)"
```

### 查看查询执行计划

```cypher
GRAPH.EXPLAIN citywalk_kg "MATCH (r:Route) WHERE r.name CONTAINS '西湖' RETURN r"
```

## 故障排查

### 连接失败

1. 检查 FalkorDB 是否运行：`docker ps | grep falkordb`
2. 检查端口是否开放：`lsof -i:6379`
3. 查看容器日志：`docker logs citywalk-falkordb`

### 查询无结果

1. 确认数据已同步：`python scripts/init_knowledge_graph.py`
2. 检查节点是否存在：使用 Redis CLI 查询
3. 验证索引是否创建

### 性能问题

1. 检查 Redis 内存使用情况
2. 优化查询语句
3. 添加必要的索引

## 与 Neo4j 的对比

| 特性 | FalkorDB | Neo4j |
|------|----------|-------|
| 存储方式 | 内存（Redis） | 磁盘 + 缓存 |
| 查询语言 | Cypher（部分） | Cypher（完整） |
| 部署复杂度 | 简单 | 中等 |
| 性能 | 高（内存） | 高（缓存） |
| 成本 | 开源免费 | 企业版收费 |
| 适用场景 | 中小规模图谱 | 大规模企业级图谱 |

## 参考资料

- [FalkorDB 官方文档](https://github.com/FalkorDB/FalkorDB)
- [Redis Graph 模块](https://redis.io/docs/modules/redisgraph/)
- [Cypher 查询语言](https://neo4j.com/docs/cypher-manual/current/)
