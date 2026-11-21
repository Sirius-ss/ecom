from enum import StrEnum

from langchain_core.tools import BaseTool

from atguigu.agent.harness.tools.definitions import search_products, get_product, list_orders, get_order, get_logistics, \
    list_after_sales, load_skill, search_knowledge


class ToolCategory(StrEnum):
    """工具类别"""
    BUSINESS = "BUSINESS"
    KNOWLEDGE = "KNOWLEDGE"
    GUIDANCE = "GUIDANCE"


class ToolCatalog:
    def __init__(self,
                 tools: list[tuple[BaseTool, ToolCategory]]
                 ):
        self.tools = tools
        self.tool_categories = {tool.name: category for tool, category in tools}  # 接收工具对象和工具类别之间的关系

    def get_agent_tools(self) -> list[BaseTool]:
        """返回所有工具对象"""
        return [tool for tool, _ in self.tools]

    def get_tool_category(self, tool_name: str):
        """根据工具名称获取工具类别"""
        return self.tool_categories.get(tool_name)


TOOL_CATALOG = ToolCatalog([
    (search_products, ToolCategory.BUSINESS),
    (get_product, ToolCategory.BUSINESS),
    (list_orders, ToolCategory.BUSINESS),
    (get_order, ToolCategory.BUSINESS),
    (get_logistics, ToolCategory.BUSINESS),
    (list_after_sales, ToolCategory.BUSINESS),
    (load_skill, ToolCategory.GUIDANCE),
    (search_knowledge, ToolCategory.KNOWLEDGE)
])
