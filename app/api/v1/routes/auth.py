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
from app.utils.session import (
    get_current_user_id,
    get_session_remaining_time,
    is_authenticated,
    login_user,
    logout_user,
    update_session_activity,
)

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

    # 디버그: 세션 정보 출력
    from app.core.config import get_settings
    settings = get_settings()
    print(f"\n{'='*50}")
    print(f"🔐 로그인 성공")
    print(f"{'='*50}")
    print(f"👤 User ID: {user.user_id}")
    print(f"📧 Email: {login_data.email}")
    print(f"⏱️  세션 유효 시간: {settings.session_max_age}초 ({settings.session_max_age // 60}분)")
    print(f"🍪 세션 쿠키 이름: {settings.session_cookie_name}")
    print(f"{'='*50}\n")

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
    현재 로그인한 사용자 정보 조회 (읽기 전용 - 세션 갱신 안함)
    """
    if not is_authenticated(request):
        print(f"❌ 세션 체크 실패: 인증되지 않음")
        raise HTTPException(status_code=401, detail="인증이 필요합니다.")

    user_id = get_current_user_id(request)
    
    from app.core.config import get_settings
    settings = get_settings()
    
    # 디버그: 세션 데이터 확인
    print(f"🔍 세션 데이터: {dict(request.session)}")
    
    # 남은 세션 시간 계산
    remaining = get_session_remaining_time(request)
    
    # last_activity가 없으면 지금 설정 (세션이 갱신되어 사라진 경우)
    if request.session.get("last_activity") is None:
        import time
        request.session["last_activity"] = time.time()
        remaining = settings.session_max_age
        print(f"⚠️ last_activity 없음 - 새로 설정")
    
    # 세션 만료 체크
    if remaining is not None and remaining <= 0:
        print(f"⚠️ 세션 만료됨 - User ID: {user_id}")
        logout_user(request)
        raise HTTPException(status_code=401, detail="세션이 만료되었습니다.")
    
    # 디버그: 세션 체크 정보
    minutes = remaining // 60 if remaining else 0
    seconds = remaining % 60 if remaining else 0
    print(f"✅ 세션 체크 성공 - User ID: {user_id}, 남은시간: {minutes}분 {seconds}초")
    
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
        session_max_age=settings.session_max_age,
        session_remaining=remaining,
    )


@router.post("/refresh-session")
async def refresh_session(request: Request) -> dict:
    """
    세션 갱신 (사용자 활동 시 호출) - 마지막 활동 시간 업데이트
    """
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="인증이 필요합니다.")
    
    user_id = get_current_user_id(request)
    from app.core.config import get_settings
    settings = get_settings()
    
    # 갱신 전 남은 시간
    remaining_before = get_session_remaining_time(request)
    
    # 세션 활동 시간 갱신
    update_session_activity(request)
    
    # 갱신 후 남은 시간
    remaining_after = get_session_remaining_time(request)
    
    # 디버그: 세션 갱신 정보
    print(f"\n{'='*50}")
    print(f"🔄 세션 갱신 요청")
    print(f"{'='*50}")
    print(f"👤 User ID: {user_id}")
    print(f"⏱️  갱신 전 남은시간: {remaining_before}초")
    print(f"⏱️  갱신 후 남은시간: {remaining_after}초")
    print(f"🔄 세션 최대 유효시간: {settings.session_max_age}초")
    print(f"{'='*50}\n")
    
    return {
        "success": True,
        "message": "세션이 갱신되었습니다.",
        "session_max_age": settings.session_max_age,
        "remaining_before": remaining_before,
        "remaining_after": remaining_after,
    }
