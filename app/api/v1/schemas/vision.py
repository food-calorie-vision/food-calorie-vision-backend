"""음식 이미지 분석 관련 Pydantic 스키마"""

from pydantic import BaseModel, ConfigDict, Field


class FoodNutrients(BaseModel):
    """음식 영양소"""

    protein: float
    carbs: float
    fat: float
    sodium: float
    fiber: float = 0.0  # 식이섬유 추가


class FoodAnalysisRequest(BaseModel):
    """음식 이미지 분석 요청"""

    model_config = ConfigDict(populate_by_name=True)

    image_data: str = Field(alias="imageData")
    file_name: str = Field(alias="fileName")
    file_size: int = Field(alias="fileSize")
    file_type: str = Field(alias="fileType")
    user_id: str | None = Field(None, alias="userId")
    timestamp: str | None = None


class FoodCandidate(BaseModel):
    """후보 음식 정보"""

    model_config = ConfigDict(populate_by_name=True)

    food_name: str = Field(alias="foodName")
    confidence: float  # 0.0 ~ 1.0
    description: str = ""
    ingredients: list[str] = []  # 각 후보의 재료 정보


class FoodAnalysisResult(BaseModel):
    """음식 분석 결과"""

    model_config = ConfigDict(populate_by_name=True)

    food_name: str = Field(alias="foodName")
    description: str = ""  # 음식 설명 (필요시)
    ingredients: list[str] = []  # 주요 재료 3-4개
    confidence: float
    candidates: list[FoodCandidate] = []  # 여러 후보 음식 리스트


class FoodAnalysisData(BaseModel):
    """음식 분석 응답 데이터"""

    analysis: FoodAnalysisResult
    timestamp: str
    processing_time: int = Field(alias="processingTime")


class FoodReanalysisRequest(BaseModel):
    """음식 재분석 요청 (사용자가 다른 후보 선택)"""

    model_config = ConfigDict(populate_by_name=True)

    selected_food_name: str = Field(alias="selectedFoodName")
    ingredients: list[str] = []  # 원본 재료 정보 (있으면 재사용)


class SaveFoodRequest(BaseModel):
    """음식 저장 요청 (Preview 단계에서 확정된 정보 저장)"""

    model_config = ConfigDict(populate_by_name=True)

    user_id: int = Field(alias="userId")
    food_name: str = Field(alias="foodName")
    food_id: str = Field(alias="foodId", description="Preview에서 확정된 Food ID")
    
    # 섭취 정보
    meal_type: str = Field(default="lunch", alias="mealType")
    portion_size_g: float = Field(alias="portionSizeG")
    image_ref: str | None = Field(None, alias="imageRef")
    
    # 확정된 영양 정보 (Preview에서 계산됨)
    calories: float = Field(alias="calories")
    protein: float = Field(alias="protein")
    carbs: float = Field(alias="carbs")
    fat: float = Field(alias="fat")
    sodium: float = Field(alias="sodium")
    fiber: float = Field(default=0.0, alias="fiber")
    
    # 선택적 추가 영양소 (NRF 계산에 사용된 값들)
    vitamin_a: float | None = Field(None, alias="vitaminA")
    vitamin_c: float | None = Field(None, alias="vitaminC")
    calcium: float | None = Field(None, alias="calcium")
    iron: float | None = Field(None, alias="iron")
    potassium: float | None = Field(None, alias="potassium")
    magnesium: float | None = Field(None, alias="magnesium")
    saturated_fat: float | None = Field(None, alias="saturatedFat")
    added_sugar: float | None = Field(None, alias="addedSugar")
    
    # 확정된 점수 정보
    health_score: int = Field(alias="healthScore")
    
    # 메타 정보 (DB 분류용)
    food_class_1: str | None = Field(None, alias="foodClass1")
    food_class_2: str | None = Field(None, alias="foodClass2")
    ingredients: list[str] = []
    category: str | None = None


class SaveFoodResponse(BaseModel):
    """음식 저장 응답"""

    model_config = ConfigDict(populate_by_name=True)

    history_id: int = Field(alias="historyId")
    food_id: str = Field(alias="foodId")
    food_name: str = Field(alias="foodName")
    meal_type: str = Field(alias="mealType", description="식사 유형 (breakfast/lunch/dinner/snack)")
    consumed_at: str = Field(alias="consumedAt")
    portion_size_g: float | None = Field(None, alias="portionSizeG")


class PreviewNutritionRequest(BaseModel):
    """영양 정보 미리보기 요청"""
    model_config = ConfigDict(populate_by_name=True)

    food_name: str = Field(alias="foodName")
    ingredients: list[str] = Field(default=[], alias="ingredients")
    portion_text: str = Field(alias="portionText")


class PreviewNutritionResponse(BaseModel):
    """영양 정보 미리보기 응답"""
    model_config = ConfigDict(populate_by_name=True)

    food_id: str = Field(alias="foodId")
    food_name: str = Field(alias="foodName")
    calories: float = Field(alias="calories")
    nutrients: FoodNutrients = Field(alias="nutrients")
    portion_size_g: float = Field(alias="portionSizeG")
    health_score: int = Field(alias="healthScore")
    