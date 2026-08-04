"""Seed local PostGIS with platform places."""

import asyncio

from app.geo.database import GeoDatabase
from app.geo.seed import seed_demo_places


async def main() -> None:
    await GeoDatabase.connect()
    try:
        await seed_demo_places()
    finally:
        await GeoDatabase.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
