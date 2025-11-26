"""레시피 추천 API 라우트"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import datetime, date
from typing import Optional, List, Dict, Any

from app.api.v1.schemas.recipe import (
    RecipeRecommendationRequest,
    RecipeRecommendationResponse,
    RecipeRecommendationData,
    RecipeRecommendation,
    RecipeDetailRequest,
    RecipeDetailResponse,
    SaveRecipeRequest,
    IngredientCheckRequest,
    IngredientCheckResponse,
    CustomRecipeRequest,
    CustomRecipeResponse,
    RecipeIngredient,
    RecipeStep,
    NutritionInfo,
    RecipeActionType
)
from app.api.v1.schemas.common import ApiResponse
from app.db.models import User, Food, UserFoodHistory, HealthScore, DiseaseAllergyProfile
from app.db.models_food_nutrients import FoodNutrient
from app.db.models_user_contributed import UserContributedFood
from app.db.session import get_session
from app.utils.session import get_current_user_id, is_authenticated
from app.services.recipe_recommendation_service import get_recipe_recommendation_service
from app.services.health_score_service import calculate_nrf93_score
import uuid

router = APIRouter(prefix="/recipes", tags=["Recipes"])


def detect_meal_type_from_text(text: str | None) -> Optional[str]:
    if not text:
        return None
    normalized = text.replace(" ", "").lower()
    mapping = {
        "breakfast": "breakfast",
        "아침": "breakfast",
        "모닝": "breakfast",
        "점심": "lunch",
        "런치": "lunch",
        "lunch": "lunch",
        "저녁": "dinner",
        "디너": "dinner",
        "dinner": "dinner",
        "야식": "dinner",
        "간식": "snack",
        "스낵": "snack",
        "snack": "snack",
    }
    for keyword, meal_type in mapping.items():
        if keyword in normalized:
            return meal_type
    return None


def build_user_intent_text(
    user_request: Optional[str],
    conversation_history: Optional[List[Dict[str, str]]]
) -> str:
    """대화 기록과 최신 발화를 묶어 LangChain에 전달할 사용자 의도를 구성"""
    user_sentences: List[str] = []
    if conversation_history:
        for entry in conversation_history:
            role = (entry.get("role") or "").lower()
            content = (entry.get("content") or "").strip()
            if role == "user" and content:
                user_sentences.append(content)
    latest = (user_request or "").strip()
    if latest:
        if not user_sentences or user_sentences[-1] != latest:
            user_sentences.append(latest)
    trimmed = user_sentences[-3:]  # 최근 사용자 의도 3개만 유지
    if not trimmed:
        return latest
    return "\n".join(trimmed)


@router.post("/recommendations", response_model=ApiResponse[RecipeRecommendationResponse])
async def get_recipe_recommendations(
    request: RecipeRecommendationRequest,
    user_id: int,  # TODO: 실제로는 세션에서 가져와야 함
    session: AsyncSession = Depends(get_session)
):
    """
    사용자 건강 정보와 선호도를 기반으로 레시피 3개를 추천합니다.
    
    **Args:**
        - request: 사용자 요청 (선택사항: 요청사항, 대화 히스토리)
        - user_id: 사용자 ID (현재는 쿼리 파라미터, 추후 세션에서 가져옴)
        - session: DB 세션
    
    **Returns:**
        ApiResponse[RecipeRecommendationResponse]: 추천 레시피 정보
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
        
        print(f"📊 사용자 정보 조회 완료: {user.nickname or user.username}")
        
        # 3. 사용자 질병 및 알레르기 정보 조회
        profile_stmt = select(DiseaseAllergyProfile).where(
            DiseaseAllergyProfile.user_id == user_id
        )
        profile_result = await session.execute(profile_stmt)
        profiles = profile_result.scalars().all()
        
        diseases = [p.disease_name for p in profiles if p.disease_name]
        allergies = [p.allergy_name for p in profiles if p.allergy_name]
        
        print(f"🏥 사용자 건강 정보: 질병={diseases}, 알레르기={allergies}")
        
        # 5. 오늘 섭취한 영양소 집계 및 부족 영양소 분석
        from datetime import datetime, date
        today = datetime.now().date()
        
        # 오늘 섭취한 음식들의 영양소 정보 조회 (칼로리, 나트륨 포함)
        # FoodNutrient 모델에는 vitamin_e 필드가 없으므로 제외
        today_nutrients_stmt = select(
            FoodNutrient.protein,
            FoodNutrient.carb,
            FoodNutrient.fat,
            FoodNutrient.fiber,
            FoodNutrient.vitamin_a,
            FoodNutrient.vitamin_c,
            FoodNutrient.calcium,
            FoodNutrient.iron,
            FoodNutrient.potassium,
            FoodNutrient.magnesium,
            FoodNutrient.sodium,
            HealthScore.kcal,
            UserFoodHistory.portion_size_g
        ).join(
            UserFoodHistory, FoodNutrient.food_id == UserFoodHistory.food_id
        ).outerjoin(
            HealthScore, UserFoodHistory.history_id == HealthScore.history_id
        ).where(
            and_(
                UserFoodHistory.user_id == user_id,
                func.date(UserFoodHistory.consumed_at) == today
            )
        )
        
        nutrients_result = await session.execute(today_nutrients_stmt)
        nutrients_data = nutrients_result.all()
        
        # 일일 권장량 (한국인 영양소 섭취기준)
        # vitamin_e는 FoodNutrient에 없으므로 제외
        daily_values = {
            'protein': 55.0,  # g
            'fiber': 25.0,  # g
            'vitamin_a': 700.0,  # μg RAE
            'vitamin_c': 100.0,  # mg
            'calcium': 700.0,  # mg
            'iron': 10.0 if user.gender == 'M' else 14.0,  # mg
            'potassium': 3500.0,  # mg
            'magnesium': 350.0 if user.gender == 'M' else 280.0,  # mg
            'sodium': 2000.0,  # mg
        }
        
        # 목표 칼로리 계산 (BMR 기반)
        target_calories = 2000  # 기본값
        if user.weight and user.age and user.gender:
            # 간단한 BMR 계산 (Mifflin-St Jeor)
            if user.gender == 'M':
                bmr = 10 * float(user.weight) + 6.25 * (user.age or 30) - 5 * (user.age or 30) + 5
            else:
                bmr = 10 * float(user.weight) + 6.25 * (user.age or 30) - 5 * (user.age or 30) - 161
            
            # 활동 수준에 따른 TDEE (기본: 중간 활동)
            tdee = bmr * 1.55
            
            # 건강 목표에 따른 조정
            if user.health_goal == 'loss':
                target_calories = int(tdee * 0.85)  # 15% 감소
            elif user.health_goal == 'gain':
                target_calories = int(tdee * 1.15)  # 15% 증가
            else:
                target_calories = int(tdee)
        
        # 오늘 섭취한 영양소 합계 계산
        total_nutrients = {
            'protein': 0.0,
            'fiber': 0.0,
            'vitamin_a': 0.0,
            'vitamin_c': 0.0,
            'calcium': 0.0,
            'iron': 0.0,
            'potassium': 0.0,
            'magnesium': 0.0,
            'sodium': 0.0,
        }
        total_calories = 0.0
        
        for row in nutrients_data:
            # Decimal 타입을 float로 변환하여 연산 오류 방지
            portion_size = float(row[12] or 100.0)
            portion_ratio = portion_size / 100.0  # portion_size_g / reference_value(100g)
            
            total_nutrients['protein'] += float(row[0] or 0.0) * portion_ratio
            total_nutrients['fiber'] += float(row[3] or 0.0) * portion_ratio
            total_nutrients['vitamin_a'] += float(row[4] or 0.0) * portion_ratio
            total_nutrients['vitamin_c'] += float(row[5] or 0.0) * portion_ratio
            total_nutrients['calcium'] += float(row[6] or 0.0) * portion_ratio
            total_nutrients['iron'] += float(row[7] or 0.0) * portion_ratio
            total_nutrients['potassium'] += float(row[8] or 0.0) * portion_ratio
            total_nutrients['magnesium'] += float(row[9] or 0.0) * portion_ratio
            total_nutrients['sodium'] += float(row[10] or 0.0) * portion_ratio
            total_calories += float(row[11] or 0.0)  # HealthScore.kcal은 이미 실제 섭취량
        
        # 부족한 영양소 분석 (권장량의 50% 미만인 경우)
        deficient_nutrients = []
        nutrient_names_kr = {
            'protein': '단백질',
            'fiber': '식이섬유',
            'vitamin_a': '비타민A',
            'vitamin_c': '비타민C',
            'calcium': '칼슘',
            'iron': '철분',
            'potassium': '칼륨',
            'magnesium': '마그네슘',
        }
        
        for nutrient_key, nutrient_name_kr in nutrient_names_kr.items():
            consumed = total_nutrients[nutrient_key]
            required = daily_values[nutrient_key]
            percentage = (consumed / required * 100) if required > 0 else 0
            
            if percentage < 50:  # 권장량의 50% 미만이면 부족
                deficient_nutrients.append({
                    'name': nutrient_name_kr,
                    'key': nutrient_key,
                    'consumed': round(consumed, 1),
                    'required': required,
                    'percentage': round(percentage, 1)
                })
        
        # 오늘 아무것도 안 먹었는지 확인
        has_eaten_today = len(nutrients_data) > 0
        
        # 칼로리 및 나트륨 초과 여부 확인
        calories_exceeded = total_calories >= target_calories * 1.1  # 목표 칼로리의 110% 이상
        sodium_exceeded = total_nutrients['sodium'] >= daily_values['sodium'] * 1.2  # 권장량의 120% 이상
        
        # 초과 경고 메시지 생성
        excess_warnings = []
        if calories_exceeded:
            excess_warnings.append(f"오늘 이미 목표 칼로리({target_calories:.0f}kcal)의 110% 이상을 섭취하셨습니다.")
        if sodium_exceeded:
            excess_warnings.append(f"오늘 이미 권장 나트륨량({daily_values['sodium']:.0f}mg)의 120% 이상을 섭취하셨습니다.")
        
        print(f"📊 오늘 섭취 영양소 분석:")
        print(f"  - 섭취한 음식 수: {len(nutrients_data)}개")
        print(f"  - 총 칼로리: {total_calories:.0f}kcal (목표: {target_calories}kcal)")
        print(f"  - 총 나트륨: {total_nutrients['sodium']:.0f}mg (권장: {daily_values['sodium']:.0f}mg)")
        print(f"  - 부족한 영양소: {[n['name'] for n in deficient_nutrients]}")
        print(f"  - 칼로리 초과: {calories_exceeded}, 나트륨 초과: {sodium_exceeded}")
        print(f"  - 초과 경고: {excess_warnings}")
        
        health_context_parts = []
        if not has_eaten_today:
            health_context_parts.append("오늘은 아직 아무것도 드시지 않았어요.")
        else:
            health_context_parts.append(
                f"오늘 섭취 칼로리는 {total_calories:.0f}kcal, 목표는 {target_calories}kcal입니다."
            )
        if deficient_nutrients:
            lacking = ", ".join([n["name"] for n in deficient_nutrients[:3]])
            health_context_parts.append(f"{lacking} 보충이 필요해 보여요.")
        if diseases:
            disease_text = ", ".join(diseases)
            health_context_parts.append(f"{disease_text} 관리 중이라 자극적이지 않은 메뉴를 추천드리고 싶어요.")
        health_context_text = " ".join(health_context_parts).strip()
        
        request_text_clean = (request.user_request or "").strip()
        detected_meal_type = request.meal_type or detect_meal_type_from_text(request_text_clean)
        combined_user_intent = build_user_intent_text(request.user_request, request.conversation_history)
        
        # 음식 관련이 아닌 요청인지 확인
        user_request_lower = (request.user_request or "").lower()
        non_food_keywords = ["날씨", "시간", "날짜", "계산", "수학", "게임", "영화", "음악", "책", "여행"]
        is_non_food_request = any(keyword in user_request_lower for keyword in non_food_keywords)
        
        if is_non_food_request:
            gentle_message = f"{user.nickname or '고객'}님, 음식 관련해서 말씀해주시면 도와드릴게요! 🍳\n\n레시피 추천이나 식단 관리에 대해 궁금하신 점이 있으시면 언제든지 말씀해주세요!"
            
            return ApiResponse(
                success=True,
                data=RecipeRecommendationResponse(
                    response_id=f"recipe-{uuid.uuid4()}",
                    action_type="TEXT_ONLY",
                    message=gentle_message,
                    data=RecipeRecommendationData(
                        inferred_preference="음식 관련이 아닌 요청",
                        user_friendly_message=gentle_message
                    ),
                    suggestions=["샐러드 추천해줘", "저녁 메뉴 알려줘"]
                ),
                message="✅ 음식 관련 안내 메시지"
            )
        
        # 사용자가 실제로 음식 요청을 했는지 확인
        # 빈 문자열이 아니고, 단순 인사나 의미 없는 텍스트가 아닌 경우
        user_request_clean = (request.user_request or "").strip()
        has_food_request = len(user_request_clean) > 0
        
        # 음식 관련 키워드가 있는지 확인 (더 확실한 판단)
        food_keywords_in_request = ["먹", "요리", "레시피", "음식", "식사", "간식", "치킨", "피자", "라면", "떡볶이", 
                                     "국", "찌개", "볶음", "구이", "튀김", "샐러드", "밥", "면", "떡", "고기", "생선", 
                                     "야채", "채소", "과일", "디저트", "케이크", "커피", "차", "주스"]
        has_food_keyword = any(keyword in user_request_clean for keyword in food_keywords_in_request)
        
        # 사용자가 실제로 음식 요청을 한 경우 (키워드가 있거나, 충분히 긴 텍스트인 경우)
        is_actual_food_request = has_food_request and (has_food_keyword or len(user_request_clean) > 5)
        
        # 칼로리나 나트륨 초과 시 alert 메시지 표시
        # 단, 사용자가 실제로 음식 요청을 한 경우는 alert를 건너뛰고 레시피 추천 진행
        if has_eaten_today and (calories_exceeded or sodium_exceeded) and not is_actual_food_request:
            warning_messages = []
            if calories_exceeded:
                warning_messages.append(f"오늘 이미 목표 칼로리({target_calories}kcal) 이상을 섭취하셨습니다.")
            if sodium_exceeded:
                warning_messages.append(f"오늘 이미 권장 나트륨량({daily_values['sodium']:.0f}mg) 이상을 섭취하셨습니다.")
            
            warning_text = " ".join(warning_messages)
            alert_message = f"{user.nickname or '고객'}님, {warning_text}\n\n더 드시면 건강에 좋지 않을 수 있으니, 자제하는 편이 훨씬 좋을 것 같아요! 😊\n\n하지만 원하시는 음식이 있다면 말씀해주세요. 레시피를 추천해드릴게요!"
            
            return ApiResponse(
                success=True,
                data=RecipeRecommendationResponse(
                    response_id=f"recipe-{uuid.uuid4()}",
                    action_type="TEXT_ONLY",
                    message=alert_message,
                    data=RecipeRecommendationData(
                        inferred_preference="오늘 충분히 섭취하여 추가 섭취 자제 권장",
                        user_friendly_message=alert_message
                    ),
                    suggestions=["그래도 추천해줘", "내일 다시 추천받을게"]
                ),
                message="✅ 건강을 위한 자제 권장 메시지"
            )
        
        recipe_service = get_recipe_recommendation_service()
        print(f"[Recommend] Phase-0 user={user_id} Clarification pipeline 시작")
        decision = await recipe_service.decide_recipe_tool(
            user=user,
            user_request=request.user_request or "",
            health_context=health_context_text,
            conversation_history=request.conversation_history
        )
        decision_meal_type = decision.get("meal_type")
        call_tool = bool(decision.get("call_tool"))
        assistant_reply = decision.get("assistant_reply") or "조금 더 자세히 말씀해주시면 레시피를 준비해드릴게요!"
        decision_suggestions = decision.get("suggestions") or []
        if not call_tool:
            suggestions = decision_suggestions or [
                "자세히 알려줄게",
                "다른 재료 말해줄게"
            ]
            return ApiResponse(
                success=True,
                data=RecipeRecommendationResponse(
                    response_id=f"recipe-{uuid.uuid4()}",
                    action_type="TEXT_ONLY",
                    message=assistant_reply,
                    data=None,
                    suggestions=suggestions
                ),
                message="✅ 대화형 안내 메시지"
            )
        
        combined_meal_type = decision_meal_type or detected_meal_type
        if not combined_meal_type:
            confirmation_message = (
                f"{assistant_reply}\n\n"
                "어느 끼니에 드실 계획인지 알려주시면 맞춤 레시피를 바로 추천해드릴게요!"
            )
            suggestions = decision_suggestions or [
                "아침으로 먹을래",
                "점심으로 부탁해",
                "저녁 레시피 궁금해",
                "간식으로 먹을래"
            ]
            return ApiResponse(
                success=True,
                data=RecipeRecommendationResponse(
                    response_id=f"recipe-{uuid.uuid4()}",
                    action_type="CONFIRMATION",
                    message=confirmation_message,
                    data=None,
                    suggestions=suggestions
                ),
                message="✅ 식사 유형 확인 필요"
            )
        
        # 6. 레시피 추천 서비스 호출 (칼로리/나트륨 초과가 아닌 경우에만)
        recipe_service = get_recipe_recommendation_service()
        result_data = await recipe_service.get_recipe_recommendations(
            user=user,
            user_request=request.user_request or "",
            llm_user_intent=combined_user_intent,
            conversation_history=request.conversation_history,
            diseases=diseases if diseases else None,
            allergies=allergies if allergies else None,
            user_nickname=user.nickname or user.username,
            has_eaten_today=has_eaten_today,
            deficient_nutrients=deficient_nutrients if deficient_nutrients else None,
            meal_type=combined_meal_type,
            excess_warnings=excess_warnings  # ✨ 초과 경고 전달
        )
        
        print(f"[Recommend] Phase-1 카드 추천 완료 user={user_id}, count={len(result_data.get('recommendations', []))}")
        
        health_warning_text = result_data.get("health_warning")
        if health_warning_text:
            confirmation = await recipe_service.evaluate_health_warning(
                user=user,
                user_request=combined_user_intent,
                health_warning=health_warning_text,
                conversation_history=request.conversation_history
            )
            if confirmation.get("requires_confirmation"):
                confirm_message = confirmation.get("assistant_reply") or (
                    f"{health_warning_text}\n\n정말 그대로 진행할까요?"
                )
                confirm_suggestions = confirmation.get("suggestions") or [
                    "그래도 진행할래",
                    "다른 메뉴 추천해줘"
                ]
                return ApiResponse(
                    success=True,
                    data=RecipeRecommendationResponse(
                        response_id=f"recipe-{uuid.uuid4()}",
                        action_type="TEXT_ONLY",
                        message=confirm_message,
                        data=None,
                        suggestions=confirm_suggestions
                    ),
                    message="⚠️ 건강 경고 확인 필요"
                )
        
        recipes = [
            RecipeRecommendation(**rec) for rec in result_data.get("recommendations", [])
        ] if result_data.get("recommendations") else []
        response_message = result_data.get("user_friendly_message") or "원하시는 레시피를 아래에서 선택해주세요!"
        response_data = RecipeRecommendationData(
            recipes=recipes or None,
            inferred_preference=result_data.get("inferred_preference"),
            health_warning=result_data.get("health_warning"),
            user_friendly_message=result_data.get("user_friendly_message")
        )
        result_suggestions = await recipe_service.generate_action_suggestions(
            action_type="RECOMMENDATION_RESULT",
            user_request=combined_user_intent,
            meal_type=combined_meal_type,
            recommendations=result_data.get("recommendations"),
            deficient_nutrients=deficient_nutrients if deficient_nutrients else None,
            diseases=diseases if diseases else None,
            assistant_message=response_message
        )
        suggestions = result_suggestions or ["다른 메뉴도 추천해줘", "다른 식사로 바꿀래"]
        
        return ApiResponse(
            success=True,
            data=RecipeRecommendationResponse(
                response_id=f"recipe-{uuid.uuid4()}",
                action_type="RECOMMENDATION_RESULT",
                message=response_message,
                data=response_data,
                suggestions=suggestions
            ),
            message="✅ 레시피 추천이 완료되었습니다."
        )
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 레시피 추천 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"레시피 추천 중 오류가 발생했습니다: {str(e)}"
        )


