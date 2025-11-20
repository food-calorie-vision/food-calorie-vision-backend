"""레시피 추천 관련 스키마"""
from typing import Optional, List
from pydantic import BaseModel, Field


class RecipeRecommendation(BaseModel):
    """레시피 추천 항목"""
    name: str = Field(..., description="레시피 이름")
    description: str = Field(..., description="레시피 설명")
    calories: int = Field(..., description="예상 칼로리")
    cooking_time: str = Field(..., description="조리 시간")
    difficulty: str = Field(..., description="난이도")
    suitable_reason: str = Field(..., description="적합한 이유")


class RecipeRecommendationRequest(BaseModel):
    """레시피 추천 요청"""
    user_request: str = Field("", description="사용자 요청사항 (예: 매콤한 음식 먹고 싶어요)")
    conversation_history: Optional[List[dict]] = Field(None, description="대화 히스토리")
    meal_type: Optional[str] = Field(None, description="식사 유형 (breakfast, lunch, dinner, snack)")


class RecipeRecommendationResponse(BaseModel):
    """레시피 추천 응답"""
    inferred_preference: str = Field(..., description="추론된 선호도 (시스템용)")
    health_warning: Optional[str] = Field(None, description="건강 경고 메시지")
    user_friendly_message: str = Field(..., description="사용자에게 보여줄 친화적 메시지")
    recommendations: List[RecipeRecommendation] = Field(..., description="추천 레시피 목록")


class RecipeIngredient(BaseModel):
    """레시피 재료"""
    name: str = Field(..., description="재료명")
    amount: str = Field(..., description="양")


class RecipeStep(BaseModel):
    """레시피 조리 단계"""
    step_number: int = Field(..., description="단계 번호")
    title: str = Field(..., description="단계 제목")
    description: str = Field(..., description="상세 설명")
    tip: Optional[str] = Field(None, description="팁")
    image_suggestion: Optional[str] = Field(None, description="이미지 설명")


class NutritionInfo(BaseModel):
    """영양 정보"""
    calories: int = Field(..., description="칼로리 (kcal)")
    protein: str = Field(..., description="단백질 (g)")
    carbs: str = Field(..., description="탄수화물 (g)")
    fat: str = Field(..., description="지방 (g)")
    fiber: Optional[str] = Field(None, description="식이섬유 (g)")
    sodium: Optional[str] = Field(None, description="나트륨 (mg)")


class RecipeDetailRequest(BaseModel):
    """레시피 상세 요청"""
    recipe_name: str = Field(..., description="레시피 이름")


class RecipeDetailResponse(BaseModel):
    """레시피 상세 응답"""
    recipe_name: str = Field(..., description="레시피 이름")
    intro: str = Field(..., description="레시피 소개")
    estimated_time: str = Field(..., description="예상 조리 시간")
    total_steps: int = Field(..., description="총 단계 수")
    ingredients: List[RecipeIngredient] = Field(..., description="재료 목록")
    steps: List[RecipeStep] = Field(..., description="조리 단계")
    nutrition_info: NutritionInfo = Field(..., description="영양 정보")


class SaveRecipeRequest(BaseModel):
    """레시피 완료 후 식단 기록 요청"""
    recipe_name: str = Field(..., description="레시피 이름")
    actual_servings: float = Field(1.0, description="실제 섭취량 (인분)")
    meal_type: str = Field("lunch", description="식사 유형 (breakfast, lunch, dinner, snack)")
    nutrition_info: NutritionInfo = Field(..., description="영양 정보")
    ingredients: Optional[List[str]] = Field(None, description="재료 목록")
    food_class_1: Optional[str] = Field(None, description="음식 대분류 (예: 볶음류, 구이류, 찜류 등)")


