"""인증 관련 스키마 - ERDCloud 스키마 기반"""
from typing import Literal, Optional
from pydantic import BaseModel, EmailStr, Field, field_validator


class SignupRequest(BaseModel):
    """
    회원가입 요청 (ERDCloud User 테이블 기반)
    user_id는 DB에서 자동생성됨
    """
    # 필수 정보
    email: EmailStr = Field(..., description="이메일 (고유)")
    username: str = Field(..., min_length=2, max_length=50, description="사용자명 (고유)")
    password: str = Field(..., min_length=6, description="비밀번호")
    
    # 선택 정보
    nickname: Optional[str] = Field(None, max_length=50, description="닉네임")
    gender: Optional[Literal['M', 'F']] = Field(None, description="성별 (M/F)")
    age: Optional[int] = Field(None, ge=0, le=150, description="나이")
    weight: Optional[float] = Field(None, ge=0, description="체중 (kg)")
    health_goal: Literal['gain', 'maintain', 'loss'] = Field(default="maintain", description="건강 목표 (gain/maintain/loss)")
    
    allergies: Optional[str] = Field(None, description="알레르기 정보 (콤마로 구분된 문자열)")
    diseases: Optional[str] = Field(None, description="기저 정보 (콤마로 구분된 문자열)")
    
    @field_validator('gender')
    @classmethod
    def validate_gender(cls, v):
        if v is not None and v not in ['M', 'F']:
            raise ValueError('gender must be M or F')
        return v
    
    @field_validator('health_goal')
    @classmethod
    def validate_health_goal(cls, v):
        if v not in ['gain', 'maintain', 'loss']:
            raise ValueError('health_goal must be gain, maintain, or loss')
        return v


class SignupResponse(BaseModel):
    """회원가입 응답"""
    success: bool
    message: str
    user_id: int | None = None  # BIGINT


class LoginRequest(BaseModel):
    """로그인 요청 (이메일 기반)"""
    email: EmailStr = Field(..., description="이메일")
    password: str = Field(..., description="비밀번호")


class LoginResponse(BaseModel):
    """로그인 응답"""
    success: bool
    message: str
    user_id: int | None = None  # BIGINT
    username: str | None = None


class LogoutResponse(BaseModel):
    """로그아웃 응답"""
    success: bool
    message: str


class SessionInfoResponse(BaseModel):
    """세션 정보 응답"""
    authenticated: bool
    user_id: int | None = None  # BIGINT


class UserInfoResponse(BaseModel):
    """사용자 정보 응답"""
    user_id: int  # BIGINT
    username: str
    email: str
    nickname: str | None = None
    gender: str | None = None
    age: int | None = None
    weight: float | None = None
    health_goal: str
    recommended_calories: int = 2000  # 목표 칼로리 (계산된 값)
    created_at: str | None = None
    updated_at: str | None = None
    session_max_age: int | None = None  # 세션 최대 유효 시간 (초)
    session_remaining: int | None = None  # 남은 세션 시간 (초, 추정값)


class EmailAvailabilityResponse(BaseModel):
    """이메일 중복 확인 응답"""
    available: bool
    message: str