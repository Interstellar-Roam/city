"""高德地图POI服务 - 周边搜索、路线POI匹配"""

import math
from typing import Any

import httpx
from loguru import logger

from app.config import get_settings


# ========== 坐标转换工具 (WGS-84 -> GCJ-02) ==========
PI = math.pi
A = 6378245.0  # 长半轴
EE = 0.00669342162296594323  # 扁率


def _is_in_china(lng: float, lat: float) -> bool:
    """判断是否在中国境内"""
    return 72.004 <= lng <= 137.8347 and 0.8293 <= lat <= 55.8271


def _transform_lng(lng: float, lat: float) -> float:
    """转换经度"""
    ret = 300.0 + lng + 2.0 * lat + 0.1 * lng * lng + 0.1 * lng * lat + 0.1 * math.sqrt(abs(lng))
    ret += (20.0 * math.sin(6.0 * lng * PI) + 20.0 * math.sin(2.0 * lng * PI)) * 2.0 / 3.0
    ret += (20.0 * math.sin(lng * PI) + 40.0 * math.sin(lng / 3.0 * PI)) * 2.0 / 3.0
    ret += (150.0 * math.sin(lng / 12.0 * PI) + 300.0 * math.sin(lng / 30.0 * PI)) * 2.0 / 3.0
    return ret


def _transform_lat(lng: float, lat: float) -> float:
    """转换纬度"""
    ret = -100.0 + 2.0 * lng + 3.0 * lat + 0.2 * lat * lat + 0.1 * lng * lat + 0.2 * math.sqrt(abs(lng))
    ret += (20.0 * math.sin(6.0 * lng * PI) + 20.0 * math.sin(2.0 * lng * PI)) * 2.0 / 3.0
    ret += (20.0 * math.sin(lat * PI) + 40.0 * math.sin(lat / 3.0 * PI)) * 2.0 / 3.0
    ret += (160.0 * math.sin(lat / 12.0 * PI) + 320 * math.sin(lat * PI / 30.0)) * 2.0 / 3.0
    return ret


def wgs84_to_gcj02(lng: float, lat: float) -> tuple[float, float]:
    """
    WGS-84 坐标系 转 GCJ-02 (火星坐标系)
    
    GPS原始坐标使用WGS-84，高德地图使用GCJ-02
    此函数用于在查询高德API前转换坐标
    """
    if not _is_in_china(lng, lat):
        return lng, lat  # 不在中国境内，不转换
    
    d_lng = _transform_lng(lng - 105.0, lat - 35.0)
    d_lat = _transform_lat(lng - 105.0, lat - 35.0)
    rad_lat = lat / 180.0 * PI
    magic = math.sin(rad_lat)
    magic = 1 - EE * magic * magic
    sqrt_magic = math.sqrt(magic)
    
    d_lng = (d_lng * 180.0) / (A / sqrt_magic * math.cos(rad_lat) * PI)
    d_lat = (d_lat * 180.0) / ((A * (1 - EE)) / (magic * sqrt_magic) * PI)
    
    mg_lng = lng + d_lng
    mg_lat = lat + d_lat
    
    return mg_lng, mg_lat


