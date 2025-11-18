"""Food 테이블 관련 서비스"""
import hashlib
import json
from typing import Optional
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Food


def generate_food_id(food_name: str, ingredients: list[str] = None) -> str:
    """
    음식명과 재료를 기반으로 고유한 food_id 생성
    
    Args:
        food_name: 음식 이름
        ingredients: 재료 리스트
        
    Returns:
        생성된 food_id (예: "pizza_tomato_cheese_abc123")
    """
    ingredients = ingredients or []
    
    # 음식명 + 재료를 조합하여 해시 생성
    ingredients_str = "_".join(sorted(ingredients)) if ingredients else ""
    combined = f"{food_name}_{ingredients_str}"
    
    # SHA256 해시의 앞 8자리 사용
    hash_suffix = hashlib.sha256(combined.encode()).hexdigest()[:8]
    
    # 음식명을 영문으로 변환 (간단한 처리)
    # 실제로는 더 정교한 변환이 필요할 수 있음
    food_id = f"{food_name}_{hash_suffix}"
    
    # 최대 200자 제한
    return food_id[:200]


async def get_or_create_food(
    session: AsyncSession,
    food_id: str,
    food_name: str,
    food_class_1: Optional[str] = None,
    food_class_2: Optional[str] = None,
    ingredients: list[str] = None,
    image_ref: Optional[str] = None,
    category: Optional[str] = None,
) -> Food:
    """
    Food 테이블에서 음식을 조회하거나 없으면 생성
    
    Args:
        session: DB 세션
        food_id: 음식 ID (food_nutrients의 food_id 사용)
        food_name: 음식 이름
        food_class_1: 대분류 (예: "피자", "국밥")
        food_class_2: 중분류 (예: "페퍼로니", "돼지머리")
        ingredients: 재료 리스트
        image_ref: 이미지 참조
        category: 카테고리
        
    Returns:
        Food 객체
    """
    ingredients = ingredients or []
    
    # 기존 음식 조회
    stmt = select(Food).where(Food.food_id == food_id)
    result = await session.execute(stmt)
    existing_food = result.scalar_one_or_none()
    
    if existing_food:
        print(f"✅ 기존 Food 발견: {food_id}")
        return existing_food
    
    # 새로운 음식 생성
    print(f"🆕 새로운 Food 생성: {food_id}")
    
    # ingredients를 JSON 문자열로 변환
    ingredients_json = json.dumps(ingredients, ensure_ascii=False) if ingredients else None
    
    new_food = Food(
        food_id=food_id,
        food_name=food_name,
        food_class_1=food_class_1,
        food_class_2=food_class_2,
        image_ref=image_ref,
        category=category,
        ingredients=ingredients_json,
    )
    
    session.add(new_food)
    await session.flush()
    
    return new_food


async def get_food_by_id(
    session: AsyncSession,
    food_id: str
) -> Optional[Food]:
    """
    food_id로 음식 조회
    
    Args:
        session: DB 세션
        food_id: 음식 ID
        
    Returns:
        Food 객체 또는 None
    """
    stmt = select(Food).where(Food.food_id == food_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def search_foods_by_name(
    session: AsyncSession,
    food_name: str,
    limit: int = 10
) -> list[Food]:
    """
    음식 이름으로 검색
    
    Args:
        session: DB 세션
        food_name: 검색할 음식 이름
        limit: 최대 결과 개수
        
    Returns:
        Food 리스트
    """
    stmt = select(Food).where(
        Food.food_name.like(f"%{food_name}%")
    ).limit(limit)
    
    result = await session.execute(stmt)
    return list(result.scalars().all())

