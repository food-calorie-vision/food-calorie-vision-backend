"""음식 이미지 분석 관련 라우트"""

import time
from datetime import datetime, timezone

from fastapi import APIRouter

from app.api.v1.schemas.common import ApiResponse
from app.api.v1.schemas.vision import (
    FoodAnalysisData,
    FoodAnalysisRequest,
    FoodAnalysisResult,
    FoodNutrients,
)

router = APIRouter()


def _analyze_food_image(file_name: str) -> FoodAnalysisResult:
    """음식 이미지 분석 (목 구현)"""
    # TODO: 실제 AI 비전 모델로 대체
    lower_name = file_name.lower()

    # 간단한 규칙 기반 분석
    if "pizza" in lower_name or "피자" in lower_name:
        return FoodAnalysisResult(
            foodName="피자",
            calories=800,
            nutrients=FoodNutrients(protein=30, carbs=80, fat=40, sodium=1500),
            confidence=0.87,
            suggestions=["피자는 칼로리가 높으니 적당히 섭취하세요.", "채소를 추가하여 영양 균형을 맞추세요."],
        )
    elif "salad" in lower_name or "샐러드" in lower_name:
        return FoodAnalysisResult(
            foodName="샐러드",
            calories=250,
            nutrients=FoodNutrients(protein=15, carbs=20, fat=10, sodium=300),
            confidence=0.92,
            suggestions=["신선한 채소와 단백질이 풍부한 샐러드입니다.", "드레싱 양을 조절하여 칼로리를 낮출 수 있습니다."],
        )
    elif "burger" in lower_name or "햄버거" in lower_name:
        return FoodAnalysisResult(
            foodName="햄버거",
            calories=600,
            nutrients=FoodNutrients(protein=25, carbs=50, fat=35, sodium=1000),
            confidence=0.89,
            suggestions=["햄버거는 지방 함량이 높을 수 있습니다.", "탄산음료 대신 물을 마시는 것이 좋습니다."],
        )
    elif "rice" in lower_name or "밥" in lower_name:
        return FoodAnalysisResult(
            foodName="밥",
            calories=300,
            nutrients=FoodNutrients(protein=5, carbs=60, fat=1, sodium=5),
            confidence=0.95,
            suggestions=["탄수화물 섭취의 좋은 원천입니다.", "다양한 반찬과 함께 균형 잡힌 식사를 하세요."],
        )
    elif "chicken" in lower_name or "치킨" in lower_name:
        return FoodAnalysisResult(
            foodName="치킨",
            calories=700,
            nutrients=FoodNutrients(protein=40, carbs=30, fat=50, sodium=1200),
            confidence=0.88,
            suggestions=[
                "단백질이 풍부하지만 튀긴 치킨은 지방 함량이 높습니다.",
                "구운 치킨이나 닭가슴살을 선택하는 것이 좋습니다.",
            ],
        )
    elif "kimchi" in lower_name or "김치" in lower_name:
        return FoodAnalysisResult(
            foodName="김치찌개",
            calories=250,
            nutrients=FoodNutrients(protein=12, carbs=20, fat=8, sodium=800),
            confidence=0.85,
            suggestions=["균형 잡힌 영양소를 포함하고 있습니다.", "적당한 양으로 섭취하시기 바랍니다.", "채소와 함께 드시면 더욱 좋습니다."],
        )
    else:
        return FoodAnalysisResult(
            foodName="알 수 없는 음식",
            calories=350,
            nutrients=FoodNutrients(protein=15, carbs=40, fat=12, sodium=600),
            confidence=0.60,
            suggestions=["다양한 음식을 섭취하여 균형 잡힌 식단을 유지하세요."],
        )


@router.post("/analysis", response_model=ApiResponse[FoodAnalysisData])
async def analyze_food_image(request: FoodAnalysisRequest) -> ApiResponse[FoodAnalysisData]:
    """음식 이미지 분석 (메모리 기반 스텁)"""
    start_time = time.time()

    # 이미지 분석 시뮬레이션 (약간의 지연)
    # time.sleep(0.5)  # 실제 API에서는 AI 모델 처리 시간

    analysis_result = _analyze_food_image(request.file_name)
    processing_time = int((time.time() - start_time) * 1000)  # ms

    return ApiResponse(
        success=True,
        data=FoodAnalysisData(
            analysis=analysis_result,
            timestamp=datetime.now(timezone.utc).isoformat(),
            processingTime=processing_time,
        ),
    )

