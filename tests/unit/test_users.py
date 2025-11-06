"""사용자 관련 라우트 테스트"""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_get_user_intake_data():
    """사용자 섭취 현황 조회 테스트"""
    response = client.get("/api/v1/user/intake-data")

    assert response.status_code == 200
    data = response.json()

    assert "totalCalories" in data
    assert "targetCalories" in data
    assert "nutrients" in data

    nutrients = data["nutrients"]
    assert "sodium" in nutrients
    assert "carbs" in nutrients
    assert "protein" in nutrients
    assert "fat" in nutrients
    assert "sugar" in nutrients


def test_get_user_health_info():
    """사용자 건강 정보 조회 테스트"""
    response = client.get("/api/v1/user/health-info")

    assert response.status_code == 200
    data = response.json()

    assert "goal" in data
    assert "diseases" in data
    assert "recommendedCalories" in data
    assert "activityLevel" in data
    assert isinstance(data["diseases"], list)

