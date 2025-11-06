"""공통 스키마"""

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """API 응답 래퍼"""

    success: bool
    data: T | None = None
    message: str | None = None
    error: str | None = None

