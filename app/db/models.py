"""데이터베이스 모델 정의 - ERDCloud 스키마 원본"""
from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, Date, DateTime, Enum, Integer, String, DECIMAL, BigInteger, Boolean, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class User(Base):
    """User 테이블 - ERDCloud 원본"""

    __tablename__ = "User"

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str] = mapped_column(String(100), nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    gender: Mapped[Optional[str]] = mapped_column(Enum('M', 'F', 'Other', name='gender_enum'), nullable=True)
    age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    weight: Mapped[Optional[float]] = mapped_column(DECIMAL(5, 2), nullable=True)
    health_goal: Mapped[str] = mapped_column(Enum('gain', 'maintain', 'loss', name='health_goal_enum'), nullable=False)
    nickname: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, server_default=func.current_timestamp())

    def __repr__(self) -> str:
        return f"<User(user_id={self.user_id}, nickname={self.nickname})>"


class Food(Base):
    """Food 테이블 - ERDCloud 원본"""

    __tablename__ = "Food"

    food_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    image_ref: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    food_class_1: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment='식품大분류명')
    food_class_2: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment='식품중분류 -> 음식 명칭')
    food_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    def __repr__(self) -> str:
        return f"<Food(food_id={self.food_id}, food_name={self.food_name})>"


class UserFoodHistory(Base):
    """UserFoodHistory 테이블 - ERDCloud 원본"""

    __tablename__ = "UserFoodHistory"

    history_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    food_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    consumed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    portion_size_g: Mapped[Optional[float]] = mapped_column(DECIMAL(10, 2), nullable=True)
    Field: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    food_name: Mapped[str] = mapped_column(String(200), nullable=False)

    def __repr__(self) -> str:
        return f"<UserFoodHistory(history_id={self.history_id}, user_id={self.user_id}, food_name={self.food_name})>"


class HealthScore(Base):
    """health_score 테이블 - ERDCloud 원본 (Untitled)"""

    __tablename__ = "health_score"

    history_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    food_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    reference_value: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment='영양성분함량기준량')
    kcal: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    positive_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment='SUM(권장영양소 9가지의 %값) / 9')
    negative_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment='SUM(제한영양소 3가지의 %값) / 3')
    final_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment='최종점수 = 권장영양소점수 - 제한영양소점수')
    food_grade: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment='영양 등급')
    calc_method: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment='계산 방식')

    def __repr__(self) -> str:
        return f"<HealthScore(history_id={self.history_id}, final_score={self.final_score})>"


class HealthReport(Base):
    """HealthReport 테이블 - ERDCloud 원본"""

    __tablename__ = "HealthReport"

    report_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    period_type: Mapped[Optional[str]] = mapped_column(Enum('daily', 'weekly', 'monthly', name='period_type_enum'), nullable=True)
    start_date: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)
    summary_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    generated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<HealthReport(report_id={self.report_id}, user_id={self.user_id}, period_type={self.period_type})>"


class UserPreferences(Base):
    """UserPreferences 테이블 - ERDCloud 원본"""

    __tablename__ = "UserPreferences"

    pref_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    preference_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    preference_value: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<UserPreferences(pref_id={self.pref_id}, user_id={self.user_id})>"


class DiseaseAllergyProfile(Base):
    """disease_allergy_profile 테이블 - ERDCloud 원본"""

    __tablename__ = "disease_allergy_profile"

    profile_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    allergy_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    disease_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    def __repr__(self) -> str:
        return f"<DiseaseAllergyProfile(profile_id={self.profile_id}, user_id={self.user_id})>"


class Announcement(Base):
    """공지사항 테이블"""

    __tablename__ = "Announcement"

    announcement_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False, comment='공지사항 제목')
    content: Mapped[str] = mapped_column(Text, nullable=False, comment='공지사항 내용')
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.current_timestamp(), comment='작성일')
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.current_timestamp(), onupdate=func.current_timestamp(), comment='수정일')
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, comment='활성 여부')
    view_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment='조회수')

    def __repr__(self) -> str:
        return f"<Announcement(announcement_id={self.announcement_id}, title={self.title})>"


class Inquiry(Base):
    """문의하기 테이블"""

    __tablename__ = "Inquiry"

    inquiry_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment='사용자 ID (필수)')
    nickname: Mapped[str] = mapped_column(String(50), nullable=False, comment='닉네임')
    email: Mapped[str] = mapped_column(String(100), nullable=False, comment='이메일')
    inquiry_type: Mapped[str] = mapped_column(String(50), nullable=False, comment='문의 유형')
    subject: Mapped[str] = mapped_column(String(200), nullable=False, comment='문의 제목')
    content: Mapped[str] = mapped_column(Text, nullable=False, comment='문의 내용')
    status: Mapped[str] = mapped_column(Enum('pending', 'in_progress', 'completed', name='inquiry_status_enum'), nullable=False, default='pending', comment='답변 상태')
    response: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment='답변 내용')
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.current_timestamp(), comment='문의 작성일')
    responded_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment='답변 완료일')

    def __repr__(self) -> str:
        return f"<Inquiry(inquiry_id={self.inquiry_id}, subject={self.subject}, status={self.status})>"
