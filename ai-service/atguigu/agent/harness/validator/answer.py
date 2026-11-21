import re

from atguigu.agent.harness.validator.validator import ValidateAgentOutError
from atguigu.app.models.models import AgentToolCall
from atguigu.common.utils import normalized_resource_id

RESOURCE_ID_RE = re.compile(
    r"\b(?:ORDER|PRODUCT|AS)[_-][A-Z0-9_-]+\b",
    re.IGNORECASE,
)

NUMBER_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:元|块|件|台|套|笔|单)")

STATUS_CODE_MAP = {
    "已支付": "paid",
    "待发货": "pending_shipment",
    "已发货": "shipped",
    "已完成": "completed",
    "已取消": "cancelled",
    "已退款": "refunded",
    "运输中": "in_transit",
    "已签收": "delivered",
    "待处理": "pending",
    "已通过": "approved",
    "处理中": "processing",
    "已拒绝": "rejected"
}


def validate_answer(reply_text: str, successful_tool_calls: list[AgentToolCall]):
    unsupported_facts = []
    # 根据工具调用记录查找事实
    evidence_text, evidence_number = _collect_fact_evidence(successful_tool_calls)

    for raw_id in set(re.findall(RESOURCE_ID_RE, reply_text)):
        normalized_raw_id = normalized_resource_id(raw_id)
        if normalized_raw_id not in evidence_text:
            unsupported_facts.append(normalized_raw_id)

    for number_id in set(re.findall(NUMBER_RE, reply_text)):
        if float(number_id) not in evidence_number:
            unsupported_facts.append(number_id)

    for label, code in STATUS_CODE_MAP.items():
        if (label in reply_text or code in reply_text) and code not in evidence_text:
            unsupported_facts.append(code)

    if unsupported_facts:
        values = "、".join(unsupported_facts)
        raise ValidateAgentOutError(f"回复中的业务事实缺少工具支持：{values}，请根据工具返回结果回答")


def _collect_fact_evidence(successful_tool_calls: list[AgentToolCall]) -> tuple[set[str], set[str]]:
    evidence_text = set()
    evidence_number = set()

    def collect(value: object):
        if isinstance(value, dict):
            for v in value.values():
                collect(v)
        if isinstance(value, list):
            evidence_number.add(len(value))
            for item in value:
                collect(item)

        if isinstance(value, str):
            evidence_text.add(value)

        if isinstance(value, int | float):
            evidence_number.add(float(value))

    for stc in successful_tool_calls:
        collect(stc.arguments)
        collect(stc.result["data"])

    return evidence_text, evidence_number
