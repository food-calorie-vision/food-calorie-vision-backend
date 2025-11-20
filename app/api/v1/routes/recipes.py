"""레시피 추천 API 라우트"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import datetime, date

from app.api.v1.schemas.recipe import (
    RecipeRecommendationRequest,
    RecipeRecommendationResponse,
    RecipeDetailRequest,
    RecipeDetailResponse,
    SaveRecipeRequest
)
from app.api.v1.schemas.common import ApiResponse
from app.db.models import User, Food, UserFoodHistory, HealthScore, DiseaseAllergyProfile
from app.db.models_food_nutrients import FoodNutrient
from app.db.session import get_session
from app.utils.session import get_current_user_id, is_authenticated
from app.services.recipe_recommendation_service import get_recipe_recommendation_service
from app.services.health_score_service import calculate_nrf93_score
import uuid

router = APIRouter(prefix="/recipes", tags=["Recipes"])


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
        
        # 4. 오늘 섭취한 영양소 집계 및 부족 영양소 분석
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
        
        # 음식 관련이 아닌 요청인지 확인
        user_request_lower = (request.user_request or "").lower()
        non_food_keywords = ["날씨", "시간", "날짜", "계산", "수학", "게임", "영화", "음악", "책", "여행"]
        is_non_food_request = any(keyword in user_request_lower for keyword in non_food_keywords)
        
        if is_non_food_request:
            gentle_message = f"{user.nickname or '고객'}님, 음식 관련해서 말씀해주시면 도와드릴게요! 🍳\n\n레시피 추천이나 식단 관리에 대해 궁금하신 점이 있으시면 언제든지 말씀해주세요!"
            
            return ApiResponse(
                success=True,
                data=RecipeRecommendationResponse(
                    inferred_preference="음식 관련이 아닌 요청",
                    health_warning=None,
                    user_friendly_message=gentle_message,
                    recommendations=[]  # 레시피 추천 없음
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
                    inferred_preference="오늘 충분히 섭취하여 추가 섭취 자제 권장",
                    health_warning=None,
                    user_friendly_message=alert_message,
                    recommendations=[]  # 레시피 추천 없음 - 사용자가 다시 요청하면 그때 추천
                ),
                message="✅ 건강을 위한 자제 권장 메시지"
            )
        
        # 5. 레시피 추천 서비스 호출 (칼로리/나트륨 초과가 아닌 경우에만)
        recipe_service = get_recipe_recommendation_service()
        result_data = await recipe_service.get_recipe_recommendations(
            user=user,
            user_request=request.user_request,
            conversation_history=request.conversation_history,
            diseases=diseases if diseases else None,
            allergies=allergies if allergies else None,
            user_nickname=user.nickname or user.username,
            has_eaten_today=has_eaten_today,
            deficient_nutrients=deficient_nutrients if deficient_nutrients else None,
            meal_type=request.meal_type,  # ✨ 식사 유형 전달
            excess_warnings=excess_warnings  # ✨ 초과 경고 전달
        )
        
        print(f"✅ 레시피 추천 완료: {len(result_data.get('recommendations', []))}개")
        
        # 6. 응답 반환
        return ApiResponse(
            success=True,
            data=RecipeRecommendationResponse(**result_data),
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
        calories = float(save_request.nutrition_info.calories)
        protein_g = float(save_request.nutrition_info.protein.replace('g', '').replace('G', ''))
        fat_g = float(save_request.nutrition_info.fat.replace('g', '').replace('G', ''))
        carbs_g = float(save_request.nutrition_info.carbs.replace('g', '').replace('G', ''))
        fiber_g = float(save_request.nutrition_info.fiber.replace('g', '').replace('G', '')) if save_request.nutrition_info.fiber else 0.0
        sodium_mg = float(save_request.nutrition_info.sodium.replace('mg', '').replace('MG', '')) if save_request.nutrition_info.sodium else 0.0
        
        # 인분 비율 적용
        actual_calories = calories * save_request.actual_servings
        actual_protein_g = protein_g * save_request.actual_servings
        actual_fat_g = fat_g * save_request.actual_servings
        actual_carbs_g = carbs_g * save_request.actual_servings
        actual_fiber_g = fiber_g * save_request.actual_servings
        actual_sodium_mg = sodium_mg * save_request.actual_servings
        
        # ========== STEP 1: Food 테이블 확인/생성 ==========
        # food_name으로 검색
        food_stmt = select(Food).where(Food.food_name == save_request.recipe_name)
        food_result = await session.execute(food_stmt)
        food = food_result.scalar_one_or_none()
        
        if not food:
            # Food 레코드 생성 (food_id는 UUID 생성)
            food_id = str(uuid.uuid4())[:200]  # VARCHAR(200) 제한
            
            # 재료 목록을 콤마로 구분된 문자열로 변환
            ingredients_str = ""
            if save_request.ingredients:
                ingredients_str = ", ".join(save_request.ingredients)
            
            # 음식 분류 설정 (기본값: 요리)
            food_class_1 = save_request.food_class_1 or "요리"
            
            food = Food(
                food_id=food_id,
                food_name=save_request.recipe_name,
                category="요리",
                food_class_1=food_class_1,  # 음식 대분류 (볶음류, 구이류 등)
                food_class_2=save_request.recipe_name,  # 음식 명칭
                ingredients=ingredients_str if ingredients_str else None  # 재료 목록
            )
            session.add(food)
            await session.flush()
            print(f"✅ 새로운 Food 레코드 생성: {food.food_name} (ID={food.food_id})")
            print(f"   - 재료: {ingredients_str}")
            print(f"   - 분류: {food_class_1}")
        else:
            food_id = food.food_id
            # 기존 레코드가 있어도 재료 정보 업데이트
            if save_request.ingredients:
                ingredients_str = ", ".join(save_request.ingredients)
                food.ingredients = ingredients_str
                print(f"✅ 기존 Food 레코드 재료 정보 업데이트: {ingredients_str}")
            if save_request.food_class_1:
                food.food_class_1 = save_request.food_class_1
            print(f"✅ 기존 Food 레코드 사용: {food.food_name} (ID={food_id})")
        
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


