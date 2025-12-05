"""사용자 관련 Pydantic 스키마"""

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class UserHealthInfo(BaseModel):
    """사용자 건강 정보"""

    model_config = ConfigDict(populate_by_name=True)

    goal: str
    diseases: list[str] = Field(default_factory=list)
    recommended_calories: int = Field(alias="recommendedCalories")
    activity_level: str = Field(alias="activityLevel")
    body_type: str | None = Field(default=None, alias="bodyType")
    allergies: list[str] | None = Field(default=None, alias="allergies")
    medical_conditions: list[str] | None = Field(default=None, alias="medicalConditions")


class NutrientInfo(BaseModel):
    """영양소 정보"""

    sodium: int
    carbs: int
    protein: int
    fat: int
    sugar: int


class UserIntakeData(BaseModel):
    """사용자 섭취 현황"""

    model_config = ConfigDict(populate_by_name=True)

    total_calories: int = Field(alias="totalCalories")
    target_calories: int = Field(alias="targetCalories")
    nutrients: NutrientInfo


# ===== Settings 페이지용 스키마 =====

class UserProfileResponse(BaseModel):
    """사용자 프로필 응답"""
    nickname: str | None = None
    height: float | None = None
    weight: float | None = None
    age: int | None = None
    gender: str | None = None
    health_goal: str | None = None


class UserProfileUpdateRequest(BaseModel):
    """사용자 프로필 수정 요청"""
    nickname: Optional[str] = None
    height: Optional[float] = None
    weight: Optional[float] = None


class PasswordChangeRequest(BaseModel):
    """비밀번호 변경 요청"""
    current_password: str = Field(..., min_length=1, description="현재 비밀번호")
    new_password: str = Field(..., min_length=6, description="새 비밀번호")


class HealthProfileItem(BaseModel):
    """알러지/질환 항목"""
    profile_id: int
    name: str
    type: str  # 'allergy' or 'disease'


class HealthProfileResponse(BaseModel):
    """건강 프로필 응답 (알러지/질환 목록)"""
    allergies: list[HealthProfileItem] = Field(default_factory=list)
    diseases: list[HealthProfileItem] = Field(default_factory=list)


class AddHealthProfileRequest(BaseModel):
    """알러지/질환 추가 요청"""
    name: str = Field(..., min_length=1, max_length=100, description="알러지 또는 질환 이름")
    type: str = Field(..., description="'allergy' 또는 'disease'")

