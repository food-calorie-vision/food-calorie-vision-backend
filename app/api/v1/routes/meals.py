"""식단 관련 라우트"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.api.v1.schemas.common import ApiResponse
from app.api.v1.schemas.meals import (
    MealNutrients,
    MealRecommendation,
    MealRecommendationsResponse,
    MealSelectionData,
    MealSelectionRequest,
    SelectedMealInfo,
)
from app.services import recommendation_service
from app.utils.session import get_current_user_id

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
async def get_meal_recommendations(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[MealRecommendationsResponse]:
    """식단 추천 조회"""
    user_id = get_current_user_id(request)
    
    # 로그인하지 않은 경우 목 데이터 반환
    if not user_id:
        return ApiResponse(
            success=True,
            data=MealRecommendationsResponse(
                recommendations=MOCK_MEALS,
                timestamp=datetime.now(timezone.utc).isoformat(),
            ),
        )
    
    # DB에서 사용자의 식단 추천 조회
    recommendations = await recommendation_service.get_user_recommendations(
        session=session,
        user_id=user_id,
        limit=10,
    )
    
    # DB에 추천이 없으면 목 데이터 + DB 저장
    if not recommendations:
        for mock_meal in MOCK_MEALS:
            await recommendation_service.create_recommendation(
                session=session,
                user_id=user_id,
                meal_name=mock_meal.name,
                calories=mock_meal.calories,
                protein=mock_meal.nutrients.protein,
                carbs=mock_meal.nutrients.carbs,
                fat=mock_meal.nutrients.fat,
                sodium=mock_meal.nutrients.sodium,
                description=mock_meal.description,
            )
        # 다시 조회
        recommendations = await recommendation_service.get_user_recommendations(
            session=session,
            user_id=user_id,
            limit=10,
        )
    
    # 모델 변환
    meal_list = [
        MealRecommendation(
            id=rec.recommendation_id,
            name=rec.meal_name,
            calories=int(rec.calories),
            description=rec.description or "",
            isSelected=rec.is_selected,
            nutrients=MealNutrients(
                protein=int(rec.protein),
                carbs=int(rec.carbs),
                fat=int(rec.fat),
                sodium=int(rec.sodium) if rec.sodium else 0,
            ),
        )
        for rec in recommendations
    ]
    
    return ApiResponse(
        success=True,
        data=MealRecommendationsResponse(
            recommendations=meal_list,
            timestamp=datetime.now(timezone.utc).isoformat(),
        ),
    )


@router.post("/selection", response_model=ApiResponse[MealSelectionData])
async def select_meal(
    meal_request: MealSelectionRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[MealSelectionData]:
    """식단 선택"""
    user_id = get_current_user_id(request)
    
    if not user_id:
        return ApiResponse(
            success=False,
            error="로그인이 필요합니다.",
        )
    
    # DB에서 식단 선택
    recommendation = await recommendation_service.select_recommendation(
        session=session,
        recommendation_id=meal_request.meal_id,
        user_id=user_id,
    )
    
    if not recommendation:
        return ApiResponse(
            success=False,
            error=f"식단 ID {meal_request.meal_id}을(를) 찾을 수 없습니다.",
        )
    
    return ApiResponse(
        success=True,
        data=MealSelectionData(
            success=True,
            message=f"식단 '{recommendation.meal_name}'이(가) 성공적으로 선택되었습니다.",
            selectedMeal=SelectedMealInfo(
                id=recommendation.recommendation_id,
                name=recommendation.meal_name,
                calories=int(recommendation.calories),
            ),
        ),
    )

