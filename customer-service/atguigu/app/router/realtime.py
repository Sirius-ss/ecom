import asyncio
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, status

from atguigu.app.services.auth import decode_access_token
from atguigu.infrastucture.redis import redis_client

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

router = APIRouter(tags=["实时事件推送路由"])


@router.websocket("/api/v1/realtime")
async def get_realtime_endpoint(ws: WebSocket):
    # 建立websocket连接 把普通http协议升级为ws协议
    await ws.accept()

    # 获取前端发送过来的认证信息
    try:
        auth_info: dict[str:Any] = await ws.receive_json()
        access_token = auth_info["token"]
    except Exception as exc:
        logger.exception(f"用户认证信息获取失败：{exc}")
        await ws.close(code=status.WS_1008_POLICY_VIOLATION, reason="用户未认证")
        return

    # 根据认证信息获取用户信息
    current_user = decode_access_token(access_token)
    target_channel = current_user.user_id if current_user.role == 'user' else "staff"

    # 注册通道到redis
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(target_channel)

    # 发送成功注册到redis中
    await ws.send_json({"event_type": "connected"})

    async def forward_event():
        async for message in pubsub.listen():
            if message["type"] == "message":
                event_data = message["data"]
                await ws.send_text(event_data)

    async def disconnected():
        while True:
            await ws.receive_text() # 断线探测器 当浏览器关闭时抛WebSocketDisconnect

    task = [
        asyncio.create_task(forward_event()),
        asyncio.create_task(disconnected())
    ]

    try:
        _, pending = await asyncio.wait(task, return_when=asyncio.FIRST_COMPLETED)

        for pend in pending:
            pend.cancel()

        await asyncio.gather(*task, return_exceptions=True)
    finally:
        # 连接断开时释放订阅，归还 Redis 连接；订阅者归零后 channel 自动消失
        try:
            await pubsub.unsubscribe(target_channel)
        finally:
            await pubsub.aclose()
