"""路线相关数据模型"""

from datetime import datetime
from typing import Any

from bson import ObjectId
from pydantic import BaseModel, Field, field_validator

from app.utils.helpers import PyObjectId


class Location(BaseModel):
    """地理位置坐标"""

    type: str = "Point"
    coordinates: list[float] = Field(..., min_length=2, max_length=2)  # [longitude, latitude]

    @field_validator("coordinates")
    @classmethod
    def validate_coordinates(cls, v: list[float]) -> list[float]:
        lon, lat = v[0], v[1]
        if not (-180 <= lon <= 180):
            raise ValueError("经度必须在 -180 到 180 之间")
        if not (-90 <= lat <= 90):
            raise ValueError("纬度必须在 -90 到 90 之间")
        return v


class RoutePointPhoto(BaseModel):
    """轨迹点照片（Base64内嵌）"""

    id: str = Field(default_factory=lambda: str(ObjectId()))
    data: str  # Base64编码的图片数据
    content_type: str = "image/jpeg"  # MIME类型
    caption: str | None = None  # 照片说明
    size: int = 0  # 原始文件大小(字节)
    created_at: datetime = Field(default_factory=datetime.now)


class RoutePoint(BaseModel):
    """路线上的一个点"""

    location: Location
    elevation: float | None = None  # 海拔高度(米)
    timestamp: datetime | None = None
    poi_id: str | None = None  # 关联的POI ID
    name: str | None = None
    description: str | None = None

    # 编辑功能扩展
    is_waypoint: bool = False  # 是否为用户标记的途径点
    photos: list[RoutePointPhoto] = Field(default_factory=list)  # 照片列表（最多5张）
    is_edited: bool = False  # 是否被用户编辑过
    original_location: Location | None = None  # 原始位置（编辑后保留）


class POI(BaseModel):
    """兴趣点(Point of Interest)"""

    id: str = Field(default_factory=lambda: str(ObjectId()))
    name: str
    location: Location
    category: str  # 景点、餐饮、休息点等
    description: str | None = None
    images: list[str] = Field(default_factory=list)
    rating: float | None = None
    tags: list[str] = Field(default_factory=list)
    amap_poi_id: str | None = None  # 高德地图POI ID


class Route(BaseModel):
    """路线模型"""

    id: str = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    name: str
    description: str | None = None
    cover: str | None = None  # 封面图 URL

    # 路线数据
    points: list[RoutePoint] = Field(default_factory=list)
    pois: list[POI] = Field(default_factory=list)

    # 统计信息
    distance: float = 0.0  # 总距离(米)
    elevation_gain: float = 0.0  # 累计爬升(米)
    estimated_duration: int = 0  # 预计时间(分钟)

    # 位置信息
    start_location: Location  # 起点
    end_location: Location | None = None  # 终点
    city: str | None = None
    district: str | None = None

    # 交互数据
    favorites_count: int = 0
    views_count: int = 0
    completions_count: int = 0

    # 元数据
    difficulty: str = "medium"  # easy, medium, hard
    tags: list[str] = Field(default_factory=list)
    created_by: str | None = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    is_published: bool = True
    is_featured: bool = False  # 是否精选路线

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}


class GPSTrack(BaseModel):
    """GPS轨迹记录"""

    id: str = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    route_id: str | None = None
    user_id: str | None = None

    # 轨迹点数据
    points: list[dict[str, Any]] = Field(default_factory=list)  # [{location, elevation, timestamp, ...}]

    # 统计信息
    distance: float = 0.0
    elevation_gain: float = 0.0
    duration: int = 0  # 实际用时(秒)
    average_speed: float = 0.0  # 平均速度(m/s)

    # 元数据
    started_at: datetime
    ended_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}
