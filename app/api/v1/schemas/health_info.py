"""건강 정보 관련 스키마"""
from typing import Optional
from datetime import date
from pydantic import BaseModel, Field


class HealthInfoResponse(BaseModel):
    """건강 정보 조회 응답"""
    user_id: str
    birth_date: date
    gender: str
    health_goal: str
    body_type: str
    has_allergy: str
    allergy_info: Optional[str] = None
    medical_condition: Optional[str] = None
    recommended_calories: int
    
    class Config:
        from_attributes = True


class HealthInfoUpdateRequest(BaseModel):
    """건강 정보 수정 요청"""
    health_goal: Optional[str] = Field(None, description="건강 목표 (다이어트/유지/증량)")
    body_type: Optional[str] = Field(None, description="체형 (다이어트/유지/증량)")
    has_allergy: Optional[str] = Field(None, description="알러지 여부 (예/아니오)")
    allergy_info: Optional[str] = Field(None, description="알러지 정보")
    medical_condition: Optional[str] = Field(None, description="기저질환")


class HealthInfoUpdateResponse(BaseModel):
    """건강 정보 수정 응답"""
    success: bool
    message: str
    data: Optional[HealthInfoResponse] = None

