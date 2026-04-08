"""KML/GPX文件导入脚本"""

import asyncio
import xml.etree.ElementTree as ET
from pathlib import Path
import sys
import re

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from motor.motor_asyncio import AsyncIOMotorClient
from loguru import logger
from datetime import datetime
from bson import ObjectId

from app.config import get_settings


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """计算两点间距离（米）"""
    import math
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def parse_gpx(file_path: str) -> dict:
    """解析GPX文件"""
    tree = ET.parse(file_path)
    root = tree.getroot()
    
    # GPX命名空间
    ns = {'gpx': 'http://www.topografix.com/GPX/1/1'}
    
    # 获取名称
    name = Path(file_path).stem
    name_elem = root.find('.//gpx:name', ns)
    if name_elem is not None and name_elem.text:
        name = name_elem.text.strip()
    else:
        # 尝试从 type 获取 (Mi Fitness 格式)
        type_elem = root.find('.//gpx:type', ns)
        if type_elem is not None and type_elem.text:
            name = type_elem.text.strip()
    
    # 解析扩展数据 (Mi Fitness 格式)
    total_time = None
    total_distance = None
    for ext in root.findall('.//gpx:extensions', ns):
        for child in ext:
            tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
            if tag == 'totalTime' and child.text:
                total_time = int(child.text)
            elif tag == 'totalDistance' and child.text:
                total_distance = float(child.text)
    
    # 备用：无命名空间查找
    for elem in root.iter():
        tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
        if tag == 'totalTime' and elem.text:
            total_time = int(elem.text)
        elif tag == 'totalDistance' and elem.text:
            total_distance = float(elem.text)
    
    # 解析航点 (POI)
    pois = []
    for wpt in root.findall('.//gpx:wpt', ns):
        lat = float(wpt.get('lat'))
        lon = float(wpt.get('lon'))
        ele_elem = wpt.find('gpx:ele', ns)
        elevation = float(ele_elem.text) if ele_elem is not None and ele_elem.text else None
        name_elem = wpt.find('gpx:name', ns)
        wpt_name = name_elem.text.strip() if name_elem is not None and name_elem.text else None
        
        if wpt_name in ['起点', '终点'] or wpt_name:
            is_checkpoint = wpt_name in ['起点', '终点'] if wpt_name else False
            pois.append({
                "id": str(ObjectId()),
                "name": wpt_name,
                "location": {
                    "type": "Point",
                    "coordinates": [lon, lat]
                },
                "category": "起终点" if wpt_name in ['起点', '终点'] else "标注点",
                "description": None,
                "images": [],
                "rating": None,
                "tags": [],
                "amap_poi_id": None
            })
    
    # 备用：无命名空间查找航点
    if not pois:
        for elem in root.iter():
            tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
            if tag == 'wpt':
                lat = float(elem.get('lat', 0))
                lon = float(elem.get('lon', 0))
                ele = None
                wpt_name = None
                for child in elem:
                    ctag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                    if ctag == 'ele' and child.text:
                        ele = float(child.text)
                    elif ctag == 'name' and child.text:
                        wpt_name = child.text.strip()
                
                if wpt_name:
                    pois.append({
                        "id": str(ObjectId()),
                        "name": wpt_name,
                        "location": {
                            "type": "Point",
                            "coordinates": [lon, lat]
                        },
                        "category": "起终点" if wpt_name in ['起点', '终点'] else "标注点",
                        "description": None,
                        "images": [],
                        "rating": None,
                        "tags": [],
                        "amap_poi_id": None
                    })
    
    # 解析轨迹点
    points = []
    for trkpt in root.findall('.//gpx:trkpt', ns):
        lat = float(trkpt.get('lat'))
        lon = float(trkpt.get('lon'))
        ele_elem = trkpt.find('gpx:ele', ns)
        elevation = float(ele_elem.text) if ele_elem is not None and ele_elem.text else None
        
        points.append({
            "location": {
                "type": "Point",
                "coordinates": [lon, lat]
            },
            "elevation": elevation,
            "timestamp": None,
            "poi_id": None,
            "name": None,
            "description": None,
            "is_waypoint": False,
            "photos": [],
            "is_edited": False,
            "original_location": None
        })
    
    # 备用：无命名空间查找轨迹点
    if not points:
        for elem in root.iter():
            tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
            if tag == 'trkpt':
                lat = float(elem.get('lat', 0))
                lon = float(elem.get('lon', 0))
                ele = None
                for child in elem:
                    ctag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                    if ctag == 'ele' and child.text:
                        ele = float(child.text)
                
                points.append({
                    "location": {
                        "type": "Point",
                        "coordinates": [lon, lat]
                    },
                    "elevation": ele,
                    "timestamp": None,
                    "poi_id": None,
                    "name": None,
                    "description": None,
                    "is_waypoint": False,
                    "photos": [],
                    "is_edited": False,
                    "original_location": None
                })
    
    # 计算距离和爬升
    distance = total_distance if total_distance else 0
    elevation_gain = 0
    
    if distance == 0 and len(points) > 1:
        for i in range(1, len(points)):
            prev = points[i - 1]["location"]["coordinates"]
            curr = points[i]["location"]["coordinates"]
            distance += _haversine(prev[1], prev[0], curr[1], curr[0])
            
            prev_ele = points[i - 1].get("elevation")
            curr_ele = points[i].get("elevation")
            if prev_ele is not None and curr_ele is not None:
                diff = curr_ele - prev_ele
                if diff > 0:
                    elevation_gain += diff
    
    # 计算用时
    actual_duration = total_time  # 秒
    if actual_duration is None or actual_duration <= 0:
        actual_duration = int(distance / 1.39)  # 约5km/h步行速度
    
    # 难度评估
    if distance > 20000 and elevation_gain > 1000:
        difficulty = "hard"
    elif distance > 10000 or elevation_gain > 500:
        difficulty = "medium"
    else:
        difficulty = "easy"
    
    # 构建路线数据
    route_data = {
        "_id": str(ObjectId()),
        "name": name,
        "description": None,
        "preview_image": None,
        "images": [],
        "points": points,
        "pois": pois,
        "distance": distance,
        "elevation_gain": elevation_gain,
        "estimated_duration": actual_duration,
        "start_location": points[0]["location"] if points else None,
        "end_location": points[-1]["location"] if points else None,
        "city": "深圳",
        "district": None,
        "favorites_count": 0,
        "views_count": 0,
        "completions_count": 0,
        "difficulty": difficulty,
        "tags": ["户外运动"],
        "created_by": None,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "is_published": True
    }
    
    return route_data


