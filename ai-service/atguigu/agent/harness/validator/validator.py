import logging
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from atguigu.agent.llm.output import AgentOutput
from atguigu.app.models.enums import ReplyType, ToolResultCode
from atguigu.app.models.models import AgentToolCall
from langchain_protocol import AgentResult
from atguigu.agent.harness.tools.catalog import TOOL_CATALOG, ToolCategory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ValidateAgentOutError(ValueError):
    pass


from atguigu.agent.harness.validator.action import validate_page_action
from atguigu.agent.harness.validator.answer import validate_answer
from atguigu.agent.harness.validator.jev import check_output


BUSINESS_FAILURE_MESSAGE = "暂时无法查询到可靠的订单、商品、物流或售后信息，请您稍后重试，或直接发送“转人工”由人工客服为您处理。"


class Validator:

    def __init__(self, session: AsyncSession):
        self.session = session

    async def validate_agent_output(self,
                                    skill_code: str | None,
                                    agent_output: AgentOutput,
                                    trace_id: str
                                    ) -> dict[str:Any]:
        # 获取agent输出类型
        reply_type = agent_output.reply_type
        logger.info(f"reply_type:{reply_type}")

        # 查询工具调用记录
        stmt = select(AgentToolCall).where(AgentToolCall.trace_id == trace_id).order_by(AgentToolCall.created_at)
        tool_calls: list[AgentToolCall] = list((await self.session.scalars(stmt)).all())
        logger.info(f"***tool_calls:{tool_calls}")
        if reply_type == ReplyType.ANSWER:
            # 如果有skill_code 但没有查询到工具调用记录则校验不通过 抛异常
            if skill_code is not None and tool_calls is None:
                raise ValidateAgentOutError(f"加载领域技能码{skill_code},但没有调用工具查询获取回复结果，请调用工具查询")
            # 查询出本次调用的业务来类的toll
            bs_tool_calls = [tool_call for tool_call in tool_calls if
                             TOOL_CATALOG.get_tool_category(tool_call.tool_name) == ToolCategory.BUSINESS]
            logger.info(f"bs_tool_calls:{bs_tool_calls}")
            # 总调用工具中有值，业务类工具没值 说明只调用了知识检索工具 跳过不做校验
            if tool_calls and not bs_tool_calls:
                return build_request(
                    ReplyType.ANSWER,
                    agent_output.text
                )
            # 调用成功的业务类工具记录
            successful_tool_call = [tool_call for tool_call in bs_tool_calls if
                                    tool_call.result["code"] != ToolResultCode.TOOL_CALL_FAILED]
            logger.info(f"****successful_tool_call:{successful_tool_call}")
            # 所有工具都调用失败了 直接兜底降级
            if bs_tool_calls and not successful_tool_call:
                return build_request(
                    ReplyType.DECLINE,  # 自己构建明确的拒绝
                    BUSINESS_FAILURE_MESSAGE
                )

            # 有成功的业务工具，校验answer
            validate_answer(agent_output.text, successful_tool_call)

            # Jev语义护栏校验answer
            await check_output(agent_output.text,successful_tool_call)

            # 校验页面行动
            logger.info(f"******开始做页面动作校验agent_output.page_action：{agent_output.page_action}*******")
            page_action: dict[str, Any] = validate_page_action(successful_tool_call, agent_output.page_action)

            logger.info(f"ANSWER:{ReplyType.ANSWER}\n")
            logger.info(f"text:{agent_output.text}\n")
            logger.info(f"page_action:{page_action}")
            # 返回
            return build_request(ReplyType.ANSWER, agent_output.text, page_action=page_action)

        if reply_type == ReplyType.REQUEST_HANDOFF:
            if agent_output.handoff_summary is None:
                raise ValidateAgentOutError(f"转人工请求必须提供handoff_summary")

            return build_request(ReplyType.REQUEST_HANDOFF, agent_output.text, summary=agent_output.handoff_summary)

        if reply_type == ReplyType.CLARIFY:
            choices = _build_clarify_choices(tool_calls)
            return build_request(ReplyType.CLARIFY, agent_output.text, choices=choices)

        return build_request(
            ReplyType.DECLINE,
            BUSINESS_FAILURE_MESSAGE
        )


def build_request(
        reply_type: ReplyType,
        reply_text: str,
        *,
        summary: str | None = None,
        page_action: dict[str, Any] | None = None,
        choices: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    logger.info(f"build_request方法中的page_action：{page_action}")
    return {
        "reply_type": reply_type,
        "text": reply_text,
        "summary": summary,
        "page_action": page_action,
        "choices": choices
    }


def _build_clarify_choices(tool_calls: list[AgentToolCall]) -> list[dict[str, Any]] | None:
    """
    只对订单做澄清
    :param tool_calls:
    :return:
    """
    for tool_call in tool_calls:
        if tool_call.tool_name == "list_orders" and tool_call.success == True:
            return [
                {
                    "object_type": "order",
                    "object_id": order["id"],
                    "label": f"{order['id']} · {'、'.join(item['product_name'] for item in order['items'])}",
                    "description": f"¥{order['total_amount']} · {order['status_label']}",
                }
                for order in tool_call.result['data'][:5]  # 五个单
            ]
    return None
