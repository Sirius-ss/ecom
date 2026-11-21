from typing import Any

from fastapi import APIRouter

from atguigu.app.dependencies import ChatServiceDep, UserRoleAuthDep
from atguigu.app.schemas import ChatMessageRequest

router = APIRouter(prefix="/api/v1/chat", tags=["会话管理路由:对话、加载历史会话消息"])


@router.post("/messages")
async def chat_endpoint(
        payload: ChatMessageRequest,
        service: ChatServiceDep, # TODO调用这个接口时 service user_role 从哪里获得传入的 好像不是传入的 是依赖注入
        user_role_dep: UserRoleAuthDep
):
    await service.process_chat_message(user_role_dep.user_id, payload)


@router.get("/history")
async def get_history_endpoint(
        service: ChatServiceDep,
        user_role_dep: UserRoleAuthDep) -> dict[str, Any]:
    return await service.get_chat_history(user_role_dep.user_id)
