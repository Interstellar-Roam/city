"""KML文件导入脚本 - 将KML轨迹导入为路线"""

import asyncio
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any
import math

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
from app.agent.memory import KnowledgeBaseClient
from app.services.amap_service import RoutePOIMatcher, AmapService


def parse_kml(file_path: str) -> dict[str, Any]:
    """解析KML文件"""
    tree = ET.parse(file_path)
    root = tree.getroot()
    
    # KML 命名空间
    ns = {
        'kml': 'http://www.opengis.net/kml/2.2',
        'gx': 'http://www.google.com/kml/ext/2.2'
    }
    
    # 获取文档
    doc = root.find('kml:Document', ns)
    
    # 获取路线名称
    name_elem = doc.find('kml:name', ns)
    route_name = name_elem.text if name_elem is not None else "未命名路线"
    
    # 解析扩展数据
    extended_data = {}
    ext_data = doc.find('kml:ExtendedData', ns)
    if ext_data is not None:
        for data in ext_data.findall('kml:Data', ns):
            name = data.get('name')
            value_elem = data.find('kml:value', ns)
            if name and value_elem is not None:
                extended_data[name] = value_elem.text
    
    # 从扩展数据获取信息
    total_distance = float(extended_data.get('Distance', 0))
    elevation_gain = float(extended_data.get('ElevationGain', 0))
    start_name = extended_data.get('PosStartName', '起点')
    end_name = extended_data.get('PosEndName', '终点')
    creater_name = extended_data.get('CreaterName', '')
    
    # 解析标注点（POI/照片点）
    pois = []
    poi_folder = doc.find(".//kml:Folder[@id='TbuluHisPointFolder']", ns)
    if poi_folder is not None:
        for placemark in poi_folder.findall('kml:Placemark', ns):
            poi_name_elem = placemark.find('kml:name', ns)
            poi_name = poi_name_elem.text if poi_name_elem is not None else '未命名'
            
            # 获取坐标
            point = placemark.find('kml:Point', ns)
            if point is not None:
                coords_text = point.find('kml:coordinates', ns)
                if coords_text is not None:
                    coords = coords_text.text.strip().split(',')
                    lon, lat, alt = float(coords[0]), float(coords[1]), float(coords[2])
                    
                    # 判断是否是起点/终点
                    style_url = placemark.find('kml:styleUrl', ns)
                    is_start = style_url is not None and 'startPoint' in style_url.text
                    is_end = style_url is not None and 'endPoint' in style_url.text
                    
                    pois.append({
                        'name': poi_name,
                        'location': {
                            'type': 'Point',
                            'coordinates': [lon, lat]
                        },
                        'is_start': is_start,
                        'is_end': is_end,
                        'altitude': alt
                    })
    
    # 解析轨迹线
    points = []
    line_folder = doc.find(".//kml:Folder[@id='TbuluLineStringFolder']", ns)
    if line_folder is not None:
        linestring = line_folder.find(".//kml:LineString", ns)
        if linestring is not None:
            coords_text = linestring.find('kml:coordinates', ns)
            if coords_text is not None:
                # 坐标格式: lon,lat,alt lon,lat,alt ...
                coords_list = coords_text.text.strip().split()
                for i, coord_str in enumerate(coords_list):
                    parts = coord_str.split(',')
                    lon = float(parts[0])
                    lat = float(parts[1])
                    alt = float(parts[2]) if len(parts) > 2 else 0
                    
                    points.append({
                        'location': {
                            'type': 'Point',
                            'coordinates': [lon, lat]
                        },
                        'elevation': alt,
                        'timestamp': None,
                        'is_waypoint': False,
                        'photos': [],
                        'is_edited': False,
                    })
    
    # 推断城市
    city = infer_city(points[0]['location']['coordinates'] if points else [0, 0])
    
    # 根据距离估算时长（步行 5km/h）
    estimated_duration = int(total_distance / 1000 / 5 * 60) if total_distance > 0 else 0
    
    # 根据难度判断
    if total_distance > 15000 or elevation_gain > 300:
        difficulty = 'hard'
    elif total_distance > 8000 or elevation_gain > 100:
        difficulty = 'medium'
    else:
        difficulty = 'easy'
    
    return {
        'name': route_name,
        'description': f'从KML文件导入的徒步路线，总距离{total_distance/1000:.2f}公里，累计爬升{elevation_gain:.0f}米',
        'points': points,
        'distance': total_distance,
        'elevation_gain': elevation_gain,
        'estimated_duration': estimated_duration,
        'start_location': points[0]['location'] if points else None,
        'end_location': points[-1]['location'] if points else None,
        'city': city,
        'total_points': len(points),
        'difficulty': difficulty,
        'start_name': start_name,
        'end_name': end_name,
        'creater_name': creater_name,
        'imported_pois': pois,
    }


