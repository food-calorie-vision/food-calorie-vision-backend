"""식재료 관련 스키마"""
from typing import List, Optional
from datetime import datetime

from pydantic import BaseModel, Field


class IngredientItem(BaseModel):
    """개별 식재료 아이템"""
    name: str = Field(..., description="식재료 이름")
    count: int = Field(..., ge=0, description="수량")


class SaveIngredientsRequest(BaseModel):
    """식재료 저장 요청"""
    ingredients: List[IngredientItem] = Field(..., description="식재료 목록")


class IngredientResponse(BaseModel):
    """식재료 응답"""
    ingredient_id: int
    user_id: int
    ingredient_name: str
    count: int
    created_at: datetime
    is_used: bool


class SaveIngredientsData(BaseModel):
    """식재료 저장 응답 데이터"""
    saved_count: int = Field(..., description="저장된 식재료 개수")
    ingredients: List[IngredientResponse] = Field(..., description="저장된 식재료 목록")


class RecommendationData(BaseModel):
    """음식 추천 응답 데이터"""
    recommendations: str = Field(..., description="LLM이 생성한 음식 추천 텍스트")
    ingredients_used: List[str] = Field(..., description="추천에 사용된 식재료 목록")
    total_ingredients: int = Field(..., description="전체 보유 식재료 개수")








