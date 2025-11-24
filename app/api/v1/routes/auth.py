"""인증 관련 라우트 (세션 기반) - ERDCloud 스키마 기반"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.auth import (
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    SessionInfoResponse,
    SignupRequest,
    SignupResponse,
    UserInfoResponse,
)
from app.db.session import get_session
from app.services import auth_service
from app.utils.session import get_current_user_id, is_authenticated, login_user, logout_user

router = APIRouter()


@router.post("/signup", response_model=SignupResponse)
async def signup(
    signup_data: SignupRequest,
    session: AsyncSession = Depends(get_session),
) -> SignupResponse:
    """
    회원가입 (ERDCloud User 테이블 기반)
    
    - user_id는 DB에서 자동생성 (BIGINT AUTO_INCREMENT)
    - email과 username은 고유해야 함
    """
    print(f"[DEBUG] 회원가입 요청 데이터: {signup_data}")
    try:
        # 사용자 생성 (user_id는 자동생성)
        user = await auth_service.create_user(
            session=session,
            email=signup_data.email,
            username=signup_data.username,
            password=signup_data.password,
            nickname=signup_data.nickname,
            gender=signup_data.gender,
            age=signup_data.age,
            weight=signup_data.weight,
            health_goal=signup_data.health_goal,
        )

        # 커밋
        await session.commit()

        return SignupResponse(
            success=True,
            message="회원가입이 완료되었습니다.",
            user_id=user.user_id,  # 자동생성된 BIGINT ID
        )

    except ValueError as e:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"회원가입 중 오류가 발생했습니다: {str(e)}")


@router.post("/login", response_model=LoginResponse)
async def login(
    request: Request,
    login_data: LoginRequest,
    session: AsyncSession = Depends(get_session),
) -> LoginResponse:
    """
    로그인 (이메일 기반, 세션 사용)
    
    - 이메일과 비밀번호로 인증
    - 성공 시 세션에 user_id(BIGINT) 저장
    """
    # DB에서 사용자 인증 (이메일 기반)
    user = await auth_service.authenticate_user(
        session=session,
        email=login_data.email,
        password=login_data.password,
    )

    if not user:
        raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 일치하지 않습니다.")

    # 세션에 사용자 정보 저장 (user_id는 BIGINT)
    login_user(request, user_id=user.user_id, username=user.username)

    return LoginResponse(
        success=True,
        message="로그인 성공",
        user_id=user.user_id,
        username=user.username,
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


@router.get("/me", response_model=UserInfoResponse)
async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> UserInfoResponse:
    """
    현재 로그인한 사용자 정보 조회
    """
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="인증이 필요합니다.")

    user_id = get_current_user_id(request)
    
    # DB에서 사용자 정보 조회 (user_id는 BIGINT)
    user = await auth_service.get_user_by_id(session, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    return UserInfoResponse(
        user_id=user.user_id,
        username=user.username,
        email=user.email,
        nickname=user.nickname,
        gender=user.gender,
        age=user.age,
        weight=user.weight,
        health_goal=user.health_goal,
        created_at=user.created_at.isoformat() if user.created_at else None,
        updated_at=user.updated_at.isoformat() if user.updated_at else None,
    )


@router.post("/refresh-session")
async def refresh_session(request: Request) -> dict:
    """
    세션 갱신 (사용자 활동 시 호출)
    """
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="인증이 필요합니다.")
    
    # 세션이 유효하면 자동으로 갱신됨 (SessionMiddleware의 sliding session)
    return {"success": True, "message": "세션이 갱신되었습니다."}