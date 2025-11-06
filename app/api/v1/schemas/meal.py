"""식사 기록 관련 스키마"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class FoodAnalysisItem(BaseModel):
    """음식 분석 결과 아이템"""
    food_id: int
    food_name: str
    quantity: float
    calories: float
    protein: float
    carbs: float
    fat: float


class MealRecordCreateRequest(BaseModel):
    """식사 기록 생성 요청"""
    meal_type: str = Field(..., description="식사 유형 (아침/점심/저녁/간식)")
    image_url: str = Field(..., description="음식 이미지 URL")
    foods: List[FoodAnalysisItem] = Field(..., description="음식 분석 결과 리스트")
    memo: Optional[str] = Field(None, description="메모")


class MealRecordResponse(BaseModel):
    """식사 기록 응답"""
    record_id: int
    user_id: str
    meal_type: str
    meal_date: datetime
    image_url: str
    total_calories: float
    total_protein: float
    total_carbs: float
    total_fat: float
    memo: Optional[str] = None
    foods: List[FoodAnalysisItem]
    
    class Config:
        from_attributes = True


class MealRecordListResponse(BaseModel):
    """식사 기록 리스트 응답"""
    total: int
    records: List[MealRecordResponse]


class DailyMealSummary(BaseModel):
    """일일 식사 요약"""
    date: str
    total_calories: float
    total_protein: float
    total_carbs: float
    total_fat: float
    meal_count: int
    recommended_calories: int
    calories_remaining: float

