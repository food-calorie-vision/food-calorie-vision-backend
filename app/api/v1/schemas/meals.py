"""식단 관련 Pydantic 스키마"""

from pydantic import BaseModel, ConfigDict, Field


class MealNutrients(BaseModel):
    """식단 영양소"""

    protein: int
    carbs: int
    fat: int
    sodium: int


class MealRecommendation(BaseModel):
    """식단 추천"""

    model_config = ConfigDict(populate_by_name=True)

    id: int
    name: str
    calories: int
    description: str
    is_selected: bool = Field(alias="isSelected")
    nutrients: MealNutrients | None = None


class MealRecommendationsResponse(BaseModel):
    """식단 추천 응답 데이터"""

    recommendations: list[MealRecommendation]
    timestamp: str | None = None


class MealSelectionRequest(BaseModel):
    """식단 선택 요청"""

    model_config = ConfigDict(populate_by_name=True)

    meal_id: int = Field(alias="mealId")
    user_id: str = Field(alias="userId")
    timestamp: str | None = None


class SelectedMealInfo(BaseModel):
    """선택된 식단 정보"""

    id: int
    name: str
    calories: int


class MealSelectionData(BaseModel):
    """식단 선택 응답 데이터"""

    success: bool
    message: str
    selected_meal: SelectedMealInfo = Field(alias="selectedMeal")

