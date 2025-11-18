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
    description: str = ""  # 음식 설명
    ingredients: list[str] = []  # 주요 재료 3-4개
    calories: int
    nutrients: FoodNutrients
    portion_size: str = Field(default="1인분", alias="portionSize")  # 1회 제공량
    health_score: int = Field(default=0, alias="healthScore")  # 건강 점수 (0-100)
    confidence: float
    suggestions: list[str]
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
    """음식 저장 요청"""

    model_config = ConfigDict(populate_by_name=True)

    user_id: int = Field(alias="userId")
    food_name: str = Field(alias="foodName")
    food_class_1: str | None = Field(None, alias="foodClass1")  # 대분류
    food_class_2: str | None = Field(None, alias="foodClass2")  # 중분류
    ingredients: list[str] = []  # 재료 리스트
    portion_size_g: float | None = Field(None, alias="portionSizeG")  # 섭취량(g)
    image_ref: str | None = Field(None, alias="imageRef")  # 이미지 참조 (선택)
    category: str | None = None  # 카테고리 (선택)


class SaveFoodResponse(BaseModel):
    """음식 저장 응답"""

    model_config = ConfigDict(populate_by_name=True)

    history_id: int = Field(alias="historyId")
    food_id: str = Field(alias="foodId")
    food_name: str = Field(alias="foodName")
    consumed_at: str = Field(alias="consumedAt")
    portion_size_g: float | None = Field(None, alias="portionSizeG")