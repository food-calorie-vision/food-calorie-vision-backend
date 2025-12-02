"""음식 이미지 분석 관련 라우트"""

import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.common import ApiResponse
from app.api.v1.schemas.vision import (
    FoodAnalysisData,
    FoodAnalysisRequest,
    FoodAnalysisResult,
    FoodNutrients,
    FoodReanalysisRequest,
    SaveFoodRequest,
    SaveFoodResponse,
    PreviewNutritionRequest,
    PreviewNutritionResponse,
    FoodCandidate,
)
from app.db.session import get_session
from app.db.models_food_nutrients import FoodNutrient
from app.db.models_user_contributed import UserContributedFood
from app.services.gpt_vision_service import get_gpt_vision_service
from app.services.yolo_service import get_yolo_service
from app.services.food_matching_service import get_food_matching_service
from app.services.llm_nutrient_estimator import get_nutrient_estimator
from app.services.health_score_service import calculate_nrf93_score, create_health_score, calculate_food_grade
from app.services.food_service import get_or_create_food
from app.services.food_history_service import create_food_history
from app.utils.food_name import extract_display_name

router = APIRouter()


def _analyze_food_image(file_name: str) -> FoodAnalysisResult:
    """음식 이미지 분석 (목 구현)"""
    # TODO: 실제 AI 비전 모델로 대체
    lower_name = file_name.lower()

    # 간단한 규칙 기반 분석
    if "pizza" in lower_name or "피자" in lower_name:
        return FoodAnalysisResult(
            foodName="피자",
            calories=800,
            nutrients=FoodNutrients(protein=30, carbs=80, fat=40, sodium=1500),
            confidence=0.87,
            suggestions=["피자는 칼로리가 높으니 적당히 섭취하세요.", "채소를 추가하여 영양 균형을 맞추세요."],
        )
    elif "salad" in lower_name or "샐러드" in lower_name:
        return FoodAnalysisResult(
            foodName="샐러드",
            calories=250,
            nutrients=FoodNutrients(protein=15, carbs=20, fat=10, sodium=300),
            confidence=0.92,
            suggestions=["신선한 채소와 단백질이 풍부한 샐러드입니다.", "드레싱 양을 조절하여 칼로리를 낮출 수 있습니다."],
        )
    elif "burger" in lower_name or "햄버거" in lower_name:
        return FoodAnalysisResult(
            foodName="햄버거",
            calories=600,
            nutrients=FoodNutrients(protein=25, carbs=50, fat=35, sodium=1000),
            confidence=0.89,
            suggestions=["햄버거는 지방 함량이 높을 수 있습니다.", "탄산음료 대신 물을 마시는 것이 좋습니다."],
        )
    elif "rice" in lower_name or "밥" in lower_name:
        return FoodAnalysisResult(
            foodName="밥",
            calories=300,
            nutrients=FoodNutrients(protein=5, carbs=60, fat=1, sodium=5),
            confidence=0.95,
            suggestions=["탄수화물 섭취의 좋은 원천입니다.", "다양한 반찬과 함께 균형 잡힌 식사를 하세요."],
        )
    elif "chicken" in lower_name or "치킨" in lower_name:
        return FoodAnalysisResult(
            foodName="치킨",
            calories=700,
            nutrients=FoodNutrients(protein=40, carbs=30, fat=50, sodium=1200),
            confidence=0.88,
            suggestions=[
                "단백질이 풍부하지만 튀긴 치킨은 지방 함량이 높습니다.",
                "구운 치킨이나 닭가슴살을 선택하는 것이 좋습니다.",
            ],
        )
    elif "kimchi" in lower_name or "김치" in lower_name:
        return FoodAnalysisResult(
            foodName="김치찌개",
            calories=250,
            nutrients=FoodNutrients(protein=12, carbs=20, fat=8, sodium=800),
            confidence=0.85,
            suggestions=["균형 잡힌 영양소를 포함하고 있습니다.", "적당한 양으로 섭취하시기 바랍니다.", "채소와 함께 드시면 더욱 좋습니다."],
        )
    else:
        return FoodAnalysisResult(
            foodName="알 수 없는 음식",
            calories=350,
            nutrients=FoodNutrients(protein=15, carbs=40, fat=12, sodium=600),
            confidence=0.60,
            suggestions=["다양한 음식을 섭취하여 균형 잡힌 식단을 유지하세요."],
        )


