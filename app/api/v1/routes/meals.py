"""음식 기록 및 건강 점수 관리 API"""
from datetime import datetime, date, timedelta
from functools import lru_cache
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from langchain.schema import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.api.v1.schemas.common import ApiResponse
from app.api.dependencies import require_authentication
from app.core.config import get_settings
from app.db.models import UserFoodHistory, HealthScore, User, Food, UserIngredient
from app.db.models_food_nutrients import FoodNutrient
from app.db.models_user_contributed import UserContributedFood
from app.db.session import get_session
from app.services.health_score_service import (
    create_health_score,
    calculate_korean_nutrition_score,
    calculate_nrf93_score,
    get_user_health_scores,
    calculate_daily_comprehensive_score
)
from app.services.user_service import calculate_daily_calories

router = APIRouter()
settings = get_settings()


@lru_cache
def get_nutrition_llm() -> ChatOpenAI:
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY 환경 변수가 필요합니다.")
    return ChatOpenAI(
        api_key=settings.openai_api_key,
        model="gpt-4o-mini",
        temperature=0.3,
    )


# ========== Request/Response 스키마 ==========

class FoodItem(BaseModel):
    """음식 아이템"""
    food_id: str = Field(..., description="음식 ID (food_nutrients 테이블)")
    food_name: str = Field(..., description="음식 이름")
    portion_size_g: float = Field(..., description="섭취량 (g)")
    calories: int = Field(..., description="칼로리")
    protein: float = Field(0.0, description="단백질 (g)")
    carbs: float = Field(0.0, description="탄수화물 (g)")
    fat: float = Field(0.0, description="지방 (g)")
    sodium: float = Field(0.0, description="나트륨 (mg)")
    fiber: Optional[float] = Field(0.0, description="식이섬유 (g)")


class SaveMealRequest(BaseModel):
    """음식 기록 저장 요청"""
    meal_type: str = Field(..., description="식사 유형: 아침/점심/저녁/간식")
    foods: List[FoodItem] = Field(..., description="음식 목록")
    memo: Optional[str] = Field(None, description="메모")
    image_url: Optional[str] = Field(None, description="음식 사진 URL")


class IngredientUsage(BaseModel):
    """사용한 재료와 수량"""
    name: str = Field(..., description="재료 이름")
    quantity: int = Field(1, description="사용한 수량")


class SaveRecommendedMealRequest(BaseModel):
    """추천 음식 선택 및 저장 요청"""
    food_name: str = Field(..., description="선택한 음식 이름")
    ingredients_used: List[str] = Field(..., description="사용된 식재료 목록 (레거시)")
    ingredients_with_quantity: Optional[List[IngredientUsage]] = Field(None, description="재료와 수량")
    meal_type: str = Field("점심", description="식사 유형: 아침/점심/저녁/간식")
    portion_size_g: float = Field(300.0, description="예상 섭취량 (g)")
    memo: Optional[str] = Field(None, description="메모")


class MealRecordResponse(BaseModel):
    """음식 기록 응답"""
    history_id: int
    user_id: int
    food_id: str
    food_name: str
    consumed_at: datetime
    portion_size_g: float
    calories: int
    health_score: Optional[int] = None
    food_grade: Optional[str] = None
    meal_type: Optional[str] = None  # 식사 유형 추가


class DashboardStatsResponse(BaseModel):
    """대시보드 통계 응답"""
    total_calories_today: int = Field(..., description="오늘 총 칼로리")
    total_calories_week: int = Field(..., description="이번 주 총 칼로리")
    avg_health_score: float = Field(..., description="오늘 평균 건강 점수")
    today_score_feedback: Optional[str] = Field(None, description="오늘 점수 피드백 메시지")  # ✨ 추가됨
    previous_day_score: Optional[float] = Field(None, description="전날 평균 건강 점수")
    score_change: Optional[float] = Field(None, description="전날 대비 점수 변화")
    frequent_foods: List[dict] = Field(..., description="자주 먹는 음식 Top 5")
    daily_calories: List[dict] = Field(..., description="일일 칼로리 (최근 7일)")
    nutrition_balance: dict = Field(..., description="영양소 밸런스")


class CategoryScore(BaseModel):
    """카테고리별 점수"""
    name: str = Field(..., description="카테고리 이름")
    score: float = Field(..., description="점수")
    max_score: float = Field(100.0, description="최대 점수")
    trend: str = Field(..., description="트렌드: up, down, same")
    feedback: str = Field(..., description="피드백 메시지")


class ScoreDetailResponse(BaseModel):
    """상세 점수 현황 응답"""
    overall_score: float = Field(..., description="전체 점수")
    quality_score: Optional[float] = Field(None, description="식단 품질 점수 (평균 HealthScore)")  # ✨ 추가
    quantity_score: Optional[float] = Field(None, description="양적 달성도 점수 (0~100 환산)")  # ✨ 추가
    calorie_ratio: Optional[float] = Field(None, description="목표 대비 칼로리 비율 (%)")  # ✨ 추가
    previous_score: Optional[float] = Field(None, description="전날 점수")
    score_change: Optional[float] = Field(None, description="점수 변화")
    categories: List[CategoryScore] = Field(..., description="카테고리별 점수")
    weekly_trend: List[dict] = Field(..., description="주간 트렌드")


class MostEatenFood(BaseModel):
    """자주 먹은 음식"""
    food_id: str = Field(..., description="음식 ID")
    food_name: str = Field(..., description="음식 이름")
    eat_count: int = Field(..., description="먹은 횟수")


# ========== API 엔드포인트 ==========