def infer_city(coordinates: list[float]) -> str:
    """根据坐标推断城市"""
    lon, lat = coordinates
    
    city_bounds = {
        '深圳': [(113.7, 22.4), (114.7, 22.9)],
        '广州': [(113.0, 22.5), (113.7, 23.5)],
        '上海': [(120.8, 30.7), (122.2, 31.9)],
        '北京': [(115.7, 39.4), (117.5, 41.1)],
    }
    
    for city, bounds in city_bounds.items():
        if bounds[0][0] <= lon <= bounds[1][0] and bounds[0][1] <= lat <= bounds[1][1]:
            return city
    
    return '未知'


async def import_kml_to_route(
    kml_path: str,
    route_name: str = None,
    tags: list[str] = None,
    match_pois: bool = True,
    poi_types: list[str] = None,
    max_pois: int = 50,
):
    """
    导入KML文件为路线
    
    Args:
        kml_path: KML文件路径
        route_name: 路线名称（可选，默认从KML读取）
        tags: 标签列表
        match_pois: 是否自动匹配沿途POI
        poi_types: 要匹配的POI类型
        max_pois: 最大POI数量
    """
    
    print(f"📍 解析KML文件: {kml_path}")
    kml_data = parse_kml(kml_path)
    
    # 覆盖名称和标签
    if route_name:
        kml_data['name'] = route_name
    if tags:
        kml_data['tags'] = tags
    else:
        kml_data['tags'] = ['徒步', '户外', '深圳']
    
    print(f"📊 路线信息:")
    print(f"   名称: {kml_data['name']}")
    print(f"   城市: {kml_data['city']}")
    print(f"   距离: {kml_data['distance']/1000:.2f} km")
    print(f"   时长: {kml_data['estimated_duration']} 分钟")
    print(f"   累计爬升: {kml_data['elevation_gain']:.0f} m")
    print(f"   难度: {kml_data['difficulty']}")
    print(f"   轨迹点: {kml_data['total_points']} 个")
    print(f"   起点: {kml_data.get('start_name', '未知')}")
    print(f"   终点: {kml_data.get('end_name', '未知')}")
    
    # 自动匹配POI
    pois = []
    if match_pois and kml_data['points']:
        print(f"\n🔍 正在匹配沿途POI...")
        amap_service = AmapService()
        matcher = RoutePOIMatcher(amap_service)
        
        pois = await matcher.match_pois_for_route(
            points=kml_data['points'],
            poi_types=poi_types or ["景点", "餐饮", "咖啡", "公园", "文创"],
            max_pois=max_pois,
        )
        print(f"   匹配到 {len(pois)} 个POI")
    
    # 连接MongoDB
    client = AsyncIOMotorClient('mongodb://localhost:27017')
    db = client.citywalk
    collection = db.routes
    
    # 准备路线文档
    route_doc = {
        '_id': str(ObjectId()),
        'name': kml_data['name'],
        'description': kml_data['description'],
        'points': kml_data['points'],
        'distance': kml_data['distance'],
        'elevation_gain': kml_data['elevation_gain'],
        'estimated_duration': kml_data['estimated_duration'],
        'start_location': kml_data['start_location'],
        'end_location': kml_data['end_location'],
        'city': kml_data['city'],
        'district': None,
        'difficulty': kml_data['difficulty'],
        'tags': kml_data['tags'],
        'pois': pois,
        'images': [],
        'preview_image': None,
        'favorites_count': 0,
        'views_count': 0,
        'completions_count': 0,
        'is_published': True,
        'created_at': datetime.now(),
        'updated_at': datetime.now()
    }
    
    # 插入数据库
    result = await collection.insert_one(route_doc)
    print(f"\n✅ 已导入路线，ID: {result.inserted_id}")
    
    # 同步到知识图谱
    print(f"\n📚 同步到知识图谱...")
    kg_client = KnowledgeBaseClient()
    await kg_client.connect()
    
    await kg_client.add_route_knowledge(
        route_id=route_doc['_id'],
        name=route_doc['name'],
        description=route_doc['description'],
        tags=route_doc['tags'],
        metadata={
            'distance': route_doc['distance'],
            'elevation_gain': route_doc['elevation_gain'],
            'difficulty': route_doc['difficulty'],
            'city': route_doc['city']
        }
    )
    
    await kg_client.close()
    client.close()
    
    print(f"\n🎉 KML导入完成!")
    return route_doc


if __name__ == '__main__':
    import sys
    
    kml_file = sys.argv[1] if len(sys.argv) > 1 else '深圳湾.kml'
    name = sys.argv[2] if len(sys.argv) > 2 else None
    
    asyncio.run(import_kml_to_route(kml_file, name, ['徒步', '户外', '深圳', '深圳湾']))
