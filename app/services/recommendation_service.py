"""식단 추천 관련 서비스"""
from typing import List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.db.models import MealRecommendation


async def create_recommendation(
    session: AsyncSession,
    user_id: str,
    meal_name: str,
    calories: float,
    protein: float,
    carbs: float,
    fat: float,
    sodium: Optional[float] = None,
    description: Optional[str] = None,
) -> MealRecommendation:
    """식단 추천 생성"""
    recommendation = MealRecommendation(
        user_id=user_id,
        meal_name=meal_name,
        calories=calories,
        protein=protein,
        carbs=carbs,
        fat=fat,
        sodium=sodium,
        description=description,
        is_selected=False,
        recommended_date=datetime.now(),
    )
    
    session.add(recommendation)
    await session.commit()
    await session.refresh(recommendation)
    
    return recommendation


async def get_user_recommendations(
    session: AsyncSession,
    user_id: str,
    skip: int = 0,
    limit: int = 10,
) -> List[MealRecommendation]:
    """사용자의 식단 추천 조회"""
    result = await session.execute(
        select(MealRecommendation)
        .where(MealRecommendation.user_id == user_id)
        .order_by(MealRecommendation.recommended_date.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def select_recommendation(
    session: AsyncSession,
    recommendation_id: int,
    user_id: str,
) -> Optional[MealRecommendation]:
    """식단 추천 선택"""
    result = await session.execute(
        select(MealRecommendation).where(
            and_(
                MealRecommendation.recommendation_id == recommendation_id,
                MealRecommendation.user_id == user_id,
            )
        )
    )
    recommendation = result.scalar_one_or_none()
    
    if not recommendation:
        return None
    
    recommendation.is_selected = True
    recommendation.selected_date = datetime.now()
    
    await session.commit()
    await session.refresh(recommendation)
    
    return recommendation

