"""food_nutrients 테이블 모델 (기존 데이터 활용)"""
from typing import Optional

from sqlalchemy import Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class FoodNutrient(Base):
    """food_nutrients 테이블 - 기존 영양소 데이터"""

    __tablename__ = "food_nutrients"

    food_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    nutrient_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    food_class1: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    food_class2: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    unit: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    reference_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 영양성분함량기준 (g)
    
    # 주요 영양소
    protein: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    fiber: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    vitamin_a: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    vitamin_c: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    vitamin_e: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    calcium: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    iron: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    potassium: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    magnesium: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # 제한 영양소
    saturated_fat: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    added_sugar: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sodium: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # 관심 영양소
    cholesterol: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    trans_fat: Mapped[Optional[float]] = mapped_column(Float, nullable=True, name="trans_Fat")
    
    # 기타
    carb: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    fat: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    def __repr__(self) -> str:
        return f"<FoodNutrient(food_id={self.food_id}, nutrient_name={self.nutrient_name})>"

