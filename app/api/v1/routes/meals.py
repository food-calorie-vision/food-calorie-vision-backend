"""식단 관련 라우트"""

from datetime import datetime, timezone

from fastapi import APIRouter

from app.api.v1.schemas.common import ApiResponse
from app.api.v1.schemas.meals import (
    MealNutrients,
    MealRecommendation,
    MealRecommendationsResponse,
    MealSelectionData,
    MealSelectionRequest,
    SelectedMealInfo,
)

router = APIRouter()

# 메모리 기반 목 데이터
MOCK_MEALS = [
    MealRecommendation(
        id=1,
        name="연어 덮밥",
        calories=450,
        description="사용자 건강 목표에 따른 추천 메뉴",
        isSelected=True,
        nutrients=MealNutrients(protein=35, carbs=45, fat=12, sodium=800),
    ),
    MealRecommendation(
        id=2,
        name="제육볶음",
        calories=380,
        description="사용자 건강 목표에 따른 추천 메뉴",
        isSelected=False,
        nutrients=MealNutrients(protein=28, carbs=35, fat=15, sodium=1200),
    ),
    MealRecommendation(
        id=3,
        name="고등어 구이 정식",
        calories=420,
        description="사용자 건강 목표에 따른 추천 메뉴",
        isSelected=False,
        nutrients=MealNutrients(protein=32, carbs=40, fat=18, sodium=900),
    ),
]


@router.get("/recommendations", response_model=ApiResponse[MealRecommendationsResponse])
async def get_meal_recommendations() -> ApiResponse[MealRecommendationsResponse]:
    """식단 추천 조회 (메모리 기반 스텁)"""
    # TODO: 사용자 건강 정보와 선호도 기반으로 식단 추천
    return ApiResponse(
        success=True,
        data=MealRecommendationsResponse(
            recommendations=MOCK_MEALS,
            timestamp=datetime.now(timezone.utc).isoformat(),
        ),
    )


@router.post("/selection", response_model=ApiResponse[MealSelectionData])
async def select_meal(request: MealSelectionRequest) -> ApiResponse[MealSelectionData]:
    """식단 선택 (메모리 기반 스텁)"""
    # TODO: DB에 사용자 식단 선택 저장
    # 선택된 식단 찾기
    selected_meal = next((meal for meal in MOCK_MEALS if meal.id == request.meal_id), None)

    if not selected_meal:
        return ApiResponse(
            success=False,
            error=f"식단 ID {request.meal_id}을(를) 찾을 수 없습니다.",
        )

    return ApiResponse(
        success=True,
        data=MealSelectionData(
            success=True,
            message=f"식단 {request.meal_id}이(가) 성공적으로 선택되었습니다.",
            selectedMeal=SelectedMealInfo(
                id=selected_meal.id,
                name=selected_meal.name,
                calories=selected_meal.calories,
            ),
        ),
    )

