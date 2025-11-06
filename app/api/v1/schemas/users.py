"""사용자 관련 Pydantic 스키마"""

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

