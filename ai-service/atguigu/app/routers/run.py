from typing import Any
import logging
from fastapi import APIRouter

from atguigu.app.dependencies import UserDep, AgentExecutorDep, TokenAuthDep
from atguigu.app.schemas import AgentRunRequest, CurrentUser

logging.basicConfig(level=logging.INFO)
logger=logging.getLogger(__name__)
router = APIRouter(tags=["Ai Service允许路由"])


@router.post("/internal/v1/agent/runs")
async def start_run_endpoint(
        payload: AgentRunRequest,
        current_user: UserDep,
        agent_executor: AgentExecutorDep,
        _: TokenAuthDep
) -> dict[str, Any]:
    result = await agent_executor.start_run(payload, current_user)
    logger.info(f"路由获得的return:{result}")
    return result