@router.post("/analysis", response_model=ApiResponse[FoodAnalysisData])
async def analyze_food_image(request: FoodAnalysisRequest) -> ApiResponse[FoodAnalysisData]:
    """음식 이미지 분석 (메모리 기반 스텁) - 레거시 엔드포인트"""
    start_time = time.time()

    # 이미지 분석 시뮬레이션 (약간의 지연)
    # time.sleep(0.5)  # 실제 API에서는 AI 모델 처리 시간

    analysis_result = _analyze_food_image(request.file_name)
    processing_time = int((time.time() - start_time) * 1000)  # ms

    return ApiResponse(
        success=True,
        data=FoodAnalysisData(
            analysis=analysis_result,
            timestamp=datetime.now(timezone.utc).isoformat(),
            processingTime=processing_time,
        ),
    )


@router.post("/analysis-upload", response_model=ApiResponse[FoodAnalysisData])
async def analyze_food_image_with_yolo_gpt(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session)
) -> ApiResponse[FoodAnalysisData]:
    """
    음식 이미지 분석 (YOLO + GPT-Vision 2단계 + DB 파이프라인)
    
    **처리 과정 (2단계 GPT 방식):**
    1. 사용자가 이미지 업로드
    2. YOLO 모델로 음식 객체 detection
    3. DB에서 대분류 목록 조회 (예: "피자", "밥류", "국 및 탕류" 등)
    4. [1차 GPT] 이미지 + 대분류 목록 → GPT가 대분류 선택
    5. 선택된 대분류의 모든 음식 조회 (예: 피자류 78개)
    6. [2차 GPT] 이미지 + 음식 목록 → GPT가 구체적인 음식 선택
    7. 선택된 음식의 영양소 데이터 반환
    
    **장점:**
    - DB에 실제로 있는 음식만 선택하므로 매칭 정확도 100%
    - "비슷한 이름" 찾기 불필요
    
    **Args:**
        file: 업로드된 이미지 파일 (JPEG, PNG 등)
        session: DB 세션
        
    **Returns:**
        음식 분석 결과 (음식명, 재료, 칼로리, 영양소, 건강 제안 등)
    """
    start_time = time.time()
    
    try:
        # 1. 이미지 파일 읽기
        image_bytes = await file.read()
        
        if not image_bytes:
            raise HTTPException(status_code=400, detail="이미지 파일이 비어있습니다.")
        
        # 2. YOLO detection 실행
        print("🔍 YOLO detection 시작...")
        yolo_service = get_yolo_service()
        yolo_result = yolo_service.detect_food(image_bytes)
        print(f"✅ YOLO detection 완료: {yolo_result['summary']}")
        
        # 3. GPT-Vision 간단 분석 (음식명 + 재료 추출)
        print("🤖 GPT-Vision 분석 시작...")
        gpt_service = get_gpt_vision_service()
        gpt_result = await gpt_service.analyze_food_with_detection(
            image_bytes, 
            yolo_result
        )
        print(f"✅ GPT-Vision 분석 완료: {gpt_result['food_name']}")
        print(f"📝 추출된 재료: {', '.join(gpt_result['ingredients'])}")
        
        # 4. LangChain을 이용한 DB 조회 및 영양소 추론 로직 제거
        #    이 단계에서는 오직 AI가 인식한 음식명과 재료만 반환합니다.
        
        # 5. 응답 데이터 구성 (간소화)
        
        # 메인 음식명에서 표시용 이름 추출 (언더스코어 뒤 부분만)
        display_food_name = extract_display_name(gpt_result["food_name"])
        
        # 후보 음식 리스트 변환
        candidates = []
        raw_candidates = gpt_result.get("candidates", [])
        
        if raw_candidates:
            for c in raw_candidates:
                try:
                    # 필수 필드 확인 및 기본값 처리
                    food_name = c.get("food_name") or c.get("foodName") or "알 수 없는 음식"
                    confidence = c.get("confidence", 0.0)
                    
                    candidate = FoodCandidate(
                        foodName=extract_display_name(food_name),
                        confidence=float(confidence),
                        description=c.get("description", ""),
                        ingredients=c.get("ingredients") or []
                    )
                    candidates.append(candidate)
                except Exception as e:
                    print(f"⚠️ 후보 음식 변환 중 오류 무시: {e} (데이터: {c})")
                    continue
        
        # 후보가 하나도 없으면 메인 결과로라도 채움
        if not candidates:
            candidates.append(
                FoodCandidate(
                    foodName=extract_display_name(gpt_result["food_name"]),
                    confidence=gpt_result.get("confidence", 0.0),
                    description=gpt_result.get("description", ""),
                    ingredients=gpt_result.get("ingredients", [])
                )
            )
        
        # AI 분석 결과에는 영양소 정보가 없음 (Preview 단계에서 계산)
        analysis_result = FoodAnalysisResult(
            foodName=display_food_name,  # 표시용 이름 사용
            description=gpt_result.get("description", ""),
            ingredients=gpt_result["ingredients"],
            confidence=0.9,  # GPT-Vision은 신뢰도가 높음
            candidates=candidates  # 후보 음식 리스트 추가
        )
        
        processing_time = int((time.time() - start_time) * 1000)
        
        return ApiResponse(
            success=True,
            data=FoodAnalysisData(
                analysis=analysis_result,
                timestamp=datetime.now(timezone.utc).isoformat(),
                processingTime=processing_time,
            ),
            message=f"✅ 분석 완료: {display_food_name} (건강점수: {gpt_result.get('health_score', 0)}점)"
        )
        
    except RuntimeError as e:
        # YOLO 또는 GPT-Vision 서비스 오류
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        print(f"❌ 음식 이미지 분석 실패: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"이미지 분석 중 오류가 발생했습니다: {str(e)}")


@router.post("/reanalyze-with-selection", response_model=ApiResponse[FoodAnalysisData])
async def reanalyze_with_user_selection(
    request: FoodReanalysisRequest,
    session: AsyncSession = Depends(get_session)
) -> ApiResponse[FoodAnalysisData]:
    """
    사용자가 후보 중 다른 음식을 선택했을 때 영양 정보 조회
    
    **사용 시나리오:**
    1. 초기 분석 (/analysis-upload)에서 후보 4개 반환
       - 후보1: 페퍼로니 피자 (90%) + 재료 [밀가루, 토마토소스, ...]
       - 후보2: 콤비네이션 피자 (80%) + 재료 [밀가루, ...]
       - 후보3: 하와이안 피자 (70%) + 재료 [...]
       - 후보4: 불고기 피자 (60%) + 재료 [...]
    
    2. 사용자가 "아니야, 이건 후보2 (콤비네이션 피자)야!" 선택
    
    3. 이 API 호출:
       POST /reanalyze-with-selection
       {
         "selectedFoodName": "콤비네이션 피자",
         "ingredients": ["밀가루", "토마토소스", "치즈", "햄", "올리브"]
       }
    
    4. DB에서 "콤비네이션 피자" 검색 → 영양소 정보 반환
    
    **Args:**
        request.selected_food_name: 사용자가 선택한 음식명 (후보 2~4)
        request.ingredients: 해당 후보의 재료 (검색 정확도 향상용)
        session: DB 세션
        
    **Returns:**
        선택한 후보의 정확한 영양소 정보
    """
    start_time = time.time()
    
    try:
        print(f"🔄 재분석 요청: {request.selected_food_name}")
        
        # 1. 선택한 음식명으로 DB 검색
        food_nutrient = await get_best_match_for_food(
            session,
            food_name=request.selected_food_name,
            ingredients=request.ingredients or []
        )
        
        # 2. 매칭 실패 시 대분류 기반 폴백
        is_fallback = False
        fallback_category = None
        fallback_message = None
        
        if not food_nutrient:
            print("⚠️ 정확한 매칭 실패, 대분류 기반 폴백 시도...")
            from app.services.food_nutrients_service import get_fallback_by_category
            
            food_name_parts = request.selected_food_name.split()
            category = food_name_parts[-1] if food_name_parts else request.selected_food_name
            
            food_nutrient = await get_fallback_by_category(session, category)
            
            if food_nutrient:
                is_fallback = True
                fallback_category = category
                print(f"✅ 폴백 성공: {food_nutrient.nutrient_name} 사용 (대분류: {category})")
        
        # 3. 영양소 정보 구성
        if food_nutrient:
            if not is_fallback:
                print(f"✅ DB 매칭 성공: {food_nutrient.nutrient_name}")
            
            # 칼로리 계산: DB의 kcal 우선, 없으면 Atwater 공식 사용
            reference = food_nutrient.reference_value or 100.0
            
            if food_nutrient.kcal is not None and food_nutrient.kcal > 0:
                # DB에 kcal 정보가 있으면 사용
                calories = round(food_nutrient.kcal)
                print(f"✅ DB 칼로리 사용: {calories} kcal (per {reference}g)")
            else:
                # DB에 kcal 없으면 Atwater 공식으로 계산
                protein_cal = (food_nutrient.protein or 0.0) * 4
                carb_cal = (food_nutrient.carb or 0.0) * 4
                fat_cal = (food_nutrient.fat or 0.0) * 9
                calories = round(protein_cal + carb_cal + fat_cal)
                print(f"🔢 Atwater 공식 계산: {protein_cal:.1f} + {carb_cal:.1f} + {fat_cal:.1f} = {calories} kcal (per {reference}g)")
            
            # 영양성분함량기준 정보 출력
            print(f"📊 영양소 정보 ({reference}g 기준): 단백질={food_nutrient.protein}g, 탄수화물={food_nutrient.carb}g, 지방={food_nutrient.fat}g")
            
            nutrients = FoodNutrients(
                protein=float(food_nutrient.protein or 0.0),
                carbs=float(food_nutrient.carb or 0.0),
                fat=float(food_nutrient.fat or 0.0),
                sodium=float(food_nutrient.sodium or 0.0),
                fiber=float(food_nutrient.fiber or 0.0)
            )
            
            # 폴백 사용 시 안내 메시지
            suggestions = []
            if is_fallback and fallback_category:
                fallback_message = f"ℹ️ '{display_food_name}'의 정확한 영양 정보가 없어 '{fallback_category}' 기준으로 표시됩니다."
                suggestions.append(fallback_message)
            
            suggestions.extend([
                "균형 잡힌 식단을 유지하세요.",
                "충분한 수분 섭취를 권장합니다.",
                "규칙적인 운동과 함께 건강을 관리하세요."
            ])
        else:
            print("⚠️ DB 매칭 완전 실패: 기본값 사용")
            calories = 0
            nutrients = FoodNutrients(
                protein=0.0,
                carbs=0.0,
                fat=0.0,
                sodium=0.0,
                fiber=0.0
            )
            suggestions = [
                "⚠️ 이 음식의 영양 정보가 데이터베이스에 없습니다. 유사한 음식을 참고하세요."
            ]
        
        # 4. 응답 데이터 구성
        display_food_name = extract_display_name(request.selected_food_name)
        analysis_result = FoodAnalysisResult(
            foodName=display_food_name,  # 표시용 이름 사용
            description="",
            ingredients=request.ingredients or [],
            calories=calories,
            nutrients=nutrients,
            portionSize="100g",
            healthScore=70,  # 기본 건강 점수
            confidence=0.9,
            suggestions=suggestions,
            candidates=[]  # 재분석에서는 후보 없음
        )
        
        processing_time = int((time.time() - start_time) * 1000)
        
        return ApiResponse(
            success=True,
            data=FoodAnalysisData(
                analysis=analysis_result,
                timestamp=datetime.now(timezone.utc).isoformat(),
                processingTime=processing_time,
            ),
            message=f"✅ 재분석 완료: {display_food_name}"
        )
        
    except Exception as e:
        print(f"❌ 재분석 실패: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"재분석 중 오류가 발생했습니다: {str(e)}")


@router.post("/preview-nutrition", response_model=ApiResponse[PreviewNutritionResponse])
async def preview_nutrition(
    request: PreviewNutritionRequest,
    session: AsyncSession = Depends(get_session)
) -> ApiResponse[PreviewNutritionResponse]:
    """
    음식 영양 정보 미리보기 (저장 전 단계)
    
    **처리 과정:**
    1. 자연어 섭취량 해석 (예: "반 공기" -> 105g)
    2. DB 매칭 (FoodNutrient 또는 UserContributedFood)
    3. 영양소 계산 (중량 비례)
    4. 매칭 실패 시 LLM 추론 Fallback
    5. HealthScore 및 NRF9.3 지수 계산
    
    **Returns:**
        확정된 영양 정보 (저장 API에 그대로 전달할 데이터)
    """
    try:
        print(f"🔮 영양 정보 미리보기 요청: {request.food_name} ({request.portion_text})")
        
        matching_service = get_food_matching_service()
        
        # 1. 섭취량 해석 (LLM Tool Use)
        # portion_text가 숫자로만 되어있으면 바로 사용, 아니면 해석
        try:
            portion_size_g = float(request.portion_text)
            print(f"✅ 섭취량 직접 변환: {portion_size_g}g")
        except ValueError:
            # "g" 제거 후 시도
            clean_text = request.portion_text.lower().replace("g", "").strip()
            try:
                portion_size_g = float(clean_text)
                print(f"✅ 섭취량 단위 제거 후 변환: {portion_size_g}g")
            except ValueError:
                # LLM 해석
                portion_size_g = await matching_service.interpret_portion(
                    request.food_name, request.portion_text
                )
                print(f"✅ 섭취량 LLM 해석: '{request.portion_text}' -> {portion_size_g}g")
        
        # 2. DB 매칭
        food_nutrient = await matching_service.match_food_to_db(
            session=session,
            food_name=request.food_name,
            ingredients=request.ingredients
        )
        
        nutrients_data = {}
        food_id = ""
        
        if food_nutrient:
            # DB 매칭 성공
            food_id = food_nutrient.food_id
            reference_value = food_nutrient.reference_value or 100.0
            scale_factor = portion_size_g / reference_value
            
            # 영양소 계산 (중량 비례)
            # kcal가 없으면 Atwater 계산
            kcal = food_nutrient.kcal
            if not kcal:
                kcal = (
                    (food_nutrient.protein or 0) * 4 +
                    (food_nutrient.carb or 0) * 4 +
                    (food_nutrient.fat or 0) * 9
                )
            
            nutrients_data = {
                "calories": kcal * scale_factor,
                "protein": (food_nutrient.protein or 0) * scale_factor,
                "carbs": (food_nutrient.carb or 0) * scale_factor,
                "fat": (food_nutrient.fat or 0) * scale_factor,
                "sodium": (food_nutrient.sodium or 0) * scale_factor,
                "fiber": (food_nutrient.fiber or 0) * scale_factor,
                # NRF 계산용 추가 정보
                "vitamin_a": (getattr(food_nutrient, 'vitamin_a', 0) or 0) * scale_factor,
                "vitamin_c": (getattr(food_nutrient, 'vitamin_c', 0) or 0) * scale_factor,
                "calcium": (getattr(food_nutrient, 'calcium', 0) or 0) * scale_factor,
                "iron": (getattr(food_nutrient, 'iron', 0) or 0) * scale_factor,
                "potassium": (getattr(food_nutrient, 'potassium', 0) or 0) * scale_factor,
                "magnesium": (getattr(food_nutrient, 'magnesium', 0) or 0) * scale_factor,
                "saturated_fat": (getattr(food_nutrient, 'saturated_fat', 0) or 0) * scale_factor,
                "added_sugar": (getattr(food_nutrient, 'added_sugar', 0) or 0) * scale_factor,
            }
            print(f"✅ DB 매칭 성공: {food_nutrient.nutrient_name}")
            
        else:
            # DB 매칭 실패 -> LLM 추론 Fallback
            print("⚠️ DB 매칭 실패 -> LLM 추론 실행")
            estimator = get_nutrient_estimator()
            estimated = await estimator.estimate_nutrients(
                request.food_name, request.ingredients
            )
            
            # 100g 기준값이므로 scale_factor 적용
            scale_factor = portion_size_g / 100.0
            
            nutrients_data = {
                "calories": estimated["calories"] * scale_factor,
                "protein": estimated["protein"] * scale_factor,
                "carbs": estimated["carbs"] * scale_factor,
                "fat": estimated["fat"] * scale_factor,
                "sodium": estimated["sodium"] * scale_factor,
                "fiber": estimated["fiber"] * scale_factor,
                # NRF 계산용
                "vitamin_a": estimated.get("vitamin_a", 0) * scale_factor,
                "vitamin_c": estimated.get("vitamin_c", 0) * scale_factor,
                "calcium": estimated.get("calcium", 0) * scale_factor,
                "iron": estimated.get("iron", 0) * scale_factor,
                "potassium": estimated.get("potassium", 0) * scale_factor,
                "magnesium": estimated.get("magnesium", 0) * scale_factor,
                "saturated_fat": estimated.get("saturated_fat", 0) * scale_factor,
                "added_sugar": estimated.get("added_sugar", 0) * scale_factor,
            }
            
            # 임시 ID 생성
            food_id = f"TEMP_{int(time.time())}"
            
        # 3. HealthScore (NRF9.3) 계산
        nrf_score = await calculate_nrf93_score(
            protein_g=nutrients_data["protein"],
            fiber_g=nutrients_data["fiber"],
            vitamin_a_ug=nutrients_data.get("vitamin_a", 0),
            vitamin_c_mg=nutrients_data.get("vitamin_c", 0),
            vitamin_e_mg=0, # 추후 추가
            calcium_mg=nutrients_data.get("calcium", 0),
            iron_mg=nutrients_data.get("iron", 0),
            potassium_mg=nutrients_data.get("potassium", 0),
            magnesium_mg=nutrients_data.get("magnesium", 0),
            saturated_fat_g=nutrients_data.get("saturated_fat", 0),
            added_sugar_g=nutrients_data.get("added_sugar", 0),
            sodium_mg=nutrients_data["sodium"],
            reference_value_g=portion_size_g
        )
        
        response_data = PreviewNutritionResponse(
            food_id=food_id,
            food_name=request.food_name,
            calories=round(nutrients_data["calories"]),
            nutrients=FoodNutrients(
                protein=round(nutrients_data["protein"], 1),
                carbs=round(nutrients_data["carbs"], 1),
                fat=round(nutrients_data["fat"], 1),
                sodium=round(nutrients_data["sodium"], 1),
                fiber=round(nutrients_data["fiber"], 1)
            ),
            portion_size_g=round(portion_size_g, 1),
            health_score=int(nrf_score["final_score"])
        )
        
        return ApiResponse(
            success=True,
            data=response_data,
            message=f"✅ 영양 정보 계산 완료 ({nrf_score['final_score']}점)"
        )
            
    except Exception as e:
        print(f"❌ 영양 정보 미리보기 실패: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"영양 정보 계산 중 오류가 발생했습니다: {str(e)}")


@router.post("/save-food", response_model=ApiResponse[SaveFoodResponse])
async def save_user_food(
    request: SaveFoodRequest,
    session: AsyncSession = Depends(get_session)
) -> ApiResponse[SaveFoodResponse]:
    """
    최종 음식 기록 저장 (Persistence Layer)
    
    **Note:**
    이 API는 더 이상 영양소를 계산하거나 DB 매칭을 수행하지 않습니다.
    `preview-nutrition` 단계에서 확정된 데이터를 그대로 저장합니다.
    
    **처리 과정:**
    1. Food 테이블 확인 및 저장 (참조 무결성)
    2. UserFoodHistory 저장 (섭취 기록)
    3. HealthScore 저장 (점수 기록)
    """
    try:
        print(f"💾 음식 저장 요청: user_id={request.user_id}, food_id={request.food_id}, score={request.health_score}")
        
        # 1. Food 테이블 처리 (참조 무결성을 위해 필요)
        # food_id가 'TEMP_'로 시작하면(임시 ID), user_contributed_foods 로직 대신
        # 그냥 Food 테이블에 '사용자 정의 음식'으로 저장하거나, 
        # 기존 로직처럼 UserContributedFood를 쓸 수도 있습니다.
        # 여기서는 간단하게 Food 테이블에 존재 여부만 확인하고 없으면 생성합니다.
        
        # Food 테이블에 메타 데이터 저장/확인
        await get_or_create_food(
            session=session,
            food_id=request.food_id,
            food_name=request.food_name,
            food_class_1=request.food_class_1,
            food_class_2=request.food_class_2,
            ingredients=request.ingredients,
            image_ref=request.image_ref,
            category=request.category,
        )
        
        # 2. 섭취 기록 저장
        history = await create_food_history(
            session=session,
            user_id=request.user_id,
            food_id=request.food_id,
            food_name=request.food_name,
            meal_type=request.meal_type,
            consumed_at=datetime.now(),
            portion_size_g=request.portion_size_g,
        )
        
        # 3. 건강 점수 저장 (계산 없이 그대로 저장)
        # 상세 점수(positive/negative)는 Request에 없으면 대략적으로 배분하거나 0 처리
        # (프론트에서 상세 점수까지 다 받으면 좋지만, 일단 health_score 위주로 저장)
        
        food_grade = await calculate_food_grade(request.health_score)
        
        await create_health_score(
            session=session,
            history_id=history.history_id,
            user_id=request.user_id,
            food_id=request.food_id,
            reference_value=100, # 기준값
            kcal=int(request.calories),
            # 상세 점수가 없으면 final_score를 기준으로 임의 배분 (단순 저장용)
            # 실제로는 preview에서 계산된 상세 점수를 받는 것이 가장 좋음
            positive_score=request.health_score, 
            negative_score=0,
            final_score=request.health_score,
            food_grade=food_grade,
            calc_method="NRF9.3 (Pre-calculated)"
        )
        
        await session.commit()
        
        response = SaveFoodResponse(
            history_id=history.history_id,
            food_id=request.food_id,
            food_name=history.food_name,
            meal_type=history.meal_type,
            consumed_at=history.consumed_at.isoformat(),
            portion_size_g=history.portion_size_g,
        )
        
        return ApiResponse(
            success=True,
            data=response,
            message=f"✅ 저장이 완료되었습니다."
        )
        
    except Exception as e:
        print(f"❌ 음식 저장 실패: {e}")
        import traceback
        traceback.print_exc()
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"저장 중 오류 발생: {str(e)}")

