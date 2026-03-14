"""CLI entry point for seeding."""

import asyncio

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from config.settings import get_settings
from seeds.agents import seed_agents


async def main() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as db:
        counts = await seed_agents(db)
        print(f"Seeded: {counts}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
