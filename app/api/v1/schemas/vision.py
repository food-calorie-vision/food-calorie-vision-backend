"""음식 이미지 분석 관련 Pydantic 스키마"""

from pydantic import BaseModel, ConfigDict, Field


class FoodNutrients(BaseModel):
    """음식 영양소"""

    protein: int
    carbs: int
    fat: int
    sodium: int


class FoodAnalysisRequest(BaseModel):
    """음식 이미지 분석 요청"""

    model_config = ConfigDict(populate_by_name=True)

    image_data: str = Field(alias="imageData")
    file_name: str = Field(alias="fileName")
    file_size: int = Field(alias="fileSize")
    file_type: str = Field(alias="fileType")
    user_id: str | None = Field(None, alias="userId")
    timestamp: str | None = None


class FoodAnalysisResult(BaseModel):
    """음식 분석 결과"""

    model_config = ConfigDict(populate_by_name=True)

    food_name: str = Field(alias="foodName")
    calories: int
    nutrients: FoodNutrients
    confidence: float
    suggestions: list[str]


class FoodAnalysisData(BaseModel):
    """음식 분석 응답 데이터"""

    analysis: FoodAnalysisResult
    timestamp: str
    processing_time: int = Field(alias="processingTime")

