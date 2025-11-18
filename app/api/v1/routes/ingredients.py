"""식재료 관련 라우트"""
import os
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.common import ApiResponse
from app.api.v1.schemas.ingredient import (
    SaveIngredientsRequest,
    SaveIngredientsData,
    IngredientResponse,
    RecommendationData,
)
from app.db.models import UserIngredient, User, DiseaseAllergyProfile
from app.db.session import get_session
from app.services.roboflow_service import get_roboflow_service
from app.services.gpt_vision_service import get_gpt_vision_service

router = APIRouter()


def get_current_user_id() -> int:
    """
    현재 로그인된 사용자 ID를 반환
    TODO: 실제로는 세션이나 JWT에서 가져와야 함
    """
    # 임시로 테스트 사용자 ID 반환
    return 1


@router.post("/save", response_model=ApiResponse[SaveIngredientsData])
async def save_ingredients(
    request: SaveIngredientsRequest,
    session: AsyncSession = Depends(get_session)
) -> ApiResponse[SaveIngredientsData]:
    """
    식재료 저장
    
    Roboflow로 분석한 식재료들을 데이터베이스에 저장합니다.
    이미 같은 이름의 식재료가 있으면 수량을 누적합니다.
    
    **Args:**
        request: 저장할 식재료 목록
        session: DB 세션
        
    **Returns:**
        저장된 식재료 정보
    """
    try:
        user_id = get_current_user_id()
        saved_ingredients = []
        
        for item in request.ingredients:
            # 같은 사용자의 같은 이름 식재료 조회
            stmt = select(UserIngredient).where(
                UserIngredient.user_id == user_id,
                UserIngredient.ingredient_name == item.name,
                UserIngredient.is_used == False
            )
            result = await session.execute(stmt)
            existing_ingredient = result.scalar_one_or_none()
            
            if existing_ingredient:
                # 이미 존재하면 수량 누적
                existing_ingredient.count += item.count
                await session.flush()
                await session.refresh(existing_ingredient)  # 모든 필드 다시 로드
                saved_ingredient = existing_ingredient
            else:
                # 새로 추가
                new_ingredient = UserIngredient(
                    user_id=user_id,
                    ingredient_name=item.name,
                    count=item.count,
                    is_used=False
                )
                session.add(new_ingredient)
                await session.flush()  # ID 생성을 위해 flush
                await session.refresh(new_ingredient)  # 모든 필드 다시 로드
                saved_ingredient = new_ingredient
            
            saved_ingredients.append(IngredientResponse(
                ingredient_id=saved_ingredient.ingredient_id,
                user_id=saved_ingredient.user_id,
                ingredient_name=saved_ingredient.ingredient_name,
                count=saved_ingredient.count,
                created_at=saved_ingredient.created_at,
                is_used=saved_ingredient.is_used
            ))
        
        await session.commit()
        
        return ApiResponse(
            success=True,
            data=SaveIngredientsData(
                saved_count=len(saved_ingredients),
                ingredients=saved_ingredients
            ),
            message=f"✅ {len(saved_ingredients)}개의 식재료가 저장되었습니다!"
        )
        
    except Exception as e:
        await session.rollback()
        print(f"❌ 식재료 저장 실패: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"식재료 저장 중 오류가 발생했습니다: {str(e)}")


@router.get("/list", response_model=ApiResponse[List[IngredientResponse]])
async def get_ingredients(
    session: AsyncSession = Depends(get_session)
) -> ApiResponse[List[IngredientResponse]]:
    """
    저장된 식재료 목록 조회
    
    현재 사용자가 저장한 식재료 중 아직 사용하지 않은 것들을 조회합니다.
    
    **Args:**
        session: DB 세션
        
    **Returns:**
        식재료 목록
    """
    try:
        user_id = get_current_user_id()
        
        stmt = select(UserIngredient).where(
            UserIngredient.user_id == user_id,
            UserIngredient.is_used == False
        ).order_by(UserIngredient.created_at.desc())
        
        result = await session.execute(stmt)
        ingredients = result.scalars().all()
        
        ingredient_list = [
            IngredientResponse(
                ingredient_id=ing.ingredient_id,
                user_id=ing.user_id,
                ingredient_name=ing.ingredient_name,
                count=ing.count,
                created_at=ing.created_at,
                is_used=ing.is_used
            )
            for ing in ingredients
        ]
        
        return ApiResponse(
            success=True,
            data=ingredient_list,
            message=f"✅ {len(ingredient_list)}개의 식재료를 조회했습니다."
        )
        
    except Exception as e:
        print(f"❌ 식재료 조회 실패: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"식재료 조회 중 오류가 발생했습니다: {str(e)}")


@router.get("/recommendations", response_model=ApiResponse[RecommendationData])
async def get_food_recommendations(
    session: AsyncSession = Depends(get_session)
) -> ApiResponse[RecommendationData]:
    """
    누적된 식재료 기반 음식 추천
    
    사용자가 저장한 식재료들을 기반으로 LLM을 사용하여 음식을 추천합니다.
    최신 입력된 식재료를 포함하여 모든 사용 가능한 식재료를 고려합니다.
    
    **Args:**
        session: DB 세션
        
    **Returns:**
        LLM이 생성한 음식 추천
    """
    try:
        user_id = get_current_user_id()
        
        # 1. 사용자 정보 조회 (건강 목표 등)
        user_stmt = select(User).where(User.user_id == user_id)
        user_result = await session.execute(user_stmt)
        user = user_result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
        
        # 2. 알러지/질병 정보 조회
        profile_stmt = select(DiseaseAllergyProfile).where(
            DiseaseAllergyProfile.user_id == user_id
        )
        profile_result = await session.execute(profile_stmt)
        profiles = profile_result.scalars().all()
        
        # 알러지와 질병 리스트 생성
        allergies = [p.allergy_name for p in profiles if p.allergy_name]
        diseases = [p.disease_name for p in profiles if p.disease_name]
        
        # 3. 사용자의 미사용 식재료 조회
        ingredient_stmt = select(UserIngredient).where(
            UserIngredient.user_id == user_id,
            UserIngredient.is_used == False
        ).order_by(UserIngredient.created_at.desc())
        
        ingredient_result = await session.execute(ingredient_stmt)
        ingredients = ingredient_result.scalars().all()
        
        if not ingredients:
            return ApiResponse(
                success=False,
                data=None,
                message="⚠️ 저장된 식재료가 없습니다. 먼저 식재료를 추가해주세요."
            )
        
        # 식재료 목록 문자열 생성
        ingredient_names = [f"{ing.ingredient_name} ({ing.count}개)" for ing in ingredients]
        ingredient_text = ", ".join(ingredient_names)
        
        # 건강 목표 한글 변환
        health_goal_text = {
            'gain': '체중 증가',
            'maintain': '체중 유지',
            'loss': '체중 감소'
        }.get(user.health_goal, '체중 유지')
        
        # 4. GPT를 사용하여 맞춤형 음식 추천 생성
        try:
            from openai import OpenAI
            
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.")
            
            print(f"🔑 API 키 확인: {api_key[:20]}... (총 {len(api_key)}자)")
            
            client = OpenAI(api_key=api_key)
            
            # 건강 정보 문자열 생성
            health_info = f"""
사용자 건강 정보:
- 건강 목표: {health_goal_text}
- 나이: {user.age if user.age else '정보 없음'}세
- 체중: {user.weight if user.weight else '정보 없음'}kg"""
            
            if allergies:
                health_info += f"\n- ⚠️ 알러지: {', '.join(allergies)}"
            if diseases:
                health_info += f"\n- ⚠️ 질병: {', '.join(diseases)}"
            
            prompt = f"""당신은 전문 영양사이자 요리사입니다. 

{health_info}

보유 식재료:
{ingredient_text}

**중요한 제약사항:**
{f"1. 알러지 주의: {', '.join(allergies)} - 이 재료들은 절대 사용하지 마세요!" if allergies else ""}
{f"2. 질병 고려: {', '.join(diseases)} - 이 질병에 좋은 음식을 추천해주세요." if diseases else ""}
3. 건강 목표: {health_goal_text}에 적합한 음식을 추천해주세요.

위 식재료와 건강 정보를 고려하여 3-5가지 맞춤형 음식을 추천해주세요.

**응답 형식:** 반드시 다음 JSON 형식으로만 응답하세요:

{{
  "foods": [
    {{
      "name": "음식 이름",
      "description": "간단한 설명 (건강상 이점 포함)",
      "ingredients": ["재료1", "재료2", "재료3"],
      "steps": [
        "조리 단계 1",
        "조리 단계 2",
        "조리 단계 3",
        "조리 단계 4"
      ]
    }}
  ]
}}

주의사항:
- 각 음식은 3-6개의 조리 단계로 구성하세요
- 설명은 한 문장으로 간결하게
- 보유 재료 위주로 활용하되, 필요시 기본 양념(소금, 간장 등)은 추가 가능
"""

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "당신은 친절하고 전문적인 영양사이자 요리사입니다. 반드시 JSON 형식으로만 응답합니다."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000,
                response_format={"type": "json_object"}
            )
            
            recommendation_text = response.choices[0].message.content
            
        except Exception as e:
            print(f"⚠️ OpenAI API 호출 실패: {e}")
            import traceback
            traceback.print_exc()
            
            # 폴백: JSON 형식으로 간단한 추천 생성
            ingredients_list = [ing.ingredient_name for ing in ingredients]
            
            fallback_foods = []
            
            # 보유 재료에 따라 기본 레시피 제공
            if any('양배추' in ing or '배추' in ing for ing in ingredients_list):
                fallback_foods.append({
                    "name": "양배추 볶음",
                    "description": "간단하고 건강한 채소 요리",
                    "ingredients": ["양배추", "마늘", "소금", "참기름"],
                    "steps": [
                        "양배추를 먹기 좋은 크기로 썰어주세요",
                        "팬에 기름을 두르고 마늘을 볶아주세요",
                        "양배추를 넣고 센 불에서 빠르게 볶아주세요",
                        "소금으로 간하고 참기름을 넣어 완성!"
                    ]
                })
            
            if any('닭' in ing or '고기' in ing for ing in ingredients_list):
                fallback_foods.append({
                    "name": "닭가슴살 구이",
                    "description": "단백질이 풍부한 건강 요리",
                    "ingredients": ["닭가슴살", "소금", "후추", "올리브유"],
                    "steps": [
                        "닭가슴살에 소금, 후추로 밑간해주세요",
                        "팬에 올리브유를 두르고 달궈주세요",
                        "닭가슴살을 앞뒤로 노릇하게 구워주세요",
                        "먹기 좋은 크기로 썰어 완성!"
                    ]
                })
            
            if any('채소' in ing or '브로콜리' in ing or '당근' in ing for ing in ingredients_list):
                fallback_foods.append({
                    "name": "채소 볶음",
                    "description": "다양한 영양소가 가득한 건강식",
                    "ingredients": ["각종 채소", "마늘", "간장", "참기름"],
                    "steps": [
                        "채소를 먹기 좋은 크기로 썰어주세요",
                        "팬에 마늘을 볶다가 채소를 넣어주세요",
                        "간장으로 간하며 볶아주세요",
                        "참기름을 넣어 완성!"
                    ]
                })
            
            # 기본 추천이 없으면 범용 레시피 제공
            if not fallback_foods:
                fallback_foods = [
                    {
                        "name": "간단한 볶음 요리",
                        "description": "보유 재료로 만드는 건강한 한 끼",
                        "ingredients": ingredients_list[:4] if len(ingredients_list) > 0 else ["준비된 재료"],
                        "steps": [
                            "재료를 깨끗이 씻어주세요",
                            "먹기 좋은 크기로 손질해주세요",
                            "팬에 기름을 두르고 볶아주세요",
                            "간을 맞추고 완성!"
                        ]
                    }
                ]
            
            # JSON 형식으로 반환
            import json
            recommendation_text = json.dumps({
                "foods": fallback_foods
            }, ensure_ascii=False)
        
        return ApiResponse(
            success=True,
            data=RecommendationData(
                recommendations=recommendation_text,
                ingredients_used=[ing.ingredient_name for ing in ingredients],
                total_ingredients=len(ingredients)
            ),
            message="✅ 맞춤형 음식 추천이 생성되었습니다!"
        )
        
    except Exception as e:
        print(f"❌ 음식 추천 생성 실패: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"음식 추천 생성 중 오류가 발생했습니다: {str(e)}")


@router.post("/analyze-with-roboflow-gpt")
async def analyze_ingredients_with_roboflow_gpt(
    file: UploadFile = File(...)
):
    """
    Roboflow + GPT Vision으로 식재료 분석
    
    1. Roboflow로 Bounding Box 탐지
    2. 각 Box로 이미지 Crop
    3. GPT Vision으로 정확한 재료명 확인
    
    **Args:**
        file: 업로드된 이미지 파일
        
    **Returns:**
        분석된 식재료 리스트
    """
    try:
        # 이미지 읽기
        image_bytes = await file.read()
        
        # Roboflow 서비스
        roboflow_service = get_roboflow_service()
        gpt_service = get_gpt_vision_service()
        
        # 1. Roboflow로 객체 탐지
        detections = roboflow_service.detect_ingredients(image_bytes)
        
        if not detections:
            return ApiResponse(
                success=True,
                data={
                    "ingredients": [],
                    "message": "식재료를 찾을 수 없습니다. 다른 이미지를 업로드해주세요."
                },
                message="식재료가 탐지되지 않았습니다."
            )
        
        # 2. 원본 이미지에 Bounding Box 그리기
        roboflow_hints = [det.get("class", det.get("className", "-")) for det in detections]
        image_with_boxes = roboflow_service.draw_bboxes_on_image(image_bytes, detections)
        
        # 3. GPT Vision으로 통합 분석
        identified_ingredients = gpt_service.analyze_ingredients_with_boxes(
            image_with_boxes,
            len(detections),
            roboflow_hints
        )
        
        # 결과 조합
        analyzed_ingredients = []
        
        for i in range(len(detections)):
            detection = detections[i]
            ingredient_name = identified_ingredients[i] if i < len(identified_ingredients) else "알 수 없음"
            
            roboflow_class = detection.get("class", detection.get("className", "-"))
            confidence = detection.get("confidence", 0)
            
            analyzed_ingredients.append({
                "name": ingredient_name,
                "roboflow_prediction": roboflow_class,
                "confidence": confidence,
                "bbox": {
                    "x": detection.get("x"),
                    "y": detection.get("y"),
                    "width": detection.get("width"),
                    "height": detection.get("height")
                }
            })
        
        # GPT Vision이 추가로 발견한 객체 (Few-shot 결과)
        if len(identified_ingredients) > len(detections):
            for i in range(len(detections), len(identified_ingredients)):
                additional_ingredient = identified_ingredients[i]
                
                analyzed_ingredients.append({
                    "name": additional_ingredient,
                    "roboflow_prediction": "-",
                    "confidence": 1.0,
                    "bbox": None
                })
        
        # 결과 출력
        print(f"✅ 식재료 분석 완료: {len(analyzed_ingredients)}개")
        
        return ApiResponse(
            success=True,
            data={
                "ingredients": analyzed_ingredients,
                "total_detected": len(detections),
                "total_analyzed": len(analyzed_ingredients)
            },
            message=f"✅ {len(analyzed_ingredients)}개의 식재료가 분석되었습니다!"
        )
        
    except Exception as e:
        print(f"❌ 식재료 분석 실패: {e}")
        raise HTTPException(status_code=500, detail=f"식재료 분석 중 오류가 발생했습니다: {str(e)}")

