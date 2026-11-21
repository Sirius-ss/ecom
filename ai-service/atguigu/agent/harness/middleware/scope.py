from typing import Callable, Awaitable

from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse

from atguigu.agent.harness.rules.skill import SKILL_CATALOG
from atguigu.agent.harness.run.context import AgentRunState, AgentRunContext
from atguigu.agent.llm.output import AgentOutput
from atguigu.app.schemas import AgentRunRequest


class SkillScopeMiddleWare(AgentMiddleware[AgentRunState, AgentRunContext, AgentOutput]):
    """
    定义类:目标希望能够根据领域对工具做裁剪
    """

    async def awrap_model_call(
            self,
            request: ModelRequest[AgentRunContext],
            handler: Callable[[ModelRequest[AgentRunContext]], Awaitable[ModelResponse[AgentOutput]]],
    ) -> ModelResponse[AgentOutput]:
        """
        在agent调用llm之前 程序员可以单独做增强。可以修改模型请求、响应中的内容
        职责：根据领域码找到该领域工具
        :param request:
        :param handler:
        :return:
        """
        # 获取领域码
        skill_code = request.state.get("skill_code")
        all_tool_name = ["load_skill"]

        if skill_code is not None:
            # 获取技能对象对应的tool_name
            definition = SKILL_CATALOG.get_skill_definition(skill_code)
            all_tool_name.extend(definition.tools)

        # 该领域真正的工具对象
        allow_tool = [tool for tool in request.tools if tool.name in all_tool_name]

        # 修改模型真正请求的工具
        return await handler(request.override(tools=allow_tool, model_settings={"parallel_tool_calls": False}))# 禁止并发
