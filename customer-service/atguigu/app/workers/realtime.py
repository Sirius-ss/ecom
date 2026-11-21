import asyncio
import json
import logging

from redis import RedisError

from atguigu.app.services.realtime import RealtimeService
from atguigu.common.settings import get_settings
from atguigu.infrastucture.db import session_factory
from atguigu.infrastucture.redis import redis_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RealtimeWorker:
    def __init__(self):
        self._setting = get_settings()
        self._session_factory = session_factory
        self._redis_client = redis_client

    async def start(self):
        logger.info("Realtime Worker启动")
        while True:
            claimed_event = await self._process_claim_event()
            if not claimed_event:
                await asyncio.sleep(1)

    async def _process_claim_event(self):
        async with self._session_factory() as session:
            # 实例化realtime service对象
            realtime_service = RealtimeService(session)
            # 拿取一个最早产生的未发布事件
            claim_event = await realtime_service.get_unpublish_event()
            # 未找到返回false
            if claim_event is None:
                return False

            # 发布到redis特定的通道
            try:
                await self._redis_client.publish(claim_event.target, json.dumps(claim_event.data, ensure_ascii=False))
            except RedisError as exc:
                logger.exception("发送给Redis服务的%s失败,原因:%s", claim_event.target, str(exc))
                return False

            # 修改该事件为已发布
            await realtime_service.mark_published_event(claim_event)

            # 返回
            return True