@router.post("/detail", response_model=ApiResponse[RecipeDetailResponse])
async def get_recipe_detail(
    request: RecipeDetailRequest,
    user_id: int,  # TODO: 실제로는 세션에서 가져와야 함
    session: AsyncSession = Depends(get_session)
):
    """
    선택한 레시피의 상세 단계별 조리법을 제공합니다.
    
    **Args:**
        - request: 레시피 상세 요청 (recipe_name)
        - user_id: 사용자 ID
        - session: DB 세션
    
    **Returns:**
        ApiResponse[RecipeDetailResponse]: 레시피 상세 정보
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
        
        print(f"📖 '{request.recipe_name}' 레시피 상세 조회 중...")
        
        # 2. 레시피 상세 정보 조회
        recipe_service = get_recipe_recommendation_service()
        result_data = await recipe_service.get_recipe_detail(
            recipe_name=request.recipe_name,
            user=user
        )
        
        print(f"✅ 레시피 상세 정보 조회 완료: 총 {result_data.get('total_steps', 0)}단계")
        
        # 3. 응답 반환
        return ApiResponse(
            success=True,
            data=RecipeDetailResponse(**result_data),
            message="✅ 레시피 상세 정보를 불러왔습니다."
        )
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 레시피 상세 조회 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"레시피 상세 조회 중 오류가 발생했습니다: {str(e)}"
        )


@router.post("/ingredient-check", response_model=ApiResponse[IngredientCheckResponse])
async def ingredient_check(
    request: IngredientCheckRequest,
    user_id: int,
    session: AsyncSession = Depends(get_session)
):
    """레시피 재료 확인용 빠른 조회"""
    result = await session.execute(select(User).where(User.user_id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다.")
    recipe_service = get_recipe_recommendation_service()
    print(f"[Recommend] Phase-INGREDIENT_CHECK start user={user_id}, recipe={request.recipe_name}")
    ingredient_list = await recipe_service.get_ingredient_check(request.recipe_name)
    normalized = [item for item in ingredient_list if item.get("name") or item.get("amount")]
    formatted = [
        (f"{item.get('name', '').strip()} {item.get('amount', '').strip()}").strip()
        for item in normalized
    ]
    print(f"[Recommend] Phase-INGREDIENT_CHECK done user={user_id}, count={len(formatted)}")
    return ApiResponse(
        success=True,
        data=IngredientCheckResponse(
            response_id=f"recipe-{uuid.uuid4()}",
            action_type=RecipeActionType.INGREDIENT_CHECK,
            recipe_name=request.recipe_name,
            ingredients=formatted
        ),
        message="✅ 필요한 재료를 확인했습니다."
    )


@router.post("/custom-recipe", response_model=ApiResponse[CustomRecipeResponse])
async def generate_custom_recipe(
    request: CustomRecipeRequest,
    user_id: int,
    session: AsyncSession = Depends(get_session)
):
    """재료 제외 정보를 반영한 맞춤 조리법 생성"""
    result = await session.execute(select(User).where(User.user_id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다.")
    recipe_service = get_recipe_recommendation_service()
    print(f"[Recommend] Phase-COOKING_STEPS start user={user_id}, recipe={request.recipe_name}, excluded={len(request.excluded_ingredients)}")
    custom_result = await recipe_service.generate_custom_cooking_steps(
        user=user,
        recipe_name=request.recipe_name,
        excluded_ingredients=request.excluded_ingredients,
        allowed_ingredients=request.available_ingredients,
        meal_type=request.meal_type
    )
    ingredient_models = [
        RecipeIngredient(name=ing.get("name", "재료"), amount=ing.get("amount", "적당량"))
        for ing in custom_result.get("ingredients", [])
    ]
    step_models = [
        RecipeStep(
            step_number=int(step.get("step_number") or idx + 1),
            title=step.get("title") or f"단계 {idx + 1}",
            description=step.get("description") or "",
            tip=step.get("tip")
        )
        for idx, step in enumerate(custom_result.get("steps") or [])
    ]
    nutrition_payload = custom_result.get("nutrition_info") or {}
    def _extract_int(value: Any) -> int:
        if value is None:
            return 0
        text = str(value).lower().replace("kcal", "").strip()
        try:
            return int(float(text))
        except ValueError:
            return 0

    nutrition_info = NutritionInfo(
        calories=_extract_int(nutrition_payload.get("calories")),
        protein=str(nutrition_payload.get("protein") or "0g"),
        carbs=str(nutrition_payload.get("carbs") or "0g"),
        fat=str(nutrition_payload.get("fat") or "0g"),
        fiber=nutrition_payload.get("fiber"),
        sodium=nutrition_payload.get("sodium")
    )
    response = CustomRecipeResponse(
        response_id=f"recipe-{uuid.uuid4()}",
        recipe_name=request.recipe_name,
        action_type=RecipeActionType.COOKING_STEPS,
        ingredients=ingredient_models,
        instructions_markdown=custom_result.get("instructions_markdown", ""),
        steps=step_models,
        nutrition_info=nutrition_info,
        estimated_time=custom_result.get("estimated_time"),
        intro=custom_result.get("intro")
    )
    print(f"[Recommend] Phase-COOKING_STEPS done user={user_id}, steps={len(step_models)}")
    return ApiResponse(
        success=True,
        data=response,
        message="✅ 맞춤 조리법을 생성했습니다."
    )


def _parse_nutrient_value(value: Any, unit: str = "") -> float:
    """영양소 문자열 (예: '120kcal', '10g', '200mg')을 float으로 파싱합니다."""
    if value is None:
        return 0.0
    text = str(value).lower().replace(unit.lower(), "").strip()
    try:
        return float(text)
    except ValueError:
        return 0.0


@router.post("/save", response_model=ApiResponse[dict])
async def save_recipe_as_meal(
    save_request: SaveRecipeRequest,
    http_request: Request,
    session: AsyncSession = Depends(get_session)
):
    """
    레시피 완료 후 식단 기록을 저장하고 건강 점수를 계산합니다.
    
    **전체 플로우:**
    1. Food 테이블 확인/생성
    2. UserFoodHistory 저장
    3. NRF9.3 점수 계산
    4. HealthScore 저장
    
    **Args:**
        - save_request: 레시피 저장 요청
        - http_request: HTTP Request 객체
        - session: DB 세션
    
    **Returns:**
        ApiResponse[MealRecordResponse]: 저장된 식단 기록 + 건강 점수
    """
    try:
        # 인증 확인
        if not is_authenticated(http_request):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="인증이 필요합니다. 로그인해주세요."
            )
        
        user_id = get_current_user_id(http_request)
        
        print(f"💾 레시피 '{save_request.recipe_name}' 식단 기록 저장 시작...")
        
        # 영양소 값 파싱
        calories = _parse_nutrient_value(save_request.nutrition_info.calories, "kcal")
        protein_g = _parse_nutrient_value(save_request.nutrition_info.protein, "g")
        fat_g = _parse_nutrient_value(save_request.nutrition_info.fat, "g")
        carbs_g = _parse_nutrient_value(save_request.nutrition_info.carbs, "g")
        fiber_g = _parse_nutrient_value(save_request.nutrition_info.fiber, "g")
        sodium_mg = _parse_nutrient_value(save_request.nutrition_info.sodium, "mg")
        
        # 인분 비율 적용
        actual_calories = calories * save_request.actual_servings
        actual_protein_g = protein_g * save_request.actual_servings
        actual_fat_g = fat_g * save_request.actual_servings
        actual_carbs_g = carbs_g * save_request.actual_servings
        actual_fiber_g = fiber_g * save_request.actual_servings
        actual_sodium_mg = sodium_mg * save_request.actual_servings
        
        # ========== STEP 1: food_nutrients에서 실제 음식 매칭 ==========
        from app.services.food_matching_service import get_food_matching_service
        
        matching_service = get_food_matching_service()
        
        # 재료 리스트 추출
        ingredient_list = save_request.ingredients if save_request.ingredients else []
        
        # DB에서 실제 음식 매칭 (user_id 전달)
        matched_food_nutrient = await matching_service.match_food_to_db(
            session=session,
            food_name=save_request.recipe_name,
            ingredients=ingredient_list,
            food_class_hint=save_request.food_class_1,
            user_id=user_id
        )
        
        # 매칭된 food_id 사용
        if matched_food_nutrient:
            actual_food_id = matched_food_nutrient.food_id
            actual_food_class_1 = getattr(matched_food_nutrient, 'food_class1', None)
            actual_food_class_2 = getattr(matched_food_nutrient, 'food_class2', None)
            
            if isinstance(matched_food_nutrient, FoodNutrient):
                print(f"✅ food_nutrients 매칭 성공: {actual_food_id} - {matched_food_nutrient.nutrient_name}")
            else:
                print(f"✅ user_contributed_foods 매칭 성공: {actual_food_id} - {matched_food_nutrient.food_name}")
        else:
            # 매칭 실패 시: user_contributed_foods에 새로 추가
            print(f"⚠️ 매칭 실패, user_contributed_foods에 새로 추가")
            
            actual_food_id = f"USER_{user_id}_{int(datetime.now().timestamp())}"[:200]
            actual_food_class_1 = save_request.food_class_1 or "사용자추가"
            actual_food_class_2 = save_request.recipe_name
            
            # user_contributed_foods에 추가
            new_contributed_food = UserContributedFood(
                food_id=actual_food_id,
                user_id=user_id,
                food_name=save_request.recipe_name,
                nutrient_name=save_request.recipe_name,
                food_class1=actual_food_class_1,
                food_class2=actual_food_class_2,
                ingredients=", ".join(ingredient_list) if ingredient_list else None,
                unit="g",
                reference_value=save_request.portion_size_g,
                protein=actual_protein_g,
                carb=actual_carbs_g,
                fat=actual_fat_g,
                fiber=actual_fiber_g,
                sodium=actual_sodium_mg,
                usage_count=1
            )
            session.add(new_contributed_food)
            await session.flush()
            
            print(f"✅ user_contributed_foods에 저장: {actual_food_id} - {save_request.recipe_name}")
        
        # Food 테이블 확인/생성
        food_stmt = select(Food).where(Food.food_id == actual_food_id)
        food_result = await session.execute(food_stmt)
        food = food_result.scalar_one_or_none()
        
        if not food:
            # 재료 목록을 콤마로 구분된 문자열로 변환
            ingredients_str = ", ".join(ingredient_list) if ingredient_list else None
            
            food = Food(
                food_id=actual_food_id,
                food_name=save_request.recipe_name,
                category="요리",
                food_class_1=actual_food_class_1,
                food_class_2=actual_food_class_2,
                ingredients=ingredients_str
            )
            session.add(food)
            await session.flush()
            print(f"✅ 새로운 Food 레코드 생성: {food.food_name} (ID={food.food_id})")
            print(f"   - 재료: {ingredients_str}")
            print(f"   - 분류: {actual_food_class_1}")
        else:
            # 기존 레코드가 있어도 재료 정보 업데이트
            if ingredient_list:
                ingredients_str = ", ".join(ingredient_list)
                food.ingredients = ingredients_str
                print(f"✅ 기존 Food 레코드 재료 정보 업데이트: {ingredients_str}")
            print(f"✅ 기존 Food 레코드 사용: {food.food_name} (ID={actual_food_id})")
        
        food_id = actual_food_id
        
        # ========== STEP 2: FoodNutrient 테이블에 영양소 정보 저장 (선택사항) ==========
        # 나중에 조회할 수 있도록 저장
        nutrient_stmt = select(FoodNutrient).where(FoodNutrient.food_id == food_id)
        nutrient_result = await session.execute(nutrient_stmt)
        nutrient = nutrient_result.scalar_one_or_none()
        
        if not nutrient:
            # FoodNutrient 레코드 생성
            nutrient = FoodNutrient(
                food_id=food_id,
                representative_food_name=save_request.recipe_name,
                reference_value=100.0,  # 기준량 100g
                protein=protein_g,
                fat=fat_g,
                carb=carbs_g,
                fiber=fiber_g,
                sodium=sodium_mg,
                # 기본값
                calcium=0.0,
                iron=0.0,
                potassium=0.0,
                vitamin_a=0.0,
                vitamin_c=0.0,
                saturated_fat=0.0,
                added_sugar=0.0
            )
            session.add(nutrient)
            await session.flush()
            print(f"✅ FoodNutrient 레코드 생성 완료")
        
        # ========== STEP 3: UserFoodHistory 저장 ==========
        # portion_size_g 계산 (인분 * 기본량 100g)
        portion_size_g = save_request.actual_servings * 100.0
        
        print(f"📝 UserFoodHistory 저장 - meal_type={save_request.meal_type}")
        food_history = UserFoodHistory(
            user_id=user_id,
            food_id=food_id,
            food_name=save_request.recipe_name,
            consumed_at=datetime.now(),
            portion_size_g=portion_size_g,
            meal_type=save_request.meal_type  # ✨ meal_type 추가
        )
        session.add(food_history)
        await session.flush()
        await session.refresh(food_history)
        print(f"✅ UserFoodHistory 저장 완료 (ID={food_history.history_id})")
        
        # ========== STEP 4: NRF9.3 점수 계산 ==========
        # calculate_nrf93_score는 영양소 값들을 직접 받음
        # reference_value_g는 실제 섭취량(portion_size_g)을 사용
        nrf_result = await calculate_nrf93_score(
            protein_g=actual_protein_g,
            fiber_g=actual_fiber_g,
            vitamin_a_ug=0.0,  # 레시피에서 제공하지 않음
            vitamin_c_mg=0.0,
            vitamin_e_mg=0.0,
            calcium_mg=0.0,
            iron_mg=0.0,
            potassium_mg=0.0,
            magnesium_mg=0.0,
            saturated_fat_g=0.0,
            added_sugar_g=0.0,
            sodium_mg=actual_sodium_mg,
            reference_value_g=portion_size_g  # 실제 섭취량 사용
        )
        
        nrf_score = nrf_result.get('final_score', 0)
        print(f"📊 NRF9.3 점수 계산: {nrf_score:.2f}")
        
        # ========== STEP 5: HealthScore 저장 ==========
        health_score = HealthScore(
            history_id=food_history.history_id,
            user_id=user_id,
            food_id=food_id,
            reference_value=100,
            kcal=int(actual_calories),
            positive_score=nrf_result.get('positive_score'),
            negative_score=nrf_result.get('negative_score'),
            final_score=int(nrf_score),
            food_grade=nrf_result.get('food_grade'),
            calc_method="NRF9.3"
        )
        session.add(health_score)
        await session.flush()
        print(f"✅ HealthScore 저장 완료")
        
        await session.commit()
        
        # ========== STEP 6: 응답 반환 ==========
        # 프론트엔드에서 nrf_score를 기대하므로 health_score 대신 nrf_score 사용
        response_data = {
            "history_id": food_history.history_id,
            "user_id": user_id,
            "food_id": food_id,
            "food_name": save_request.recipe_name,
            "consumed_at": food_history.consumed_at.isoformat(),
            "portion_size_g": portion_size_g,
            "calories": int(actual_calories),
            "nrf_score": float(nrf_score),  # 프론트엔드에서 nrf_score로 접근
            "health_score": int(nrf_score),  # 호환성을 위해 둘 다 제공
            "food_grade": nrf_result.get('food_grade')
        }
        
        return ApiResponse(
            success=True,
            data=response_data,
            message=f"✅ 레시피가 식단에 기록되었습니다! (NRF9.3 점수: {nrf_score:.1f})"
        )
    
    except Exception as e:
        await session.rollback()
        print(f"❌ 레시피 저장 오류: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"레시피 저장 중 오류가 발생했습니다: {str(e)}"
        )
