"""GPX文件导入脚本 - 将GPX轨迹导入为路线"""

import asyncio
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any
import math

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
from app.agent.memory import KnowledgeBaseClient


def parse_gpx(file_path: str) -> dict[str, Any]:
    """解析GPX文件"""
    tree = ET.parse(file_path)
    root = tree.getroot()
    
    # 处理命名空间
    ns = {'gpx': 'http://www.topografix.com/GPX/1/1'}
    gpx_ns = 'http://www.topografix.com/GPX/1/1'
    
    # 获取轨迹信息
    trk = root.find('gpx:trk', ns)
    
    # 获取轨迹名称和类型
    name = trk.find('gpx:type', ns)
    route_name = name.text if name is not None else "未命名路线"
    
    # 获取扩展信息
    extensions = trk.find('gpx:extensions', ns)
    total_distance = 0
    total_time = 0
    if extensions is not None:
        # 遍历子元素，处理带命名空间的标签
        for child in extensions:
            # 去除命名空间前缀
            tag_name = child.tag.replace(f'{{{gpx_ns}}}', '')
            if tag_name == 'totalDistance':
                total_distance = float(child.text)
            elif tag_name == 'totalTime':
                total_time = float(child.text)
    
    # 获取轨迹点
    points = []
    trkseg = trk.find('gpx:trkseg', ns)
    if trkseg is not None:
        for trkpt in trkseg.findall('gpx:trkpt', ns):
            lat = float(trkpt.get('lat'))
            lon = float(trkpt.get('lon'))
            
            # 获取时间
            time_elem = trkpt.find('gpx:time', ns)
            timestamp = None
            if time_elem is not None:
                timestamp = datetime.fromisoformat(time_elem.text.replace('Z', '+00:00'))
            
            # 获取海拔（如果有）
            ele_elem = trkpt.find('gpx:ele', ns)
            elevation = float(ele_elem.text) if ele_elem is not None else None
            
            points.append({
                'location': {
                    'type': 'Point',
                    'coordinates': [lon, lat]
                },
                'elevation': elevation,
                'timestamp': timestamp.isoformat() if timestamp else None
            })
    
    # 计算累计爬升
    elevation_gain = 0
    elevations = [p['elevation'] for p in points if p['elevation'] is not None]
    for i in range(1, len(elevations)):
        diff = elevations[i] - elevations[i-1]
        if diff > 0:
            elevation_gain += diff
    
    # 获取起点和终点
    start_location = points[0]['location'] if points else None
    end_location = points[-1]['location'] if points else None
    
    # 根据坐标推断城市
    city = infer_city(points[0]['location']['coordinates'] if points else [0, 0])
    
    return {
        'name': route_name,
        'description': f'从GPX文件导入的跑步路线，总距离{total_distance/1000:.2f}公里，用时{total_time/60:.0f}分钟',
        'points': points,
        'distance': total_distance,
        'elevation_gain': elevation_gain,
        'estimated_duration': int(total_time / 60),
        'start_location': start_location,
        'end_location': end_location,
        'city': city,
        'total_points': len(points)
    }


def infer_city(coordinates: list[float]) -> str:
    """根据坐标推断城市"""
    lon, lat = coordinates
    
    # 简单的城市边界判断
    city_bounds = {
        '深圳': [(113.7, 22.4), (114.7, 22.9)],
        '广州': [(113.0, 22.5), (113.7, 23.5)],
        '上海': [(120.8, 30.7), (122.2, 31.9)],
        '北京': [(115.7, 39.4), (117.5, 41.1)],
        '成都': [(103.8, 30.4), (104.3, 30.9)],
        '杭州': [(120.0, 30.1), (120.5, 30.5)],
        '南京': [(118.5, 31.8), (119.1, 32.2)],
        '武汉': [(113.7, 30.3), (114.5, 30.9)],
        '重庆': [(106.3, 29.3), (106.7, 29.7)],
        '西安': [(108.8, 34.1), (109.1, 34.4)],
        '苏州': [(120.4, 31.1), (120.9, 31.5)],
    }
    
    for city, bounds in city_bounds.items():
        if bounds[0][0] <= lon <= bounds[1][0] and bounds[0][1] <= lat <= bounds[1][1]:
            return city
    
    return '未知'


async def import_gpx_to_route(gpx_path: str, route_name: str = None, tags: list[str] = None):
    """导入GPX文件为路线"""
    
    print(f"📍 解析GPX文件: {gpx_path}")
    gpx_data = parse_gpx(gpx_path)
    
    # 覆盖名称和标签
    if route_name:
        gpx_data['name'] = route_name
    if tags:
        gpx_data['tags'] = tags
    else:
        gpx_data['tags'] = ['跑步', '户外', '导入路线']
    
    print(f"📊 路线信息:")
    print(f"   名称: {gpx_data['name']}")
    print(f"   城市: {gpx_data['city']}")
    print(f"   距离: {gpx_data['distance']/1000:.2f} km")
    print(f"   时间: {gpx_data['estimated_duration']} 分钟")
    print(f"   轨迹点: {gpx_data['total_points']} 个")
    
    # 连接MongoDB
    client = AsyncIOMotorClient('mongodb://localhost:27017')
    db = client.citywalk
    collection = db.routes
    
    # 准备路线文档
    route_doc = {
        '_id': str(ObjectId()),
        'name': gpx_data['name'],
        'description': gpx_data['description'],
        'points': gpx_data['points'],
        'distance': gpx_data['distance'],
        'elevation_gain': gpx_data['elevation_gain'],
        'estimated_duration': gpx_data['estimated_duration'],
        'start_location': gpx_data['start_location'],
        'end_location': gpx_data['end_location'],
        'city': gpx_data['city'],
        'district': None,
        'difficulty': 'medium',
        'tags': gpx_data['tags'],
        'pois': [],
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
    
    print(f"\n🎉 GPX导入完成!")
    return route_doc


if __name__ == '__main__':
    import sys
    
    gpx_file = sys.argv[1] if len(sys.argv) > 1 else '20260313户外跑步.gpx'
    name = sys.argv[2] if len(sys.argv) > 2 else None
    
    asyncio.run(import_gpx_to_route(gpx_file, name, ['跑步', '户外', '深圳']))
