"""챗봇 대화 관련 서비스"""
from typing import List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.db.models import ChatMessage


async def create_chat_message(
    session: AsyncSession,
    user_id: str,
    role: str,
    content: str,
) -> ChatMessage:
    """챗봇 대화 메시지 생성"""
    message = ChatMessage(
        user_id=user_id,
        role=role,
        content=content,
        timestamp=datetime.now(),
    )
    
    session.add(message)
    await session.commit()
    await session.refresh(message)
    
    return message


async def get_user_chat_history(
    session: AsyncSession,
    user_id: str,
    skip: int = 0,
    limit: int = 50,
) -> List[ChatMessage]:
    """사용자의 챗봇 대화 기록 조회"""
    result = await session.execute(
        select(ChatMessage)
        .where(ChatMessage.user_id == user_id)
        .order_by(ChatMessage.timestamp.asc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_recent_chat_context(
    session: AsyncSession,
    user_id: str,
    message_count: int = 10,
) -> List[ChatMessage]:
    """최근 대화 컨텍스트 조회 (대화 연속성을 위해)"""
    result = await session.execute(
        select(ChatMessage)
        .where(ChatMessage.user_id == user_id)
        .order_by(ChatMessage.timestamp.desc())
        .limit(message_count)
    )
    messages = list(result.scalars().all())
    return list(reversed(messages))  # 시간순으로 정렬


async def delete_user_chat_history(
    session: AsyncSession,
    user_id: str,
) -> int:
    """사용자의 챗봇 대화 기록 삭제"""
    result = await session.execute(
        select(ChatMessage).where(ChatMessage.user_id == user_id)
    )
    messages = result.scalars().all()
    
    count = 0
    for message in messages:
        await session.delete(message)
        count += 1
    
    await session.commit()
    
    return count

