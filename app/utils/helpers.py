"""工具函数模块"""

from bson import ObjectId
from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema


class PyObjectId(str):
    """MongoDB ObjectId的Pydantic类型"""

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: type, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.with_info_plain_validator_function(cls.validate)

    @classmethod
    def validate(cls, v: str | ObjectId, _: core_schema.ValidationInfo) -> str:
        if isinstance(v, ObjectId):
            return str(v)
        if isinstance(v, str):
            if ObjectId.is_valid(v):
                return v
            raise ValueError("Invalid ObjectId")
        raise ValueError("ObjectId expected")


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    使用Haversine公式计算两点间的距离(米)
    """
    from math import asin, cos, radians, sin, sqrt

    R = 6371000  # 地球半径(米)

    lat1_rad = radians(lat1)
    lat2_rad = radians(lat2)
    delta_lat = radians(lat2 - lat1)
    delta_lon = radians(lon2 - lon1)

    a = sin(delta_lat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lon / 2) ** 2
    c = 2 * asin(sqrt(a))

    return R * c


def calculate_elevation_gain(elevations: list[float]) -> float:
    """
    计算累计爬升(米)
    """
    if len(elevations) < 2:
        return 0.0

    gain = 0.0
    for i in range(1, len(elevations)):
        diff = elevations[i] - elevations[i - 1]
        if diff > 0:
            gain += diff
    return gain


def format_duration(minutes: int) -> str:
    """格式化时长显示"""
    if minutes < 60:
        return f"{minutes}分钟"
    hours = minutes // 60
    mins = minutes % 60
    if mins == 0:
        return f"{hours}小时"
    return f"{hours}小时{mins}分钟"


def format_distance(meters: float) -> str:
    """格式化距离显示"""
    if meters < 1000:
        return f"{meters:.0f}米"
    km = meters / 1000
    return f"{km:.1f}公里"
