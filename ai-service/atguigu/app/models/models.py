from datetime import datetime
from typing import Any

from sqlalchemy import String, JSON, Integer, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped
from sqlalchemy.testing.schema import mapped_column

from atguigu.app.models.enums import AgentTraceStatus
from atguigu.common.utils import get_uid, get_utcnow


class Base(DeclarativeBase):
    pass


class AgentTrace(Base):
    __tablename__ = "agent_traces"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=lambda: get_uid("trace"))
    conversation_id: Mapped[str] = mapped_column(String(80), index=True)
    status: Mapped[str] = mapped_column(String(20), default=AgentTraceStatus.RUNNING, index=True)
    model_name: Mapped[str] = mapped_column(String(120))
    prompt_version: Mapped[str] = mapped_column(String(20))
    result: Mapped[dict[str:Any] | None] = mapped_column(JSON, nullable=True)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utcnow())


class AgentToolCall(Base):
    """记录一次 Agent 业务工具调用及其执行结果"""

    __tablename__ = "agent_tool_calls"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=lambda: get_uid("tool"))
    trace_id: Mapped[str] = mapped_column(ForeignKey("agent_traces.id"), index=True)
    tool_call_id: Mapped[str] = mapped_column(String(120))
    tool_name: Mapped[str] = mapped_column(String(80), index=True)
    arguments: Mapped[dict[str, Any]] = mapped_column(JSONB)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    success: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utcnow)


class KnowledgeChunk(Base):
    """存储上传的 PDF 知识文档内容"""

    __tablename__ = "knowledge_chunks"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=lambda: get_uid("kb"))
    file_name: Mapped[str] = mapped_column(String(200), index=True)
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utcnow)
