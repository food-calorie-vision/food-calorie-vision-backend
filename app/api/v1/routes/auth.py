"""인증 관련 라우트 (세션 기반)"""
from datetime import datetime

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
    회원가입
    
    사용자 정보와 건강 정보를 함께 등록합니다.
    """
    print(f"[DEBUG] 회원가입 요청 데이터: {signup_data}")  # 디버깅용
    try:
        # 생년월일 파싱
        try:
            birth_date = datetime.strptime(signup_data.birth_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="생년월일 형식이 올바르지 않습니다. (YYYY-MM-DD)")

        # 사용자 생성
        user = await auth_service.create_user(
            session=session,
            user_id=signup_data.user_id,
            username=signup_data.nickname,  # username을 nickname으로 사용
            nickname=signup_data.nickname,
            password=signup_data.password,
            gender=signup_data.gender,
            birth_date=birth_date,
            email=signup_data.email,
        )

        # 권장 칼로리 계산 (간단한 예시 - 나중에 정교하게 개선)
        # 남자: 2500, 여자: 2000 기본값
        base_calories = 2500 if signup_data.gender == "남자" else 2000
        
        # 체형 목표에 따라 조정
        if signup_data.body_type == "감량":
            recommended_calories = base_calories * 0.8
        elif signup_data.body_type == "증량":
            recommended_calories = base_calories * 1.2
        else:  # 유지
            recommended_calories = float(base_calories)

        # 건강 정보 생성
        has_allergy = signup_data.has_allergy == "예"
        allergies = [signup_data.allergy_info] if has_allergy and signup_data.allergy_info else None
        diseases = [signup_data.medical_condition] if signup_data.medical_condition else None

        await auth_service.create_user_health_info(
            session=session,
            user_id=user.id,
            goal=signup_data.health_goal,
            body_type=signup_data.body_type,
            activity_level="보통",  # 기본값 (나중에 입력받을 수 있음)
            recommended_calories=recommended_calories,
            has_allergy=has_allergy,
            allergy_info=signup_data.allergy_info,
            medical_condition=signup_data.medical_condition,
            allergies=allergies,
            diseases=diseases,
        )

        # 커밋
        await session.commit()

        return SignupResponse(
            success=True,
            message="회원가입이 완료되었습니다.",
            user_id=signup_data.user_id,
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
    로그인 (세션 기반)
    
    DB에서 사용자 인증 후 세션 생성
    """
    # DB에서 사용자 인증
    user = await auth_service.authenticate_user(
        session=session,
        user_id=login_data.user_id,
        password=login_data.password,
    )

    if not user:
        raise HTTPException(status_code=401, detail="사용자 ID 또는 비밀번호가 일치하지 않습니다.")

    # 세션에 사용자 정보 저장
    login_user(request, user_id=user.user_id, username=user.username)

    return LoginResponse(
        success=True,
        message="로그인 성공",
        user_id=user.user_id,
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
    
    # DB에서 사용자 정보 조회
    user = await auth_service.get_user_by_user_id(session, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    return UserInfoResponse(
        user_id=user.user_id,
        username=user.username,
        nickname=user.nickname,
        email=user.email,
        gender=user.gender,
        birth_date=user.birth_date.isoformat(),
    )

