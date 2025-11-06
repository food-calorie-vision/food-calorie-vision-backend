"""API 의존성"""

from fastapi import HTTPException, Request

from app.utils.session import get_current_user_id, is_authenticated


async def require_authentication(request: Request) -> str:
    """
    인증 필수 의존성
    
    로그인한 사용자만 접근 가능하도록 하는 의존성
    사용 예:
        @router.get("/protected")
        async def protected_route(user_id: str = Depends(require_authentication)):
            ...
    
    Args:
        request: FastAPI Request 객체
        
    Returns:
        사용자 ID
        
    Raises:
        HTTPException: 인증되지 않은 경우 401 오류
    """
    if not is_authenticated(request):
        raise HTTPException(
            status_code=401,
            detail="인증이 필요합니다. 로그인해주세요.",
        )
    
    user_id = get_current_user_id(request)
    if user_id is None:
        raise HTTPException(
            status_code=401,
            detail="유효하지 않은 세션입니다.",
        )
    
    return user_id


async def optional_authentication(request: Request) -> str | None:
    """
    선택적 인증 의존성
    
    로그인 여부와 관계없이 접근 가능하지만, 로그인한 경우 사용자 ID를 제공
    
    Args:
        request: FastAPI Request 객체
        
    Returns:
        사용자 ID 또는 None
    """
    if is_authenticated(request):
        return get_current_user_id(request)
    return None
