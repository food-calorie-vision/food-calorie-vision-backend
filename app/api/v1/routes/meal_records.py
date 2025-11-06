"""식사 기록 API"""
from typing import Optional
from datetime import date, datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.api.v1.schemas.meal import (
    MealRecordCreateRequest,
    MealRecordResponse,
    MealRecordListResponse,
    DailyMealSummary,
    FoodAnalysisItem,
)
from app.services import meal_service, health_service
from app.utils.session import get_current_user_id

router = APIRouter()


@router.post("", response_model=MealRecordResponse)
async def create_meal_record(
    meal_data: MealRecordCreateRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> MealRecordResponse:
    """
    식사 기록 생성
    
    음식 이미지 분석 결과를 바탕으로 식사 기록을 생성합니다.
    """
    user_id = get_current_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")
    
    # 총 영양소 계산
    total_calories = sum(food.calories for food in meal_data.foods)
    total_protein = sum(food.protein for food in meal_data.foods)
    total_carbs = sum(food.carbs for food in meal_data.foods)
    total_fat = sum(food.fat for food in meal_data.foods)
    
    # 식사 기록 생성
    meal_record = await meal_service.create_meal_record(
        session=session,
        user_id=user_id,
        meal_type=meal_data.meal_type,
        image_url=meal_data.image_url,
        total_calories=total_calories,
        total_protein=total_protein,
        total_carbs=total_carbs,
        total_fat=total_fat,
        memo=meal_data.memo,
    )
    
    # 음식 분석 결과 저장
    food_analyses = []
    for food in meal_data.foods:
        food_analysis = await meal_service.create_food_analysis(
            session=session,
            record_id=meal_record.record_id,
            food_id=food.food_id,
            food_name=food.food_name,
            quantity=food.quantity,
            calories=food.calories,
            protein=food.protein,
            carbs=food.carbs,
            fat=food.fat,
        )
        food_analyses.append(
            FoodAnalysisItem(
                food_id=food_analysis.food_id,
                food_name=food_analysis.food_name,
                quantity=food_analysis.quantity,
                calories=food_analysis.calories,
                protein=food_analysis.protein,
                carbs=food_analysis.carbs,
                fat=food_analysis.fat,
            )
        )
    
    return MealRecordResponse(
        record_id=meal_record.record_id,
        user_id=meal_record.user_id,
        meal_type=meal_record.meal_type,
        meal_date=meal_record.meal_date,
        image_url=meal_record.image_url,
        total_calories=meal_record.total_calories,
        total_protein=meal_record.total_protein,
        total_carbs=meal_record.total_carbs,
        total_fat=meal_record.total_fat,
        memo=meal_record.memo,
        foods=food_analyses,
    )


@router.get("", response_model=MealRecordListResponse)
async def get_meal_records(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> MealRecordListResponse:
    """
    식사 기록 조회
    
    현재 로그인한 사용자의 식사 기록을 최신순으로 조회합니다.
    """
    user_id = get_current_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")
    
    meal_records = await meal_service.get_meal_records_by_user(
        session=session,
        user_id=user_id,
        skip=skip,
        limit=limit,
    )
    
    # 각 식사 기록의 음식 정보 가져오기
    records_with_foods = []
    for record in meal_records:
        food_analyses = await meal_service.get_food_analyses_by_record(
            session=session,
            record_id=record.record_id,
        )
        
        foods = [
            FoodAnalysisItem(
                food_id=food.food_id,
                food_name=food.food_name,
                quantity=food.quantity,
                calories=food.calories,
                protein=food.protein,
                carbs=food.carbs,
                fat=food.fat,
            )
            for food in food_analyses
        ]
        
        records_with_foods.append(
            MealRecordResponse(
                record_id=record.record_id,
                user_id=record.user_id,
                meal_type=record.meal_type,
                meal_date=record.meal_date,
                image_url=record.image_url,
                total_calories=record.total_calories,
                total_protein=record.total_protein,
                total_carbs=record.total_carbs,
                total_fat=record.total_fat,
                memo=record.memo,
                foods=foods,
            )
        )
    
    return MealRecordListResponse(
        total=len(records_with_foods),
        records=records_with_foods,
    )


@router.get("/daily-summary", response_model=DailyMealSummary)
async def get_daily_summary(
    request: Request,
    target_date: Optional[str] = Query(None, description="조회 날짜 (YYYY-MM-DD)"),
    session: AsyncSession = Depends(get_session),
) -> DailyMealSummary:
    """
    일일 식사 요약 조회
    
    특정 날짜의 식사 기록을 요약하여 반환합니다.
    """
    user_id = get_current_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")
    
    # 날짜 파싱 (기본값: 오늘)
    if target_date:
        try:
            query_date = datetime.strptime(target_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="날짜 형식이 올바르지 않습니다. (YYYY-MM-DD)")
    else:
        query_date = date.today()
    
    # 일일 요약 계산
    summary = await meal_service.get_daily_summary(
        session=session,
        user_id=user_id,
        target_date=query_date,
    )
    
    # 사용자의 권장 칼로리 조회
    health_info = await health_service.get_user_health_info(session, user_id)
    recommended_calories = health_info.recommended_calories if health_info else 2000
    
    calories_remaining = recommended_calories - summary["total_calories"]
    
    return DailyMealSummary(
        date=summary["date"],
        total_calories=summary["total_calories"],
        total_protein=summary["total_protein"],
        total_carbs=summary["total_carbs"],
        total_fat=summary["total_fat"],
        meal_count=summary["meal_count"],
        recommended_calories=recommended_calories,
        calories_remaining=calories_remaining,
    )


@router.get("/weekly-calories", response_model=list)
async def get_weekly_calories(
    request: Request,
    days: int = Query(7, ge=1, le=30, description="조회할 일수"),
    session: AsyncSession = Depends(get_session),
) -> list:
    """
    최근 N일간의 일일 칼로리 데이터 조회
    
    차트 표시용으로 사용됩니다.
    """
    user_id = get_current_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")
    
    # 오늘부터 N일 전까지의 데이터 생성
    today = date.today()
    weekly_data = []
    
    for i in range(days - 1, -1, -1):  # 과거부터 오늘까지
        target_date = today - timedelta(days=i)
        
        # 해당 날짜의 식사 기록 조회
        summary = await meal_service.get_daily_summary(
            session=session,
            user_id=user_id,
            target_date=target_date,
        )
        
        # 날짜 형식: MM-DD
        date_str = target_date.strftime("%m-%d")
        
        weekly_data.append({
            "date": date_str,
            "calories": summary["total_calories"],
        })
    
    return weekly_data


@router.get("/frequent-foods", response_model=list)
async def get_frequent_foods(
    request: Request,
    limit: int = Query(5, ge=1, le=10, description="조회할 음식 개수"),
    session: AsyncSession = Depends(get_session),
) -> list:
    """
    자주 먹는 음식 TOP N 조회
    
    사용자의 식사 기록에서 가장 자주 먹은 음식을 반환합니다.
    """
    user_id = get_current_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")
    
    frequent_foods = await meal_service.get_frequent_foods(
        session=session,
        user_id=user_id,
        limit=limit,
    )
    
    return frequent_foods

