"""LangChain 기반 음식 DB 검색 서비스"""
import json
from typing import Optional, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage

from app.core.config import get_settings
from app.db.models_food_nutrients import FoodNutrient

settings = get_settings()


class FoodDBFinder:
    """LangChain을 활용한 의미 기반 음식 DB 검색"""
    
    def __init__(self):
        if not settings.openai_api_key:
            raise ValueError("❌ OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.")
        
        self.llm = ChatOpenAI(
            api_key=settings.openai_api_key,
            model="gpt-4o-mini",
            temperature=0.3,  # 낮은 temperature로 일관성 있는 판단
        )
    
    async def find_exact_match(
        self,
        detected_food_name: str,
        session: AsyncSession
    ) -> Optional[Dict[str, Any]]:
        """
        LangChain을 사용하여 DB에서 정확한 음식 매칭
        
        Args:
            detected_food_name: GPT Vision이 감지한 음식명
            session: DB 세션
        
        Returns:
            매칭 성공 시: {
                "found": True,
                "food_data": FoodNutrient 객체,
                "confidence": 신뢰도 (0-100),
                "reason": 매칭 이유
            }
            매칭 실패 시: {
                "found": False,
                "confidence": 0,
                "reason": 실패 이유
            }
        """
        print(f"🔍 [LangChain] '{detected_food_name}' DB 검색 시작...")
        
        # 1. DB에서 정확히 일치하는 음식 먼저 검색
        exact_stmt = select(FoodNutrient).where(
            FoodNutrient.nutrient_name == detected_food_name
        ).limit(1)
        exact_result = await session.execute(exact_stmt)
        exact_match = exact_result.scalar_one_or_none()
        
        if exact_match:
            print(f"✅ [LangChain] 정확한 매칭 발견: {exact_match.nutrient_name}")
            return {
                "found": True,
                "food_data": exact_match,
                "confidence": 100,
                "reason": "DB에 정확히 일치하는 음식명이 존재합니다."
            }
        
        # 2. 유사한 음식 후보 검색 (더 정확한 검색)
        print(f"⚠️ [LangChain] 정확한 매칭 없음. 유사 음식 검색 중...")
        
        # 음식명에서 키워드 추출하여 검색
        search_keyword = detected_food_name.replace(" ", "")
        
        # 여러 검색 방법 시도
        candidates = []
        
        # 방법 1: 정확한 부분 문자열 매칭 (우선순위 높음)
        exact_partial_stmt = select(FoodNutrient).where(
            FoodNutrient.nutrient_name.like(f"%{search_keyword}%")
        ).limit(20)
        exact_partial_result = await session.execute(exact_partial_stmt)
        candidates.extend(exact_partial_result.scalars().all())
        
        # 방법 2: 대표식품명으로도 검색
        if len(candidates) < 10:
            repr_stmt = select(FoodNutrient).where(
                FoodNutrient.representative_food_name.like(f"%{search_keyword}%")
            ).limit(10)
            repr_result = await session.execute(repr_stmt)
            candidates.extend(repr_result.scalars().all())
        
        # 중복 제거
        seen_ids = set()
        unique_candidates = []
        for c in candidates:
            if c.food_id not in seen_ids:
                seen_ids.add(c.food_id)
                unique_candidates.append(c)
        candidates = unique_candidates[:10]  # 최대 10개
        
        if not candidates:
            print(f"❌ [LangChain] 유사 음식 없음")
            return {
                "found": False,
                "confidence": 0,
                "reason": f"DB에 '{detected_food_name}'과 유사한 음식이 없습니다."
            }
        
        print(f"📋 [LangChain] 유사 음식 {len(candidates)}개 발견")
        
        # 3. LLM에게 의미 기반 매칭 요청
        validation_result = await self._validate_with_llm(
            detected_food_name,
            candidates
        )
        
        if validation_result["found"]:
            # 매칭된 음식 데이터 조회
            matched_food_id = validation_result["food_id"]
            food_stmt = select(FoodNutrient).where(
                FoodNutrient.food_id == matched_food_id
            )
            food_result = await session.execute(food_stmt)
            food_data = food_result.scalar_one_or_none()
            
            if food_data:
                print(f"✅ [LangChain] LLM 검증 완료: {food_data.nutrient_name} (신뢰도: {validation_result['confidence']}%)")
                return {
                    "found": True,
                    "food_data": food_data,
                    "confidence": validation_result["confidence"],
                    "reason": validation_result["reason"]
                }
        
        print(f"❌ [LangChain] LLM 검증 실패 (신뢰도 부족)")
        return {
            "found": False,
            "confidence": validation_result.get("confidence", 0),
            "reason": validation_result.get("reason", "신뢰도가 낮아 매칭하지 않습니다.")
        }
    
    async def estimate_nutrition_without_db(
        self,
        food_name: str,
        ingredients: list,
        portion_size_g: float
    ) -> Dict[str, Any]:
        """
        DB에 없는 음식의 영양성분을 LangChain으로 추정
        
        Args:
            food_name: 음식명
            ingredients: 재료 리스트
            portion_size_g: 섭취량 (g)
        
        Returns:
            추정된 영양성분 정보
        """
        print(f"🤖 [LangChain] DB 없는 음식 영양성분 추정: {food_name} ({portion_size_g}g)")
        
        ingredients_str = ", ".join(ingredients) if ingredients else "정보 없음"
        
        prompt = f"""당신은 영양학 전문가입니다. 다음 음식의 영양성분을 추정해주세요.

**음식명:** {food_name}
**주요 재료:** {ingredients_str}
**섭취량:** {portion_size_g}g

**추정 방법:**
1. 음식명과 재료를 바탕으로 일반적인 영양 데이터베이스 지식을 활용하세요.
2. 유사한 음식의 영양성분을 참고하세요.
3. {portion_size_g}g 기준으로 영양성분을 계산하세요.
4. Atwater 공식을 사용하여 칼로리를 계산하세요:
   - 칼로리 = (단백질 × 4) + (탄수화물 × 4) + (지방 × 9)

**응답 형식 (JSON):**
{{
  "calories": 추정 칼로리 (kcal, 소수점 1자리),
  "protein": 추정 단백질 (g, 소수점 2자리),
  "carbs": 추정 탄수화물 (g, 소수점 2자리),
  "fat": 추정 지방 (g, 소수점 2자리),
  "sodium": 추정 나트륨 (mg, 소수점 1자리),
  "fiber": 추정 식이섬유 (g, 소수점 2자리),
  "confidence": 추정 신뢰도 (0-100, 정수),
  "estimation_note": "추정 근거 및 참고한 유사 음식"
}}

**중요:** 
- 보수적으로 추정하세요 (과대평가보다 과소평가가 낫습니다)
- 신뢰도는 정보가 충분하면 70-80, 불충분하면 40-60으로 설정하세요
- JSON 형식만 반환하세요 (다른 텍스트 포함 금지)
"""
        
        messages = [
            SystemMessage(content="당신은 영양학 전문가입니다. JSON 형식으로만 응답합니다."),
            HumanMessage(content=prompt)
        ]
        
        try:
            response = await self.llm.ainvoke(messages)
            response_text = response.content.strip()
            
            # JSON 파싱
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
                response_text = response_text.strip()
            
            result = json.loads(response_text)
            
            print(f"✅ [LangChain] 영양성분 추정 완료: {result['calories']} kcal (신뢰도: {result['confidence']}%)")
            print(f"📝 [LangChain] 추정 근거: {result['estimation_note']}")
            
            return result
            
        except Exception as e:
            print(f"❌ [LangChain] 영양성분 추정 실패: {e}")
            # 폴백: 매우 보수적인 기본값
            return {
                "calories": 200.0,
                "protein": 10.0,
                "carbs": 25.0,
                "fat": 5.0,
                "sodium": 300.0,
                "fiber": 2.0,
                "confidence": 30,
                "estimation_note": "추정 실패, 기본값 사용 (폴백)"
            }
    
    async def calculate_nutrition_with_llm(
        self,
        food_data: FoodNutrient,
        portion_size_g: float
    ) -> Dict[str, Any]:
        """
        LangChain을 사용하여 음식의 영양성분과 칼로리 계산
        
        Args:
            food_data: DB에서 조회한 음식 데이터
            portion_size_g: 실제 섭취량 (g)
        
        Returns:
            계산된 영양성분 정보
        """
        print(f"🧮 [LangChain] 영양성분 계산 시작: {food_data.nutrient_name} ({portion_size_g}g)")
        
        # DB 정보 구성
        reference_value = food_data.reference_value or 100.0
        
        db_info = f"""
**음식명:** {food_data.nutrient_name}
**영양성분함량기준량 (reference_value):** {reference_value}g
**식품 중량 (unit):** {food_data.unit}g
**{reference_value}g당 영양성분:**
- 칼로리(kcal): {food_data.kcal or 0}
- 단백질(g): {food_data.protein or 0}
- 탄수화물(g): {food_data.carb or 0}
- 지방(g): {food_data.fat or 0}
- 나트륨(mg): {food_data.sodium or 0}
- 식이섬유(g): {food_data.fiber or 0}

**사용자 섭취량:** {portion_size_g}g
"""
        
        prompt = f"""당신은 영양 계산 전문가입니다. 다음 음식의 영양성분을 계산해주세요.

{db_info}

**계산 방법:**
1. DB의 영양성분은 {reference_value}g 기준입니다 (reference_value={reference_value}).
2. 사용자가 섭취한 양은 {portion_size_g}g입니다.
3. 각 영양성분을 비례 계산하세요: (DB값 × {portion_size_g} / {reference_value})
4. kcal이 DB에 있으면 그 값을 사용하고, 없으면 Atwater 공식을 사용하세요:
   - 칼로리 = (단백질 × 4) + (탄수화물 × 4) + (지방 × 9)

**응답 형식 (JSON):**
{{
  "calories": 계산된 칼로리 (kcal, 소수점 1자리),
  "protein": 계산된 단백질 (g, 소수점 2자리),
  "carbs": 계산된 탄수화물 (g, 소수점 2자리),
  "fat": 계산된 지방 (g, 소수점 2자리),
  "sodium": 계산된 나트륨 (mg, 소수점 1자리),
  "fiber": 계산된 식이섬유 (g, 소수점 2자리),
  "calculation_method": "DB kcal 사용" 또는 "Atwater 공식 사용"
}}

**중요:** JSON 형식만 반환하세요 (다른 텍스트 포함 금지)
"""
        
        messages = [
            SystemMessage(content="당신은 영양 계산 전문가입니다. JSON 형식으로만 응답합니다."),
            HumanMessage(content=prompt)
        ]
        
        try:
            response = await self.llm.ainvoke(messages)
            response_text = response.content.strip()
            
            # JSON 파싱
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
                response_text = response_text.strip()
            
            result = json.loads(response_text)
            
            print(f"✅ [LangChain] 칼로리 계산 완료: {result['calories']} kcal")
            print(f"📊 [LangChain] 계산 방식: {result['calculation_method']}")
            
            return result
            
        except Exception as e:
            print(f"❌ [LangChain] 영양성분 계산 실패: {e}")
            # 폴백: 직접 계산
            reference_value = food_data.reference_value or 100.0
            ratio = portion_size_g / reference_value
            print(f"🔧 [폴백] reference_value={reference_value}g, portion_size={portion_size_g}g, ratio={ratio:.2f}")
            
            if food_data.kcal:
                calories = food_data.kcal * ratio
                method = "DB kcal 사용 (폴백)"
            else:
                protein_cal = (food_data.protein or 0) * 4
                carb_cal = (food_data.carb or 0) * 4
                fat_cal = (food_data.fat or 0) * 9
                calories = (protein_cal + carb_cal + fat_cal) * ratio
                method = "Atwater 공식 사용 (폴백)"
            
            return {
                "calories": round(calories, 1),
                "protein": round((food_data.protein or 0) * ratio, 2),
                "carbs": round((food_data.carb or 0) * ratio, 2),
                "fat": round((food_data.fat or 0) * ratio, 2),
                "sodium": round((food_data.sodium or 0) * ratio, 1),
                "fiber": round((food_data.fiber or 0) * ratio, 2),
                "calculation_method": method
            }
    
    async def _validate_with_llm(
        self,
        detected_food_name: str,
        candidates: list
    ) -> Dict[str, Any]:
        """
        LLM을 사용하여 음식명의 의미를 분석하고 매칭 검증
        
        Args:
            detected_food_name: 감지된 음식명
            candidates: DB 후보 음식 리스트
        
        Returns:
            검증 결과 딕셔너리
        """
        # 후보 음식 정보 구성
        candidates_info = []
        for i, candidate in enumerate(candidates, 1):
            candidates_info.append(
                f"{i}. {candidate.nutrient_name} (food_id: {candidate.food_id})"
            )
        
        candidates_text = "\n".join(candidates_info)
        
        # LLM 프롬프트
        prompt = f"""당신은 음식 분류 전문가입니다. 음식명을 분석하여 정확한 매칭을 판단해주세요.

**감지된 음식:** {detected_food_name}

**DB 후보 음식 목록:**
{candidates_text}

**분석 기준:**
1. **정확한 이름 매칭 우선**: 감지된 음식명과 정확히 일치하거나 포함하는 후보를 최우선으로 선택하세요.
   예: "전복죽" 감지 → "전복죽" 또는 "전복죽(냉동)" 등이 있으면 100% 매칭
   
2. **주재료 분석**: 음식명에서 주재료를 추론하세요.
   - "전복죽" → 주재료: "전복", 조리법: "죽"
   - "복죽" → 주재료: "복어", 조리법: "죽"
   - "전복"과 "복어"는 **완전히 다른 재료**입니다!
   
3. **부분 일치 주의**: 
   - "전복죽"을 찾을 때 "복죽"은 매칭하지 마세요 (주재료 다름)
   - "전복구이"도 매칭하지 마세요 (조리법 다름)
   
4. **신뢰도 기준**:
   - 정확히 일치: 100%
   - 주재료 + 조리법 일치: 90-95%
   - 조리법만 일치: 30% 이하 (found=false)
   - 주재료만 일치: 40-60%
   - 둘 다 다름: 0% (found=false)

**응답 형식 (JSON):**
{{
  "found": true 또는 false,
  "food_id": "매칭된 음식의 food_id (found가 true인 경우)",
  "matched_name": "매칭된 음식명 (found가 true인 경우)",
  "confidence": 신뢰도 점수 (0-100),
  "reason": "매칭 판단 이유 (정확한 비교 결과 포함)"
}}

**중요:**
- 신뢰도 80% 이상인 경우만 found를 true로 설정하세요
- "전복"과 "복어"는 다른 재료입니다!
- JSON 형식만 반환하세요 (다른 텍스트 포함 금지)
"""
        
        messages = [
            SystemMessage(content="당신은 음식 분류 전문가입니다. JSON 형식으로만 응답합니다."),
            HumanMessage(content=prompt)
        ]
        
        try:
            response = await self.llm.ainvoke(messages)
            response_text = response.content.strip()
            
            # JSON 파싱
            # 코드 블록 제거
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
                response_text = response_text.strip()
            
            result = json.loads(response_text)
            
            print(f"🤖 [LLM 응답] found={result.get('found')}, confidence={result.get('confidence')}%")
            print(f"📝 [LLM 이유] {result.get('reason')}")
            
            return result
            
        except json.JSONDecodeError as e:
            print(f"❌ [LLM] JSON 파싱 실패: {e}")
            print(f"📄 [LLM 응답] {response_text}")
            return {
                "found": False,
                "confidence": 0,
                "reason": "LLM 응답 파싱 실패"
            }
        except Exception as e:
            print(f"❌ [LLM] 검증 중 오류: {e}")
            return {
                "found": False,
                "confidence": 0,
                "reason": f"LLM 검증 중 오류 발생: {str(e)}"
            }


# 싱글톤 인스턴스
_food_db_finder_instance = None

def get_food_db_finder() -> FoodDBFinder:
    """FoodDBFinder 싱글톤 인스턴스 반환"""
    global _food_db_finder_instance
    if _food_db_finder_instance is None:
        _food_db_finder_instance = FoodDBFinder()
    return _food_db_finder_instance

