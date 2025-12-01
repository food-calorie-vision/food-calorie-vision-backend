"""Simple in-process cache for user health/chat context.

Redis 없이도 사용자별 기본 정보를 빠르게 재사용하기 위한 용도다.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, date, timedelta
from typing import Dict, List
import logging

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DiseaseAllergyProfile, UserFoodHistory

_CACHE: Dict[int, "CachedUserContext"] = {}
_TTL = timedelta(minutes=15)


@dataclass
class CachedUserContext:
    user_id: int
    diseases: List[str]
    allergies: List[str]
    has_eaten_today: bool
    last_refreshed: datetime


async def _fetch_user_context(session: AsyncSession, user_id: int) -> CachedUserContext:
    """DB에서 사용자 맥락 정보를 새로 조회."""
    profile_stmt = select(DiseaseAllergyProfile).where(DiseaseAllergyProfile.user_id == user_id)
    profile_results = await session.execute(profile_stmt)
    profiles = profile_results.scalars().all()

    diseases = list({p.disease_name for p in profiles if p.disease_name})
    allergies = list({p.allergy_name for p in profiles if p.allergy_name})

    today_start = datetime.combine(date.today(), datetime.min.time())
    meal_stmt = select(func.count(UserFoodHistory.history_id)).where(
        UserFoodHistory.user_id == user_id,
        UserFoodHistory.consumed_at >= today_start,
    )
    meal_result = await session.execute(meal_stmt)
    has_eaten_today = meal_result.scalar_one_or_none() > 0

    return CachedUserContext(
        user_id=user_id,
        diseases=diseases,
        allergies=allergies,
        has_eaten_today=has_eaten_today,
        last_refreshed=datetime.utcnow(),
    )


async def get_or_build_user_context(session: AsyncSession, user_id: int) -> CachedUserContext:
    """캐시된 사용자 정보를 반환하거나 필요 시 새로 조회."""
    cached = _CACHE.get(user_id)
    now = datetime.utcnow()
    if cached and now - cached.last_refreshed < _TTL:
        logging.info("==캐시된 사용자 컨텍스트 재사용==\nuser_id=%s 질병=%s 알레르기=%s", user_id, cached.diseases, cached.allergies)
        return cached

    logging.info("==DB에서 사용자 컨텍스트 새로 조회==\nuser_id=%s", user_id)
    refreshed = await _fetch_user_context(session, user_id)
    _CACHE[user_id] = refreshed
    return refreshed


async def refresh_user_context(session: AsyncSession, user_id: int) -> CachedUserContext:
    """명시적으로 캐시를 갱신."""
    refreshed = await _fetch_user_context(session, user_id)
    _CACHE[user_id] = refreshed
    return refreshed


def invalidate_user_context(user_id: int) -> None:
    """로그아웃 등에서 캐시를 제거."""
    _CACHE.pop(user_id, None)
