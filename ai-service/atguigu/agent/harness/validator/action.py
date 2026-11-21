import logging

from atguigu.agent.harness.rules.action import ACTION_CATALOG, ActionCode
from atguigu.agent.harness.validator.validator import ValidateAgentOutError
from atguigu.agent.llm.output import PageAction
from atguigu.app.models.models import AgentToolCall
from atguigu.common.utils import normalized_resource_id


def validate_page_action(successful_tool_calls: list[AgentToolCall], page_action: PageAction | None = None):
    # 无页面动作 不用校验 直接返回
    if page_action is None:
        return None

    # 校验是否有action_code
    logging.info(f"*****action_code:{page_action.action_code}******")
    action_code = page_action.action_code
    if action_code is None:
        raise ValidateAgentOutError(f"页面行动必须要有行动码")

    # 校验行动码是否白名单
    action_definition = ACTION_CATALOG.get_action_definition(action_code)
    logging.info(f"*****action_definition{action_definition}*****")
    if action_definition is None:
        raise ValidateAgentOutError(f"生成的行动码{action_code}不在白名单允许范围内")

    # 如果resource_type是None 则说明这个行动是BROWSE_ORDERS，直接构建行动页面返回
    resource_type = action_definition.resource_type
    if resource_type is None:  # BROWSE_ORDERS
        return action_definition.build_page()

    # 获得resource_id 之后的动作必须要有resource_id
    logging.info(f"******resource_id:{page_action.resource_id}******")
    resource_id = page_action.resource_id
    if resource_id is None:
        raise ValidateAgentOutError(f"{action_code}必须提供订单编号")

    normalize_resource_id = normalized_resource_id(resource_id)

    order_data = _validate_get_order(normalize_resource_id, successful_tool_calls)

    _validate_order_status(order_data["status"], action_code, normalize_resource_id)

    return action_definition.build_page(resource_id=normalize_resource_id)


def _validate_get_order(normalize_resource_id: str, successful_tool_calls: list[AgentToolCall]):
    for stc in successful_tool_calls:
        if stc.tool_name == "get_order" and stc.arguments["order_id"] == normalize_resource_id and stc.success == True:
            return stc.result['data']
    raise ValidateAgentOutError(f"页面引用的订单id{normalize_resource_id}未经get_order工具确认")


def _validate_order_status(order_status: str, action_code: ActionCode, normalize_resource_id: str):
    if action_code in (ActionCode.CANCEL_ORDER, ActionCode.EDIT_ADDRESS) and order_status in (
            "completed", "cancelled", "refunded"):
        raise ValidateAgentOutError(
            f"订单{normalize_resource_id}当前状态为{order_status},不支持生成{action_code}页面跳转动作")
