from dataclasses import dataclass
from enum import StrEnum


class ActionCode(StrEnum):
    """定义服务端允许生成的页面动作编码"""
    BROWSE_ORDERS = "BROWSE_ORDERS"
    OPEN_ORDER_DETAIL = "OPEN_ORDER_DETAIL"
    CANCEL_ORDER = "CANCEL_ORDER"
    EDIT_ADDRESS = "EDIT_ADDRESS"
    APPLY_AFTER_SALE = "APPLY_AFTER_SALE"
    VIEW_AFTER_SALES = "VIEW_AFTER_SALES"


@dataclass(frozen=True, slots=True)
class ActionDefinition:
    action_code: ActionCode
    label: str
    description: str
    path_template: str
    resource_type: str | None = None  # 订单/商品

    def build_page(self, resource_id: str | None = None):
        return {
            "label": self.label,
            "description": self.description,
            "href": self.path_template.format(resource_id=resource_id)
        }


class ActionCatalog:
    def __init__(self, definitions: list[ActionDefinition]):
        self.definition = {definition.action_code: definition for definition in definitions}

    def get_action_definition(self, action_code: ActionCode) -> ActionDefinition | None:
        """根据action_code找到action"""
        return self.definition.get(action_code)

    def get_action_page_index(self) -> str:
        return "\n".join(
            f"{action_definition.action_code}:{action_definition.description}"
            for action_definition in self.definition.values()
        )


ACTION_CATALOG = ActionCatalog(
    [
        ActionDefinition(
            action_code=ActionCode.BROWSE_ORDERS,
            label="查看我的订单",
            description="进入我的订单列表",
            path_template="/me",

        ),
        ActionDefinition(
            action_code=ActionCode.OPEN_ORDER_DETAIL,
            label="查看订单详情",
            description="进入订单详情查看状态与可用操作",
            path_template="/me/orders/{resource_id}",  # /me/orders/ORDER_001
            resource_type="order"
        ),
        ActionDefinition(
            action_code=ActionCode.CANCEL_ORDER,
            label="前往取消订单",
            description="进入订单页面核对状态并确认取消",
            path_template="/me/orders/{resource_id}/cancel",
            resource_type="order"
        ),
        ActionDefinition(
            action_code=ActionCode.EDIT_ADDRESS,
            label="前往修改地址",
            description="进入订单页面修改收货地址",
            path_template="/me/orders/{resource_id}/address",
            resource_type="order"

        ),
        ActionDefinition(
            action_code=ActionCode.APPLY_AFTER_SALE,
            label="申请售后",
            description="进入订单页面填写售后申请",
            path_template="/me/orders/{resource_id}/after-sale",
            resource_type="order"
        ),
        ActionDefinition(
            action_code=ActionCode.VIEW_AFTER_SALES,
            label="查看售后进度",
            description="进入订单页面查看售后记录",
            path_template="/me/orders/{resource_id}?section=after-sales",
            resource_type="order"
        ),
    ]
)