@router.post("/save", response_model=ApiResponse[List[MealRecordResponse]])
async def save_meal_records(
    request: SaveMealRequest,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(require_authentication)
) -> ApiResponse[List[MealRecordResponse]]:
    """
    음식 기록 저장 + 건강 점수 자동 계산
    
    1. UserFoodHistory에 음식 기록 저장
    2. FoodNutrient에서 영양소 정보 조회
    3. HealthScore 자동 계산 및 저장
    
    **Args:**
        request: 음식 기록 정보
        session: DB 세션
        
    **Returns:**
        저장된 음식 기록 + 건강 점수
    """
    try:
        saved_records = []
        
        for food_item in request.foods:
            # 1. UserFoodHistory 저장
            history = UserFoodHistory(
                user_id=user_id,
                food_id=food_item.food_id,
                food_name=food_item.food_name,
                consumed_at=datetime.now(),
                portion_size_g=food_item.portion_size_g
                # memo=request.memo  # 임시로 제거 (DB에 memo 컬럼 없음)
            )
            session.add(history)
            await session.flush()  # history_id 생성
            await session.refresh(history)
            
            # 2. FoodNutrient에서 영양소 정보 조회
            nutrient_stmt = select(FoodNutrient).where(
                FoodNutrient.food_id == food_item.food_id
            )
            nutrient_result = await session.execute(nutrient_stmt)
            nutrient = nutrient_result.scalar_one_or_none()
            
            # 3. 건강 점수 계산
            health_score_data = None
            if nutrient:
                # 한국식 영양 점수 계산
                score_result = await calculate_korean_nutrition_score(
                    protein=nutrient.protein or 0,
                    fiber=nutrient.fiber or 0,
                    calcium=nutrient.calcium or 0,
                    iron=nutrient.iron or 0,
                    sodium=nutrient.sodium or 0,
                    sugar=nutrient.added_sugar or 0,
                    saturated_fat=nutrient.saturated_fat or 0
                )
                
                # 4. HealthScore 저장
                health_score_obj = await create_health_score(
                    session=session,
                    history_id=history.history_id,
                    user_id=user_id,
                    food_id=food_item.food_id,
                    reference_value=int(nutrient.reference_value) if nutrient.reference_value else None,
                    kcal=food_item.calories,
                    positive_score=score_result["positive_score"],
                    negative_score=score_result["negative_score"],
                    final_score=score_result["final_score"],
                    food_grade=score_result["food_grade"],
                    calc_method=score_result["calc_method"]
                )
                
                health_score_data = {
                    "final_score": health_score_obj.final_score,
                    "food_grade": health_score_obj.food_grade
                }
            
            saved_records.append(MealRecordResponse(
                history_id=history.history_id,
                user_id=history.user_id,
                food_id=history.food_id,
                food_name=history.food_name,
                consumed_at=history.consumed_at,
                portion_size_g=history.portion_size_g,
                calories=food_item.calories,
                health_score=health_score_data["final_score"] if health_score_data else None,
                food_grade=health_score_data["food_grade"] if health_score_data else None
            ))
        
        await session.commit()
        
        return ApiResponse(
            success=True,
            data=saved_records,
            message=f"✅ {len(saved_records)}개의 음식이 기록되었습니다!"
        )
        
    except Exception as e:
        await session.rollback()
        print(f"❌ 음식 기록 저장 실패: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"음식 기록 저장 중 오류 발생: {str(e)}")


@router.get("/dashboard-stats", response_model=ApiResponse[DashboardStatsResponse])
async def get_dashboard_stats(
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(require_authentication)
) -> ApiResponse[DashboardStatsResponse]:
    """
    대시보드 통계 조회
    
    - 오늘/이번 주 총 칼로리
    - 평균 건강 점수
    - 자주 먹는 음식 Top 5
    - 최근 7일 일일 칼로리
    - 영양소 밸런스
    
    **Args:**
        session: DB 세션
        
    **Returns:**
        대시보드 통계 데이터
    """
    try:
        today = datetime.now().date()
        
        # 0. 사용자 정보 조회 및 목표 칼로리 계산
        user_stmt = select(User).where(User.user_id == user_id)
        user_result = await session.execute(user_stmt)
        user = user_result.scalar_one_or_none()
        
        target_calories = calculate_daily_calories(user) if user else 2000
        
        # 1. 오늘 총 칼로리
        today_stmt = select(func.sum(HealthScore.kcal)).where(
            and_(
                HealthScore.user_id == user_id,
                func.date(UserFoodHistory.consumed_at) == today
            )
        ).join(UserFoodHistory, HealthScore.history_id == UserFoodHistory.history_id)
        
        today_result = await session.execute(today_stmt)
        total_calories_today = today_result.scalar() or 0
        
        # 2. 이번 주 총 칼로리 (일요일 시작)
        # TODO: 주 시작일 계산 로직 추가
        
        # 3. 오늘 평균 건강 점수 (종합 점수로 개선)
        today_avg_stmt = select(func.avg(HealthScore.final_score)).join(
            UserFoodHistory, HealthScore.history_id == UserFoodHistory.history_id
        ).where(
            and_(
                HealthScore.user_id == user_id,
                func.date(UserFoodHistory.consumed_at) == today
            )
        )
        today_avg_result = await session.execute(today_avg_stmt)
        raw_avg_score = today_avg_result.scalar() or 0
        
        # ✨ 종합 점수 계산 (양 + 질) - HealthScoreService 활용
        comp_result = calculate_daily_comprehensive_score(
            total_calories=int(total_calories_today),
            target_calories=target_calories,
            avg_quality_score=float(raw_avg_score)
        )
        avg_health_score = comp_result["final_score"]
        score_feedback = comp_result["feedback"]  # ✨ 피드백 추출
        print(f"📊 종합 점수 계산: {raw_avg_score:.1f}(질) x {comp_result['quantity_factor']}(양) = {avg_health_score}")
        
        # 4. 전날 평균 건강 점수 (전날도 종합 점수로 계산해야 정확하지만, 일단 단순 평균 사용하거나 0 처리)
        # 개선점: 전날 데이터도 동일한 로직으로 계산하면 좋음
        yesterday = today - timedelta(days=1)
        yesterday_avg_stmt = select(func.avg(HealthScore.final_score)).join(
            UserFoodHistory, HealthScore.history_id == UserFoodHistory.history_id
        ).where(
            and_(
                HealthScore.user_id == user_id,
                func.date(UserFoodHistory.consumed_at) == yesterday
            )
        )
        yesterday_avg_result = await session.execute(yesterday_avg_stmt)
        previous_day_score = yesterday_avg_result.scalar()
        
        # 전날 대비 점수 변화 계산
        score_change = None
        if previous_day_score is not None and avg_health_score > 0:
            score_change = round(avg_health_score - previous_day_score, 1)
        
        # 5. 자주 먹는 음식 Top 5
        frequent_stmt = select(
            UserFoodHistory.food_name,
            func.count(UserFoodHistory.food_name).label('count')
        ).where(
            UserFoodHistory.user_id == user_id
        ).group_by(
            UserFoodHistory.food_name
        ).order_by(
            func.count(UserFoodHistory.food_name).desc()
        ).limit(5)
        
        frequent_result = await session.execute(frequent_stmt)
        frequent_foods = [
            {"food_name": row[0], "count": row[1]} 
            for row in frequent_result.all()
        ]
        
        # 6. 최근 7일 일일 칼로리
        seven_days_ago = today - timedelta(days=6)  # 오늘 포함 7일
        
        daily_stmt = select(
            func.date(UserFoodHistory.consumed_at).label('date'),
            func.sum(HealthScore.kcal).label('total_calories')
        ).join(
            HealthScore, 
            UserFoodHistory.history_id == HealthScore.history_id
        ).where(
            and_(
                UserFoodHistory.user_id == user_id,
                func.date(UserFoodHistory.consumed_at) >= seven_days_ago,
                func.date(UserFoodHistory.consumed_at) <= today
            )
        ).group_by(
            func.date(UserFoodHistory.consumed_at)
        ).order_by(
            func.date(UserFoodHistory.consumed_at)
        )
        
        daily_result = await session.execute(daily_stmt)
        daily_data = {row[0]: int(row[1]) for row in daily_result.all()}
        
        # 7일치 데이터 채우기 (데이터 없는 날은 0)
        daily_calories = []
        for i in range(7):
            date = seven_days_ago + timedelta(days=i)
            calories = daily_data.get(date, 0)
            daily_calories.append({
                "date": date.strftime("%m/%d"),
                "calories": calories
            })
        
        # 7. 이번 주 총 칼로리 (지난 7일 합계)
        total_calories_week = sum(item["calories"] for item in daily_calories)

        # 8. 영양소 밸런스 (최근 7일)
        portion_ratio = func.coalesce(
            func.coalesce(UserFoodHistory.portion_size_g, 0)
            / func.nullif(func.coalesce(FoodNutrient.reference_value, 0), 0),
            0,
        )
        nutrition_stmt = (
            select(
                func.sum(func.coalesce(FoodNutrient.protein, 0) * portion_ratio),
                func.sum(func.coalesce(FoodNutrient.carb, 0) * portion_ratio),
                func.sum(func.coalesce(FoodNutrient.fat, 0) * portion_ratio),
            )
            .select_from(UserFoodHistory)
            .join(FoodNutrient, UserFoodHistory.food_id == FoodNutrient.food_id)
            .where(
                and_(
                    UserFoodHistory.user_id == user_id,
                    func.date(UserFoodHistory.consumed_at) >= seven_days_ago,
                )
            )
        )
        nutrition_result = await session.execute(nutrition_stmt)
        protein, carbs, fat = nutrition_result.one_or_none() or (0, 0, 0)
        
        total_macros = (protein or 0) + (carbs or 0) + (fat or 0)
        nutrition_balance = {
            "protein": round(protein * 100 / total_macros, 1) if total_macros > 0 else 0,
            "carbs": round(carbs * 100 / total_macros, 1) if total_macros > 0 else 0,
            "fat": round(fat * 100 / total_macros, 1) if total_macros > 0 else 0,
        }
        
        return ApiResponse(
            success=True,
            data=DashboardStatsResponse(
                total_calories_today=int(total_calories_today),
                total_calories_week=total_calories_week,
                avg_health_score=float(avg_health_score),
                today_score_feedback=score_feedback,  # ✨ 추가됨
                previous_day_score=float(previous_day_score) if previous_day_score is not None else None,
                score_change=score_change,
                frequent_foods=frequent_foods,
                daily_calories=daily_calories,
                nutrition_balance=nutrition_balance
            ),
            message="✅ 대시보드 통계 조회 완료"
        )
        
    except Exception as e:
        print(f"❌ 대시보드 통계 조회 실패: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"통계 조회 중 오류 발생: {str(e)}")


@router.get("/history", response_model=ApiResponse[List[MealRecordResponse]])
async def get_meal_history(
    limit: int = 20,
    offset: int = 0,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(require_authentication)
) -> ApiResponse[List[MealRecordResponse]]:
    """
    음식 섭취 기록 조회
    
    **Args:**
        limit: 조회 개수
        offset: 오프셋
        session: DB 세션
        
    **Returns:**
        음식 기록 목록
    """
    try:
        # UserFoodHistory + HealthScore 조인 조회
        stmt = select(UserFoodHistory, HealthScore).where(
            UserFoodHistory.user_id == user_id
        ).outerjoin(
            HealthScore,
            and_(
                HealthScore.history_id == UserFoodHistory.history_id,
                HealthScore.user_id == UserFoodHistory.user_id
            )
        ).order_by(
            UserFoodHistory.consumed_at.desc()
        ).limit(limit).offset(offset)
        
        result = await session.execute(stmt)
        rows = result.all()
        
        records = []
        for history, health_score in rows:
            records.append(MealRecordResponse(
                history_id=history.history_id,
                user_id=history.user_id,
                food_id=history.food_id,
                food_name=history.food_name,
                consumed_at=history.consumed_at,
                portion_size_g=history.portion_size_g or 0,
                calories=health_score.kcal if health_score else 0,
                health_score=health_score.final_score if health_score else None,
                food_grade=health_score.food_grade if health_score else None,
                meal_type=history.meal_type  # 식사 유형 추가
            ))
        
        return ApiResponse(
            success=True,
            data=records,
            message=f"✅ {len(records)}개의 기록 조회 완료"
        )
        
    except Exception as e:
        print(f"❌ 음식 기록 조회 실패: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"기록 조회 중 오류 발생: {str(e)}")


@router.post("/save-recommended", response_model=ApiResponse[MealRecordResponse])
async def save_recommended_meal(
    request: SaveRecommendedMealRequest,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(require_authentication)
) -> ApiResponse[MealRecordResponse]:
    """
    추천 음식 선택 및 저장
    
    **전체 플로우:**
    1. 사용된 식재료 처리 (is_used = True 또는 수량 감소)
    2. GPT로 음식의 칼로리 + 영양소 추론
    3. NRF9.3 점수 계산
    4. Food 테이블 확인/생성
    5. UserFoodHistory 저장
    6. HealthScore 저장
    
    **Args:**
        request: 추천 음식 저장 요청
        session: DB 세션
        
    **Returns:**
        저장된 음식 기록 + NRF9.3 점수
    """
    try:
        # ========== STEP 0: 음식명 정규화 ==========
        from app.services.food_matching_service import normalize_food_name
        
        normalized_food_name = normalize_food_name(request.food_name, request.ingredients_used)
        if normalized_food_name != request.food_name:
            print(f"🔄 음식명 정규화: '{request.food_name}' → '{normalized_food_name}'")
            request.food_name = normalized_food_name
        
        # ========== STEP 1: 식재료 사용 처리 ==========
        # ingredients_with_quantity 우선, 없으면 레거시 방식
        missing_ingredients = []
        if request.ingredients_with_quantity:
            print(f"🥕 STEP 1: 식재료 사용 처리 (체크된 재료 = DB에서 완전 삭제)")
            for ingredient_usage in request.ingredients_with_quantity:
                ingredient_name = ingredient_usage.name
                
                stmt = select(UserIngredient).where(
                    UserIngredient.user_id == user_id,
                    UserIngredient.ingredient_name == ingredient_name,
                    UserIngredient.is_used == False
                ).order_by(UserIngredient.created_at.asc())  # 오래된 것부터
                
                result = await session.execute(stmt)
                ingredient = result.scalar_one_or_none()
                
                if ingredient:
                    # 체크된 재료는 DB에서 완전 삭제 (DELETE)
                    await session.delete(ingredient)
                    print(f"  🗑️ {ingredient_name}: DB에서 완전 삭제!")
                else:
                    print(f"  ⚠️ {ingredient_name}: 식재료 테이블에 없음")
                    missing_ingredients.append(ingredient_name)
            
            # 없는 재료가 있으면 경고 메시지
            if missing_ingredients:
                print(f"  ⚠️ 현재 식재료에 없는 재료: {', '.join(missing_ingredients)}")
        else:
            # 레거시: ingredients_used 배열 (체크 없이 저장된 경우)
            print(f"🥕 STEP 1: 식재료 사용 처리 (레거시) - {request.ingredients_used}")
            for ingredient_name in request.ingredients_used:
                stmt = select(UserIngredient).where(
                    UserIngredient.user_id == user_id,
                    UserIngredient.ingredient_name == ingredient_name,
                    UserIngredient.is_used == False
                ).order_by(UserIngredient.created_at.asc())  # 오래된 것부터
                
                result = await session.execute(stmt)
                ingredient = result.scalar_one_or_none()
                
                if ingredient:
                    # DB에서 완전 삭제
                    await session.delete(ingredient)
                    print(f"  🗑️ {ingredient_name}: DB에서 완전 삭제!")
                else:
                    print(f"  ⚠️ {ingredient_name}: UserIngredient에 없음 (건너뜀)")
        
        await session.flush()
        
        # ========== STEP 2: GPT로 영양소 추론 ==========
        print(f"🤖 STEP 2: GPT로 {request.food_name}의 영양소 추론")
        
        try:
            llm = get_nutrition_llm()
                        
            prompt = f"""당신은 영양학 전문가입니다. 다음 음식의 영양 정보를 JSON 형식으로 추정해주세요.

음식: {request.food_name}
섭취량: {request.portion_size_g}g

다음 영양소를 추정해서 JSON 형식으로 반환해주세요:
{{
  "calories": 칼로리(kcal),
  "protein_g": 단백질(g),
  "carb_g": 탄수화물(g),
  "fat_g": 지방(g),
  "fiber_g": 식이섬유(g),
  "vitamin_a_ug": 비타민A(μg RAE),
  "vitamin_c_mg": 비타민C(mg),
  "vitamin_e_mg": 비타민E(mg),
  "calcium_mg": 칼슘(mg),
  "iron_mg": 철분(mg),
  "potassium_mg": 칼륨(mg),
  "magnesium_mg": 마그네슘(mg),
  "saturated_fat_g": 포화지방(g),
  "added_sugar_g": 첨가당(g),
  "sodium_mg": 나트륨(mg)
}}

**중요:** 반드시 JSON 형식만 반환하고, 다른 설명은 포함하지 마세요.
영양소가 미미하거나 없으면 0으로 표시하세요."""

            messages = [
                SystemMessage(content="You are a nutrition expert. Always respond in valid JSON format only."),
                HumanMessage(content=prompt)
            ]
            
            import json
            response = await llm.ainvoke(messages)
            nutrition_data = json.loads(response.content)
            print(f"  ✅ 영양소 추론 완료: {nutrition_data['calories']}kcal")
            
        except Exception as e:
            print(f"  ⚠️ GPT 추론 실패, 기본값 사용: {e}")
            # 폴백: 기본값
            nutrition_data = {
                "calories": 400,
                "protein_g": 15.0,
                "carb_g": 50.0,
                "fat_g": 10.0,
                "fiber_g": 3.0,
                "vitamin_a_ug": 100.0,
                "vitamin_c_mg": 10.0,
                "vitamin_e_mg": 2.0,
                "calcium_mg": 100.0,
                "iron_mg": 2.0,
                "potassium_mg": 300.0,
                "magnesium_mg": 50.0,
                "saturated_fat_g": 3.0,
                "added_sugar_g": 5.0,
                "sodium_mg": 800.0
            }
        
        # 없는 재료가 있으면 사용자에게 알림
        if missing_ingredients:
            missing_msg = f"⚠️ 다음 재료는 현재 식재료에 없습니다: {', '.join(missing_ingredients)}"
            # 계속 진행하되 메시지 포함
        else:
            missing_msg = None
        
        # ========== STEP 3: NRF9.3 점수 계산 ==========
        print(f"📊 STEP 3: NRF9.3 점수 계산")
        score_result = await calculate_nrf93_score(
            protein_g=nutrition_data["protein_g"],
            fiber_g=nutrition_data["fiber_g"],
            vitamin_a_ug=nutrition_data["vitamin_a_ug"],
            vitamin_c_mg=nutrition_data["vitamin_c_mg"],
            vitamin_e_mg=nutrition_data["vitamin_e_mg"],
            calcium_mg=nutrition_data["calcium_mg"],
            iron_mg=nutrition_data["iron_mg"],
            potassium_mg=nutrition_data["potassium_mg"],
            magnesium_mg=nutrition_data["magnesium_mg"],
            saturated_fat_g=nutrition_data["saturated_fat_g"],
            added_sugar_g=nutrition_data["added_sugar_g"],
            sodium_mg=nutrition_data["sodium_mg"],
            reference_value_g=request.portion_size_g
        )
        print(f"  ✅ NRF9.3 점수: {score_result['final_score']}, 등급: {score_result['food_grade']}")
        
        # ========== STEP 4: food_nutrients에서 실제 음식 매칭 ==========
        print(f"🍽️ STEP 4: food_nutrients 매칭 처리")
        from app.services.food_matching_service import get_food_matching_service
        
        matching_service = get_food_matching_service()
        
        # DB에서 실제 음식 매칭 (user_id 전달)
        matched_food_nutrient = await matching_service.match_food_to_db(
            session=session,
            food_name=request.food_name,
            ingredients=request.ingredients_used if request.ingredients_used else [],
            food_class_hint=None,
            user_id=user_id
        )
        
        # 매칭된 food_id 사용
        if matched_food_nutrient:
            actual_food_id = matched_food_nutrient.food_id
            actual_food_class_1 = getattr(matched_food_nutrient, 'food_class1', None)
            actual_food_class_2 = getattr(matched_food_nutrient, 'food_class2', None)
            
            # FoodNutrient인지 UserContributedFood인지 확인
            if isinstance(matched_food_nutrient, FoodNutrient):
                print(f"✅ food_nutrients 매칭 성공: {actual_food_id} - {matched_food_nutrient.nutrient_name}")
            else:
                print(f"✅ user_contributed_foods 매칭 성공: {actual_food_id} - {matched_food_nutrient.food_name}")
        else:
            # 매칭 실패 시: user_contributed_foods에 새로 추가
            print(f"⚠️ 매칭 실패, user_contributed_foods에 새로 추가")
            
            # 재료 문자열 변환
            ingredients_str = ", ".join(request.ingredients_used) if request.ingredients_used else None
            
            # 새로운 food_id 생성
            actual_food_id = f"USER_{user_id}_{int(datetime.now().timestamp())}"[:200]
            actual_food_class_1 = "사용자추가"
            actual_food_class_2 = request.ingredients_used[0] if request.ingredients_used else None
            
            # user_contributed_foods에 추가
            new_contributed_food = UserContributedFood(
                food_id=actual_food_id,
                user_id=user_id,
                food_name=request.food_name,
                nutrient_name=request.food_name,
                food_class1=actual_food_class_1,
                food_class2=actual_food_class_2,
                ingredients=ingredients_str,
                unit="g",
                reference_value=request.portion_size_g,
                protein=nutrition_data.get("protein", 0),
                carb=nutrition_data.get("carb", 0),
                fat=nutrition_data.get("fat", 0),
                fiber=nutrition_data.get("fiber", 0),
                vitamin_a=nutrition_data.get("vitamin_a", 0),
                vitamin_c=nutrition_data.get("vitamin_c", 0),
                calcium=nutrition_data.get("calcium", 0),
                iron=nutrition_data.get("iron", 0),
                potassium=nutrition_data.get("potassium", 0),
                magnesium=nutrition_data.get("magnesium", 0),
                saturated_fat=nutrition_data.get("saturated_fat", 0),
                added_sugar=nutrition_data.get("added_sugar", 0),
                sodium=nutrition_data.get("sodium", 0),
                usage_count=1
            )
            session.add(new_contributed_food)
            await session.flush()
            
            print(f"✅ user_contributed_foods에 저장: {actual_food_id} - {request.food_name}")
        
        # Food 테이블 확인/생성
        food_stmt = select(Food).where(Food.food_id == actual_food_id)
        food_result = await session.execute(food_stmt)
        food = food_result.scalar_one_or_none()
        
        if not food:
            # 사용한 재료 문자열로 변환 (콤마 구분)
            ingredients_str = ", ".join(request.ingredients_used) if request.ingredients_used else None
            
            # 새로 생성
            food = Food(
                food_id=actual_food_id,
                food_name=request.food_name,
                category="추천음식",
                food_class_1=actual_food_class_1,
                food_class_2=actual_food_class_2,
                ingredients=ingredients_str
            )
            session.add(food)
            await session.flush()
            print(f"  ✅ Food 생성: {actual_food_id}, 재료: {ingredients_str}")
        else:
            # 이미 존재하면 그대로 사용 (이름이 달라도 ID가 같으면 같은 음식으로 간주)
            print(f"  ✅ Food 이미 존재: {actual_food_id} (기존 이름: {food.food_name})")
        
        food_id = actual_food_id
        
        # ========== STEP 5: UserFoodHistory 저장 ==========
        print(f"📝 STEP 5: UserFoodHistory 저장")
        
        # 🔍 디버깅: DB 스키마 확인 (AsyncEngine용)
        def get_table_columns(sync_conn):
            from sqlalchemy import inspect as sync_inspect
            inspector = sync_inspect(sync_conn)
            return inspector.get_columns("UserFoodHistory")
        
        columns = await session.connection(execution_options={"isolation_level": "AUTOCOMMIT"})
        column_info = await columns.run_sync(get_table_columns)
        print(f"🔍 DB 실제 컬럼 목록: {[col['name'] for col in column_info]}")
        
        print(f"📝 STEP 5: UserFoodHistory 저장 - meal_type={request.meal_type}")
        history = UserFoodHistory(
            user_id=user_id,
            food_id=food_id,
            food_name=request.food_name,
            consumed_at=datetime.now(),
            portion_size_g=request.portion_size_g,
            meal_type=request.meal_type  # ✨ meal_type 추가
            # memo=request.memo  # 임시로 제거 (DB에 memo 컬럼 없음)
        )
        session.add(history)
        await session.flush()
        await session.refresh(history)
        print(f"  ✅ History ID: {history.history_id}")
        
        # ========== STEP 6: HealthScore 저장 ==========
        print(f"💯 STEP 6: HealthScore 저장")
        health_score_obj = await create_health_score(
            session=session,
            history_id=history.history_id,
            user_id=user_id,
            food_id=food_id,
            reference_value=int(request.portion_size_g),
            kcal=nutrition_data["calories"],
            positive_score=int(score_result["positive_score"]),
            negative_score=int(score_result["negative_score"]),
            final_score=int(score_result["final_score"]),
            food_grade=score_result["food_grade"],
            calc_method=score_result["calc_method"]
        )
        print(f"  ✅ HealthScore 저장 완료")
        
        await session.commit()
        
        # ========== 응답 생성 ==========
        response_data = MealRecordResponse(
            history_id=history.history_id,
            user_id=history.user_id,
            food_id=history.food_id,
            food_name=history.food_name,
            consumed_at=history.consumed_at,
            portion_size_g=history.portion_size_g,
            calories=nutrition_data["calories"],
            health_score=health_score_obj.final_score,
            food_grade=health_score_obj.food_grade
        )
        
        # 메시지 생성
        success_message = f"✅ {request.food_name} 기록 완료! NRF9.3 점수: {score_result['final_score']:.1f}점"
        if missing_msg:
            success_message += f"\n\n{missing_msg}"
        
        return ApiResponse(
            success=True,
            data=response_data,
            message=success_message
        )
        
    except Exception as e:
        await session.rollback()
        print(f"❌ 추천 음식 저장 실패: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"추천 음식 저장 중 오류 발생: {str(e)}")


@router.get("/score-detail", response_model=ApiResponse[ScoreDetailResponse])
async def get_score_detail(
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(require_authentication)
) -> ApiResponse[ScoreDetailResponse]:
    """
    상세 점수 현황 조회
    
    - 오늘 전체 점수
    - 전날 대비 점수 변화
    - 카테고리별 점수 (칼로리 균형, 영양소 균형, 식사 패턴 등)
    - 주간 트렌드
    
    **Args:**
        session: DB 세션
        
    **Returns:**
        상세 점수 현황 데이터
    """
    try:
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        
        # 1. 오늘 전체 평균 점수
        today_score_stmt = select(func.avg(HealthScore.final_score)).join(
            UserFoodHistory, HealthScore.history_id == UserFoodHistory.history_id
        ).where(
            and_(
                HealthScore.user_id == user_id,
                func.date(UserFoodHistory.consumed_at) == today
            )
        )
        today_score_result = await session.execute(today_score_stmt)
        overall_score = today_score_result.scalar() or 0
        
        # 2. 전날 평균 점수
        yesterday_score_stmt = select(func.avg(HealthScore.final_score)).join(
            UserFoodHistory, HealthScore.history_id == UserFoodHistory.history_id
        ).where(
            and_(
                HealthScore.user_id == user_id,
                func.date(UserFoodHistory.consumed_at) == yesterday
            )
        )
        yesterday_score_result = await session.execute(yesterday_score_stmt)
        previous_score = yesterday_score_result.scalar()
        
        # score_change 계산은 종합 점수 산출 후로 이동
        score_change = None
        
        # 3. 오늘 섭취한 음식들의 영양소 정보 조회
        today_foods_stmt = select(
            HealthScore.kcal,
            HealthScore.final_score,
            FoodNutrient.protein,
            FoodNutrient.carb,
            FoodNutrient.fat,
            FoodNutrient.fiber,
            FoodNutrient.sodium,
            FoodNutrient.saturated_fat,
            FoodNutrient.added_sugar
        ).join(
            UserFoodHistory, HealthScore.history_id == UserFoodHistory.history_id
        ).outerjoin(
            FoodNutrient, UserFoodHistory.food_id == FoodNutrient.food_id
        ).where(
            and_(
                HealthScore.user_id == user_id,
                func.date(UserFoodHistory.consumed_at) == today
            )
        )
        
        foods_result = await session.execute(today_foods_stmt)
        foods_data = foods_result.all()
        
        # 4. 사용자 정보 조회 (목표 칼로리 등)
        user_stmt = select(User).where(User.user_id == user_id)
        user_result = await session.execute(user_stmt)
        user = user_result.scalar_one_or_none()
        
        # 목표 칼로리 계산 (공통 함수 사용)
        target_calories = calculate_daily_calories(user) if user else 2000
        
        # 5. 종합 점수 및 세부 지표 계산
        categories = []
        
        # 기본값 설정
        raw_quality_score = overall_score  # 기존 단순 평균 점수 (질)
        quantity_score_val = 0.0
        calorie_ratio_val = 0.0
        
        if foods_data:
            # 총 칼로리
            total_calories = sum(row[0] or 0 for row in foods_data)
            
            # ✨ 종합 점수 재계산 (양 + 질)
            comp_result = calculate_daily_comprehensive_score(
                total_calories=int(total_calories),
                target_calories=target_calories,
                avg_quality_score=float(raw_quality_score)
            )
            
            overall_score = comp_result["final_score"]  # 종합 점수로 교체
            quantity_score_val = comp_result["quantity_factor"] * 100
            calorie_ratio_val = comp_result["calorie_ratio"]
            
            # 전날 대비 점수 변화 재계산 (종합 점수 기준)
            score_change = None
            if previous_score is not None:
                score_change = round(overall_score - previous_score, 1)
            
            # 칼로리 균형 점수 (목표 대비 90-110% = 100점, 그 외는 감점)
            # calculate_daily_comprehensive_score 로직과 유사하지만 카테고리 표시용으로 유지
            calorie_ratio = (total_calories / target_calories * 100) if target_calories > 0 else 0
            if 90 <= calorie_ratio <= 110:
                calorie_score = 100
            elif 80 <= calorie_ratio < 90 or 110 < calorie_ratio <= 120:
                calorie_score = 80
            elif 70 <= calorie_ratio < 80 or 120 < calorie_ratio <= 130:
                calorie_score = 60
            else:
                calorie_score = max(0, 100 - abs(calorie_ratio - 100))
            
            calorie_trend = 'same'
            if previous_score is not None:
                # 전날 칼로리 비교는 별도로 계산 필요하지만, 간단히 점수 기반으로 판단
                calorie_trend = 'up' if overall_score > previous_score else 'down' if overall_score < previous_score else 'same'
            
            # 칼로리 피드백 메시지 생성
            if 90 <= calorie_ratio <= 110:
                calorie_feedback = f"목표 칼로리 {target_calories}kcal 대비 {total_calories:.0f}kcal 섭취. 적절한 칼로리 섭취량입니다."
            elif calorie_ratio < 90:
                calorie_feedback = f"목표 칼로리 {target_calories}kcal 대비 {total_calories:.0f}kcal 섭취. 칼로리 섭취량이 부족합니다."
            else:
                calorie_feedback = f"목표 칼로리 {target_calories}kcal 대비 {total_calories:.0f}kcal 섭취. 칼로리 섭취량이 초과입니다."
            
            categories.append(CategoryScore(
                name="칼로리 균형",
                score=round(calorie_score, 1),
                max_score=100.0,
                trend=calorie_trend,
                feedback=calorie_feedback
            ))
            
            # 영양소 균형 점수 (단백질, 탄수화물, 지방 비율)
            total_protein = sum(row[2] or 0 for row in foods_data)
            total_carbs = sum(row[3] or 0 for row in foods_data)
            total_fat = sum(row[4] or 0 for row in foods_data)
            total_macros = total_protein + total_carbs + total_fat
            
            if total_macros > 0:
                protein_ratio = (total_protein / total_macros) * 100
                carbs_ratio = (total_carbs / total_macros) * 100
                fat_ratio = (total_fat / total_macros) * 100
                
                # 권장 비율: 단백질 15-20%, 탄수화물 50-60%, 지방 20-30%
                nutrition_score = 100
                if not (15 <= protein_ratio <= 25):
                    nutrition_score -= 10
                if not (45 <= carbs_ratio <= 65):
                    nutrition_score -= 10
                if not (20 <= fat_ratio <= 35):
                    nutrition_score -= 10
                nutrition_score = max(0, nutrition_score)
            else:
                nutrition_score = 0
            
            # 영양소 균형 피드백 메시지 생성
            if nutrition_score >= 80:
                nutrition_feedback = f"단백질 {total_protein:.1f}g, 탄수화물 {total_carbs:.1f}g, 지방 {total_fat:.1f}g. 균형 잡힌 영양소 비율입니다."
            else:
                nutrition_feedback = f"단백질 {total_protein:.1f}g, 탄수화물 {total_carbs:.1f}g, 지방 {total_fat:.1f}g. 영양소 비율이 불균형합니다."
            
            categories.append(CategoryScore(
                name="영양소 균형",
                score=round(nutrition_score, 1),
                max_score=100.0,
                trend=calorie_trend,
                feedback=nutrition_feedback
            ))
            
            # 식이섬유 점수
            total_fiber = sum(row[5] or 0 for row in foods_data)
            fiber_target = 25.0  # 일일 권장량
            fiber_score = min(100, (total_fiber / fiber_target) * 100) if fiber_target > 0 else 0
            
            # 식이섬유 피드백 메시지 생성
            if fiber_score >= 80:
                fiber_feedback = f"식이섬유 {total_fiber:.1f}g 섭취. 충분한 섭취량입니다."
            else:
                fiber_feedback = f"식이섬유 {total_fiber:.1f}g 섭취. 섭취량이 부족합니다. 채소와 과일을 더 섭취해보세요."
            
            categories.append(CategoryScore(
                name="식이섬유",
                score=round(fiber_score, 1),
                max_score=100.0,
                trend='same',
                feedback=fiber_feedback
            ))
            
            # 나트륨 점수 (낮을수록 좋음)
            total_sodium = sum(row[6] or 0 for row in foods_data)
            sodium_target = 2000.0  # 일일 권장량
            sodium_ratio = (total_sodium / sodium_target) * 100 if sodium_target > 0 else 0
            sodium_score = max(0, 100 - sodium_ratio)  # 낮을수록 좋으므로 역산
            
            # 나트륨 피드백 메시지 생성
            if sodium_score >= 70:
                sodium_feedback = f"나트륨 {total_sodium:.0f}mg 섭취. 적절한 수준입니다."
            else:
                sodium_feedback = f"나트륨 {total_sodium:.0f}mg 섭취. 나트륨 섭취량이 초과입니다. 저염식을 권장합니다."
            
            categories.append(CategoryScore(
                name="나트륨 관리",
                score=round(sodium_score, 1),
                max_score=100.0,
                trend='same',
                feedback=sodium_feedback
            ))
            
            # 포화지방 점수 (낮을수록 좋음)
            total_saturated_fat = sum(row[7] or 0 for row in foods_data)
            saturated_fat_target = 15.0  # 일일 권장량
            saturated_fat_ratio = (total_saturated_fat / saturated_fat_target) * 100 if saturated_fat_target > 0 else 0
            saturated_fat_score = max(0, 100 - saturated_fat_ratio)
            
            # 포화지방 피드백 메시지 생성
            if saturated_fat_score >= 70:
                saturated_fat_feedback = f"포화지방 {total_saturated_fat:.1f}g 섭취. 적절한 수준입니다."
            else:
                saturated_fat_feedback = f"포화지방 {total_saturated_fat:.1f}g 섭취. 포화지방 섭취량이 초과입니다. 섭취를 줄여보세요."
            
            categories.append(CategoryScore(
                name="포화지방 관리",
                score=round(saturated_fat_score, 1),
                max_score=100.0,
                trend='same',
                feedback=saturated_fat_feedback
            ))
        else:
            # 데이터 없음
            categories.append(CategoryScore(
                name="칼로리 균형",
                score=0.0,
                max_score=100.0,
                trend='same',
                feedback="오늘 식사 기록이 없습니다."
            ))
        
        # 6. 주간 트렌드 (최근 7일)
        seven_days_ago = today - timedelta(days=6)
        weekly_trend_stmt = select(
            func.date(UserFoodHistory.consumed_at).label('date'),
            func.avg(HealthScore.final_score).label('avg_score')
        ).join(
            HealthScore, UserFoodHistory.history_id == HealthScore.history_id
        ).where(
            and_(
                UserFoodHistory.user_id == user_id,
                func.date(UserFoodHistory.consumed_at) >= seven_days_ago,
                func.date(UserFoodHistory.consumed_at) <= today
            )
        ).group_by(
            func.date(UserFoodHistory.consumed_at)
        ).order_by(
            func.date(UserFoodHistory.consumed_at)
        )
        
        weekly_result = await session.execute(weekly_trend_stmt)
        weekly_data = {row[0]: row[1] for row in weekly_result.all()}
        
        weekly_trend = []
        for i in range(7):
            date = seven_days_ago + timedelta(days=i)
            score = weekly_data.get(date, 0)
            weekly_trend.append({
                "date": date.strftime("%m-%d"),
                "score": round(float(score), 1) if score else 0
            })
        
        return ApiResponse(
            success=True,
            data=ScoreDetailResponse(
                overall_score=round(float(overall_score), 1),
                quality_score=round(float(raw_quality_score), 1) if raw_quality_score is not None else 0, # ✨ 추가
                quantity_score=round(float(quantity_score_val), 1), # ✨ 추가
                calorie_ratio=round(float(calorie_ratio_val), 1), # ✨ 추가
                previous_score=round(float(previous_score), 1) if previous_score is not None else None,
                score_change=score_change,
                categories=categories,
                weekly_trend=weekly_trend
            ),
            message="✅ 상세 점수 현황 조회 완료"
        )
        
    except Exception as e:
        print(f"❌ 상세 점수 현황 조회 실패: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"상세 점수 현황 조회 중 오류 발생: {str(e)}")


@router.delete("/history/{history_id}", response_model=ApiResponse[dict])
async def delete_meal_history(
    history_id: int,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(require_authentication)
) -> ApiResponse[dict]:
    """
    음식 섭취 기록 삭제
    
    **Args:**
        history_id: 삭제할 기록 ID
        session: DB 세션
        
    **Returns:**
        삭제 결과
    """
    try:
        # 기록 존재 여부 및 권한 확인
        stmt = select(UserFoodHistory).where(
            and_(
                UserFoodHistory.history_id == history_id,
                UserFoodHistory.user_id == user_id
            )
        )
        result = await session.execute(stmt)
        history = result.scalar_one_or_none()
        
        if not history:
            raise HTTPException(
                status_code=404, 
                detail="기록을 찾을 수 없거나 삭제 권한이 없습니다."
            )
        
        # HealthScore도 함께 삭제
        health_score_stmt = select(HealthScore).where(
            and_(
                HealthScore.history_id == history_id,
                HealthScore.user_id == user_id
            )
        )
        health_score_result = await session.execute(health_score_stmt)
        health_score = health_score_result.scalar_one_or_none()
        
        if health_score:
            await session.delete(health_score)
        
        # UserFoodHistory 삭제
        await session.delete(history)
        await session.commit()
        
        return ApiResponse(
            success=True,
            data={"history_id": history_id, "deleted": True},
            message=f"✅ '{history.food_name}' 기록이 삭제되었습니다."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        print(f"❌ 음식 기록 삭제 실패: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"기록 삭제 중 오류 발생: {str(e)}")


@router.get("/most-eaten", response_model=ApiResponse[List[MostEatenFood]])
async def get_most_eaten_foods(
    limit: int = 4,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(require_authentication)
) -> ApiResponse[List[MostEatenFood]]:
    """
    자주 먹은 음식 TOP N
    
    **처리 과정:**
    1. UserFoodHistory에서 food_id별 카운트
    2. 내림차순 정렬
    3. 상위 N개 반환
    
    **Args:**
        limit: 반환할 음식 개수 (기본 4개)
        session: DB 세션
        user_id: 사용자 ID
        
    **Returns:**
        자주 먹은 음식 목록
    """
    try:
        print(f"🍽️ 자주 먹은 음식 조회: user_id={user_id}, limit={limit}")
        
        # food_id별 카운트 쿼리
        # 같은 food_id는 하나로 합치고, 가장 최근 음식명 사용
        # Subquery: 각 food_id의 가장 최근 기록 찾기
        latest_food_subquery = (
            select(
                UserFoodHistory.food_id,
                UserFoodHistory.food_name,
                func.row_number().over(
                    partition_by=UserFoodHistory.food_id,
                    order_by=UserFoodHistory.consumed_at.desc()
                ).label('rn')
            )
            .where(UserFoodHistory.user_id == user_id)
            .subquery()
        )
        
        # 메인 쿼리: food_id별 카운트 + 최근 음식명 조인
        stmt = (
            select(
                UserFoodHistory.food_id,
                latest_food_subquery.c.food_name,  # 가장 최근 음식명
                func.count(UserFoodHistory.history_id).label('eat_count')
            )
            .join(
                latest_food_subquery,
                (UserFoodHistory.food_id == latest_food_subquery.c.food_id) &
                (latest_food_subquery.c.rn == 1)
            )
            .where(UserFoodHistory.user_id == user_id)
            .group_by(UserFoodHistory.food_id, latest_food_subquery.c.food_name)
            .order_by(func.count(UserFoodHistory.history_id).desc())
            .limit(limit)
        )
        
        result = await session.execute(stmt)
        rows = result.all()
        
        most_eaten_list = [
            MostEatenFood(
                food_id=row.food_id,
                food_name=row.food_name,
                eat_count=row.eat_count
            )
            for row in rows
        ]
        
        print(f"✅ 자주 먹은 음식 {len(most_eaten_list)}개 조회 완료")
        for idx, food in enumerate(most_eaten_list, 1):
            print(f"  {idx}. {food.food_name}: {food.eat_count}번")
        
        return ApiResponse(
            success=True,
            data=most_eaten_list,
            message=f"✅ 자주 먹은 음식 {len(most_eaten_list)}개를 조회했습니다."
        )
        
    except Exception as e:
        print(f"❌ 자주 먹은 음식 조회 실패: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"자주 먹은 음식 조회 중 오류 발생: {str(e)}")