def parse_kml(file_path: str) -> dict:
    """解析KML文件"""
    tree = ET.parse(file_path)
    root = tree.getroot()
    
    # KML命名空间
    ns = {
        'kml': 'http://www.opengis.net/kml/2.2',
        'gx': 'http://www.google.com/kml/ext/2.2'
    }
    
    doc = root.find('.//kml:Document', ns)
    if doc is None:
        doc = root
    
    # 解析基本信息 - 查找 Document 元素（处理 xmlns="" 的情况）
    # 两步路 KML 文件中 Document 可能有 xmlns=""，导致命名空间问题
    doc_elem = root.find('.//kml:Document[@id="TbuluKmlVersion2"]', ns)
    if doc_elem is None:
        doc_elem = root.find('.//kml:Document', ns)
    if doc_elem is None:
        # 尝试无命名空间查找
        for elem in root.iter():
            tag_name = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
            if tag_name == 'Document':
                doc_elem = elem
                break
    
    name = "未命名路线"
    if doc_elem is not None:
        # 只获取 Document 直接子元素的 name
        for child in doc_elem:
            # 检查是否为 name 元素（考虑命名空间）
            tag_name = child.tag.split('}')[-1] if '}' in child.tag else child.tag
            if tag_name == 'name' and child.text:
                name = child.text.strip()
                # 只清理多余空白，保留单词间的单个空格
                name = re.sub(r'\s+', ' ', name).strip()
                break
    
    # 解析扩展数据
    extended_data = {}
    for data in doc.findall('.//kml:Data', ns):
        name_attr = data.get('name')
        value_elem = data.find('kml:value', ns)
        if name_attr and value_elem is not None and value_elem.text:
            extended_data[name_attr] = value_elem.text
    
    # 备用方式：遍历所有 Data 元素（处理 xmlns="" 的情况）
    for elem in root.iter():
        tag_name = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
        if tag_name == 'Data':
            name_attr = elem.get('name')
            # 查找子元素 value
            for child in elem:
                child_tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                if child_tag == 'value' and child.text:
                    if name_attr:
                        extended_data[name_attr] = child.text
    
    # 解析坐标点 (支持 LineString 和 gx:Track 两种格式)
    points = []
    
    # 方式1: LineString 格式
    coordinates_text = None
    for line_string in doc.findall('.//kml:LineString', ns):
        coords_elem = line_string.find('kml:coordinates', ns)
        if coords_elem is not None and coords_elem.text:
            coordinates_text = coords_elem.text.strip()
            break
    
    if coordinates_text:
        # 坐标格式: lon,lat,elevation lon,lat,elevation ...
        coord_pairs = coordinates_text.split()
        for coord in coord_pairs:
            parts = coord.split(',')
            if len(parts) >= 2:
                lon = float(parts[0])
                lat = float(parts[1])
                elevation = float(parts[2]) if len(parts) > 2 else None
                
                points.append({
                    "location": {
                        "type": "Point",
                        "coordinates": [lon, lat]
                    },
                    "elevation": elevation,
                    "timestamp": None,
                    "poi_id": None,
                    "name": None,
                    "description": None,
                    "is_waypoint": False,
                    "photos": [],
                    "is_edited": False,
                    "original_location": None
                })
    
    # 方式2: gx:Track 格式 (两步路App常用)
    if not points:
        for track in doc.findall('.//gx:Track', ns):
            for coord_elem in track.findall('gx:coord', ns):
                if coord_elem is not None and coord_elem.text:
                    coord_text = coord_elem.text.strip()
                    parts = coord_text.split()
                    if len(parts) >= 2:
                        lon = float(parts[0])
                        lat = float(parts[1])
                        elevation = float(parts[2]) if len(parts) > 2 else None
                        
                        points.append({
                            "location": {
                                "type": "Point",
                                "coordinates": [lon, lat]
                            },
                            "elevation": elevation,
                            "timestamp": None,
                            "poi_id": None,
                            "name": None,
                            "description": None,
                            "is_waypoint": False,
                            "photos": [],
                            "is_edited": False,
                            "original_location": None
                        })
    
    # 解析标注点 (检查点)
    pois = []
    waypoint_names = set()
    for placemark in doc.findall('.//kml:Placemark', ns):
        point = placemark.find('kml:Point', ns)
        if point is not None:
            coords_elem = point.find('kml:coordinates', ns)
            poi_name_elem = placemark.find('kml:name', ns)
            
            if coords_elem is not None and coords_elem.text:
                coord_text = coords_elem.text.strip()
                parts = coord_text.split(',')
                if len(parts) >= 2:
                    lon = float(parts[0])
                    lat = float(parts[1])
                    elevation = float(parts[2]) if len(parts) > 2 else None
                    poi_name = poi_name_elem.text.strip() if poi_name_elem is not None and poi_name_elem.text else None
                    
                    if poi_name:
                        # 清理名称
                        poi_name = re.sub(r'\s+', '', poi_name)
                        waypoint_names.add(poi_name)
                        
                        # 判断是否为检查点 (CP开头或者明确的标注点)
                        is_checkpoint = poi_name.startswith('CP') or poi_name in ['起点', '终点']
                        
                        if is_checkpoint:
                            pois.append({
                                "id": str(ObjectId()),
                                "name": poi_name,
                                "location": {
                                    "type": "Point",
                                    "coordinates": [lon, lat]
                                },
                                "category": "检查点" if poi_name.startswith('CP') else "起终点",
                                "description": None,
                                "images": [],
                                "rating": None,
                                "tags": [],
                                "amap_poi_id": None
                            })
    
    # 计算距离和爬升
    distance = float(extended_data.get('Distance', 0))
    elevation_gain = float(extended_data.get('ElevationGain', 0))
    
    # 如果没有距离数据，从轨迹点计算
    if distance == 0 and len(points) > 1:
        for i in range(1, len(points)):
            prev = points[i - 1]["location"]["coordinates"]
            curr = points[i]["location"]["coordinates"]
            distance += _haversine(prev[1], prev[0], curr[1], curr[0])
            
            prev_ele = points[i - 1].get("elevation")
            curr_ele = points[i].get("elevation")
            if prev_ele is not None and curr_ele is not None:
                diff = curr_ele - prev_ele
                if diff > 0:
                    elevation_gain += diff
    
    # 起点终点
    start_name = extended_data.get('PosStartName', '')
    end_name = extended_data.get('PosEndName', '')
    
    # 计算实际用时（从 BeginTime 和 EndTime）
    begin_time = extended_data.get('BeginTime', '')
    end_time = extended_data.get('EndTime', '')
    actual_duration = None
    if begin_time and end_time:
        try:
            begin_ts = int(begin_time)
            end_ts = int(end_time)
            # 毫秒转秒，再减去暂停时间
            pause_time = int(extended_data.get('PauseTime', 0))
            actual_duration = (end_ts - begin_ts - pause_time) // 1000  # 秒
            if actual_duration <= 0:
                actual_duration = None  # 无效时间，回退到估算
        except ValueError:
            pass
    
    # 如果没有实际用时，用距离估算
    if actual_duration is None:
        # 5km/h = 5000m/3600s ≈ 1.39m/s
        actual_duration = int(distance / 1.39)  # 约5km/h步行速度
    
    # 标签
    track_tags = extended_data.get('TrackTags', '')
    tags = []
    if track_tags:
        tags.append(track_tags)
    if '越野跑' in name or '越野' in name:
        tags.extend(['越野跑', '户外'])
    if '塘朗山' in name:
        tags.append('塘朗山')
    if not tags:
        tags = ['城市漫步']
    
    # 城市/区域
    start_district_id = extended_data.get('StartDistrictId', '')
    district_map = {
        '18162': '福田区',
        '18163': '南山区',
        '18164': '罗湖区',
        '18165': '盐田区',
        '18166': '宝安区',
        '18167': '龙岗区',
        '18168': '龙华区',
        '18169': '坪山区',
        '18170': '光明区',
    }
    district = district_map.get(start_district_id, None)
    
    # 难度评估
    if distance > 20000 and elevation_gain > 1000:
        difficulty = "hard"
    elif distance > 10000 or elevation_gain > 500:
        difficulty = "medium"
    else:
        difficulty = "easy"
    
    # 构建路线数据
    route_data = {
        "_id": str(ObjectId()),
        "name": name,
        "description": f"起点: {start_name}\n终点: {end_name}\n距离: {distance/1000:.2f}公里\n累计爬升: {elevation_gain:.0f}米" if start_name or end_name else None,
        "preview_image": None,
        "images": [],
        "points": points,
        "pois": pois,
        "distance": distance,
        "elevation_gain": elevation_gain,
        "estimated_duration": actual_duration,
        "start_location": points[0]["location"] if points else None,
        "end_location": points[-1]["location"] if points else None,
        "city": "深圳",
        "district": district,
        "favorites_count": 0,
        "views_count": 0,
        "completions_count": 0,
        "difficulty": difficulty,
        "tags": tags,
        "created_by": None,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "is_published": True
    }
    
    return route_data