class AmapService:
    """高德地图API服务"""

    BASE_URL = "https://restapi.amap.com/v3"

    # POI类型编码（高德）
    POI_TYPES = {
        "景点": "110000",
        "餐饮": "050000",
        "购物": "060000",
        "咖啡": "050500",
        "休息点": "190000",  # 生活服务
        "文创": "061200",  # 特色商业街区
        "公园": "110100",
        "博物馆": "140100",
    }

    def __init__(self):
        settings = get_settings()
        # 后端使用 Web服务 类型的 Key
        self.api_key = settings.amap_api_key_backend or settings.amap_api_key

        if not self.api_key:
            logger.warning("高德API Key未配置，POI自动匹配功能将不可用")

    async def search_around(
        self,
        longitude: float,
        latitude: float,
        radius: int = 1000,
        keywords: str | None = None,
        types: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """
        周边搜索POI

        Args:
            longitude: 经度 (WGS-84)
            latitude: 纬度 (WGS-84)
            radius: 搜索半径(米)，最大50000
            keywords: 搜索关键词
            types: POI类型编码（多个用|分隔）
            limit: 返回数量限制

        Returns:
            POI列表
        """
        if not self.api_key:
            return []

        # 坐标转换: WGS-84 -> GCJ-02 (高德坐标系)
        gcj_lng, gcj_lat = wgs84_to_gcj02(longitude, latitude)

        params = {
            "key": self.api_key,
            "location": f"{gcj_lng},{gcj_lat}",
            "radius": min(radius, 50000),
            "offset": limit,
            "extensions": "all",
        }

        if keywords:
            params["keywords"] = keywords
        if types:
            params["types"] = types

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.BASE_URL}/place/around", params=params)
                response.raise_for_status()
                data = response.json()

            if data.get("status") != "1":
                logger.error(f"高德API错误: {data.get('info')}")
                return []

            pois = data.get("pois", [])
            return [self._normalize_poi(p) for p in pois]

        except Exception as e:
            logger.error(f"高德POI搜索失败: {e}")
            return []

    async def search_poi_by_types(
        self,
        longitude: float,
        latitude: float,
        radius: int = 1000,
        type_names: list[str] | None = None,
        limit_per_type: int = 5,
    ) -> list[dict[str, Any]]:
        """
        按类型搜索周边POI

        Args:
            longitude: 经度
            latitude: 纬度
            radius: 搜索半径(米)
            type_names: 类型名称列表（如 ["景点", "餐饮", "咖啡"]）
            limit_per_type: 每种类型返回数量

        Returns:
            合并后的POI列表（已去重）
        """
        if not type_names:
            type_names = list(self.POI_TYPES.keys())

        type_codes = "|".join(
            self.POI_TYPES.get(t, "") for t in type_names if t in self.POI_TYPES
        )

        if not type_codes:
            return []

        return await self.search_around(
            longitude=longitude,
            latitude=latitude,
            radius=radius,
            types=type_codes,
            limit=limit_per_type * len(type_names),
        )

    def _normalize_poi(self, raw_poi: dict[str, Any]) -> dict[str, Any]:
        """标准化POI数据"""
        from bson import ObjectId

        # 解析坐标
        location = raw_poi.get("location", "").split(",")
        lon = float(location[0]) if len(location) == 2 else 0
        lat = float(location[1]) if len(location) == 2 else 0

        # 解析图片
        photos = raw_poi.get("photos", [])
        images = [p.get("url") for p in photos if p.get("url")][:5]

        # 确定分类
        type_code = raw_poi.get("typecode", "")
        category = self._get_category_from_typecode(type_code)

        return {
            "id": str(ObjectId()),
            "name": raw_poi.get("name", ""),
            "location": {"type": "Point", "coordinates": [lon, lat]},
            "category": category,
            "description": raw_poi.get("address", ""),
            "images": images,
            "rating": float(raw_poi.get("biz_ext", {}).get("rating", 0)) or None,
            "tags": [t for t in raw_poi.get("type", "").split(";") if t][:5],
            "amap_poi_id": raw_poi.get("id"),
            "distance": int(raw_poi.get("distance", 0)),
        }

    def _get_category_from_typecode(self, typecode: str) -> str:
        """根据类型编码确定分类"""
        if not typecode:
            return "其他"

        prefix = typecode[:2]
        category_map = {
            "05": "餐饮",
            "06": "购物",
            "11": "景点",
            "14": "文化",
            "19": "生活服务",
        }
        return category_map.get(prefix, "其他")


