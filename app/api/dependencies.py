"""API 의존성"""

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.db.session import get_session
from app.services import auth_service
from app.utils.session import get_current_user_id, is_authenticated


async def require_authentication(request: Request) -> int:
    """
    인증 필수 의존성
    
    로그인한 사용자만 접근 가능하도록 하는 의존성. 사용자 ID(int)를 반환합니다.
    사용 예:
        @router.get("/protected")
        async def protected_route(user_id: int = Depends(require_authentication)):
            ...
    """
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="인증이 필요합니다. 로그인해주세요.")
    
    user_id = get_current_user_id(request)
    if user_id is None:
        raise HTTPException(status_code=401, detail="유효하지 않은 세션입니다.")
    
    return user_id


async def get_current_active_user(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> User:
    """
    현재 활성화된 사용자 객체를 반환하는 의존성
    
    - 세션을 확인하여 인증된 사용자인지 검증
    - DB에서 최신 사용자 정보를 조회하여 User 모델 객체로 반환
    """
    user_id = await require_authentication(request)
    user = await auth_service.get_user_by_id(session, user_id)
    
    if not user:
        # 이 경우는 거의 발생하지 않아야 함 (세션이 있는데 DB에 유저가 없는 경우)
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
        
    return user


async def optional_authentication(request: Request) -> int | None:
    """
    선택적 인증 의존성
    
    로그인 여부와 관계없이 접근 가능하지만, 로그인한 경우 사용자 ID를 제공
    """
    if is_authenticated(request):
        return get_current_user_id(request)
    return None
