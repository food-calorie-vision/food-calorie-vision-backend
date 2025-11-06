"""인증 관련 스키마"""
from datetime import date

from pydantic import BaseModel, Field


class SignupRequest(BaseModel):
    """회원가입 요청"""

    user_id: str = Field(..., min_length=3, max_length=50, description="사용자 ID")
    nickname: str = Field(..., min_length=2, max_length=100, description="닉네임")
    password: str = Field(..., min_length=6, description="비밀번호")
    gender: str = Field(..., description="성별 (남자/여자)")
    birth_date: str = Field(..., description="생년월일 (YYYY-MM-DD)")
    
    # 건강 정보
    has_allergy: str = Field(default="아니오", description="알레르기 유무 (예/아니오)")
    allergy_info: str | None = Field(None, description="알레르기 정보")
    body_type: str = Field(..., description="체형 목표 (감량/유지/증량)")
    medical_condition: str | None = Field(None, description="질병 정보")
    health_goal: str = Field(..., description="건강 목표")
    
    # 선택 정보
    email: str | None = Field(None, description="이메일")


class SignupResponse(BaseModel):
    """회원가입 응답"""

    success: bool
    message: str
    user_id: str | None = None


class LoginRequest(BaseModel):
    """로그인 요청"""

    user_id: str
    password: str


class LoginResponse(BaseModel):
    """로그인 응답"""

    success: bool
    message: str
    user_id: str | None = None


class LogoutResponse(BaseModel):
    """로그아웃 응답"""

    success: bool
    message: str


class SessionInfoResponse(BaseModel):
    """세션 정보 응답"""

    authenticated: bool
    user_id: str | None = None


class UserInfoResponse(BaseModel):
    """사용자 정보 응답"""

    user_id: str
    username: str
    nickname: str
    email: str | None = None
    gender: str
    birth_date: str

