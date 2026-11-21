from datetime import datetime
from typing import Any

from sqlalchemy import Index, text, String, DateTime, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from atguigu.app.models.enums import ConversationMode, TurnStatus, HandoffStatus
from atguigu.common.utils import get_uid, get_utcnow


class Base(DeclarativeBase):
    pass


class Conversations(Base):
    __tablename__ = "conversations"
    __table_args__ = (
        Index(
            "uq_open_conversation_per_user",
            "user_id",
            unique=True,
            postgresql_where=text("mode IN ('AI','HUMAN','QUEUED')")
        ),
    )

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=lambda: get_uid("conv"))
    user_id: Mapped[str] = mapped_column(String(40), index=True)
    mode: Mapped[str] = mapped_column(String(20), default=ConversationMode.AI, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utcnow)
    last_activity_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utcnow,
                                                       onupdate=get_utcnow())


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    message_id: Mapped[str] = mapped_column(String(80), unique=True)
    conversation_id: Mapped[str] = mapped_column(String(80), ForeignKey("conversations.id"), index=True)
    role: Mapped[str] = mapped_column(String(20))
    message_type: Mapped[str] = mapped_column(String(20), default="text")
    content: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utcnow)


class ConversationTurn(Base):
    __tablename__ = "conversation_turn"
    __table_args__ = (
        Index("uq_collecting_turn_per_conversation", "conversation_id", unique=True,
              postgresql_where=text("status ='COLLECTING'")),
        Index("uq_executing_turn_per_conversation", "conversation_id", unique=True,
              postgresql_where=text("status='RUNNING'"))
    )

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=lambda: get_uid("turn"))
    conversation_id: Mapped[str] = mapped_column(String(80), ForeignKey("conversations.id"), index=True)
    status: Mapped[str] = mapped_column(String(30), default=TurnStatus.COLLECTION, index=True)
    snapshot_message_id: Mapped[int | None] = mapped_column(Integer)
    collect_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utcnow)


class RealtimeEvent(Base):
    __tablename__ = "realtime_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSONB)
    target: Mapped[str] = mapped_column(String(80), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utcnow)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)


class Handoff(Base):
    __tablename__ = "handoffs"
    __table_args__ = (
        Index("uq_open_handoff_per_conversation", "conversation_id", unique=True,
              postgresql_where=text("status IN ('WAITING', 'ACTIVE')")),
    )

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=lambda: get_uid("handoff"))
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"), index=True)
    user_id: Mapped[str] = mapped_column(String(40), index=True)
    summary: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default=HandoffStatus.WAITING, index=True)
    staff_id: Mapped[str | None] = mapped_column(String(40), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utcnow)
