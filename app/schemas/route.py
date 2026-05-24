"""路线相关的API schemas"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# === 请求Schemas ===

class LocationSchema(BaseModel):
    """地理位置"""
    longitude: float = Field(..., ge=-180, le=180)
    latitude: float = Field(..., ge=-90, le=90)


# === 轨迹点编辑相关Schema ===

class RoutePointPhotoUpload(BaseModel):
    """上传轨迹点照片"""
    data: str = Field(..., description="Base64编码的图片数据（可含data:xxx;base64,前缀）")
    content_type: str | None = Field(None, description="MIME类型")
    caption: str | None = Field(None, max_length=200, description="照片说明")


class RoutePointCreate(BaseModel):
    """创建轨迹点"""
    longitude: float = Field(..., ge=-180, le=180)
    latitude: float = Field(..., ge=-90, le=90)
    elevation: float | None = None
    name: str | None = Field(None, max_length=100)
    description: str | None = Field(None, max_length=500)
    is_waypoint: bool = False


class RoutePointUpdate(BaseModel):
    """更新轨迹点"""
    longitude: float | None = Field(None, ge=-180, le=180)
    latitude: float | None = Field(None, ge=-90, le=90)
    name: str | None = Field(None, max_length=100)
    description: str | None = Field(None, max_length=500)
    is_waypoint: bool | None = None


class RoutePointsBatchUpdate(BaseModel):
    """批量更新轨迹点"""
    # 要添加的点（在指定索引位置）
    add_points: list[dict[str, Any]] | None = Field(
        None,
        description="要添加的点列表，格式: [{index: 0, point: {...}}, ...]"
    )
    # 要更新的点
    update_points: list[dict[str, Any]] | None = Field(
        None,
        description="要更新的点列表，格式: [{index: 0, updates: {...}}, ...]"
    )
    # 要删除的点索引
    delete_indices: list[int] | None = Field(
        None,
        description="要删除的点索引列表"
    )


class RoutePointResponse(BaseModel):
    """轨迹点响应"""
    index: int
    location: dict[str, Any]
    elevation: float | None = None
    name: str | None = None
    description: str | None = None
    is_waypoint: bool = False
    photos: list[dict[str, Any]] = Field(default_factory=list)
    poi_id: str | None = None


class RoutePointLight(BaseModel):
    """轨迹点精简版（用于前端地图渲染）"""
    location: dict[str, Any]
    elevation: float | None = None
    timestamp: datetime | None = None


class RouteCreate(BaseModel):
    """创建路线请求"""
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(None, max_length=2000)
    preview_image: str | None = None
    images: list[str] = Field(default_factory=list)

    points: list[dict[str, Any]] = Field(default_factory=list)
    pois: list[dict[str, Any]] = Field(default_factory=list)

    distance: float = Field(default=0.0, ge=0)
    elevation_gain: float = Field(default=0.0, ge=0)
    estimated_duration: int = Field(default=0, ge=0)

    start_location: LocationSchema
    end_location: LocationSchema | None = None
    city: str | None = None
    district: str | None = None

    difficulty: str = "medium"
    tags: list[str] = Field(default_factory=list)


class RouteUpdate(BaseModel):
    """更新路线请求"""
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=2000)
    preview_image: str | None = None
    images: list[str] | None = None

    points: list[dict[str, Any]] | None = None
    pois: list[dict[str, Any]] | None = None

    distance: float | None = Field(None, ge=0)
    elevation_gain: float | None = Field(None, ge=0)
    estimated_duration: int | None = Field(None, ge=0)

    difficulty: str | None = None
    tags: list[str] | None = None
    is_published: bool | None = None


class GPSTrackCreate(BaseModel):
    """创建GPS轨迹请求"""
    route_id: str | None = None
    user_id: str | None = None
    points: list[dict[str, Any]] = Field(..., min_length=1)
    started_at: datetime
    ended_at: datetime | None = None


class GPSTrackUpdate(BaseModel):
    """更新GPS轨迹请求"""
    ended_at: datetime | None = None
    points: list[dict[str, Any]] | None = None


# === 响应Schemas ===

class RouteListItem(BaseModel):
    """路线列表项"""
    id: str = Field(..., alias="_id")
    name: str
    description: str | None = None
    preview_image: str | None = None
    distance: float
    elevation_gain: float
    estimated_duration: int
    city: str | None = None
    favorites_count: int
    difficulty: str
    tags: list[str]
    created_at: datetime
    created_by: str | None = None

    class Config:
        populate_by_name = True


class RouteDetail(BaseModel):
    """路线详情"""
    id: str = Field(..., alias="_id")
    name: str
    description: str | None = None
    preview_image: str | None = None
    images: list[str] = Field(default_factory=list)

    points: list[dict[str, Any]] = Field(default_factory=list)
    pois: list[dict[str, Any]] = Field(default_factory=list)

    distance: float
    elevation_gain: float
    estimated_duration: int

    start_location: dict[str, Any]
    end_location: dict[str, Any] | None = None
    city: str | None = None
    district: str | None = None

    favorites_count: int
    views_count: int
    completions_count: int
    difficulty: str
    tags: list[str]
    created_at: datetime
    updated_at: datetime
    created_by: str | None = None
    is_published: bool = True
    score: float | None = None

    class Config:
        populate_by_name = True


class GPSTrackResponse(BaseModel):
    """GPS轨迹响应"""
    id: str = Field(..., alias="_id")
    route_id: str | None = None
    user_id: str | None = None

    points: list[dict[str, Any]]
    distance: float
    elevation_gain: float
    duration: int
    average_speed: float

    started_at: datetime
    ended_at: datetime | None = None
    created_at: datetime

    class Config:
        populate_by_name = True


class PaginatedRoutes(BaseModel):
    """分页路线列表"""
    items: list[RouteListItem]
    total: int
    page: int
    page_size: int
    has_more: bool


class NavigationData(BaseModel):
    """导航数据"""
    route_id: str
    points: list[dict[str, Any]]
    pois: list[dict[str, Any]]
    elevation_profile: list[dict[str, Any]]  # [{distance, elevation}, ...]
    total_distance: float
    total_elevation_gain: float
    estimated_time: int
