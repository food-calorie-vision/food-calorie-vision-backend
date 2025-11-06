"""데이터베이스 모델 정의"""
from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class User(Base):
    """사용자 테이블"""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(100), nullable=False)
    nickname: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    gender: Mapped[str] = mapped_column(String(10), nullable=False)  # '남자' or '여자'
    birth_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<User(id={self.id}, user_id={self.user_id}, nickname={self.nickname})>"


class UserHealthInfo(Base):
    """사용자 건강 정보 테이블"""

    __tablename__ = "user_health_info"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)  # User.id 참조
    goal: Mapped[str] = mapped_column(Text, nullable=False)  # 건강 목표
    body_type: Mapped[str] = mapped_column(String(20), nullable=False)  # '감량', '유지', '증량'
    activity_level: Mapped[str] = mapped_column(String(50), nullable=False)  # 활동량
    recommended_calories: Mapped[float] = mapped_column(Float, nullable=False)  # 권장 칼로리
    has_allergy: Mapped[bool] = mapped_column(Boolean, default=False)
    allergy_info: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 알레르기 정보
    medical_condition: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 질병 정보
    allergies: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # JSON 배열
    diseases: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # JSON 배열
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<UserHealthInfo(id={self.id}, user_id={self.user_id}, body_type={self.body_type})>"


# Food 테이블은 다른 팀원이 DB 서버에 이미 생성함 (CSV import 중)
# 필요시 나중에 읽기 전용으로 매핑 가능


class MealRecord(Base):
    """식사 기록 테이블"""

    __tablename__ = "meal_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)  # User.id 참조
    food_id: Mapped[int] = mapped_column(Integer, nullable=False)  # 팀원이 만든 Food 테이블의 ID 참조
    meal_type: Mapped[str] = mapped_column(String(20), nullable=False)  # '아침', '점심', '저녁', '간식'
    meal_date: Mapped[datetime] = mapped_column(Date, nullable=False, index=True)
    meal_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    portion: Mapped[float] = mapped_column(Float, default=1.0)  # 섭취량 (1.0 = 1인분)
    total_calories: Mapped[float] = mapped_column(Float, nullable=False)  # 총 칼로리
    image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # 음식 사진 URL
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 메모
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    def __repr__(self) -> str:
        return f"<MealRecord(id={self.id}, user_id={self.user_id}, meal_date={self.meal_date})>"


class DailyScore(Base):
    """일일 식단 점수 테이블"""

    __tablename__ = "daily_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)  # User.id 참조
    score_date: Mapped[datetime] = mapped_column(Date, nullable=False, index=True)
    score: Mapped[float] = mapped_column(Float, nullable=False)  # 0-100 점수
    total_calories: Mapped[float] = mapped_column(Float, nullable=False)
    target_calories: Mapped[float] = mapped_column(Float, nullable=False)
    total_protein: Mapped[float] = mapped_column(Float, default=0.0)
    total_carbs: Mapped[float] = mapped_column(Float, default=0.0)
    total_fat: Mapped[float] = mapped_column(Float, default=0.0)
    total_sodium: Mapped[float] = mapped_column(Float, default=0.0)
    total_sugar: Mapped[float] = mapped_column(Float, default=0.0)
    feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 피드백 메시지
    improvement: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 개선 제안
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    def __repr__(self) -> str:
        return f"<DailyScore(id={self.id}, user_id={self.user_id}, score={self.score})>"


class FoodAnalysis(Base):
    """음식 이미지 분석 결과 테이블"""

    __tablename__ = "food_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)  # User.id 참조
    image_url: Mapped[str] = mapped_column(String(500), nullable=False)
    food_name: Mapped[str] = mapped_column(String(200), nullable=False)
    calories: Mapped[float] = mapped_column(Float, nullable=False)
    protein: Mapped[float] = mapped_column(Float, default=0.0)
    carbs: Mapped[float] = mapped_column(Float, default=0.0)
    fat: Mapped[float] = mapped_column(Float, default=0.0)
    sodium: Mapped[float] = mapped_column(Float, default=0.0)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)  # 신뢰도 (0-1)
    suggestions: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # 제안 사항 (JSON 배열)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    def __repr__(self) -> str:
        return f"<FoodAnalysis(id={self.id}, food_name={self.food_name}, confidence={self.confidence})>"


class ChatMessage(Base):
    """챗봇 대화 기록 테이블"""

    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)  # User.id 참조
    message_type: Mapped[str] = mapped_column(String(10), nullable=False)  # 'user' or 'bot'
    content: Mapped[str] = mapped_column(Text, nullable=False)
    image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    def __repr__(self) -> str:
        return f"<ChatMessage(id={self.id}, user_id={self.user_id}, type={self.message_type})>"


class MealRecommendation(Base):
    """식단 추천 테이블"""

    __tablename__ = "meal_recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)  # User.id 참조
    food_id: Mapped[int] = mapped_column(Integer, nullable=False)  # 팀원이 만든 Food 테이블의 ID 참조
    recommendation_date: Mapped[datetime] = mapped_column(Date, nullable=False, index=True)
    meal_type: Mapped[str] = mapped_column(String(20), nullable=False)  # '아침', '점심', '저녁'
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 추천 이유
    is_selected: Mapped[bool] = mapped_column(Boolean, default=False)  # 사용자가 선택했는지
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    def __repr__(self) -> str:
        return f"<MealRecommendation(id={self.id}, user_id={self.user_id}, food_id={self.food_id})>"
<<<<<<< HEAD
=======

>>>>>>> 0fc06cfb80a7627348b1a0ff9669bdb9cf8eb34b
