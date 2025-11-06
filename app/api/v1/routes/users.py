"""사용자 관련 라우트"""

from fastapi import APIRouter

from app.api.v1.schemas.users import NutrientInfo, UserHealthInfo, UserIntakeData

router = APIRouter()


@router.get("/intake-data", response_model=UserIntakeData)
async def get_user_intake_data() -> UserIntakeData:
    """사용자 섭취 현황 조회 (메모리 기반 스텁)"""
    # TODO: DB에서 실제 사용자 섭취 현황을 조회
    return UserIntakeData(
        totalCalories=1850,
        targetCalories=2000,
        nutrients=NutrientInfo(
            sodium=1200,
            carbs=180,
            protein=85,
            fat=45,
            sugar=30,
        ),
    )


@router.get("/health-info", response_model=UserHealthInfo)
async def get_user_health_info() -> UserHealthInfo:
    """사용자 건강 정보 조회 (메모리 기반 스텁)"""
    # TODO: DB에서 실제 사용자 건강 정보를 조회
    return UserHealthInfo(
        goal="체중 감량",
        diseases=["고혈압", "고지혈증"],
        recommendedCalories=2000,
        activityLevel="중간",
        bodyType="감량",
        allergies=[],
        medicalConditions=[],
    )

