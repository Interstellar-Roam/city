"""
功能验证测试 - 确保AI只基于数据库/知识库数据回答

测试目标：
1. 验证现有数据查询返回正确结果
2. 验证不存在的数据不会产生幻觉
3. 验证返回的POI/路线名称与数据库一致
"""

import asyncio
import json
import httpx
from motor.motor_asyncio import AsyncIOMotorClient
from app.agent.memory import KnowledgeBaseClient


# 测试配置
BASE_URL = "http://localhost:8000/api/v1/search/stream"


class TestDataValidator:
    """数据验证器"""
    
    def __init__(self):
        self.db_routes: list[dict] = []
        self.db_pois: list[str] = []
        self.db_cities: set[str] = set()
        self.db_tags: set[str] = set()
        self.kg_routes: list[dict] = []
        
    async def load_db_data(self):
        """加载数据库数据"""
        client = AsyncIOMotorClient('mongodb://localhost:27017')
        db = client.citywalk
        
        self.db_routes = await db.routes.find({}).to_list(length=100)
        
        for route in self.db_routes:
            self.db_cities.add(route.get('city', ''))
            self.db_tags.update(route.get('tags', []))
            for poi in route.get('pois', []):
                self.db_pois.append(poi.get('name', ''))
        
        client.close()
        print(f"✅ 加载数据库: {len(self.db_routes)}条路线, {len(self.db_pois)}个POI")
        
    async def load_kg_data(self):
        """加载知识图谱数据"""
        kg_client = KnowledgeBaseClient()
        await kg_client.connect()
        
        stats = await kg_client.get_stats()
        print(f"✅ 加载知识图谱: {stats}")
        
        await kg_client.close()
        
    def route_exists(self, name: str) -> bool:
        """检查路线是否存在"""
        return any(r['name'] == name for r in self.db_routes)
    
    def city_exists(self, city: str) -> bool:
        """检查城市是否存在"""
        return city in self.db_cities
    
    def poi_exists(self, poi_name: str) -> bool:
        """检查POI是否存在（支持部分匹配）"""
        return any(poi_name in name for name in self.db_pois)
    
    def get_routes_by_city(self, city: str) -> list[str]:
        """获取指定城市的路线"""
        return [r['name'] for r in self.db_routes if r.get('city') == city]


