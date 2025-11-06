"""음식 이미지 분석 관련 라우트 테스트"""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_analyze_food_image_pizza():
    """피자 이미지 분석 테스트"""
    request_data = {
        "imageData": "base64_encoded_image_data",
        "fileName": "pizza.jpg",
        "fileSize": 1024,
        "fileType": "image/jpeg",
        "userId": "test_user",
    }

    response = client.post("/api/v1/food/analysis", json=request_data)

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert "data" in data
    assert "analysis" in data["data"]
    assert "timestamp" in data["data"]
    assert "processingTime" in data["data"]

    analysis = data["data"]["analysis"]
    assert analysis["foodName"] == "피자"
    assert "calories" in analysis
    assert "nutrients" in analysis
    assert "confidence" in analysis
    assert "suggestions" in analysis
    assert isinstance(analysis["suggestions"], list)


def test_analyze_food_image_salad():
    """샐러드 이미지 분석 테스트"""
    request_data = {
        "imageData": "base64_encoded_image_data",
        "fileName": "salad.jpg",
        "fileSize": 1024,
        "fileType": "image/jpeg",
    }

    response = client.post("/api/v1/food/analysis", json=request_data)

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    analysis = data["data"]["analysis"]
    assert analysis["foodName"] == "샐러드"
    assert analysis["calories"] < 500  # 샐러드는 칼로리가 낮음


def test_analyze_food_image_unknown():
    """알 수 없는 음식 이미지 분석 테스트"""
    request_data = {
        "imageData": "base64_encoded_image_data",
        "fileName": "unknown_food.jpg",
        "fileSize": 1024,
        "fileType": "image/jpeg",
    }

    response = client.post("/api/v1/food/analysis", json=request_data)

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    analysis = data["data"]["analysis"]
    assert analysis["foodName"] == "알 수 없는 음식"
    assert analysis["confidence"] < 0.7  # 알 수 없는 음식은 신뢰도가 낮음

