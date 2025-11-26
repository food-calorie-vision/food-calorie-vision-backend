"""사용자 관련 라우트"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.dependencies import get_current_active_user
from app.api.v1.schemas.users import NutrientInfo, UserHealthInfo, UserIntakeData
from app.db.models import DiseaseAllergyProfile, User
from app.db.session import get_session

router = APIRouter()


@router.get("/me/status", response_model=UserIntakeData)
async def get_user_intake_data(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
) -> UserIntakeData:
    """오늘의 사용자 섭취 현황 조회"""
    today = datetime.now().date()
    user_id = current_user.user_id

    # 1. 목표 칼로리 계산
    bmr, tdee, target_calories = 0, 0, 2000 # 기본값
    if current_user.weight and current_user.age and current_user.gender:
        if current_user.gender == 'M':
            bmr = 10 * float(current_user.weight) + 6.25 * current_user.age - 5 * current_user.age + 5
        else:
            bmr = 10 * float(current_user.weight) + 6.25 * current_user.age - 5 * current_user.age - 161
        
        tdee = bmr * 1.55
        
        if current_user.health_goal == 'loss':
            target_calories = int(tdee * 0.85)
        elif current_user.health_goal == 'gain':
            target_calories = int(tdee * 1.15)
        else:
            target_calories = int(tdee)
    
    # 2. 오늘 섭취한 칼로리 합계
    total_calories_stmt = select(func.sum(HealthScore.kcal)).where(
        and_(
            HealthScore.user_id == user_id,
            func.date(HealthScore.created_at) == today,
        )
    )
    total_calories_result = await session.execute(total_calories_stmt)
    total_calories = total_calories_result.scalar_one_or_none() or 0

    # 3. 주요 영양소 섭취량 (TODO)
    # TODO: meals.py의 /daily-summary 로직과 통합하거나 재사용하여 실제 영양소 값 조회
    
    return UserIntakeData(
        totalCalories=int(total_calories),
        targetCalories=target_calories,
        nutrients=NutrientInfo(
            sodium=0, carbs=0, protein=0, fat=0, sugar=0,
        ),
    )


@router.get("/me/health-info", response_model=UserHealthInfo)
async def get_user_health_info(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
) -> UserHealthInfo:
    """사용자 건강 정보 조회"""
    # 사용자의 질병 및 알레르기 정보 조회
    profile_stmt = select(DiseaseAllergyProfile).where(
        DiseaseAllergyProfile.user_id == current_user.user_id
    )
    profile_result = await session.execute(profile_stmt)
    profiles = profile_result.scalars().all()

    diseases = [p.disease_name for p in profiles if p.disease_name]
    allergies = [p.allergy_name for p in profiles if p.allergy_name]

    # 간단한 BMR 계산 (Mifflin-St Jeor)
    bmr, tdee, target_calories = 0, 0, 2000 # 기본값
    if current_user.weight and current_user.age and current_user.gender:
        if current_user.gender == 'M':
            bmr = 10 * float(current_user.weight) + 6.25 * current_user.age - 5 * current_user.age + 5
        else:
            bmr = 10 * float(current_user.weight) + 6.25 * current_user.age - 5 * current_user.age - 161
        
        tdee = bmr * 1.55  # 중간 활동 기준
        
        if current_user.health_goal == 'loss':
            target_calories = int(tdee * 0.85)
        elif current_user.health_goal == 'gain':
            target_calories = int(tdee * 1.15)
        else:
            target_calories = int(tdee)

    return UserHealthInfo(
        goal=current_user.health_goal or "정보 없음",
        diseases=diseases,
        recommendedCalories=target_calories,
        activityLevel="중간",  # 현재는 하드코딩
        bodyType=current_user.health_goal or "정보 없음", # goal과 동일하게 매핑
        allergies=allergies,
        medicalConditions=[], # 현재 스키마에 없음
    )

