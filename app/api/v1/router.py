"""API v1 라우터 - ERDCloud 스키마 기반"""
from fastapi import APIRouter

from app.api.v1.routes import auth, users, vision

api_router = APIRouter()

# 인증 관련 라우트
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])

# 사용자 관련 라우트
api_router.include_router(users.router, prefix="/user", tags=["users"])

# 음식 이미지 분석 라우트
api_router.include_router(vision.router, prefix="/food", tags=["vision"])

# TODO: 새로운 ERDCloud 기반 라우트 추가 예정
# - UserFoodHistory 라우트
# - health_score 라우트
# - HealthReport 라우트
# - UserPreferences 라우트
# - DiseaseAllergyProfile 라우트
