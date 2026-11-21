from datetime import timedelta
from typing import Any

from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from atguigu.app.models.enums import ConversationMode, MessageRole, TurnStatus
from atguigu.app.models.models import Message, Conversations, ConversationTurn
from atguigu.app.schemas import ChatMessageRequest
from atguigu.app.services.realtime import RealtimeService
from atguigu.common.settings import get_settings
from atguigu.common.utils import get_utcnow, get_uid


class ChatService:
    def __init__(self, session: AsyncSession):
        self._realtime_services = RealtimeService(session)
        self._session = session
        self._get_setting = get_settings()

    async def get_chat_history(self, user_id: str) -> dict[str:Any]:
        # 已经拿到用户id了 用用户id去message表中查询该用户的所有信息  最外层要用当前会话的会话id和会话模式包裹
        # 关联message表和conversation表拿到该用户的所有信息
        stmt = select(Message).join(Conversations, Message.conversation_id == Conversations.id).where(
            Conversations.user_id == user_id)
        records = (await self._session.scalars(stmt)).all()
        # 构造消息格式
        conversation_messages = [
            {
                "conversation_id": record.conversation_id,
                "role": record.role,
                "content": record.content
            }
            for record in records
        ]
        # 获取当前用户会话
        conversation = await self._create_or_get_conversation(user_id)
        # 提交
        await self._session.commit()
        # 返回
        return {
            "conversation_id": conversation.id,
            "conversation_mode": conversation.mode,
            "messages": conversation_messages
        }

    async def process_chat_message(self,
                                   user_id: str,
                                   payload: ChatMessageRequest
                                   ):
        # 现在从路由传过来了用户id和payload(message_id,type,content)
        # 1.message_id去重
        stmt = select(Message).where(Message.message_id == payload.message_id)
        message = await self._session.scalar(stmt)
        if message:
            return
        # 获取有效会话id 若无有效则创建新的
        conversation = await self._create_or_get_conversation(user_id)

        # 创建新消息对象 并 将信息保存到messages表中 修改会话的激活时间
        message = Message(
            message_id=payload.message_id,
            conversation_id=conversation.id,
            role=MessageRole.USER,
            message_type=payload.type,
            content=payload.content
        )
        self._session.add(message)
        conversation.last_activity_at = get_utcnow()

        # 消息根据会话模式分流 if 若会话模式是AI则 获取turn 否则往realtime_event中存消息
        if conversation.mode == ConversationMode.AI:
            await self._create_or_get_turn(conversation.id)
        else:
            self._realtime_services.add_event(message, conversation, notify_staff=True)
        # 统一提交 同生共死
        await self._session.commit()

    async def _create_or_get_conversation(self, user_id: str):
        # 查询该用户下是否是活跃会话 无活跃会话则创建 有活跃会话还需判断当mode是AI时 有没有过期 若过期则将mode设置为close且创建新的
        stmt = select(Conversations).where(Conversations.user_id == user_id,
                                           Conversations.mode != ConversationMode.CLOSED)
        conversation = await self._session.scalar(stmt)
        if conversation:
            # 如果存在活跃的会话 且会话模式是AI 判断是否过期，QUEUED和HUMAN没有过期时间说法
            timeout = timedelta(minutes=self._get_setting.conversation_idle_timeout_minutes)
            if conversation.mode == ConversationMode.AI and get_utcnow() - conversation.last_activity_at >= timeout:
                # 修改过期的会话状态为过期
                conversation.mode = ConversationMode.CLOSED
            else:
                return conversation
        # 创建新的会话
        conversation = Conversations(
            id=get_uid("conv"),
            user_id=user_id,
            mode=ConversationMode.AI
        )
        # 保存会话
        self._session.add(conversation)
        # 返回
        return conversation

    async def _create_or_get_turn(self, conversation_id):
        # 查询消息轮次表中 是否有处于COLLECTION的轮次 若无则创建 有则复用 返回
        stmt = select(ConversationTurn).where(ConversationTurn.conversation_id == conversation_id,
                                              ConversationTurn.status == TurnStatus.COLLECTION)
        turn = await self._session.scalar(stmt)
        if turn is None:
            turn = ConversationTurn(
                conversation_id=conversation_id,
                status=TurnStatus.COLLECTION,
                collect_until=get_utcnow() + timedelta(milliseconds=self._get_setting.message_merge_delay_ms)
            )
        self._session.add(turn)
        return turn

    async def claim_turn_and_build_payload(self):
        # 获取一个活跃中的turn
        stmt = (select(ConversationTurn).where(ConversationTurn.status == TurnStatus.COLLECTION,
                                               ConversationTurn.collect_until <= get_utcnow())
                .order_by(ConversationTurn.collect_until))
        claimed_turn = await self._session.scalar(stmt)
        # print(get_utcnow())
        # 没有turn则返回空
        if not claimed_turn:
            return None

        # 拿到一个会话 并加锁
        stmt = select(Conversations).where(Conversations.id == claimed_turn.conversation_id).with_for_update()
        conversation = await self._session.scalar(stmt)

        # 修改turn表中的状态和尝试次数
        claimed_turn.status = TurnStatus.RUNNING
        claimed_turn.attempts += 1

        # 获取该会话中最新一条message_id 下限
        latest_user_message_id = await self._get_latest_message_id(str(conversation.id))
        # 修改turn表的snapshot_message_id
        claimed_turn.snapshot_message_id = latest_user_message_id

        # 构建请求载荷
        payload: dict[str, Any] = await self._build_request_payload(claimed_turn, conversation)

        # 提交
        await self._session.commit()

        # 返回
        return claimed_turn, payload, str(conversation.user_id)

    async def finish_turn(self, claim_turn: ConversationTurn, ai_result, error):

        # 查询当前轮次对应的会话
        stmt = select(Conversations).where(Conversations.id == claim_turn.conversation_id).with_for_update()
        conversation = await self._session.scalar(stmt)

        # 判断调AI接口是否成功
        if error:
            # 失败还有重试次数
            if claim_turn.attempts <= self._get_setting.ai_worker_max_attempts:
                claim_turn.status = TurnStatus.COLLECTION  # TODO 了状态还要改 until时间
                claim_turn.collect_until = get_utcnow() + timedelta(
                    seconds=self._get_setting.ai_worker_retry_delay_seconds)
            else:
                # 无重试次数
                claim_turn.status = TurnStatus.FAILED
                # 往message realtime插入ai调用失败信息

                conversation.mode = ConversationMode.QUEUED
                self._realtime_services.add_handoff(conversation,
                                                    summary="AI 服务多次调用异常，系统自动降级转接人工客服")
                self._save_ai_reply({"text": "当前智能助手正忙，已自动为您转接人工客服处理，请稍候。"}, conversation)

            await self._session.commit()
            return
        # 判断是否插话
        if claim_turn.snapshot_message_id != await self._get_latest_message_id(claim_turn.conversation_id):
            # 插话
            claim_turn.status = TurnStatus.SUPERSEDE
            await self._session.commit()
            return
        # 判断是否转人工
        claim_turn.status = TurnStatus.COMPLETED

        # 转人工
        if ai_result['reply_type'] == "REQUEST_HANDOFF":
            self._realtime_services.add_handoff(conversation, ai_result["summary"])
            conversation.mode = ConversationMode.QUEUED  # TODO没有改会话模式为QUEUED

        self._save_ai_reply(ai_result, conversation)
        await self._session.commit()

    def _save_ai_reply(self, ai_result: dict[str:Any], conversation: Conversations):
        # 还要设置一个键来判断要插入realtime表的哪个target
        # 插入message表
        message = Message(
            message_id=get_uid("msg"),
            conversation_id=conversation.id,
            role=MessageRole.AI,
            message_type="text",
            content=ai_result
        )
        self._session.add(message)

        # 修改会话最后一个活跃时间
        conversation.last_activity_at = get_utcnow()  # TODO 别忘记

        # 插入realtime表
        self._realtime_services.add_event(message, conversation,
                                          notify_user=True,
                                          notify_staff=conversation.mode == ConversationMode.QUEUED)

    async def _get_latest_message_id(self, conversation_id):
        stmt = select(func.max(Message.id)).where(Message.conversation_id == conversation_id,
                                                  Message.role == MessageRole.USER)
        return await self._session.scalar(stmt)

    async def _build_request_payload(self, claimed_turn, conversation):
        # 需要拿去的轮次消息上限 拿该轮会话中非user角色的最后一条消息
        stmt = select(func.max(Message.id)).where(Message.conversation_id == conversation.id,
                                                  Message.role != MessageRole.USER)
        lasted_reply_message_id = await self._session.scalar(stmt) or 0  # 做一个兜底
        # 查询范围
        current_turn_messages_stmt = select(Message).where(Message.id > lasted_reply_message_id,
                                                           Message.id <= claimed_turn.snapshot_message_id,
                                                           Message.conversation_id == conversation.id).order_by(
            Message.id)
        current_turn_messages = (await self._session.scalars(current_turn_messages_stmt)).all()

        # 要返回payload message history conversation_id 现在需要构造history
        stmt = select(Message).where(Message.conversation_id == conversation.id,
                                     Message.id < current_turn_messages[0].id).order_by(Message.id.desc()).limit(30)
        histories = reversed((await self._session.scalars(stmt)).all())
        return {
            "conversation_id": conversation.id,
            "messages": [
                {
                    "role": message.role,
                    "content": message.content,
                    "type": message.message_type
                }
                for message in current_turn_messages
            ],
            "history": [
                {
                    "role": history.role,
                    "content": history.content,
                    "type": history.message_type
                }
                for history in histories
            ]
        }
