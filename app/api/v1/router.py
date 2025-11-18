"""API v1 라우터 - ERDCloud 스키마 기반"""
from fastapi import APIRouter

from app.api.v1.routes import auth, users, vision, customer_service, ingredients, meals

api_router = APIRouter()

# 인증 관련 라우트
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])

# 사용자 관련 라우트
api_router.include_router(users.router, prefix="/user", tags=["users"])

# 음식 이미지 분석 라우트
api_router.include_router(vision.router, prefix="/food", tags=["vision"])

# 식재료 관련 라우트
api_router.include_router(ingredients.router, prefix="/ingredients", tags=["ingredients"])

# 음식 기록 및 건강 점수 라우트
api_router.include_router(meals.router, prefix="/meals", tags=["meals"])

# 고객센터 관련 라우트 (공지사항, 문의하기)
api_router.include_router(customer_service.router, tags=["customer-service"])

# TODO: 새로운 ERDCloud 기반 라우트 추가 예정
# - UserFoodHistory 라우트
# - health_score 라우트
# - HealthReport 라우트
# - UserPreferences 라우트
# - DiseaseAllergyProfile 라우트
