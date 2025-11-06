"""식사 기록 관련 서비스"""
from typing import List, Optional
from datetime import date, datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from app.db.models import MealRecord, FoodAnalysis


async def create_meal_record(
    session: AsyncSession,
    user_id: str,
    meal_type: str,
    image_url: str,
    total_calories: float,
    total_protein: float,
    total_carbs: float,
    total_fat: float,
    memo: Optional[str] = None,
) -> MealRecord:
    """식사 기록 생성"""
    meal_record = MealRecord(
        user_id=user_id,
        meal_type=meal_type,
        meal_date=datetime.now(),
        image_url=image_url,
        total_calories=total_calories,
        total_protein=total_protein,
        total_carbs=total_carbs,
        total_fat=total_fat,
        memo=memo,
    )
    
    session.add(meal_record)
    await session.commit()
    await session.refresh(meal_record)
    
    return meal_record


async def create_food_analysis(
    session: AsyncSession,
    record_id: int,
    food_id: int,
    food_name: str,
    quantity: float,
    calories: float,
    protein: float,
    carbs: float,
    fat: float,
) -> FoodAnalysis:
    """음식 분석 결과 생성"""
    food_analysis = FoodAnalysis(
        record_id=record_id,
        food_id=food_id,
        food_name=food_name,
        quantity=quantity,
        calories=calories,
        protein=protein,
        carbs=carbs,
        fat=fat,
    )
    
    session.add(food_analysis)
    await session.commit()
    await session.refresh(food_analysis)
    
    return food_analysis


async def get_meal_records_by_user(
    session: AsyncSession,
    user_id: str,
    skip: int = 0,
    limit: int = 100,
) -> List[MealRecord]:
    """사용자의 식사 기록 조회"""
    result = await session.execute(
        select(MealRecord)
        .where(MealRecord.user_id == user_id)
        .order_by(MealRecord.meal_date.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_meal_records_by_date(
    session: AsyncSession,
    user_id: str,
    target_date: date,
) -> List[MealRecord]:
    """특정 날짜의 식사 기록 조회"""
    start_datetime = datetime.combine(target_date, datetime.min.time())
    end_datetime = datetime.combine(target_date, datetime.max.time())
    
    result = await session.execute(
        select(MealRecord)
        .where(
            and_(
                MealRecord.user_id == user_id,
                MealRecord.meal_date >= start_datetime,
                MealRecord.meal_date <= end_datetime,
            )
        )
        .order_by(MealRecord.meal_date.asc())
    )
    return list(result.scalars().all())


async def get_food_analyses_by_record(
    session: AsyncSession,
    record_id: int,
) -> List[FoodAnalysis]:
    """식사 기록의 음식 분석 결과 조회"""
    result = await session.execute(
        select(FoodAnalysis)
        .where(FoodAnalysis.record_id == record_id)
        .order_by(FoodAnalysis.analysis_id.asc())
    )
    return list(result.scalars().all())


async def get_daily_summary(
    session: AsyncSession,
    user_id: str,
    target_date: date,
) -> dict:
    """일일 식사 요약 계산"""
    meal_records = await get_meal_records_by_date(session, user_id, target_date)
    
    total_calories = sum(record.total_calories for record in meal_records)
    total_protein = sum(record.total_protein for record in meal_records)
    total_carbs = sum(record.total_carbs for record in meal_records)
    total_fat = sum(record.total_fat for record in meal_records)
    
    return {
        "date": target_date.isoformat(),
        "total_calories": total_calories,
        "total_protein": total_protein,
        "total_carbs": total_carbs,
        "total_fat": total_fat,
        "meal_count": len(meal_records),
    }


async def get_frequent_foods(
    session: AsyncSession,
    user_id: str,
    limit: int = 5,
) -> List[dict]:
    """자주 먹는 음식 TOP N 조회"""
    # 모든 식사 기록에서 음식 분석 데이터 가져오기
    meal_records = await get_meal_records_by_user(session, user_id, skip=0, limit=1000)
    
    # 음식별 빈도수와 영양소 정보 집계
    food_frequency = {}
    
    for record in meal_records:
        food_analyses = await get_food_analyses_by_record(session, record.record_id)
        
        for food in food_analyses:
            food_name = food.food_name
            
            if food_name not in food_frequency:
                food_frequency[food_name] = {
                    "name": food_name,
                    "count": 0,
                    "total_calories": 0,
                    "total_protein": 0,
                    "total_carbs": 0,
                    "total_fat": 0,
                }
            
            food_frequency[food_name]["count"] += 1
            food_frequency[food_name]["total_calories"] += food.calories
            food_frequency[food_name]["total_protein"] += food.protein
            food_frequency[food_name]["total_carbs"] += food.carbs
            food_frequency[food_name]["total_fat"] += food.fat
    
    # 빈도수 기준 정렬
    sorted_foods = sorted(
        food_frequency.values(),
        key=lambda x: x["count"],
        reverse=True
    )[:limit]
    
    # 평균 영양소 계산
    result = []
    for idx, food in enumerate(sorted_foods, 1):
        count = food["count"]
        result.append({
            "id": idx,
            "name": food["name"],
            "calories": round(food["total_calories"] / count, 1),
            "nutrients": {
                "carbs": round(food["total_carbs"] / count, 1),
                "protein": round(food["total_protein"] / count, 1),
                "fat": round(food["total_fat"] / count, 1),
            },
            "frequency": count,
        })
    
    return result

