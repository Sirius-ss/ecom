import json
from dataclasses import dataclass
from typing import Any, NotRequired

from langchain.agents import AgentState
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage

from atguigu.agent.harness.rules.skill import SkillCode, SKILL_CATALOG, SkillDefinition
from atguigu.app.schemas import AgentRunRequest
from atguigu.common.settings import get_settings


@dataclass(frozen=True,
           slots=True)  # @dataclass装饰器 自动实现__init__ __eq__等类方法，frozen冻结数据不可变 slots不再生成__dict__内存优化 BaseModel适合做输入输出的校验 dataclass做内部数据的流转 因为不用再做各种校验，所以效率很高
class AgentRunContext:
    trace_id: str
    access_token: str


class AgentRunState(AgentState):
    """Agent运行时的上下文state 动态改变"""
    skill_code: NotRequired[str]

def build_messages(payload: AgentRunRequest, skill_code: SkillCode | None = None) -> list[BaseMessage]:
    """标准化消息对象为LangChain的消息对象"""
    # 1.获取历史消息
    history_messages: list[dict[str, Any]] = _build_history_messages(payload.history)
    # 2.标准化消息对象
    messages: list[BaseMessage] = [
        HumanMessage(content=_format_message(history_message))
        if history_message['role'] == 'USER' else
        AIMessage(content=_format_message(history_message))
        for history_message in history_messages
    ]
    # 3.获取当前轮次消息
    current_messages = _build_current_messages(payload.messages)
    messages.append(HumanMessage(content=current_messages))

    # 4.若匹配到领域技能，将对应领域技能规则注入上下文
    if skill_code is not None:
        skill_definition: SkillDefinition = SKILL_CATALOG.get_skill_definition(skill_code)
        skill_guidance = "\n".join(f"- {guidance}" for guidance in skill_definition.guidance)
        messages.append(SystemMessage(content=f"已经成功加载技能{skill_code},请遵循以下规则：{skill_guidance}"))
    # 5.返回 历史对话消息+当前轮次消息
    return messages


def _build_history_messages(history: list[dict[str, Any]]):
    # 输入历史消息 1.倒叙截取30条 2.控制整体字符长度 3.第一条只要从用户开始的
    settings = get_settings()
    # 只取最后30条
    candidate_history_messages = history[-settings.history_message_limit:]
    usage_total = 0
    messages = []
    # 控制字符长度
    for history_message in reversed(candidate_history_messages):
        message_content = _format_message(history_message)
        if usage_total + len(message_content) > settings.history_character_budget:
            break
        messages.append(history_message)
        usage_total += len(message_content)
    # 反转回来
    messages.reverse()

    # 去掉开始非user角色的消息
    index = next((index for index, message in enumerate(messages) if message["role"] == 'USER'), None)
    return messages[index:] if index is not None else messages


def _build_current_messages(messages: list[dict[str, Any]]):
    # 单条消息直接返回内容 多条需要做个拼接
    message_contents = [_format_message(message) for message in messages]
    if len(message_contents) == 1:
        return message_contents[0]
    items = "\n".join(f"{index}.{content}" for index, content in enumerate(message_contents, start=1))
    return "用户当前发送了多条消息，请您当作一个整体来理解：\n" + items


def _format_message(message: dict[str:Any]) -> str:
    """针对单条消息做结构化 如果是text类型的消息直接返回，是结构类型的消息json.dumps转以下再返回"""
    if message.get("type") == "text":
        return message["content"].get("text")

    message_content = message["content"]
    return f"消息是一个对象，结构是：\n" + json.dumps(message_content, ensure_ascii=False, indent=2)



