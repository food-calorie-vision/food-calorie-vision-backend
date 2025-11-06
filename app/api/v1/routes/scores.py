"""점수 관련 API"""
from typing import Optional
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.services import score_service
from app.utils.session import get_current_user_id

router = APIRouter()


@router.get("/today")
async def get_today_score(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    오늘의 점수 조회
    
    실시간으로 점수를 계산하여 반환합니다.
    """
    user_id = get_current_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")
    
    today = date.today()
    
    # 오늘의 점수 계산
    score_data = await score_service.calculate_daily_score(
        session=session,
        user_id=user_id,
        target_date=today,
    )
    
    # DB에 저장
    await score_service.save_daily_score(
        session=session,
        user_id=user_id,
        target_date=today,
        score_data=score_data,
    )
    
    # 어제 점수 조회 (점수 변화 계산용)
    yesterday = date.today().replace(day=date.today().day - 1) if date.today().day > 1 else None
    previous_score = 0
    
    if yesterday:
        yesterday_score_data = await score_service.get_daily_score(
            session=session,
            user_id=user_id,
            target_date=yesterday,
        )
        if yesterday_score_data:
            previous_score = yesterday_score_data.total_score
    
    score_change = score_data["total_score"] - previous_score
    
    return {
        "todayScore": score_data["total_score"],
        "previousScore": previous_score,
        "scoreChange": score_change,
        "feedback": score_data["feedback"],
        "improvement": score_data["improvement"],
        "details": {
            "calorie_score": score_data["calorie_score"],
            "balance_score": score_data["balance_score"],
            "frequency_score": score_data["frequency_score"],
            "consistency_score": score_data["consistency_score"],
        },
        "meal_summary": {
            "meal_count": score_data["meal_count"],
            "total_calories": score_data["total_calories"],
            "target_calories": score_data["target_calories"],
        },
    }

