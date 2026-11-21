import asyncio
import logging
from typing import Any

import httpx

from atguigu.app.services.auth import encode_access_token
from atguigu.app.services.chat import ChatService
from atguigu.common.event_loop import run_async
from atguigu.common.settings import get_settings
from atguigu.infrastucture.db import session_factory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AIWorker:
    def __init__(self):
        self._setting = get_settings()

    async def start(self):
        logger.info("AI Work 启动")
        while True:
            # print('已经进入ai-worker')
            claimed_turn = await self._process_claim_turn()
            if not claimed_turn:
                await asyncio.sleep(self._setting.ai_worker_poll_interval_ms / 1000)

    async def _process_claim_turn(self):
        async with session_factory() as session:
            chat_service = ChatService(session)
            # 获取一个活跃的turn和获得要发给大模型的payload
            claim_turn_and_payload = await chat_service.claim_turn_and_build_payload()

            if not claim_turn_and_payload:
                return False

            claim_turn, payload, user_id = claim_turn_and_payload

            # 调用AI service
            ai_result, error = await self._call_ai_service(payload, user_id)

            # 结算轮次相关信息
            await chat_service.finish_turn(claim_turn, ai_result, error)
            return True

    async def _call_ai_service(self, payload: dict[str:Any], user_id: str) -> tuple[
        dict[str, Any] | None, Exception | None]:
        """"
        # 构建ai-service请求url
        # 携带参数 payload
        # 发送请求
        # 接收响应数据
        """
        access_token = encode_access_token(user_id)

        # 构造请求头
        headers = {
            "Authorization": f"Bearer {access_token}",
            "X-Internal-Service-Token": self._setting.internal_service_token
        }

        # 构造过期时间
        timeout = httpx.Timeout(self._setting.ai_timeout_seconds, connect=5)

        # 发送请求
        try:
            async with httpx.AsyncClient(timeout=timeout, trust_env=False) as client:
                response = await client.post(
                    f"{self._setting.ai_service_url}/internal/v1/agent/runs",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()  # 确认返回是200 否则走exception
                return response.json(), None
        except Exception as exc:
            # 请求失败返回
            logger.exception("会话 %s 调用 AI Service 失败: %s", payload["conversation_id"], exc)
            return None, exc


async def main():
    ai_work = AIWorker()
    await ai_work.start()

if __name__ == '__main__':
    run_async(main())
