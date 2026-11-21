import logging
import time
from typing import Any

from fastapi import HTTPException, status
from langchain_core.callbacks import UsageMetadataCallbackHandler
from langchain_core.messages import SystemMessage
from sqlalchemy.ext.asyncio import AsyncSession

from atguigu.agent.harness.run.context import build_messages, AgentRunContext
from atguigu.agent.harness.validator.jev import check_input
from atguigu.agent.harness.validator.validator import ValidateAgentOutError, Validator, build_request
from atguigu.app.models.enums import AgentTraceStatus, ReplyType
from atguigu.app.models.models import AgentTrace
from atguigu.app.schemas import AgentRunRequest, CurrentUser
from atguigu.common.settings import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AgentExecutor:
    def __init__(self, session: AsyncSession, *, agent: Any):
        self._setting = get_settings()
        self._session = session
        self._agent = agent
        self._validator = Validator(session)  # 用来校验

    async def start_run(self,
                        payload: AgentRunRequest,
                        current_user: CurrentUser
                        ) -> dict[str, Any]:
        """
        customer_service的ai-worker请求ai-service，在请求路由处已经完成JWT和服务令牌的双重校验，在这个任务中需获得session 、agent 要完成：
        1.创建一条trace轨迹
        2.构造请求参数
        3.调用agent
        4.拿到llm返回保存记录
        5.返回    TODO推测的 不一定正确 且未加入skill部分 不知道这部分需要如何配合
        :param payload:
        :param current_user:
        :return:
        """
        # 1.创造一条agent_trace轨迹 并报错到agent_trace表中
        agent_traces = AgentTrace(
            conversation_id=payload.conversation_id,
            status=AgentTraceStatus.RUNNING,
            model_name=self._setting.llm_model,
            prompt_version=self._setting.prompt_version
        )
        self._session.add(agent_traces)
        await self._session.commit()

        # 2.调用agent
        start_time = time.perf_counter()
        try:
            run_result = await self._invoke_agent(payload, current_user, agent_traces)
        except Exception as exc:
            logger.exception("Agent推理会话 %s 任务期间出错", payload.conversation_id)
            agent_traces.status = AgentTraceStatus.FAILED
            agent_traces.result = {"text": f"AI 执行出错，原因:{exc}"}
            agent_traces.latency_ms = int((time.perf_counter() - start_time) * 1000)
            await self._session.commit()
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="AI智能体执行出错")

        agent_traces.status = AgentTraceStatus.COMPLETED
        agent_traces.result = run_result
        agent_traces.latency_ms = int((time.perf_counter() - start_time) * 1000)

        await self._session.commit()
        return run_result

    async def _invoke_agent(self,
                            payload: AgentRunRequest,
                            current_user: CurrentUser,
                            agent_traces: AgentTrace) -> dict[str:Any] | None:

        # 回调处理器
        call_back = UsageMetadataCallbackHandler()

        jev_input_tokens = 0
        jev_output_tokens = 0

        try:
            # 1.前置护栏校验
            need_handoff, skill_code, jev_input_tokens, jev_output_tokens = await check_input(payload.messages)
            if need_handoff:
                return build_request(
                    ReplyType.REQUEST_HANDOFF,
                    reply_text="已收到您的诉求，正在为您转接人工客服优先处理，请稍候。",
                    summary="用户要求转接人工客服或情绪较为焦急，请人工客服优先介入处理。"
                )

            # 2.构建LangChain标准消息对象
            messages = build_messages(payload,skill_code)
            logger.info(f"构建好的messages：{messages}")

            # 3.构建上下文
            context = AgentRunContext(
                access_token=current_user.access_token,
                trace_id=agent_traces.id
            )
            for attempt in range(self._setting.agent_max_attempts):
                # 4. agent运行（带纠错）
                agent_output = await self._agent.ainvoke({"messages": messages,"skill_code":skill_code  },
                                                         context=context,
                                                         config={
                                                             "callbacks": [call_back]
                                                         })
                logger.info(f"agent_output:{agent_output}")
                # 护栏校验
                try:
                    return await self._validator.validate_agent_output(
                        skill_code=agent_output.get("skill_code"),
                        agent_output=agent_output['structured_response'],
                        trace_id=context.trace_id
                    )
                except ValidateAgentOutError as e:
                    # 重试纠错（把执行完成的结果和【我要求你根据上一次结果的信息，给我重试】指令）
                    if attempt == self._setting.agent_max_attempts - 1:
                        raise e
                    logger.exception(f"执行Agent期间出现了护栏校验异常：{e}")
                    messages = [
                        *agent_output["messages"],
                        SystemMessage(content=f"上一次回复未通过校验：{e},请修正后重新回复")
                    ]
        # 统计token用量
        finally:
            input_tokens, output_tokens = self._summary_tokens(call_back)
            agent_traces.input_tokens = input_tokens + jev_input_tokens
            agent_traces.output_tokens = output_tokens + jev_output_tokens

    def _summary_tokens(self, call_back: UsageMetadataCallbackHandler):
        all_model_usages: list[dict[str, Any]] = list(call_back.usage_metadata.values())
        input_tokens = sum(model_usage.get("input_tokens", 0) for model_usage in all_model_usages)
        output_tokens = sum(model_usage.get("output_tokens", 0) for model_usage in all_model_usages)
        return input_tokens, output_tokens



