"""사용자 기여 음식 테이블 모델"""
from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UserContributedFood(Base):
    """사용자 기여 음식 테이블 - 사용자가 추가한 음식 관리"""

    __tablename__ = "user_contributed_foods"

    # 기본 정보
    food_id: Mapped[str] = mapped_column(String(200), primary_key=True, comment='음식 ID (USER_{user_id}_{timestamp})')
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True, comment='기여한 사용자 ID')
    
    # 음식 정보
    food_name: Mapped[str] = mapped_column(String(200), nullable=False, comment='음식 이름')
    nutrient_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True, comment='영양소 DB 형식 이름')
    food_class1: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True, comment='대분류')
    food_class2: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, comment='중분류/재료')
    representative_food_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, comment='대표 음식명')
    
    # 재료 정보
    ingredients: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, comment='재료 목록 (JSON 또는 콤마 구분)')
    
    # 기준량
    unit: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment='단위')
    reference_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment='영양성분함량기준량 (g)')
    
    # 주요 영양소
    kcal: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment='칼로리 (kcal)')
    protein: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment='단백질 (g)')
    carb: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment='탄수화물 (g)')
    fat: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment='지방 (g)')
    fiber: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment='식이섬유 (g)')
    
    # 비타민
    vitamin_a: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment='비타민 A (μg)')
    vitamin_c: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment='비타민 C (mg)')
    
    # 미네랄
    calcium: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment='칼슘 (mg)')
    iron: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment='철분 (mg)')
    potassium: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment='칼륨 (mg)')
    magnesium: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment='마그네슘 (mg)')
    
    # 제한 영양소
    saturated_fat: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment='포화지방 (g)')
    added_sugar: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment='첨가당 (g)')
    sodium: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment='나트륨 (mg)')
    
    # 관심 영양소
    cholesterol: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment='콜레스테롤 (mg)')
    trans_fat: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment='트랜스지방 (g)')
    
    # 메타데이터
    usage_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1, comment='사용 횟수')
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.current_timestamp(), comment='생성일시')
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.current_timestamp(), onupdate=func.current_timestamp(), comment='수정일시')
    
    # 승인 상태 (향후 관리자 승인 기능용)
    is_approved: Mapped[bool] = mapped_column(nullable=False, default=False, comment='관리자 승인 여부')
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment='승인일시')

    def __repr__(self) -> str:
        return f"<UserContributedFood(food_id={self.food_id}, food_name={self.food_name}, usage_count={self.usage_count})>"

