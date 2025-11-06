"""식단 관련 라우트 테스트"""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_get_meal_recommendations():
    """식단 추천 조회 테스트"""
    response = client.get("/api/v1/meals/recommendations")

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert "data" in data
    assert "recommendations" in data["data"]
    assert isinstance(data["data"]["recommendations"], list)
    assert len(data["data"]["recommendations"]) > 0

    # 첫 번째 추천 식단 검증
    first_meal = data["data"]["recommendations"][0]
    assert "id" in first_meal
    assert "name" in first_meal
    assert "calories" in first_meal
    assert "description" in first_meal
    assert "isSelected" in first_meal


def test_select_meal():
    """식단 선택 테스트"""
    request_data = {"mealId": 1, "userId": "test_user"}

    response = client.post("/api/v1/meals/selection", json=request_data)

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert "data" in data
    assert data["data"]["success"] is True
    assert "message" in data["data"]
    assert "selectedMeal" in data["data"]

    selected_meal = data["data"]["selectedMeal"]
    assert selected_meal["id"] == 1
    assert "name" in selected_meal
    assert "calories" in selected_meal


def test_select_meal_invalid_id():
    """존재하지 않는 식단 선택 테스트"""
    request_data = {"mealId": 9999, "userId": "test_user"}

    response = client.post("/api/v1/meals/selection", json=request_data)

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is False
    assert "error" in data

