from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from atguigu.app.models.enums import HandoffStatus
from atguigu.app.models.models import Message, Conversations, RealtimeEvent, Handoff
from atguigu.common.utils import get_uid, get_utcnow


class RealtimeService:
    def __init__(self, session: AsyncSession):
        self._session = session

    def add_event(self,
                  message: Message,
                  conversation: Conversations,
                  *,
                  notify_user: bool = False,
                  notify_staff: bool = False):

        # 确定目标通道
        target_channels = []
        if notify_user:
            target_channels.append(conversation.user_id)
        if notify_staff:
            target_channels.append("staff")

        # 构建时间通道的数据结构
        event_data = {
            "role": message.role,
            "content": message.content,
            "conversation_mode": conversation.mode
        }
        # 遍历通道保存消息
        for target in target_channels:
            self._session.add(RealtimeEvent(target=target, data=event_data))

    def add_handoff(self, conversation, summary):
        handoff = Handoff(
            id=get_uid("handoff"),
            conversation_id=conversation.id,
            user_id=conversation.user_id,
            summary=summary,
            status=HandoffStatus.WAITING
        )
        self._session.add(handoff)

    async def get_unpublish_event(self) -> RealtimeEvent:
        stmt = select(RealtimeEvent).where(RealtimeEvent.published_at.is_(None)).order_by(
            RealtimeEvent.created_at).limit(1)
        return await self._session.scalar(stmt)


    async def mark_published_event(self,event:RealtimeEvent):
        event.published_at=get_utcnow()
        await self._session.commit()