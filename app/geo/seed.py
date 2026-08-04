"""Idempotent platform place seeding for local development."""

from loguru import logger

from app.geo.repositories import PlaceRepository
from app.geo.schemas import GeoPoint, PlaceCreate

DEMO_PLACES = [
    PlaceCreate(
        name="武康大楼",
        description="上海历史建筑与街区漫步地标",
        address="淮海中路1850号",
        location=GeoPoint(longitude=121.43831, latitude=31.20756),
        categories=["建筑"],
        tags=["历史", "拍照"],
        city="上海",
        district="徐汇区",
    ),
    PlaceCreate(
        name="衡山公园",
        description="适合短暂停留的社区公园",
        address="广元路2号",
        location=GeoPoint(longitude=121.44122, latitude=31.20437),
        categories=["公园"],
        tags=["安静", "树荫"],
        city="上海",
        district="徐汇区",
    ),
    PlaceCreate(
        name="徐家汇书院",
        description="公共文化空间与阅读场所",
        address="漕溪北路158号",
        location=GeoPoint(longitude=121.43695, latitude=31.19158),
        categories=["文化"],
        tags=["安静", "建筑"],
        city="上海",
        district="徐汇区",
    ),
    PlaceCreate(
        name="上海工艺美术博物馆",
        description="法式建筑中的工艺美术展馆",
        address="汾阳路79号",
        location=GeoPoint(longitude=121.45221, latitude=31.21109),
        categories=["文化", "建筑"],
        tags=["历史", "拍照"],
        city="上海",
        district="徐汇区",
    ),
    PlaceCreate(
        name="襄阳公园",
        description="市中心的小型林荫公园",
        address="淮海中路1008号",
        location=GeoPoint(longitude=121.45769, latitude=31.21680),
        categories=["公园"],
        tags=["树荫", "安静"],
        city="上海",
        district="徐汇区",
    ),
    PlaceCreate(
        name="永康路咖啡街区",
        description="沿街分布多家咖啡与小店",
        address="永康路",
        location=GeoPoint(longitude=121.45702, latitude=31.21313),
        categories=["咖啡"],
        tags=["街区", "拍照"],
        city="上海",
        district="徐汇区",
    ),
]


async def seed_demo_places(repository: PlaceRepository | None = None) -> int:
    repository = repository or PlaceRepository()
    created = 0
    for place_data in DEMO_PLACES:
        if await repository.find_duplicate(place_data, radius_m=25):
            continue
        await repository.create_place(
            place_data,
            source_type="platform",
            external_refs={"seed": f"demo:{place_data.name}"},
            quality_score=0.9,
        )
        created += 1
    logger.info(f"平台预置地点完成，新增 {created} 个地点")
    return created
