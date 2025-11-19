"""식단 추천 API 라우트"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.v1.schemas.diet import DietPlanRequest, DietPlanResponse
from app.api.v1.schemas.common import ApiResponse
from app.db.models import User
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

