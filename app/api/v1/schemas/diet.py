"""식단 추천 API 스키마"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class DietPlanRequest(BaseModel):
    """식단 추천 요청 스키마"""
    user_request: str = Field(
        default="",
        description="사용자의 추가 요청사항 (예: '고기류를 먹고 싶어요', '채식 위주로 부탁해요')",
        example="고기류를 먹고 싶어요"
    )
    activity_level: str = Field(
        default="moderate",
        description="활동 수준 (sedentary, light, moderate, active, very_active)",
        example="moderate"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_request": "고기류를 먹고 싶어요",
                "activity_level": "moderate"
            }
        }


class MealInfo(BaseModel):
    """끼니별 식사 정보"""
    breakfast: str = Field(description="아침 메뉴")
    lunch: str = Field(description="점심 메뉴")
    dinner: str = Field(description="저녁 메뉴")
    snack: str = Field(description="간식 메뉴")


class DietPlanOption(BaseModel):
    """식단 옵션 (A/B/C 중 하나)"""
    name: str = Field(description="식단 이름 (예: 고단백 식단)")
    description: str = Field(description="식단 설명")
    totalCalories: str = Field(description="총 칼로리 (예: 1500 kcal)")
    meals: MealInfo = Field(description="끼니별 식사 정보")
    nutrients: str = Field(description="영양소 정보 (단백질/탄수화물/지방)")


class DietPlanResponse(BaseModel):
    """식단 추천 응답 스키마"""
    bmr: float = Field(description="기초대사량 (kcal/day)")
    tdee: float = Field(description="1일 총 에너지 소비량 (kcal/day)")
    target_calories: float = Field(alias="targetCalories", description="목표 칼로리 (kcal/day)")
    health_goal: str = Field(alias="healthGoal", description="건강 목표 (gain/maintain/loss)")
    health_goal_kr: str = Field(alias="healthGoalKr", description="건강 목표 한글 (체중 증가/유지/감량)")
    diet_plans: list[DietPlanOption] = Field(alias="dietPlans", description="추천 식단 옵션 (최대 3개)")
    gpt_response: str = Field(alias="gptResponse", description="GPT 원문 응답")
    
    class Config:
        populate_by_name = True


class SaveMealRequest(BaseModel):
    """저장할 끼니 정보"""
    food_name: str = Field(description="음식명 (예: '균형 잡힌 식단 - 아침')")
    meal_type: str = Field(description="끼니 타입 (breakfast/lunch/dinner/snack)")
    ingredients: list[str] = Field(description="재료 목록")
    calories: float = Field(description="칼로리 (kcal)")
    protein: float = Field(default=0, description="단백질 (g)")
    carb: float = Field(default=0, description="탄수화물 (g)")
    fat: float = Field(default=0, description="지방 (g)")
    consumed_at: Optional[datetime] = Field(default=None, description="섭취 시각 (ISO 8601 형식)")


class SaveDietPlanRequest(BaseModel):
    """추천 식단 저장 요청 스키마"""
    user_id: int = Field(description="사용자 ID")
    diet_plan_name: str = Field(description="식단 이름 (예: '고단백 식단')")
    description: Optional[str] = Field(default=None, description="식단 설명")
    
    # 메타데이터 (추천 당시 정보)
    bmr: Optional[float] = Field(default=None, description="기초대사량 (kcal/day)")
    tdee: Optional[float] = Field(default=None, description="1일 총 에너지 소비량 (kcal/day)")
    target_calories: Optional[float] = Field(default=None, description="목표 칼로리 (kcal/day)")
    health_goal: Optional[str] = Field(default=None, description="건강 목표 (gain/maintain/loss)")
    
    meals: list[SaveMealRequest] = Field(description="저장할 끼니 목록")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": 1,
                "diet_plan_name": "고단백 식단",
                "meals": [
                    {
                        "food_name": "고단백 식단 - 아침",
                        "meal_type": "breakfast",
                        "ingredients": ["현미밥 1공기", "닭가슴살 구이 100g", "시금치 무침"],
                        "calories": 450.0,
                        "protein": 35.0,
                        "carb": 55.0,
                        "fat": 8.0,
                        "consumed_at": "2024-01-15T08:00:00"
                    }
                ]
            }
        }


class SaveDietPlanResponse(BaseModel):
    """추천 식단 저장 응답 스키마"""
    success: bool = Field(description="저장 성공 여부")
    message: str = Field(description="응답 메시지")
    diet_plan_id: str = Field(description="저장된 식단 ID")
    saved_count: int = Field(description="저장된 끼니 수")

