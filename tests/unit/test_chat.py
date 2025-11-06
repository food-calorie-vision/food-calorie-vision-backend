"""챗봇 관련 라우트 테스트"""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_chat_greeting():
    """챗봇 인사 테스트"""
    request_data = {"message": "안녕하세요", "userId": "test_user"}

    response = client.post("/api/v1/chat", json=request_data)

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert "data" in data
    assert "message" in data["data"]
    assert "안녕하세요" in data["data"]["message"]


def test_chat_calorie_question():
    """칼로리 질문 테스트"""
    selected_meal = {
        "name": "연어 덮밥",
        "calories": 450,
        "nutrients": {"protein": 35, "carbs": 45, "fat": 12, "sodium": 800},
    }

    request_data = {"message": "칼로리가 궁금해요", "selectedMeal": selected_meal, "userId": "test_user"}

    response = client.post("/api/v1/chat", json=request_data)

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert "450" in data["data"]["message"]
    assert "연어 덮밥" in data["data"]["message"]


def test_chat_recipe_question():
    """레시피 질문 테스트"""
    selected_meal = {"name": "연어 덮밥"}

    request_data = {"message": "레시피를 알려주세요", "selectedMeal": selected_meal, "userId": "test_user"}

    response = client.post("/api/v1/chat", json=request_data)

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert "레시피" in data["data"]["message"]


def test_chat_without_selected_meal():
    """식단 선택 없이 챗봇 테스트"""
    request_data = {"message": "영양 정보가 궁금해요"}

    response = client.post("/api/v1/chat", json=request_data)

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert "message" in data["data"]

