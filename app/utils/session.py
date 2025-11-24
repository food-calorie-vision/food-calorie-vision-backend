"""세션 관리 유틸리티"""

from typing import Any

from fastapi import Request


def get_session(request: Request) -> dict[str, Any]:
    """
    세션 데이터 조회
    
    Args:
        request: FastAPI Request 객체
        
    Returns:
        세션 데이터 딕셔너리
    """
    return request.session


def set_session_value(request: Request, key: str, value: Any) -> None:
    """
    세션에 값 설정
    
    Args:
        request: FastAPI Request 객체
        key: 세션 키
        value: 저장할 값
    """
    request.session[key] = value


def get_session_value(request: Request, key: str, default: Any = None) -> Any:
    """
    세션에서 값 조회
    
    Args:
        request: FastAPI Request 객체
        key: 세션 키
        default: 기본값
        
    Returns:
        세션 값 또는 기본값
    """
    return request.session.get(key, default)


def delete_session_value(request: Request, key: str) -> None:
    """
    세션에서 값 삭제
    
    Args:
        request: FastAPI Request 객체
        key: 세션 키
    """
    if key in request.session:
        del request.session[key]


def clear_session(request: Request) -> None:
    """
    세션 전체 삭제 (로그아웃 시 사용)
    
    Args:
        request: FastAPI Request 객체
    """
    request.session.clear()


def is_authenticated(request: Request) -> bool:
    """
    사용자 인증 여부 확인
    
    Args:
        request: FastAPI Request 객체
        
    Returns:
        인증 여부
    """
    return get_session_value(request, "user_id") is not None


def get_current_user_id(request: Request) -> int | None:
    """
    현재 로그인한 사용자 ID 조회 (users.user_id - BIGINT)
    
    Args:
        request: FastAPI Request 객체
        
    Returns:
        사용자 ID (정수) 또는 None
    """
    return get_session_value(request, "user_id")


def login_user(request: Request, user_id: int, **kwargs: Any) -> None:
    """
    사용자 로그인 처리 (세션에 사용자 정보 저장)
    
    Args:
        request: FastAPI Request 객체
        user_id: 사용자 ID (users.user_id - BIGINT)
        **kwargs: 추가 사용자 정보
    """
    import time
    request.session["user_id"] = user_id
    request.session["authenticated"] = True
    request.session["login_time"] = time.time()  # 로그인 시간 저장
    request.session["last_activity"] = time.time()  # 마지막 활동 시간
    
    # 추가 정보 저장
    for key, value in kwargs.items():
        request.session[key] = value


def get_session_remaining_time(request: Request) -> int | None:
    """
    세션 남은 시간 계산 (초)
    
    Args:
        request: FastAPI Request 객체
        
    Returns:
        남은 시간 (초) 또는 None
    """
    import time
    from app.core.config import get_settings
    
    last_activity = get_session_value(request, "last_activity")
    if last_activity is None:
        return None
    
    settings = get_settings()
    elapsed = time.time() - last_activity
    remaining = settings.session_max_age - int(elapsed)
    
    return max(0, remaining)


def update_session_activity(request: Request) -> None:
    """
    세션 활동 시간 갱신 (refresh-session 호출 시에만 사용)
    
    Args:
        request: FastAPI Request 객체
    """
    import time
    new_time = time.time()
    old_time = request.session.get("last_activity")
    request.session["last_activity"] = new_time
    
    # 디버그: 세션 업데이트 확인
    print(f"🔧 세션 활동 시간 업데이트:")
    print(f"   이전: {old_time} ({time.ctime(old_time) if old_time else 'None'})")
    print(f"   현재: {new_time} ({time.ctime(new_time)})")
    print(f"   세션 데이터: {dict(request.session)}")


def logout_user(request: Request) -> None:
    """
    사용자 로그아웃 처리 (세션 삭제)
    
    Args:
        request: FastAPI Request 객체
    """
    clear_session(request)

