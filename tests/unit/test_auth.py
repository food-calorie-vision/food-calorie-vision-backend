"""인증 관련 라우트 테스트"""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_login_success():
    """로그인 성공 테스트"""
    response = client.post(
        "/api/v1/auth/login",
        json={"user_id": "test_user", "password": "password123"},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert data["user_id"] == "test_user"
    assert "message" in data


def test_login_invalid_user():
    """존재하지 않는 사용자 로그인 테스트"""
    response = client.post(
        "/api/v1/auth/login",
        json={"user_id": "nonexistent", "password": "password123"},
    )

    assert response.status_code == 401


def test_login_wrong_password():
    """잘못된 비밀번호 로그인 테스트"""
    response = client.post(
        "/api/v1/auth/login",
        json={"user_id": "test_user", "password": "wrongpassword"},
    )

    assert response.status_code == 401


def test_session_info_not_authenticated():
    """비인증 상태 세션 정보 조회 테스트"""
    # 새로운 클라이언트 (세션 없음)
    new_client = TestClient(app)
    response = new_client.get("/api/v1/auth/session")

    assert response.status_code == 200
    data = response.json()

    assert data["authenticated"] is False
    assert data["user_id"] is None


def test_session_info_authenticated():
    """인증 상태 세션 정보 조회 테스트"""
    # 로그인
    login_response = client.post(
        "/api/v1/auth/login",
        json={"user_id": "test_user", "password": "password123"},
    )
    assert login_response.status_code == 200

    # 세션 정보 조회
    response = client.get("/api/v1/auth/session")

    assert response.status_code == 200
    data = response.json()

    assert data["authenticated"] is True
    assert data["user_id"] == "test_user"


def test_get_current_user_authenticated():
    """인증된 사용자 정보 조회 테스트"""
    # 로그인
    login_response = client.post(
        "/api/v1/auth/login",
        json={"user_id": "test_user", "password": "password123"},
    )
    assert login_response.status_code == 200

    # 사용자 정보 조회
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 200
    data = response.json()

    assert data["user_id"] == "test_user"
    assert "username" in data
    assert "email" in data


def test_get_current_user_not_authenticated():
    """비인증 상태 사용자 정보 조회 테스트"""
    new_client = TestClient(app)
    response = new_client.get("/api/v1/auth/me")

    assert response.status_code == 401


def test_logout():
    """로그아웃 테스트"""
    # 로그인
    login_response = client.post(
        "/api/v1/auth/login",
        json={"user_id": "test_user", "password": "password123"},
    )
    assert login_response.status_code == 200

    # 로그아웃
    response = client.post("/api/v1/auth/logout")

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert "message" in data


def test_logout_not_authenticated():
    """비인증 상태 로그아웃 테스트"""
    new_client = TestClient(app)
    response = new_client.post("/api/v1/auth/logout")

    assert response.status_code == 401


def test_login_logout_flow():
    """로그인-로그아웃 전체 플로우 테스트"""
    test_client = TestClient(app)

    # 1. 초기 상태 확인
    session_response = test_client.get("/api/v1/auth/session")
    assert session_response.json()["authenticated"] is False

    # 2. 로그인
    login_response = test_client.post(
        "/api/v1/auth/login",
        json={"user_id": "test_user", "password": "password123"},
    )
    assert login_response.status_code == 200

    # 3. 인증 상태 확인
    session_response = test_client.get("/api/v1/auth/session")
    assert session_response.json()["authenticated"] is True

    # 4. 로그아웃
    logout_response = test_client.post("/api/v1/auth/logout")
    assert logout_response.status_code == 200

    # 5. 로그아웃 후 상태 확인
    session_response = test_client.get("/api/v1/auth/session")
    assert session_response.json()["authenticated"] is False

