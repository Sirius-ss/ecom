from enum import StrEnum


class AgentTraceStatus(StrEnum):
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ToolResultCode(StrEnum):
    TOOL_CALL_FAILED = "TOOL_CALL_FAILED"
    KNOWLEDGE_SEARCH_COMPLETED = "KNOWLEDGE_SEARCH_COMPLETED"


class ReplyType(StrEnum):
    ANSWER = "ANSWER"
    REQUEST_HANDOFF = "REQUEST_HANDOFF"
    CLARIFY = "CLARIFY"
    DECLINE = "DECLINE"
