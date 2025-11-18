"""음식 섭취 기록 서비스 - UserFoodHistory 테이블"""
from datetime import datetime, date
from typing import List, Optional, Tuple

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import UserFoodHistory, Food


async def create_food_history(
    session: AsyncSession,
    user_id: int,
    food_id: str,
    food_name: str,
    consumed_at: Optional[datetime] = None,
    portion_size_g: Optional[float] = None,
) -> UserFoodHistory:
    """
    음식 섭취 기록 생성
    
    Args:
        session: DB 세션
        user_id: 사용자 ID (BIGINT)
        food_id: 음식 ID (VARCHAR(200))
        food_name: 음식 이름
        consumed_at: 섭취 시간 (기본값: 현재 시간)
        portion_size_g: 섭취량 (g)
    
    Returns:
        생성된 UserFoodHistory 객체
    """
    history = UserFoodHistory(
        user_id=user_id,
        food_id=food_id,
        food_name=food_name,
        consumed_at=consumed_at or datetime.now(),
        portion_size_g=portion_size_g,
    )
    
    session.add(history)
    await session.flush()
    
    return history


async def get_food_history_by_id(
    session: AsyncSession,
    history_id: int,
) -> Optional[UserFoodHistory]:
    """
    history_id로 음식 섭취 기록 조회
    
    Args:
        session: DB 세션
        history_id: 기록 ID
    
    Returns:
        UserFoodHistory 객체 또는 None
    """
    result = await session.execute(
        select(UserFoodHistory).where(UserFoodHistory.history_id == history_id)
    )
    return result.scalar_one_or_none()


async def get_user_food_history(
    session: AsyncSession,
    user_id: int,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 100,
    offset: int = 0,
) -> List[UserFoodHistory]:
    """
    사용자의 음식 섭취 기록 조회 (기간별)
    
    Args:
        session: DB 세션
        user_id: 사용자 ID
        start_date: 시작 날짜 (선택)
        end_date: 종료 날짜 (선택)
        limit: 최대 결과 개수
        offset: 결과 오프셋
    
    Returns:
        UserFoodHistory 리스트
    """
    query = select(UserFoodHistory).where(UserFoodHistory.user_id == user_id)
    
    # 날짜 필터링
    if start_date:
        query = query.where(UserFoodHistory.consumed_at >= start_date)
    if end_date:
        query = query.where(UserFoodHistory.consumed_at <= end_date)
    
    # 최신순 정렬
    query = query.order_by(UserFoodHistory.consumed_at.desc())
    
    # 페이지네이션
    query = query.limit(limit).offset(offset)
    
    result = await session.execute(query)
    return list(result.scalars().all())


async def get_daily_food_history(
    session: AsyncSession,
    user_id: int,
    date: datetime,
) -> List[UserFoodHistory]:
    """
    특정 날짜의 음식 섭취 기록 조회
    
    Args:
        session: DB 세션
        user_id: 사용자 ID
        date: 조회할 날짜
    
    Returns:
        해당 날짜의 UserFoodHistory 리스트
    """
    start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = date.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    return await get_user_food_history(
        session=session,
        user_id=user_id,
        start_date=start_of_day,
        end_date=end_of_day,
    )


async def update_food_history(
    session: AsyncSession,
    history_id: int,
    portion_size_g: Optional[float] = None,
    consumed_at: Optional[datetime] = None,
) -> Optional[UserFoodHistory]:
    """
    음식 섭취 기록 수정
    
    Args:
        session: DB 세션
        history_id: 기록 ID
        portion_size_g: 수정할 섭취량
        consumed_at: 수정할 섭취 시간
    
    Returns:
        수정된 UserFoodHistory 객체 또는 None
    """
    history = await get_food_history_by_id(session, history_id)
    if not history:
        return None
    
    if portion_size_g is not None:
        history.portion_size_g = portion_size_g
    if consumed_at is not None:
        history.consumed_at = consumed_at
    
    await session.flush()
    return history


async def delete_food_history(
    session: AsyncSession,
    history_id: int,
) -> bool:
    """
    음식 섭취 기록 삭제
    
    Args:
        session: DB 세션
        history_id: 기록 ID
    
    Returns:
        삭제 성공 여부
    """
    history = await get_food_history_by_id(session, history_id)
    if not history:
        return False
    
    await session.delete(history)
    await session.flush()
    return True


async def get_food_history_count(
    session: AsyncSession,
    user_id: int,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> int:
    """
    사용자의 음식 섭취 기록 개수 조회
    
    Args:
        session: DB 세션
        user_id: 사용자 ID
        start_date: 시작 날짜
        end_date: 종료 날짜
    
    Returns:
        기록 개수
    """
    query = select(func.count(UserFoodHistory.history_id)).where(
        UserFoodHistory.user_id == user_id
    )
    
    if start_date:
        query = query.where(UserFoodHistory.consumed_at >= start_date)
    if end_date:
        query = query.where(UserFoodHistory.consumed_at <= end_date)
    
    result = await session.execute(query)
    return result.scalar() or 0


async def get_user_food_history_with_details(
    session: AsyncSession,
    user_id: int,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 100,
    offset: int = 0,
) -> Tuple[List[dict], int]:
    """
    사용자의 음식 섭취 기록을 Food 정보와 함께 조회
    
    Args:
        session: DB 세션
        user_id: 사용자 ID
        start_date: 시작 날짜 (선택)
        end_date: 종료 날짜 (선택)
        limit: 최대 결과 개수
        offset: 결과 오프셋
    
    Returns:
        (기록 리스트, 전체 개수) 튜플
    """
    # 전체 개수 조회
    total = await get_food_history_count(session, user_id, start_date, end_date)
    
    # LEFT JOIN으로 Food 정보와 함께 조회
    query = (
        select(
            UserFoodHistory.history_id,
            UserFoodHistory.user_id,
            UserFoodHistory.food_id,
            UserFoodHistory.food_name,
            UserFoodHistory.consumed_at,
            UserFoodHistory.portion_size_g,
            Food.food_class_1,
            Food.food_class_2,
            Food.category,
            Food.image_ref,
        )
        .outerjoin(Food, UserFoodHistory.food_id == Food.food_id)
        .where(UserFoodHistory.user_id == user_id)
    )
    
    # 날짜 필터링
    if start_date:
        query = query.where(UserFoodHistory.consumed_at >= start_date)
    if end_date:
        query = query.where(UserFoodHistory.consumed_at <= end_date)
    
    # 최신순 정렬
    query = query.order_by(UserFoodHistory.consumed_at.desc())
    
    # 페이지네이션
    query = query.limit(limit).offset(offset)
    
    result = await session.execute(query)
    rows = result.all()
    
    # 딕셔너리 리스트로 변환
    histories = []
    for row in rows:
        histories.append({
            "history_id": row.history_id,
            "user_id": row.user_id,
            "food_id": row.food_id,
            "food_name": row.food_name,
            "consumed_at": row.consumed_at,
            "portion_size_g": row.portion_size_g,
            "food_class_1": row.food_class_1,
            "food_class_2": row.food_class_2,
            "category": row.category,
            "image_ref": row.image_ref,
        })
    
    return histories, total

