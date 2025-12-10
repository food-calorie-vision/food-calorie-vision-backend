"""레시피 추천 관련 스키마"""
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


class RecipeActionType(str, Enum):
    CONFIRMATION = "CONFIRMATION"
    HEALTH_CONFIRMATION = "HEALTH_CONFIRMATION"
    RECOMMENDATION_RESULT = "RECOMMENDATION_RESULT"
    TEXT_ONLY = "TEXT_ONLY"
    INGREDIENT_CHECK = "INGREDIENT_CHECK"
    COOKING_STEPS = "COOKING_STEPS"


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


class RecipeRecommendationData(BaseModel):
    """에이전트 응답 데이터"""
    recipes: Optional[List[RecipeRecommendation]] = Field(None, description="추천 레시피 목록")
    inferred_preference: Optional[str] = Field(None, description="추론된 선호도")
    health_warning: Optional[str] = Field(None, description="건강 경고 메시지")
    user_friendly_message: Optional[str] = Field(None, description="사용자 친화적 메시지")


class RecipeRecommendationResponse(BaseModel):
    """에이전트 응답 래퍼"""
    response_id: str = Field(..., description="응답 추적용 ID")
    action_type: RecipeActionType = Field(..., description="다음 UI 동작을 결정하는 Action 타입")
    message: str = Field(..., description="챗봇이 사용자에게 전달할 기본 메시지")
    data: Optional[RecipeRecommendationData] = Field(None, description="추가 데이터(레시피, 메타 등)")
    suggestions: Optional[List[str]] = Field(None, description="빠른 응답 또는 추천 문구")


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
    total_weight_g: float = Field(250.0, description="총 중량(g)")


class SaveRecipeRequest(BaseModel):
    """레시피 완료 후 식단 기록 요청"""
    recipe_name: str = Field(..., description="레시피 이름")
    actual_servings: float = Field(1.0, description="실제 섭취량 (인분)")
    portion_size_g: float = Field(250.0, description="1인분 기준 중량(g)")
    meal_type: str = Field("lunch", description="식사 유형 (breakfast, lunch, dinner, snack)")
    nutrition_info: NutritionInfo = Field(..., description="영양 정보")
    ingredients: Optional[List[str]] = Field(None, description="재료 목록")
    food_class_1: Optional[str] = Field(None, description="음식 대분류 (예: 볶음류, 구이류, 찜류 등)")


class IngredientCheckRequest(BaseModel):
    """재료 확인 요청"""
    recipe_name: str = Field(..., description="레시피 이름")


class IngredientCheckResponse(BaseModel):
    """재료 확인 응답"""
    response_id: str = Field(..., description="응답 추적용 ID")
    action_type: RecipeActionType = Field(RecipeActionType.INGREDIENT_CHECK, description="INGREDIENT_CHECK 고정")
    recipe_name: str = Field(..., description="레시피 이름")
    ingredients: List[str] = Field(..., description="필수 재료 목록")


class CustomRecipeRequest(BaseModel):
    """맞춤 조리법 생성 요청"""
    recipe_name: str = Field(..., description="레시피 이름")
    excluded_ingredients: List[str] = Field(default_factory=list, description="사용자가 제외할 재료 목록")
    meal_type: Optional[str] = Field(None, description="선택된 식사 유형")
    available_ingredients: List[str] = Field(default_factory=list, description="원래 레시피의 재료 목록")


class CustomRecipeResponse(BaseModel):
    """맞춤 조리법 응답"""
    response_id: str = Field(..., description="응답 추적용 ID")
    action_type: RecipeActionType = Field(RecipeActionType.COOKING_STEPS, description="COOKING_STEPS 고정")
    recipe_name: str = Field(..., description="레시피 이름")
    ingredients: List[RecipeIngredient] = Field(..., description="변경된 재료 목록")
    instructions_markdown: str = Field(..., description="마크다운 형태의 조리 단계")
    steps: List[RecipeStep] = Field(..., description="맞춤 조리 단계 목록")
    nutrition_info: NutritionInfo = Field(..., description="맞춤 영양 정보")
    estimated_time: Optional[str] = Field(None, description="예상 조리 시간")
    intro: Optional[str] = Field(None, description="조리 도입부 설명")
    total_weight_g: float = Field(250.0, description="총 중량(g)")
