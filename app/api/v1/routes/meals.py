"""음식 기록 및 건강 점수 관리 API"""
import os
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.api.v1.schemas.common import ApiResponse
from app.db.models import UserFoodHistory, HealthScore, User, Food, UserIngredient
from app.db.models_food_nutrients import FoodNutrient
from app.db.session import get_session
from app.services.health_score_service import (
    create_health_score,
    calculate_korean_nutrition_score,
    calculate_nrf93_score,
    get_user_health_scores
)

router = APIRouter()


def get_current_user_id() -> int:
    """현재 로그인된 사용자 ID 반환 (임시)"""
    return 1


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


class DashboardStatsResponse(BaseModel):
    """대시보드 통계 응답"""
    total_calories_today: int = Field(..., description="오늘 총 칼로리")
    total_calories_week: int = Field(..., description="이번 주 총 칼로리")
    avg_health_score: float = Field(..., description="평균 건강 점수")
    frequent_foods: List[dict] = Field(..., description="자주 먹는 음식 Top 5")
    daily_calories: List[dict] = Field(..., description="일일 칼로리 (최근 7일)")
    nutrition_balance: dict = Field(..., description="영양소 밸런스")


# ========== API 엔드포인트 ==========

@router.post("/save", response_model=ApiResponse[List[MealRecordResponse]])
async def save_meal_records(
    request: SaveMealRequest,
    session: AsyncSession = Depends(get_session)
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
        user_id = get_current_user_id()
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
    session: AsyncSession = Depends(get_session)
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
        user_id = get_current_user_id()
        today = datetime.now().date()
        
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
        
        # 3. 평균 건강 점수
        avg_stmt = select(func.avg(HealthScore.final_score)).where(
            HealthScore.user_id == user_id
        )
        avg_result = await session.execute(avg_stmt)
        avg_health_score = avg_result.scalar() or 0
        
        # 4. 자주 먹는 음식 Top 5
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
        
        # 5. 최근 7일 일일 칼로리
        from datetime import timedelta
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
        
        # 6. 이번 주 총 칼로리 (지난 7일 합계)
        total_calories_week = sum(item["calories"] for item in daily_calories)
        
        return ApiResponse(
            success=True,
            data=DashboardStatsResponse(
                total_calories_today=int(total_calories_today),
                total_calories_week=total_calories_week,
                avg_health_score=float(avg_health_score),
                frequent_foods=frequent_foods,
                daily_calories=daily_calories,
                nutrition_balance={}  # TODO: 추후 구현
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
    session: AsyncSession = Depends(get_session)
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
        user_id = get_current_user_id()
        
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
                food_grade=health_score.food_grade if health_score else None
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
    session: AsyncSession = Depends(get_session)
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
        user_id = get_current_user_id()
        
        # ========== STEP 1: 식재료 사용 처리 ==========
        # ingredients_with_quantity 우선, 없으면 레거시 방식
        if request.ingredients_with_quantity:
            print(f"🥕 STEP 1: 식재료 사용 처리 (수량 포함)")
            for ingredient_usage in request.ingredients_with_quantity:
                ingredient_name = ingredient_usage.name
                quantity_to_use = ingredient_usage.quantity
                
                stmt = select(UserIngredient).where(
                    UserIngredient.user_id == user_id,
                    UserIngredient.ingredient_name == ingredient_name,
                    UserIngredient.is_used == False
                ).order_by(UserIngredient.created_at.asc())  # 오래된 것부터
                
                result = await session.execute(stmt)
                ingredient = result.scalar_one_or_none()
                
                if ingredient:
                    if ingredient.count > quantity_to_use:
                        ingredient.count -= quantity_to_use
                        print(f"  - {ingredient_name}: 수량 감소 ({ingredient.count + quantity_to_use} → {ingredient.count})")
                    elif ingredient.count == quantity_to_use:
                        ingredient.is_used = True
                        print(f"  - {ingredient_name}: 사용 완료 (is_used = True)")
                    else:
                        # 보유량보다 많이 사용하려는 경우 - 보유량 전체 사용
                        print(f"  ⚠️ {ingredient_name}: 보유량({ingredient.count})보다 많이 사용({quantity_to_use}) - 전체 사용")
                        ingredient.is_used = True
                else:
                    print(f"  ⚠️ {ingredient_name}: UserIngredient에 없음 (건너뜀)")
        else:
            # 레거시: ingredients_used 배열 (각 재료 1개씩)
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
                    if ingredient.count > 1:
                        ingredient.count -= 1
                        print(f"  - {ingredient_name}: 수량 감소 ({ingredient.count + 1} → {ingredient.count})")
                    else:
                        ingredient.is_used = True
                        print(f"  - {ingredient_name}: 사용 완료 (is_used = True)")
                else:
                    print(f"  ⚠️ {ingredient_name}: UserIngredient에 없음 (건너뜀)")
        
        await session.flush()
        
        # ========== STEP 2: GPT로 영양소 추론 ==========
        print(f"🤖 STEP 2: GPT로 {request.food_name}의 영양소 추론")
        
        try:
            from openai import OpenAI
            
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.")
            
            client = OpenAI(api_key=api_key)
            
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

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a nutrition expert. Always respond in valid JSON format only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            import json
            nutrition_data = json.loads(response.choices[0].message.content)
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
        
        # ========== STEP 4: Food 테이블 확인/생성 ==========
        print(f"🍽️ STEP 4: Food 테이블 처리")
        food_id = f"recommended_{request.food_name}_{int(datetime.now().timestamp())}"
        
        # Food 테이블에 있는지 확인
        food_stmt = select(Food).where(Food.food_name == request.food_name)
        food_result = await session.execute(food_stmt)
        food = food_result.scalar_one_or_none()
        
        if not food:
            # 사용한 재료 문자열로 변환 (콤마 구분)
            ingredients_str = ", ".join(request.ingredients_used) if request.ingredients_used else None
            
            # 새로 생성
            food = Food(
                food_id=food_id,
                food_name=request.food_name,
                category="추천음식",
                food_class_2=request.food_name,
                ingredients=ingredients_str
            )
            session.add(food)
            await session.flush()
            print(f"  ✅ Food 생성: {food_id}, 재료: {ingredients_str}")
        else:
            food_id = food.food_id
            print(f"  ✅ Food 존재: {food_id}")
        
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
        
        history = UserFoodHistory(
            user_id=user_id,
            food_id=food_id,
            food_name=request.food_name,
            consumed_at=datetime.now(),
            portion_size_g=request.portion_size_g
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
        
        return ApiResponse(
            success=True,
            data=response_data,
            message=f"✅ {request.food_name} 기록 완료! NRF9.3 점수: {score_result['final_score']:.1f}점"
        )
        
    except Exception as e:
        await session.rollback()
        print(f"❌ 추천 음식 저장 실패: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"추천 음식 저장 중 오류 발생: {str(e)}")

