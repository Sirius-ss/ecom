import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from atguigu.app.models.models import Base
from atguigu.common.event_loop import run_async
from atguigu.common.settings import get_settings

async_engine = create_async_engine(get_settings().database_url, echo=False)
session_factory = async_sessionmaker(async_engine, expire_on_commit=False)


async def get_async_session() -> AsyncGenerator[AsyncSession]:
    async with session_factory() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            raise e


async def main():
    async for session in get_async_session():
        result =await session.execute(text("select 1"))
        print(result.scalar())

async def init_db():
    async with async_engine.begin() as conn:
        logger.info("开始初始化customer-service表")
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
        logger.info("初始化结束")

if __name__ == '__main__':
    # run_async(main())
    run_async(init_db())