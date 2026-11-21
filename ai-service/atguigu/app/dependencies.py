from typing import Annotated

from fastapi import Depends, Header, HTTPException, status, Request
from fastapi.params import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from atguigu.agent.agent import create_ai_agent
from atguigu.agent.harness.run.executor import AgentExecutor
from atguigu.app.schemas import CurrentUser
from atguigu.app.services.admin import AdminService
from atguigu.app.services.auth import get_authorized_user
from atguigu.app.services.knowledge import KnowledgeService
from atguigu.common.settings import get_settings
from atguigu.infrastructure.db import get_async_session

SessionDep = Annotated[AsyncSession, Depends(get_async_session)]


def require_user(authorization: Annotated[str | None, Header()] = None) -> CurrentUser:
    return get_authorized_user(authorization, "user")


UserDep = Annotated[CurrentUser, Depends(require_user)]


def get_agent_executor(session: SessionDep, request: Request) -> AgentExecutor:
    return AgentExecutor(session, agent=request.app.state.agent)


AgentExecutorDep = Annotated[AgentExecutor, Depends(get_agent_executor)]


def require_internal_service(token: Annotated[str | None, Header(alias="X-Internal-Service-Token")] = None):
    if token != get_settings().internal_service_token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无效的内部访问令牌")


TokenAuthDep = Annotated[None, Depends(require_internal_service)]


def require_admin(authorization: Annotated[str | None, Header()] = None) -> CurrentUser:
    return get_authorized_user(authorization, "admin")


AdminDep = Annotated[CurrentUser, Depends(require_admin)]


def get_admin_service(session: SessionDep) -> AdminService:
    return AdminService(session)


AdminServiceDep = Annotated[AdminService, Depends(get_admin_service)]


def get_knowledge_service(session: SessionDep) -> KnowledgeService:
    return KnowledgeService(session)


KnowledgeServiceDep = Annotated[KnowledgeService, Depends(get_knowledge_service)]
