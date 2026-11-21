import json

import time
from typing import Any
from pydantic import BaseModel
from langchain.tools import ToolRuntime

from atguigu.agent.harness.run.context import AgentRunContext
from atguigu.app.models.enums import ToolResultCode
from atguigu.app.models.models import AgentToolCall
from atguigu.infrastructure.db import async_session_factory


class ToolResult(BaseModel):
    success: bool
    code: str
    message: str
    data: Any | None = None


class ToolExecutor:
    async def executor_tool(self,
                            runtime: ToolRuntime[AgentRunContext],
                            tool_name: str,
                            arguments: dict[str, Any],
                            *,
                            operator: Any
                            ):

        start_time = time.perf_counter()

        try:
            response: dict[str, Any] = await operator()
            tool_result = ToolResult.model_validate(response)
        except Exception as exc:
            tool_result = ToolResult(
                success=False,
                code=ToolResultCode.TOOL_CALL_FAILED,
                message=f"业务工具调用失败，无法获取可靠依据，异常原因:{exc}"
            )
        await self._save_tool_result(trace_id=runtime.context.trace_id,
                                     tool_call_id=runtime.tool_call_id,
                                     tool_name=tool_name,
                                     arguments=arguments,
                                     result=tool_result.model_dump(),
                                     success=tool_result.success,
                                     latency_ms=int((time.perf_counter() - start_time
                                                     ) * 1000)
                                     )
        return json.dumps(tool_result.model_dump(), ensure_ascii=False)

    async def _save_tool_result(self,
                                trace_id: str,
                                tool_call_id: str,
                                tool_name: str,
                                arguments: dict[str, Any],
                                result: dict[str, Any],
                                success: bool,
                                latency_ms: int
                                ):
        async with async_session_factory() as session:
            agent_tool_call = AgentToolCall(trace_id=trace_id,
                                            tool_call_id=tool_call_id,
                                            tool_name=tool_name,
                                            arguments=arguments,
                                            result=result,
                                            success=success,
                                            latency_ms=latency_ms
                                            )
            session.add(agent_tool_call)
            await session.commit()


tool_executor = ToolExecutor()
