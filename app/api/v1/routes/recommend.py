"""식단 추천 API 라우트"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import hashlib

from app.api.v1.schemas.diet import (
    DietPlanRequest, 
    DietPlanResponse, 
    SaveDietPlanRequest, 
    SaveDietPlanResponse
)
from app.api.v1.schemas.common import ApiResponse
from app.db.models import User, Food, UserFoodHistory, DietPlan, DietPlanMeal
from app.db.session import get_session
from app.services.diet_recommendation_service import get_diet_recommendation_service

router = APIRouter(prefix="/recommend", tags=["Recommendations"])


@router.post("/diet-plan", response_model=ApiResponse[DietPlanResponse])
async def get_diet_plan_recommendation(
    request: DietPlanRequest,
    user_id: int,  # TODO: 실제로는 세션/토큰에서 가져와야 함
    session: AsyncSession = Depends(get_session)
):
    """
    사용자 건강 정보를 기반으로 GPT가 개인 맞춤 식단을 추천합니다.
    
    **동작 과정:**
    1. User 테이블에서 사용자 정보 조회 (gender, age, weight, health_goal)
    2. 기초대사량(BMR) 계산 (Harris-Benedict 공식)
    3. 1일 총 에너지 소비량(TDEE) 계산
    4. 건강 목표에 따른 목표 칼로리 계산
       - loss: TDEE - 500kcal
       - maintain: TDEE
       - gain: TDEE + 500kcal
    5. GPT에게 식단 추천 요청 (3가지 옵션)
    6. 식단 응답 파싱 및 반환
    
    **Args:**
        - request: 사용자 요청 (선택사항: 추가 요청사항, 활동 수준)
        - user_id: 사용자 ID (현재는 쿼리 파라미터, 추후 세션에서 가져옴)
        - session: DB 세션
    
    **Returns:**
        ApiResponse[DietPlanResponse]: 추천 식단 정보
        - bmr: 기초대사량
        - tdee: 1일 총 에너지 소비량
        - targetCalories: 목표 칼로리
        - healthGoal: 건강 목표
        - dietPlans: 추천 식단 옵션 3개
    
    **Example Request:**
    ```json
    POST /api/v1/recommend/diet-plan?user_id=1
    {
        "user_request": "고기류를 먹고 싶어요",
        "activity_level": "moderate"
    }
    ```
    
    **Example Response:**
    ```json
    {
        "success": true,
        "data": {
            "bmr": 1650.5,
            "tdee": 2558.3,
            "targetCalories": 2058.3,
            "healthGoal": "loss",
            "healthGoalKr": "체중 감량",
            "dietPlans": [
                {
                    "name": "고단백 식단",
                    "description": "근육 생성에 최적화된 고단백 식단",
                    "totalCalories": "1500 kcal",
                    "meals": {
                        "breakfast": "현미밥 1공기 + 닭가슴살 구이 100g + 시금치 무침",
                        "lunch": "연어 덮밥 1인분 + 계란국",
                        "dinner": "고등어 구이 1마리 + 두부조림 + 배추김치",
                        "snack": "그릭요거트 1컵 + 아몬드 10알"
                    },
                    "nutrients": "단백질 120g / 탄수화물 150g / 지방 45g"
                },
                ...
            ],
            "gptResponse": "..."
        },
        "message": "식단 추천이 완료되었습니다."
    }
    ```
    """
    try:
        # 1. 사용자 정보 조회
        result = await session.execute(
            select(User).where(User.user_id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"사용자를 찾을 수 없습니다. (user_id={user_id})"
            )
        
        # 2. 필수 정보 확인
        if not user.gender or not user.age or not user.weight:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="사용자의 건강 정보가 불완전합니다. 프로필 설정에서 성별, 나이, 체중을 입력해주세요."
            )
        
        print(f"📊 사용자 정보 조회 완료: {user.nickname or user.username} (gender={user.gender}, age={user.age}, weight={user.weight}, height={user.height or '평균값'}, goal={user.health_goal})")
        
        # 3. 식단 추천 서비스 호출
        diet_service = get_diet_recommendation_service()
        result_data = await diet_service.generate_diet_plan(
            user=user,
            user_request=request.user_request,
            activity_level=request.activity_level
        )
        
        print(f"✅ 식단 추천 완료: BMR={result_data['bmr']}, TDEE={result_data['tdee']}, Target={result_data['target_calories']}")
        print(f"📋 추천 식단 개수: {len(result_data['diet_plans'])}개")
        
        # 4. 응답 반환
        return ApiResponse(
            success=True,
            data=DietPlanResponse(**result_data),
            message="✅ 식단 추천이 완료되었습니다."
        )
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 식단 추천 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"식단 추천 중 오류가 발생했습니다: {str(e)}"
        )


@router.post("/save-diet-plan", response_model=ApiResponse[SaveDietPlanResponse])
async def save_diet_plan(
    request: SaveDietPlanRequest,
    session: AsyncSession = Depends(get_session)
):
    """
    GPT가 추천한 식단을 저장합니다.
    
    **저장 구조:**
    1. DietPlan 테이블: 식단 메타데이터 (BMR, TDEE, 목표 칼로리 등)
    2. DietPlanMeal 테이블: 끼니별 상세 정보
    3. (선택) UserFoodHistory: 즉시 섭취 기록 (consumed_at 있는 경우)
    
    **Args:**
        - request: 저장할 식단 정보
          - user_id: 사용자 ID
          - diet_plan_name: 식단 이름 (예: "고단백 식단")
          - meals: 끼니 목록 (각 끼니의 음식명, 재료, 영양소 정보)
    
    **Returns:**
        ApiResponse[SaveDietPlanResponse]: 저장 결과
        - success: 성공 여부
        - message: 결과 메시지
        - saved_count: 저장된 끼니 수
    
    **Example Request:**
    ```json
    POST /api/v1/recommend/save-diet-plan
    {
        "user_id": 1,
        "diet_plan_name": "고단백 식단",
        "meals": [
            {
                "food_name": "고단백 식단 - 아침",
                "meal_type": "breakfast",
                "ingredients": ["현미밥 1공기", "닭가슴살 구이 100g"],
                "calories": 450.0,
                "protein": 35.0,
                "carb": 55.0,
                "fat": 8.0,
                "consumed_at": "2024-01-15T08:00:00"
            }
        ]
    }
    ```
    """
    try:
        # 1. 사용자 존재 확인
        result = await session.execute(
            select(User).where(User.user_id == request.user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"사용자를 찾을 수 없습니다. (user_id={request.user_id})"
            )
        
        print(f"💾 추천 식단 저장 요청: user_id={request.user_id}, diet_plan={request.diet_plan_name}, meals={len(request.meals)}개")
        
        # 2. DietPlan 생성 (고유 ID 생성)
        timestamp = int(datetime.now().timestamp() * 1000)
        diet_plan_id = f"plan_{timestamp}"
        
        # 총 영양소 계산
        total_calories = sum(meal.calories for meal in request.meals)
        total_protein = sum(meal.protein for meal in request.meals)
        total_carb = sum(meal.carb for meal in request.meals)
        total_fat = sum(meal.fat for meal in request.meals)
        
        diet_plan = DietPlan(
            diet_plan_id=diet_plan_id,
            user_id=request.user_id,
            plan_name=request.diet_plan_name,
            description=request.description,
            bmr=request.bmr,
            tdee=request.tdee,
            target_calories=request.target_calories,
            health_goal=request.health_goal,
            total_calories=total_calories,
            total_protein=total_protein,
            total_carb=total_carb,
            total_fat=total_fat,
            is_active=True
        )
        session.add(diet_plan)
        print(f"  ✅ DietPlan 생성: {diet_plan_id}")
        
        # 3. DietPlanMeal 생성 (끼니별 상세)
        saved_count = 0
        for meal in request.meals:
            diet_plan_meal = DietPlanMeal(
                diet_plan_id=diet_plan_id,
                meal_type=meal.meal_type,
                meal_name=meal.food_name,
                food_description=meal.food_name,  # 음식 설명 (재료 포함)
                ingredients=meal.ingredients,  # JSON으로 저장
                calories=meal.calories,
                protein=meal.protein,
                carb=meal.carb,
                fat=meal.fat,
                consumed=False,  # 기본값: 아직 섭취 안 함
                consumed_at=None
            )
            session.add(diet_plan_meal)
            print(f"  📝 DietPlanMeal 생성: {meal.food_name} (meal_type={meal.meal_type}, calories={meal.calories})")
            saved_count += 1
        
        # 4. 트랜잭션 커밋
        await session.commit()
        
        print(f"✅ 추천 식단 저장 완료: {saved_count}개 끼니 저장됨 (diet_plan_id={diet_plan_id})")
        
        return ApiResponse(
            success=True,
            data=SaveDietPlanResponse(
                success=True,
                message=f"✅ {request.diet_plan_name} 식단이 저장되었습니다.",
                diet_plan_id=diet_plan_id,
                saved_count=saved_count
            ),
            message=f"✅ {saved_count}개 끼니가 저장되었습니다."
        )
    
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        print(f"❌ 추천 식단 저장 실패: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"식단 저장 중 오류가 발생했습니다: {str(e)}"
        )


@router.get("/my-diet-plans", response_model=ApiResponse)
async def get_my_diet_plans(
    user_id: int,  # TODO: 세션에서 가져오기
    session: AsyncSession = Depends(get_session)
):
    """
    내가 저장한 추천 식단 목록을 조회합니다.
    
    **반환 정보:**
    - 식단 ID, 이름, 설명
    - 목표 칼로리, 건강 목표
    - 생성일시, 활성 여부
    - 총 끼니 수, 섭취한 끼니 수, 진행률
    
    **Example:**
    ```
    GET /api/v1/recommend/my-diet-plans?user_id=1
    ```
    """
    try:
        # 사용자 확인
        result = await session.execute(
            select(User).where(User.user_id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"사용자를 찾을 수 없습니다. (user_id={user_id})"
            )
        
        # 식단 목록 조회 (최신순)
        result = await session.execute(
            select(DietPlan)
            .where(DietPlan.user_id == user_id)
            .order_by(DietPlan.created_at.desc())
        )
        diet_plans = result.scalars().all()
        
        # 각 식단의 끼니 정보 조회
        diet_plans_data = []
        for plan in diet_plans:
            # 끼니 정보 조회
            meals_result = await session.execute(
                select(DietPlanMeal)
                .where(DietPlanMeal.diet_plan_id == plan.diet_plan_id)
            )
            meals = meals_result.scalars().all()
            
            total_meals = len(meals)
            consumed_meals = sum(1 for meal in meals if meal.consumed)
            progress_percent = round(consumed_meals * 100 / total_meals, 1) if total_meals > 0 else 0
            
            diet_plans_data.append({
                "diet_plan_id": plan.diet_plan_id,
                "plan_name": plan.plan_name,
                "description": plan.description,
                "target_calories": float(plan.target_calories) if plan.target_calories else None,
                "health_goal": plan.health_goal,
                "created_at": plan.created_at.isoformat() if plan.created_at else None,
                "is_active": plan.is_active,
                "total_meals": total_meals,
                "consumed_meals": consumed_meals,
                "progress_percent": progress_percent
            })
        
        print(f"✅ 식단 목록 조회: user_id={user_id}, 총 {len(diet_plans_data)}개")
        
        return ApiResponse(
            success=True,
            data=diet_plans_data,
            message=f"✅ {len(diet_plans_data)}개의 식단을 찾았습니다."
        )
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 식단 목록 조회 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"식단 목록 조회 중 오류가 발생했습니다: {str(e)}"
        )


@router.get("/diet-plans/{diet_plan_id}", response_model=ApiResponse)
async def get_diet_plan_detail(
    diet_plan_id: str,
    user_id: int,  # TODO: 세션에서 가져오기
    session: AsyncSession = Depends(get_session)
):
    """
    특정 추천 식단의 상세 정보를 조회합니다.
    
    **반환 정보:**
    - 식단 메타데이터 (BMR, TDEE, 목표 칼로리)
    - 끼니별 상세 정보 (음식명, 재료, 영양소)
    - 섭취 여부 및 진행률
    
    **Example:**
    ```
    GET /api/v1/recommend/diet-plans/plan_1732012345678?user_id=1
    ```
    """
    try:
        # 식단 조회
        result = await session.execute(
            select(DietPlan)
            .where(
                DietPlan.diet_plan_id == diet_plan_id,
                DietPlan.user_id == user_id
            )
        )
        diet_plan = result.scalar_one_or_none()
        
        if not diet_plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"식단을 찾을 수 없습니다. (diet_plan_id={diet_plan_id})"
            )
        
        # 끼니 정보 조회
        meals_result = await session.execute(
            select(DietPlanMeal)
            .where(DietPlanMeal.diet_plan_id == diet_plan_id)
            .order_by(
                # breakfast, lunch, dinner, snack 순서
                DietPlanMeal.meal_type
            )
        )
        meals = meals_result.scalars().all()
        
        # 끼니 데이터 변환
        meals_data = []
        for meal in meals:
            meals_data.append({
                "meal_id": meal.meal_id,
                "meal_type": meal.meal_type,
                "meal_name": meal.meal_name,
                "food_description": meal.food_description,
                "ingredients": meal.ingredients,
                "calories": float(meal.calories) if meal.calories else None,
                "protein": float(meal.protein) if meal.protein else None,
                "carb": float(meal.carb) if meal.carb else None,
                "fat": float(meal.fat) if meal.fat else None,
                "consumed": meal.consumed,
                "consumed_at": meal.consumed_at.isoformat() if meal.consumed_at else None
            })
        
        # 진행률 계산
        total_meals = len(meals)
        consumed_meals = sum(1 for meal in meals if meal.consumed)
        progress_percent = round(consumed_meals * 100 / total_meals, 1) if total_meals > 0 else 0
        
        # 응답 데이터 구성
        response_data = {
            "diet_plan_id": diet_plan.diet_plan_id,
            "plan_name": diet_plan.plan_name,
            "description": diet_plan.description,
            "bmr": float(diet_plan.bmr) if diet_plan.bmr else None,
            "tdee": float(diet_plan.tdee) if diet_plan.tdee else None,
            "target_calories": float(diet_plan.target_calories) if diet_plan.target_calories else None,
            "health_goal": diet_plan.health_goal,
            "total_calories": float(diet_plan.total_calories) if diet_plan.total_calories else None,
            "total_protein": float(diet_plan.total_protein) if diet_plan.total_protein else None,
            "total_carb": float(diet_plan.total_carb) if diet_plan.total_carb else None,
            "total_fat": float(diet_plan.total_fat) if diet_plan.total_fat else None,
            "created_at": diet_plan.created_at.isoformat() if diet_plan.created_at else None,
            "is_active": diet_plan.is_active,
            "meals": meals_data,
            "progress": {
                "total_meals": total_meals,
                "consumed_meals": consumed_meals,
                "progress_percent": progress_percent
            }
        }
        
        print(f"✅ 식단 상세 조회: {diet_plan_id} (진행률: {progress_percent}%)")
        
        return ApiResponse(
            success=True,
            data=response_data,
            message="✅ 식단 상세 정보를 조회했습니다."
        )
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 식단 상세 조회 실패: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"식단 상세 조회 중 오류가 발생했습니다: {str(e)}"
        )

