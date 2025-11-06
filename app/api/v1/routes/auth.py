"""인증 관련 라우트 (세션 기반)"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.utils.session import get_current_user_id, is_authenticated, login_user, logout_user

router = APIRouter()


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


@router.post("/login", response_model=LoginResponse)
async def login(request: Request, login_data: LoginRequest) -> LoginResponse:
    """
    로그인 (세션 기반)
    
    현재는 하드코딩된 사용자로 테스트
    향후 DB에서 사용자 인증 구현 필요
    """
    # TODO: DB에서 사용자 확인 및 비밀번호 검증
    # 임시 하드코딩된 사용자
    MOCK_USERS = {
        "test_user": "password123",
        "admin": "admin123",
        "user1": "user123",
    }

    if login_data.user_id not in MOCK_USERS:
        raise HTTPException(status_code=401, detail="사용자를 찾을 수 없습니다.")

    if MOCK_USERS[login_data.user_id] != login_data.password:
        raise HTTPException(status_code=401, detail="비밀번호가 일치하지 않습니다.")

    # 세션에 사용자 정보 저장
    login_user(request, user_id=login_data.user_id, username=login_data.user_id)

    return LoginResponse(
        success=True,
        message="로그인 성공",
        user_id=login_data.user_id,
    )


@router.post("/logout", response_model=LogoutResponse)
async def logout(request: Request) -> LogoutResponse:
    """
    로그아웃 (세션 삭제)
    """
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="로그인되어 있지 않습니다.")

    logout_user(request)

    return LogoutResponse(
        success=True,
        message="로그아웃 성공",
    )


@router.get("/session", response_model=SessionInfoResponse)
async def get_session_info(request: Request) -> SessionInfoResponse:
    """
    현재 세션 정보 조회
    """
    authenticated = is_authenticated(request)
    user_id = get_current_user_id(request) if authenticated else None

    return SessionInfoResponse(
        authenticated=authenticated,
        user_id=user_id,
    )


@router.get("/me")
async def get_current_user(request: Request) -> dict:
    """
    현재 로그인한 사용자 정보 조회
    """
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="인증이 필요합니다.")

    user_id = get_current_user_id(request)
    
    # TODO: DB에서 사용자 정보 조회
    # 임시 목 데이터
    return {
        "user_id": user_id,
        "username": user_id,
        "email": f"{user_id}@example.com",
    }

