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
)
from app.db.session import get_session
from app.services.gpt_vision_service import get_gpt_vision_service
from app.services.yolo_service import get_yolo_service
from app.services.food_nutrients_service import get_best_match_for_food

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
    음식 이미지 분석 (YOLO + GPT-Vision + DB 파이프라인)
    
    **처리 과정:**
    1. 사용자가 이미지 업로드
    2. YOLO 모델로 음식 객체 detection
    3. GPT-Vision이 음식명 + 주요 재료 3-4개 추출
    4. food_nutrients 테이블에서 영양소 데이터 조회
    5. GPT 결과 + DB 데이터 결합하여 반환
    
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
        
        # 3. GPT-Vision 분석 실행 (음식명 + 재료 추출)
        print("🤖 GPT-Vision 분석 시작...")
        gpt_service = get_gpt_vision_service()
        gpt_result = gpt_service.analyze_food_with_detection(image_bytes, yolo_result)
        print(f"✅ GPT-Vision 분석 완료: {gpt_result['food_name']}")
        print(f"📝 추출된 재료: {', '.join(gpt_result['ingredients'])}")
        
        # 4. food_nutrients 테이블에서 영양소 데이터 조회
        print("🔍 DB에서 영양소 데이터 조회 중...")
        food_nutrient = await get_best_match_for_food(
            session,
            food_name=gpt_result["food_name"],
            ingredients=gpt_result["ingredients"]
        )
        
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
            
            # 칼로리 계산 (Atwater 시스템: 단백질 4kcal/g, 탄수화물 4kcal/g, 지방 9kcal/g)
            protein_cal = (food_nutrient.protein or 0.0) * 4
            carb_cal = (food_nutrient.carb or 0.0) * 4
            fat_cal = (food_nutrient.fat or 0.0) * 9
            calories = round(protein_cal + carb_cal + fat_cal)
            
            # 영양성분함량기준 정보 출력
            reference = food_nutrient.reference_value or 100.0
            print(f"📊 영양소 정보 ({reference}g 기준): 단백질={food_nutrient.protein}g, 탄수화물={food_nutrient.carb}g, 지방={food_nutrient.fat}g")
            print(f"🔢 칼로리 계산: {protein_cal:.1f} + {carb_cal:.1f} + {fat_cal:.1f} = {calories} kcal (per {reference}g)")
            
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
            print("⚠️ DB 매칭 완전 실패: 기본값 사용")
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
        
        # 후보 음식 리스트 변환
        candidates = [
            FoodCandidate(
                foodName=c["food_name"],
                confidence=c["confidence"],
                description=c.get("description", "")
            )
            for c in gpt_result.get("candidates", [])
        ]
        
        analysis_result = FoodAnalysisResult(
            foodName=gpt_result["food_name"],
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
            message=f"✅ 분석 완료: {gpt_result['food_name']} (건강점수: {gpt_result.get('health_score', 0)}점)"
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
    사용자가 선택한 음식으로 재분석
    
    사용자가 여러 후보 중 다른 음식을 선택했을 때,
    해당 음식명으로 DB를 재검색하여 영양 정보를 반환합니다.
    
    **Args:**
        request: 선택한 음식명과 재료 정보
        session: DB 세션
        
    **Returns:**
        선택한 음식의 영양 정보
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
            
            protein_cal = (food_nutrient.protein or 0.0) * 4
            carb_cal = (food_nutrient.carb or 0.0) * 4
            fat_cal = (food_nutrient.fat or 0.0) * 9
            calories = round(protein_cal + carb_cal + fat_cal)
            
            reference = food_nutrient.reference_value or 100.0
            print(f"📊 영양소 정보 ({reference}g 기준): 단백질={food_nutrient.protein}g, 탄수화물={food_nutrient.carb}g, 지방={food_nutrient.fat}g")
            print(f"🔢 칼로리 계산: {protein_cal:.1f} + {carb_cal:.1f} + {fat_cal:.1f} = {calories} kcal (per {reference}g)")
            
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
                fallback_message = f"ℹ️ '{request.selected_food_name}'의 정확한 영양 정보가 없어 '{fallback_category}' 기준으로 표시됩니다."
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
        analysis_result = FoodAnalysisResult(
            foodName=request.selected_food_name,
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
            message=f"✅ 재분석 완료: {request.selected_food_name}"
        )
        
    except Exception as e:
        print(f"❌ 재분석 실패: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"재분석 중 오류가 발생했습니다: {str(e)}")

