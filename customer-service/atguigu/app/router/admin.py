from fastapi import APIRouter

from atguigu.app.dependencies import AdminService, AdminRoleAuthDep, StaffRoleAuthDep
from atguigu.app.schemas import ReplyRequest

router = APIRouter(prefix="/api/v1", tags=["管理端路由接口"])


@router.get("/handoffs", description="获取工单列表")
async def get_handoff_endpoint(
        service: AdminService,
        _: StaffRoleAuthDep
):
    return await service.get_handoffs()


@router.get("/handoffs/{handoff_id}/messages", description="获取工单对应的消息id")
async def get_handoff_messages_endpoint(
        service: AdminService,
        _: StaffRoleAuthDep,
        handoff_id: str
):
    return await service.get_handoff_message(handoff_id)


@router.post("/handoffs/{handoff_id}/accept", description="接受工单")
async def accept_handoff_endpoint(
        service: AdminService,
        staff_auth: StaffRoleAuthDep,
        handoff_id: str
):
    await service.accept_handoff(handoff_id, staff_auth.user_id)


@router.post("/handoffs/{handoff_id}/messages", description="客服回复客户消息")
async def reply_messages_endpoint(
        service: AdminService,
        _: StaffRoleAuthDep,
        handoff_id: str,
        payload: ReplyRequest
):
    await service.reply_messages(handoff_id, payload)


@router.post("/handoffs/{handoff_id}/resolve", description="结束工单")
async def resolve_handoff_endpoint(
        service: AdminService,
        _: StaffRoleAuthDep,
        handoff_id: str
):
    await service.resolve_handoff(handoff_id)


@router.get("/admin/metrics", description="获取admin管理页面指标信息")
async def get_metrics_endpoint(
        service: AdminService,
        _: AdminRoleAuthDep
):
    return await service.get_metrics()
