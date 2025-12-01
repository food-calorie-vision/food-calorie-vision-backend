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
)
from app.db.models_food_nutrients import FoodNutrient
from app.db.models_user_contributed import UserContributedFood
from app.db.session import get_session
from app.services.gpt_vision_service import get_gpt_vision_service
from app.services.yolo_service import get_yolo_service
from app.services.food_nutrients_service import get_best_match_for_food
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
        gpt_result = gpt_service.analyze_food_with_detection(
            image_bytes, 
            yolo_result
        )
        print(f"✅ GPT-Vision 분석 완료: {gpt_result['food_name']}")
        print(f"📝 추출된 재료: {', '.join(gpt_result['ingredients'])}")
        
        # 4. LangChain으로 DB 조회 (전체 로직 위임)
        print("🔍 [LangChain] DB에서 음식 검색 중...")
        from app.services.food_db_finder import get_food_db_finder
        
        food_nutrient = None
        langchain_match_result = None
        
        # LangChain으로 의미 기반 매칭 시도
        try:
            db_finder = get_food_db_finder()
            langchain_match_result = await db_finder.find_exact_match(
                detected_food_name=gpt_result["food_name"],
                session=session
            )
            
            if langchain_match_result["found"] and langchain_match_result["confidence"] >= 80:
                food_nutrient = langchain_match_result["food_data"]
                print(f"✅ [LangChain] 매칭 성공: {food_nutrient.nutrient_name} (신뢰도: {langchain_match_result['confidence']}%)")
            else:
                print(f"⚠️ [LangChain] 매칭 실패 (신뢰도: {langchain_match_result.get('confidence', 0)}%)")
                print(f"📝 [LangChain] 이유: {langchain_match_result.get('reason', 'Unknown')}")
                # 매칭 실패 시 food_nutrient는 None으로 유지
        except Exception as e:
            print(f"❌ [LangChain] 오류 발생: {e}")
            import traceback
            traceback.print_exc()
            # 오류 발생 시에도 food_nutrient는 None으로 유지
        
        # 4-1. 매칭 실패 시 대분류 기반 폴백 시도
        is_fallback = False
        fallback_category = None  # 폴백에 사용된 대분류 저장
        
        if not food_nutrient:
            print("⚠️ 정확한 매칭 실패, 대분류 기반 폴백 시도...")
            from app.services.food_nutrients_service import get_fallback_by_category
            
            # 음식명에서 대분류 추출 (예: "페퍼로니 피자" → "피자")
            # 간단한 휴리스틱: 마지막 단어를 대분류로 가정
            food_name_parts = gpt_result["food_name"].split()
            category = food_name_parts[-1] if food_name_parts else gpt_result["food_name"]
            
            food_nutrient = await get_fallback_by_category(session, category)
            
            if food_nutrient:
                is_fallback = True
                fallback_category = category  # 대분류 저장
                print(f"✅ 폴백 성공: {food_nutrient.nutrient_name} 사용 (대분류: {category})")
            else:
                print("❌ 폴백도 실패: 기본값 사용")
        
        # 5. DB 데이터로 영양소 정보 구성
        fallback_message = None  # 폴백 메시지 임시 저장
        
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
            
            # 폴백 사용 시 안내 메시지 생성 (나중에 맨 앞에 삽입)
            if is_fallback and fallback_category:
                fallback_message = f"ℹ️ '{gpt_result['food_name']}'의 정확한 영양 정보가 없어 '{fallback_category}' 기준으로 표시됩니다."
        else:
            # DB 매칭 완전 실패 → LangChain으로 영양성분 추정
            print("⚠️ DB 매칭 완전 실패 → LangChain으로 영양성분 추정 시도")
            
            try:
                db_finder = get_food_db_finder()
                nutrition_result = await db_finder.estimate_nutrition_without_db(
                    food_name=gpt_result["food_name"],
                    ingredients=gpt_result["ingredients"],
                    portion_size_g=250.0  # 기본 1인분 추정
                )
                
                print(f"✅ [LangChain] 영양성분 추정 완료:")
                print(f"   - 칼로리: {nutrition_result['calories']} kcal")
                print(f"   - 단백질: {nutrition_result['protein']}g")
                print(f"   - 탄수화물: {nutrition_result['carbs']}g")
                print(f"   - 지방: {nutrition_result['fat']}g")
                print(f"   - 신뢰도: {nutrition_result['confidence']}%")
                print(f"   - 추정 근거: {nutrition_result['estimation_note']}")
                
                calories = int(nutrition_result['calories'])
                nutrients = FoodNutrients(
                    protein=nutrition_result['protein'],
                    carbs=nutrition_result['carbs'],
                    fat=nutrition_result['fat'],
                    sodium=nutrition_result['sodium'],
                    fiber=nutrition_result['fiber']
                )
                fallback_message = f"🤖 AI가 영양성분을 추정했습니다 (신뢰도: {nutrition_result['confidence']}%). 참고용으로 활용하세요."
                
            except Exception as e:
                print(f"❌ [LangChain] 영양성분 추정 실패: {e}")
                import traceback
                traceback.print_exc()
                
                # 최종 폴백: 기본값
                calories = 0
                nutrients = FoodNutrients(
                    protein=0.0,
                    carbs=0.0,
                    fat=0.0,
                    sodium=0.0,
                    fiber=0.0
                )
                fallback_message = "⚠️ 이 음식의 영양 정보가 데이터베이스에 없습니다. 유사한 음식을 참고하세요."
        
        # 6. 폴백 메시지를 suggestions 맨 앞에 삽입
        if fallback_message:
            gpt_result["suggestions"].insert(0, fallback_message)
        
        # 7. 응답 데이터 구성
        from app.api.v1.schemas.vision import FoodCandidate
        
        # 메인 음식명에서 표시용 이름 추출 (언더스코어 뒤 부분만)
        display_food_name = extract_display_name(gpt_result["food_name"])
        
        # 후보 음식 리스트 변환
        candidates = [
            FoodCandidate(
                foodName=extract_display_name(c["food_name"]),  # 후보 음식명도 표시용으로 변환
                confidence=c["confidence"],
                description=c.get("description", ""),
                ingredients=c.get("ingredients", [])  # 후보별 재료 추가
            )
            for c in gpt_result.get("candidates", [])
        ]
        
        analysis_result = FoodAnalysisResult(
            foodName=display_food_name,  # 표시용 이름 사용
            description=gpt_result.get("description", ""),
            ingredients=gpt_result["ingredients"],
            calories=calories,
            nutrients=nutrients,
            portionSize=gpt_result.get("portion_size", "1인분"),
            healthScore=gpt_result.get("health_score", 0),
            confidence=0.9,  # GPT-Vision은 신뢰도가 높음
            suggestions=gpt_result["suggestions"],
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


@router.post("/save-food", response_model=ApiResponse[SaveFoodResponse])
async def save_user_food(
    request: SaveFoodRequest,
    session: AsyncSession = Depends(get_session)
) -> ApiResponse[SaveFoodResponse]:
    """
    사용자가 선택한 음식을 저장
    
    **처리 과정:**
    1. Food 테이블에 음식 정보 저장 (없으면 생성)
    2. UserFoodHistory 테이블에 섭취 기록 저장
    
    **Args:**
        request: 저장할 음식 정보
        session: DB 세션
        
    **Returns:**
        저장된 음식 기록 정보
    """
    try:
        print(f"💾 음식 저장 요청: user_id={request.user_id}, food_name={request.food_name}")
        
        # 1. 음식명 정규화 (재료 순서 통일)
        from app.services.food_matching_service import get_food_matching_service, normalize_food_name
        
        normalized_food_name = normalize_food_name(request.food_name, request.ingredients)
        if normalized_food_name != request.food_name:
            print(f"🔄 음식명 정규화: '{request.food_name}' → '{normalized_food_name}'")
            request.food_name = normalized_food_name
        
        # 2. food_nutrients에서 영양소 정보 조회 (개선된 매칭 서비스 사용)
        print("🔍 food_nutrients에서 음식 정보 조회 중...")
        
        matching_service = get_food_matching_service()
        food_nutrient = await matching_service.match_food_to_db(
            session=session,
            food_name=request.food_name,
            ingredients=request.ingredients,
            food_class_hint=request.food_class_1,
            user_id=request.user_id
        )
        
        # 3. portion_size_g 기본값 설정 (DB의 unit 사용)
        if request.portion_size_g is None or request.portion_size_g <= 0:
            # DB에서 unit (식품 중량) 사용
            if food_nutrient:
                unit_value = food_nutrient.unit  # 이제 Float 타입
                reference_value = food_nutrient.reference_value or 100.0
                
                print(f"🔍 [DEBUG] DB 값 - unit: {unit_value}, reference_value: {reference_value}")
                
                if unit_value is not None and unit_value > 0:
                    request.portion_size_g = float(unit_value)
                    print(f"✅ DB unit 사용: {request.portion_size_g}g (식품 중량)")
                else:
                    request.portion_size_g = 100.0
                    print(f"⚠️ unit 없음, 기본값 사용: 100g")
            else:
                request.portion_size_g = 100.0
                print(f"⚠️ DB 매칭 실패, 기본값 사용: 100g")
        else:
            print(f"✅ 사용자 입력 사용: {request.portion_size_g}g")
        
        # 2. food_id 결정
        if food_nutrient:
            actual_food_id = food_nutrient.food_id
            actual_food_class_1 = getattr(food_nutrient, 'food_class1', None)
            actual_food_class_2 = getattr(food_nutrient, 'food_class2', None)
            
            if isinstance(food_nutrient, FoodNutrient):
                print(f"✅ food_nutrients에서 매칭: {actual_food_id} (분류: {actual_food_class_1} > {actual_food_class_2})")
            else:
                print(f"✅ user_contributed_foods에서 매칭: {actual_food_id} - {food_nutrient.food_name}")
        else:
            # 매칭 실패 시: LangChain으로 영양성분 추정 후 user_contributed_foods에 추가
            print(f"⚠️ 매칭 실패 → LangChain으로 영양성분 추정 후 user_contributed_foods에 저장")
            
            # LangChain으로 영양성분 추정
            from app.services.food_db_finder import get_food_db_finder
            
            db_finder = get_food_db_finder()
            nutrition_result = await db_finder.estimate_nutrition_without_db(
                food_name=request.food_name,
                ingredients=request.ingredients,
                portion_size_g=float(request.portion_size_g)
            )
            
            print(f"✅ [LangChain] 영양성분 추정 완료:")
            print(f"   - 칼로리: {nutrition_result['calories']} kcal")
            print(f"   - 단백질: {nutrition_result['protein']}g")
            print(f"   - 탄수화물: {nutrition_result['carbs']}g")
            print(f"   - 지방: {nutrition_result['fat']}g")
            print(f"   - 신뢰도: {nutrition_result['confidence']}%")
            
            actual_food_id = f"USER_{request.user_id}_{int(datetime.now().timestamp())}"[:200]
            actual_food_class_1 = request.food_class_1 or (estimated_nutrients['food_class1'] if estimated_nutrients else "사용자추가")
            actual_food_class_2 = request.food_class_2 or (estimated_nutrients['food_class2'] if estimated_nutrients else (request.ingredients[0] if request.ingredients else None))
            
            # user_contributed_foods에 추가 (LangChain 추정값 사용)
            new_contributed_food = UserContributedFood(
                food_id=actual_food_id,
                user_id=request.user_id,
                food_name=request.food_name,
                nutrient_name=request.food_name,
                food_class1=actual_food_class_1,
                food_class2=actual_food_class_2,
                ingredients=", ".join(request.ingredients) if request.ingredients else None,
                unit=float(request.portion_size_g),  # 식품 중량
                reference_value=100.0,  # 영양성분함량기준량 (100g 기준)
                kcal=nutrition_result['calories'],  # 칼로리 추가
                protein=nutrition_result['protein'],
                carb=nutrition_result['carbs'],
                fat=nutrition_result['fat'],
                sodium=nutrition_result['sodium'],
                fiber=nutrition_result['fiber'],
                usage_count=1
            )
            session.add(new_contributed_food)
            await session.flush()
            food_nutrient = new_contributed_food  # 이후 로직에서 사용할 수 있도록 설정
            
            print(f"✅ user_contributed_foods에 저장: {actual_food_id} - {request.food_name} (LangChain 추정값)")
        
        # 3. Food 테이블에 음식 저장/조회 (food_nutrients 정보 활용)
        food = await get_or_create_food(
            session=session,
            food_id=actual_food_id,  # food_nutrients의 food_id
            food_name=request.food_name,
            food_class_1=actual_food_class_1,  # food_nutrients의 food_class1
            food_class_2=actual_food_class_2,  # food_nutrients의 food_class2
            ingredients=request.ingredients,
            image_ref=request.image_ref,
            category=request.category,
        )
        
        print(f"✅ Food 준비 완료: {food.food_id}")
        
        # 4. UserFoodHistory에 섭취 기록 저장
        history = await create_food_history(
            session=session,
            user_id=request.user_id,
            food_id=actual_food_id,  # 같은 food_id 사용
            food_name=request.food_name,
            meal_type=request.meal_type,  # 식사 유형 추가
            consumed_at=datetime.now(),
            portion_size_g=request.portion_size_g,
        )
        
        print(f"✅ 섭취 기록 저장 완료: history_id={history.history_id}, meal_type={request.meal_type}")
        
        # 5. NRF9.3 점수 계산 및 HealthScore 저장
        if food_nutrient:
            try:
                from app.services.health_score_service import calculate_nrf93_score as calc_nrf_score, create_health_score
                from app.services.food_db_finder import get_food_db_finder
                
                # food_nutrient가 FoodNutrient(DB 매칭 성공) vs UserContributedFood(LangChain 추정) 구분
                is_from_db = isinstance(food_nutrient, FoodNutrient)
                
                if is_from_db:
                    # DB 매칭 성공 → LangChain으로 portion_size_g에 맞게 재계산
                    print(f"✅ DB 음식 → LangChain으로 영양성분 계산")
                    db_finder = get_food_db_finder()
                    nutrition_result = await db_finder.calculate_nutrition_with_llm(
                        food_data=food_nutrient,
                        portion_size_g=float(request.portion_size_g)
                    )
                    
                    actual_kcal = nutrition_result['calories']
                    protein = nutrition_result['protein']
                    carb = nutrition_result['carbs']
                    fat = nutrition_result['fat']
                    sodium = nutrition_result['sodium']
                    fiber = nutrition_result['fiber']
                    
                    print(f"🔢 [LangChain] 영양성분 계산 완료:")
                    print(f"   - 칼로리: {nutrition_result['calories']} kcal")
                    print(f"   - 단백질: {nutrition_result['protein']}g")
                    print(f"   - 탄수화물: {nutrition_result['carbs']}g")
                    print(f"   - 지방: {nutrition_result['fat']}g")
                    print(f"   - 계산 방식: {nutrition_result['calculation_method']}")
                else:
                    # UserContributedFood (LangChain 추정) → 이미 추정된 값 사용
                    print(f"✅ LangChain 추정 음식 → 저장된 값 사용")
                    actual_kcal = getattr(food_nutrient, 'kcal', 0) or 0
                    protein = getattr(food_nutrient, 'protein', 0) or 0
                    carb = getattr(food_nutrient, 'carb', 0) or 0
                    fat = getattr(food_nutrient, 'fat', 0) or 0
                    sodium = getattr(food_nutrient, 'sodium', 0) or 0
                    fiber = getattr(food_nutrient, 'fiber', 0) or 0
                    
                    print(f"📊 저장된 영양성분:")
                    print(f"   - 칼로리: {actual_kcal} kcal")
                    print(f"   - 단백질: {protein}g")
                    print(f"   - 탄수화물: {carb}g")
                    print(f"   - 지방: {fat}g")
                
                # 공통: 비타민/미네랄 정보 추출
                vitamin_a = getattr(food_nutrient, 'vitamin_a', 0) or 0
                vitamin_c = getattr(food_nutrient, 'vitamin_c', 0) or 0
                calcium = getattr(food_nutrient, 'calcium', 0) or 0
                iron = getattr(food_nutrient, 'iron', 0) or 0
                potassium = getattr(food_nutrient, 'potassium', 0) or 0
                magnesium = getattr(food_nutrient, 'magnesium', 0) or 0
                saturated_fat = getattr(food_nutrient, 'saturated_fat', 0) or 0
                added_sugar = getattr(food_nutrient, 'added_sugar', 0) or 0
                
                # NRF9.3 점수 계산
                score_result = await calc_nrf_score(
                    protein_g=protein,
                    fiber_g=fiber,
                    vitamin_a_ug=vitamin_a,
                    vitamin_c_mg=vitamin_c,
                    vitamin_e_mg=0,
                    calcium_mg=calcium,
                    iron_mg=iron,
                    potassium_mg=potassium,
                    magnesium_mg=magnesium,
                    saturated_fat_g=saturated_fat,
                    added_sugar_g=added_sugar,
                    sodium_mg=sodium,
                    reference_value_g=float(request.portion_size_g)
                )
                
                print(f"📊 NRF9.3 점수 계산 완료: {score_result['final_score']:.1f}점")
                
                # HealthScore 저장
                await create_health_score(
                    session=session,
                    history_id=history.history_id,
                    user_id=request.user_id,
                    food_id=actual_food_id,
                    reference_value=100,
                    kcal=int(actual_kcal),
                    positive_score=int(score_result['positive_score']),
                    negative_score=int(score_result['negative_score']),
                    final_score=int(score_result['final_score']),
                    food_grade=score_result['food_grade'],
                    calc_method=score_result['calc_method']
                )
                print(f"✅ HealthScore 저장 완료: {score_result['final_score']:.1f}점, {score_result['food_grade']}")
            except Exception as e:
                print(f"⚠️ NRF 점수 계산 실패: {e}")
                import traceback
                traceback.print_exc()
        else:
            # DB 매칭 실패 → LangChain으로 영양성분 추정
            print(f"⚠️ food_nutrient 없음 → LangChain으로 영양성분 추정 시도")
            
            try:
                from app.services.food_db_finder import get_food_db_finder
                
                db_finder = get_food_db_finder()
                nutrition_result = await db_finder.estimate_nutrition_without_db(
                    food_name=request.food_name,
                    ingredients=request.ingredients,
                    portion_size_g=float(request.portion_size_g)
                )
                
                print(f"✅ [LangChain] 영양성분 추정 완료:")
                print(f"   - 칼로리: {nutrition_result['calories']} kcal")
                print(f"   - 단백질: {nutrition_result['protein']}g")
                print(f"   - 탄수화물: {nutrition_result['carbs']}g")
                print(f"   - 지방: {nutrition_result['fat']}g")
                print(f"   - 신뢰도: {nutrition_result['confidence']}%")
                print(f"   - 추정 근거: {nutrition_result['estimation_note']}")
                
                # NRF 점수 계산 (추정값 사용)
                from app.services.health_score_service import calculate_nrf93_score as calc_nrf_score, create_health_score
                
                score_result = await calc_nrf_score(
                    protein_g=nutrition_result['protein'],
                    fiber_g=nutrition_result['fiber'],
                    vitamin_a_ug=0,  # 추정 불가
                    vitamin_c_mg=0,  # 추정 불가
                    vitamin_e_mg=0,
                    calcium_mg=0,
                    iron_mg=0,
                    potassium_mg=0,
                    magnesium_mg=0,
                    saturated_fat_g=nutrition_result['fat'] * 0.3,  # 지방의 30%로 추정
                    added_sugar_g=0,
                    sodium_mg=nutrition_result['sodium'],
                    reference_value_g=float(request.portion_size_g)
                )
                
                print(f"📊 NRF9.3 점수 계산 완료 (추정값 기반): {score_result['final_score']:.1f}점")
                
                # HealthScore 저장
                await create_health_score(
                    session=session,
                    history_id=history.history_id,
                    user_id=request.user_id,
                    food_id=actual_food_id,
                    reference_value=100,
                    kcal=int(nutrition_result['calories']),
                    positive_score=int(score_result['positive_score']),
                    negative_score=int(score_result['negative_score']),
                    final_score=int(score_result['final_score']),
                    food_grade=score_result['food_grade'],
                    calc_method=f"{score_result['calc_method']} (LangChain 추정, 신뢰도: {nutrition_result['confidence']}%)"
                )
                print(f"✅ HealthScore 저장 완료 (추정값): {score_result['final_score']:.1f}점")
                
            except Exception as e:
                print(f"❌ LangChain 영양성분 추정 실패: {e}")
                import traceback
                traceback.print_exc()
        
        # 6. 변경사항 커밋
        await session.commit()
        
        # 4. 응답 데이터 구성
        response = SaveFoodResponse(
            history_id=history.history_id,
            food_id=food.food_id,
            food_name=history.food_name,
            meal_type=history.meal_type,  # 식사 유형 추가
            consumed_at=history.consumed_at.isoformat() if history.consumed_at else datetime.now().isoformat(),
            portion_size_g=float(history.portion_size_g) if history.portion_size_g else None,
        )
        
        return ApiResponse(
            success=True,
            data=response,
            message=f"✅ 음식이 성공적으로 저장되었습니다: {request.food_name}"
        )
        
    except Exception as e:
        print(f"❌ 음식 저장 실패: {e}")
        import traceback
        traceback.print_exc()
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"음식 저장 중 오류가 발생했습니다: {str(e)}")

