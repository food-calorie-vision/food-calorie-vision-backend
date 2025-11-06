"""건강 정보 관련 서비스"""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models import UserHealthInfo


async def get_user_health_info(
    session: AsyncSession,
    user_id: str
) -> Optional[UserHealthInfo]:
    """사용자 건강 정보 조회"""
    result = await session.execute(
        select(UserHealthInfo).where(UserHealthInfo.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def update_user_health_info(
    session: AsyncSession,
    user_id: str,
    health_goal: Optional[str] = None,
    body_type: Optional[str] = None,
    has_allergy: Optional[str] = None,
    allergy_info: Optional[str] = None,
    medical_condition: Optional[str] = None,
) -> Optional[UserHealthInfo]:
    """사용자 건강 정보 수정"""
    health_info = await get_user_health_info(session, user_id)
    
    if not health_info:
        return None
    
    # 필드 업데이트 (None이 아닌 값만)
    if health_goal is not None:
        health_info.health_goal = health_goal
    if body_type is not None:
        health_info.body_type = body_type
    if has_allergy is not None:
        health_info.has_allergy = has_allergy
    if allergy_info is not None:
        health_info.allergy_info = allergy_info
    if medical_condition is not None:
        health_info.medical_condition = medical_condition
    
    await session.commit()
    await session.refresh(health_info)
    
    return health_info

