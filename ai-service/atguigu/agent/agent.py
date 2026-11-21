from langchain.agents import create_agent, AgentState

from atguigu.agent.harness.middleware.scope import SkillScopeMiddleWare
from atguigu.agent.harness.run.context import AgentRunContext, AgentRunState
from atguigu.agent.harness.tools.catalog import TOOL_CATALOG
from atguigu.agent.llm.adapter import get_llm_client
from atguigu.agent.llm.output import AgentOutput
from atguigu.agent.llm.prompt import build_system_prompt


def create_ai_agent():
    return create_agent(
        model=get_llm_client(),
        system_prompt=build_system_prompt(),
        tools=TOOL_CATALOG.get_agent_tools(),
        middleware=[SkillScopeMiddleWare()],
        response_format=AgentOutput,
        context_schema=AgentRunContext,
        state_schema=AgentRunState
    )


if __name__ == '__main__':
    agent = create_ai_agent()
    res = agent.invoke({"messages": "心情不好怎么办"})
    print(res)
