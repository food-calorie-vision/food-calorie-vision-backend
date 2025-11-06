"""챗봇 관련 Pydantic 스키마"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    """챗봇 요청"""

    model_config = ConfigDict(populate_by_name=True)

    message: str
    selected_meal: dict[str, Any] | None = Field(None, alias="selectedMeal")
    image_data: str | None = Field(None, alias="imageData")
    user_id: str | None = Field(None, alias="userId")
    timestamp: str | None = None


class ChatData(BaseModel):
    """챗봇 응답 데이터"""

    message: str
    timestamp: str | None = None

