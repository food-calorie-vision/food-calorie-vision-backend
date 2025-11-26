"""API v1 schemas package"""

from app.api.v1.schemas.common import ApiResponse
from app.api.v1.schemas.meals import (
    MealNutrients,
    MealRecommendation,
    MealRecommendationsResponse,
    MealSelectionData,
    MealSelectionRequest,
    SelectedMealInfo,
)
from app.api.v1.schemas.users import NutrientInfo, UserHealthInfo, UserIntakeData
from app.api.v1.schemas.vision import (
    FoodAnalysisData,
    FoodAnalysisRequest,
    FoodAnalysisResult,
    FoodNutrients,
)

__all__ = [
    # Common
    "ApiResponse",
    # Users
    "UserHealthInfo",
    "UserIntakeData",
    "NutrientInfo",
    # Meals
    "MealNutrients",
    "MealRecommendation",
    "MealRecommendationsResponse",
    "MealSelectionRequest",
    "MealSelectionData",
    "SelectedMealInfo",
    # Vision
    "FoodAnalysisRequest",
    "FoodAnalysisResult",
    "FoodAnalysisData",
    "FoodNutrients",
]
