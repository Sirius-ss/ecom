from enum import StrEnum


class ConversationMode(StrEnum):
    """会话模式"""
    AI = "AI"
    QUEUED = "QUEUED"
    HUMAN = "HUMAN"
    CLOSED = "CLOSED"


class MessageRole(StrEnum):
    """消息角色"""
    USER = "USER"
    AI = "AI"
    HUMAN = "HUMAN"


class TurnStatus(StrEnum):
    """轮次状态 """
    COLLECTION = "COLLECTION"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    SUPERSEDE = "SUPERSEDE"
    FAILED = "FAILED"


class HandoffStatus(StrEnum):
    """工单状态"""
    WAITING = "WAITING"
    ACTIVE = "ACTIVE"
    RESOLVED = "RESOLVED"