async def import_to_db(route_data: dict):
    """导入到数据库"""
    settings = get_settings()
    client = AsyncIOMotorClient(settings.mongodb_url)
    db = client[settings.mongodb_db_name]
    
    try:
        # 检查是否已存在同名路线
        existing = await db.routes.find_one({"name": route_data["name"]})
        if existing:
            logger.info(f"路线已存在，更新: {route_data['name']}")
            # 移除 _id 字段，避免修改不可变字段
            update_data = {k: v for k, v in route_data.items() if k != "_id"}
            await db.routes.update_one(
                {"_id": existing["_id"]},
                {"$set": update_data}
            )
            route_data["_id"] = existing["_id"]
        else:
            logger.info(f"创建新路线: {route_data['name']}")
            await db.routes.insert_one(route_data)
        
        logger.info(f"导入成功! 路线ID: {route_data['_id']}")
        logger.info(f"  - 名称: {route_data['name']}")
        logger.info(f"  - 距离: {route_data['distance']/1000:.2f}公里")
        logger.info(f"  - 爬升: {route_data['elevation_gain']:.0f}米")
        logger.info(f"  - 难度: {route_data['difficulty']}")
        logger.info(f"  - 轨迹点数: {len(route_data['points'])}")
        logger.info(f"  - 检查点数: {len(route_data['pois'])}")
        
        return route_data["_id"]
    finally:
        client.close()


async def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python import_kml.py <kml/gpx文件路径>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    if not Path(file_path).exists():
        logger.error(f"文件不存在: {file_path}")
        sys.exit(1)
    
    # 根据文件扩展名选择解析器
    ext = Path(file_path).suffix.lower()
    if ext == '.gpx':
        logger.info(f"开始解析GPX文件: {file_path}")
        route_data = parse_gpx(file_path)
    elif ext == '.kml':
        logger.info(f"开始解析KML文件: {file_path}")
        route_data = parse_kml(file_path)
    else:
        logger.error(f"不支持的文件格式: {ext}")
        sys.exit(1)
    
    logger.info("导入数据库...")
    await import_to_db(route_data)


if __name__ == "__main__":
    asyncio.run(main())
