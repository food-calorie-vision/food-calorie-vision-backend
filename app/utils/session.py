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
    request.session["user_id"] = user_id
    request.session["authenticated"] = True
    
    # 추가 정보 저장
    for key, value in kwargs.items():
        request.session[key] = value


def logout_user(request: Request) -> None:
    """
    사용자 로그아웃 처리 (세션 삭제)
    
    Args:
        request: FastAPI Request 객체
    """
    clear_session(request)