async def call_search_api(query: str) -> tuple[str, list[dict]]:
    """调用搜索API并收集响应"""
    full_response = ""
    tool_calls = []
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        async with client.stream(
            "POST",
            BASE_URL,
            json={"query": query},
            headers={"Content-Type": "application/json"}
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    try:
                        data = json.loads(line[6:])
                        if data.get("type") == "text":
                            full_response += data.get("content", "")
                        elif data.get("type") == "tool_call":
                            tool_calls.append({
                                "name": data.get("name"),
                                "arguments": json.loads(data.get("arguments", "{}"))
                            })
                    except json.JSONDecodeError:
                        pass
    
    return full_response, tool_calls


def check_hallucination(response: str, validator: TestDataValidator, query_city: str = None) -> list[str]:
    """检查响应中是否存在幻觉内容"""
    issues = []
    
    # 检查是否推荐了不存在城市的路线（而不是仅仅提到城市名）
    # 关键词：推荐、路线、可以前往
    fake_cities = ['天津', '青岛', '厦门', '大连', '长沙', '郑州', '福州']
    for city in fake_cities:
        if city in response and not validator.city_exists(city):
            # 检查是否在推荐路线（而不仅仅是引用用户的查询）
            recommendation_patterns = [
                f"推荐{city}",
                f"{city}的路线",
                f"前往{city}",
                f"在{city}有",
                f"{city}适合",
            ]
            for pattern in recommendation_patterns:
                if pattern in response:
                    issues.append(f"🚨 幻觉: 推荐了不存在城市的路线 '{pattern}'")
                    break
    
    # 检查是否提到不存在的路线特征
    fake_features = ['长城', '故宫', '兵马俑', '东方明珠', '东方之珠']
    for feature in fake_features:
        if feature in response:
            # 检查数据库中是否有相关描述
            found = any(feature in r.get('description', '') or feature in r.get('name', '') 
                       for r in validator.db_routes)
            if not found:
                issues.append(f"⚠️ 可能幻觉: 响应中提到 '{feature}' 但数据库中无此内容")
    
    return issues


async def test_existing_data(validator: TestDataValidator):
    """测试1: 查询现有数据"""
    print("\n" + "=" * 60)
    print("📋 测试1: 查询现有数据")
    print("=" * 60)
    
    test_cases = [
        ("上海咖啡路线", "上海"),
        ("深圳商场", "深圳"),
        ("杭州西湖", "杭州"),
        ("成都太古里", "成都"),
    ]
    
    results = []
    for query, expected_city in test_cases:
        print(f"\n🔍 测试: '{query}'")
        response, tool_calls = await call_search_api(query)
        
        # 检查工具调用是否包含正确的城市
        city_found = False
        for tc in tool_calls:
            args = tc.get('arguments', {})
            if args.get('city') == expected_city or expected_city in args.get('query', ''):
                city_found = True
                break
        
        # 检查幻觉
        issues = check_hallucination(response, validator)
        
        status = "✅ 通过" if city_found and not issues else "❌ 失败"
        results.append({
            "query": query,
            "city_found": city_found,
            "issues": issues,
            "status": status
        })
        
        print(f"   城市参数正确: {'是' if city_found else '否'}")
        print(f"   幻觉检查: {'无' if not issues else issues}")
        print(f"   状态: {status}")
    
    return results


async def test_nonexistent_data(validator: TestDataValidator):
    """测试2: 查询不存在的数据"""
    print("\n" + "=" * 60)
    print("📋 测试2: 查询不存在的数据")
    print("=" * 60)
    
    # 数据库中不存在的城市
    test_cases = [
        "天津的咖啡路线",
        "青岛的海边漫步",
        "厦门的鼓浪屿路线",
        "长沙的美食路线",
    ]
    
    results = []
    for query in test_cases:
        print(f"\n🔍 测试: '{query}'")
        response, tool_calls = await call_search_api(query)
        
        # 检查是否产生幻觉
        issues = check_hallucination(response, validator)
        
        # 检查响应是否正确说明没有数据
        no_data_indicators = ['没有', '暂时', '未找到', '无相关', '抱歉']
        correctly_handled = any(indicator in response for indicator in no_data_indicators)
        
        status = "✅ 通过" if correctly_handled and not issues else "⚠️ 需检查"
        results.append({
            "query": query,
            "issues": issues,
            "correctly_handled": correctly_handled,
            "status": status
        })
        
        print(f"   正确处理无数据: {'是' if correctly_handled else '否'}")
        print(f"   幻觉检查: {'无' if not issues else issues}")
        print(f"   状态: {status}")
    
    return results


async def test_poi_accuracy(validator: TestDataValidator):
    """测试3: POI准确性"""
    print("\n" + "=" * 60)
    print("📋 测试3: POI名称准确性")
    print("=" * 60)
    
    # 从数据库中选取已知的POI进行测试
    known_pois = [
        ("%Arabica", "静安咖啡馆漫步"),
        ("赛格国际购物中心", "西安小寨"),
        ("太古里", "成都"),
        ("西湖国宾馆", "杭州西湖"),
    ]
    
    results = []
    for poi_name, query_hint in known_pois:
        query = f"搜索包含{poi_name}的路线"
        print(f"\n🔍 测试: '{query}'")
        
        response, tool_calls = await call_search_api(query)
        
        # 检查POI是否在响应中
        poi_in_response = poi_name in response
        
        # 检查是否是真实数据
        is_real_poi = validator.poi_exists(poi_name)
        
        status = "✅ 通过" if (poi_in_response and is_real_poi) or (not poi_in_response and not is_real_poi) else "❌ 失败"
        results.append({
            "poi": poi_name,
            "is_real": is_real_poi,
            "in_response": poi_in_response,
            "status": status
        })
        
        print(f"   POI真实存在: {'是' if is_real_poi else '否'}")
        print(f"   POI在响应中: {'是' if poi_in_response else '否'}")
        print(f"   状态: {status}")
    
    return results


async def test_tool_call_accuracy(validator: TestDataValidator):
    """测试4: 工具调用准确性"""
    print("\n" + "=" * 60)
    print("📋 测试4: 工具调用参数准确性")
    print("=" * 60)
    
    test_cases = [
        {
            "query": "推荐北京三里屯的购物路线",
            "expected_city": "北京",
            "expected_keywords": ["三里屯", "购物", "时尚"]
        },
        {
            "query": "广州天河有什么商场路线",
            "expected_city": "广州",
            "expected_keywords": ["天河", "商场"]
        },
        {
            "query": "苏州金鸡湖周边的咖啡店路线",
            "expected_city": "苏州",
            "expected_keywords": ["金鸡湖", "咖啡"]
        },
    ]
    
    results = []
    for case in test_cases:
        print(f"\n🔍 测试: '{case['query']}'")
        response, tool_calls = await call_search_api(case['query'])
        
        # 检查工具调用参数
        correct_city = False
        correct_keywords = False
        used_knowledge_search = False
        
        for tc in tool_calls:
            args = tc.get('arguments', {})
            
            # 检查城市
            if args.get('city') == case['expected_city']:
                correct_city = True
            
            # 检查关键词
            query_str = args.get('query', '')
            if any(kw in query_str for kw in case['expected_keywords']):
                correct_keywords = True
            
            # 检查是否使用知识图谱
            if tc.get('name') == 'search_knowledge':
                used_knowledge_search = True
        
        status = "✅ 通过" if correct_city and correct_keywords else "⚠️ 需检查"
        results.append({
            "query": case['query'],
            "correct_city": correct_city,
            "correct_keywords": correct_keywords,
            "used_knowledge": used_knowledge_search,
            "status": status
        })
        
        print(f"   城市参数正确: {'是' if correct_city else '否'}")
        print(f"   关键词包含: {'是' if correct_keywords else '否'}")
        print(f"   使用知识图谱: {'是' if used_knowledge_search else '否'}")
        print(f"   状态: {status}")
    
    return results


async def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("🧪 CityWalk 功能验证测试")
    print("=" * 60)
    
    # 初始化验证器
    validator = TestDataValidator()
    await validator.load_db_data()
    await validator.load_kg_data()
    
    # 运行测试
    all_results = {}
    
    all_results['test1'] = await test_existing_data(validator)
    all_results['test2'] = await test_nonexistent_data(validator)
    all_results['test3'] = await test_poi_accuracy(validator)
    all_results['test4'] = await test_tool_call_accuracy(validator)
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("📊 测试汇总")
    print("=" * 60)
    
    total_tests = 0
    passed_tests = 0
    
    for test_name, results in all_results.items():
        for r in results:
            total_tests += 1
            if "✅" in r.get('status', ''):
                passed_tests += 1
    
    print(f"\n总测试数: {total_tests}")
    print(f"通过数: {passed_tests}")
    print(f"通过率: {passed_tests/total_tests*100:.1f}%")
    
    if passed_tests == total_tests:
        print("\n🎉 所有测试通过！")
    else:
        print("\n⚠️ 部分测试需要关注")


if __name__ == "__main__":
    asyncio.run(run_all_tests())