class RoutePOIMatcher:
    """路线POI匹配器"""

    # 采样间隔（米）- 沿途采样轨迹点用于POI搜索
    SAMPLE_INTERVAL = 200  # 增大采样间隔，减少API调用
    # POI匹配半径（米）
    POI_MATCH_RADIUS = 150  # 稍微增大半径
    # 去重半径（米）- 同一位置多个POI去重
    DEDUP_RADIUS = 50
    # API请求间隔（秒）- 避免QPS限制
    API_REQUEST_INTERVAL = 0.15

    def __init__(self, amap_service: AmapService | None = None):
        self.amap = amap_service or AmapService()

    async def match_pois_for_route(
        self,
        points: list[dict[str, Any]],
        poi_types: list[str] | None = None,
        max_pois: int = 50,
    ) -> list[dict[str, Any]]:
        """
        为路线自动匹配沿途POI

        Args:
            points: 轨迹点列表 [{location: {coordinates: [lon, lat]}, ...}]
            poi_types: 要匹配的POI类型
            max_pois: 最大POI数量

        Returns:
            匹配到的POI列表（已去重）
        """
        if not self.amap.api_key or not points:
            return []

        # 采样轨迹点
        sample_points = self._sample_points(points)

        # 对每个采样点搜索周边POI（添加请求间隔避免QPS限制）
        import asyncio
        all_pois = []
        for pt in sample_points:
            lon, lat = pt["location"]["coordinates"]
            pois = await self.amap.search_poi_by_types(
                longitude=lon,
                latitude=lat,
                radius=self.POI_MATCH_RADIUS,
                type_names=poi_types,
            )
            all_pois.extend(pois)
            # 添加请求间隔避免QPS限制
            await asyncio.sleep(self.API_REQUEST_INTERVAL)

        # 去重并排序
        unique_pois = self._deduplicate_pois(all_pois)
        sorted_pois = self._sort_pois_by_route(unique_pois, points)

        return sorted_pois[:max_pois]

    def _sample_points(
        self,
        points: list[dict[str, Any]],
        interval: float | None = None,
    ) -> list[dict[str, Any]]:
        """
        按距离间隔采样轨迹点

        Args:
            points: 轨迹点列表
            interval: 采样间隔(米)

        Returns:
            采样后的点列表
        """
        interval = interval or self.SAMPLE_INTERVAL
        if not points:
            return []

        sampled = [points[0]]  # 起点
        accumulated_dist = 0

        for i in range(1, len(points)):
            prev = points[i - 1]["location"]["coordinates"]
            curr = points[i]["location"]["coordinates"]
            dist = haversine_distance(prev[1], prev[0], curr[1], curr[0])

            accumulated_dist += dist

            if accumulated_dist >= interval:
                sampled.append(points[i])
                accumulated_dist = 0

        # 确保终点包含
        if points[-1] not in sampled:
            sampled.append(points[-1])

        return sampled

    def _deduplicate_pois(
        self,
        pois: list[dict[str, Any]],
        radius: float | None = None,
    ) -> list[dict[str, Any]]:
        """
        去除距离过近的重复POI

        保留距离路线更近的POI
        """
        radius = radius or self.DEDUP_RADIUS
        if not pois:
            return []

        unique = []

        for poi in pois:
            is_duplicate = False
            poi_lon, poi_lat = poi["location"]["coordinates"]

            for existing in unique:
                ex_lon, ex_lat = existing["location"]["coordinates"]
                dist = haversine_distance(poi_lat, poi_lon, ex_lat, ex_lon)

                if dist < radius:
                    is_duplicate = True
                    # 保留距离更近的
                    if poi.get("distance", 0) < existing.get("distance", float("inf")):
                        unique.remove(existing)
                        unique.append(poi)
                    break

            if not is_duplicate:
                unique.append(poi)

        return unique

    def _sort_pois_by_route(
        self,
        pois: list[dict[str, Any]],
        points: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        按照路线顺序排序POI
        """
        if not points or not pois:
            return pois

        # 计算每个POI在路线上的最近点索引
        poi_with_index = []
        for poi in pois:
            poi_lon, poi_lat = poi["location"]["coordinates"]
            min_dist = float("inf")
            nearest_idx = 0

            for i, pt in enumerate(points):
                pt_lon, pt_lat = pt["location"]["coordinates"]
                dist = haversine_distance(poi_lat, poi_lon, pt_lat, pt_lon)
                if dist < min_dist:
                    min_dist = dist
                    nearest_idx = i

            poi_with_index.append((nearest_idx, poi))

        # 按索引排序
        poi_with_index.sort(key=lambda x: x[0])
        return [p for _, p in poi_with_index]


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    计算两点间的球面距离（米）
    使用Haversine公式
    """
    R = 6371000  # 地球半径(米)

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c
