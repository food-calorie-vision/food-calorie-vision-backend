"""LLM을 사용한 영양소 추정 서비스"""
import json
from typing import Dict, List, Optional

from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema.output_parser import StrOutputParser

from app.core.config import get_settings


class NutrientEstimatorService:
    """LLM을 사용하여 음식의 영양소 정보를 추정하는 서비스"""
    
    def __init__(self):
        settings = get_settings()
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")
        self.llm = ChatOpenAI(
            api_key=settings.openai_api_key,
            model="gpt-4o-mini",
            temperature=0.3,
            model_kwargs={"response_format": {"type": "json_object"}}
        )
    
    async def estimate_nutrients(
        self,
        food_name: str,
        ingredients: List[str],
        portion_size_g: float = 100.0
    ) -> Dict:
        """
        음식명과 재료를 기반으로 영양소 정보를 추정합니다.
        
        Args:
            food_name: 음식 이름 (예: "라멘", "닭가슴살 샐러드")
            ingredients: 재료 목록 (예: ["라면", "계란", "파"])
            portion_size_g: 기준량 (g, 기본값 100g)
            
        Returns:
            영양소 정보 딕셔너리
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", """당신은 영양학 전문가입니다. 음식명과 재료를 기반으로 영양소 정보를 추정하십시오.

**중요 지침:**
1. 100g 기준으로 영양소를 계산하십시오.
2. 한국 식품의약품안전처 데이터베이스 기준을 참고하십시오.
3. 보수적으로 추정하되, 일반적인 레시피를 기준으로 하십시오.
4. 모든 값은 숫자만 반환하십시오 (단위 제외).
5. 정보가 불확실한 경우 0을 반환하십시오.

**출력 형식 (JSON):**
{{
  "protein": 단백질(g),
  "carbs": 탄수화물(g),
  "fat": 지방(g),
  "fiber": 식이섬유(g),
  "sodium": 나트륨(mg),
  "calcium": 칼슘(mg),
  "iron": 철분(mg),
  "vitamin_a": 비타민A(μg),
  "vitamin_c": 비타민C(mg),
  "potassium": 칼륨(mg),
  "magnesium": 마그네슘(mg),
  "saturated_fat": 포화지방(g),
  "cholesterol": 콜레스테롤(mg),
  "trans_fat": 트랜스지방(g),
  "added_sugar": 첨가당(g),
  "calories": 칼로리(kcal),
  "food_class1": "대분류 (예: 면류, 샐러드류)",
  "food_class2": "중분류 또는 주재료"
}}"""),
            ("human", """음식명: {food_name}
재료: {ingredients}

위 음식의 100g 당 영양소 정보를 JSON 형식으로 추정해주세요.""")
        ])
        
        chain = prompt | self.llm | StrOutputParser()
        
        try:
            ingredients_str = ", ".join(ingredients) if ingredients else "정보 없음"
            response = await chain.ainvoke({
                "food_name": food_name,
                "ingredients": ingredients_str
            })
            
            # JSON 파싱
            nutrients = json.loads(response)
            
            # 기본값 설정 (누락된 필드 처리)
            default_nutrients = {
                "protein": 0.0,
                "carbs": 0.0,
                "fat": 0.0,
                "fiber": 0.0,
                "sodium": 0.0,
                "calcium": 0.0,
                "iron": 0.0,
                "vitamin_a": 0.0,
                "vitamin_c": 0.0,
                "potassium": 0.0,
                "magnesium": 0.0,
                "saturated_fat": 0.0,
                "cholesterol": 0.0,
                "trans_fat": 0.0,
                "added_sugar": 0.0,
                "calories": 0,
                "food_class1": "사용자추가",
                "food_class2": None
            }
            
            # 기본값과 병합
            result = {**default_nutrients, **nutrients}
            
            # 칼로리가 0이면 자동 계산
            if result["calories"] == 0:
                result["calories"] = int(
                    result["protein"] * 4 +
                    result["carbs"] * 4 +
                    result["fat"] * 9
                )
            
            print(f"✅ LLM 영양소 추정 완료: {food_name} - {result['calories']}kcal")
            print(f"   단백질={result['protein']}g, 탄수화물={result['carbs']}g, 지방={result['fat']}g")
            
            return result
            
        except json.JSONDecodeError as e:
            print(f"⚠️ LLM 응답 JSON 파싱 실패: {e}")
            print(f"   응답: {response}")
            # 기본값 반환
            return {
                "protein": 0.0,
                "carbs": 0.0,
                "fat": 0.0,
                "fiber": 0.0,
                "sodium": 0.0,
                "calcium": 0.0,
                "iron": 0.0,
                "vitamin_a": 0.0,
                "vitamin_c": 0.0,
                "potassium": 0.0,
                "magnesium": 0.0,
                "saturated_fat": 0.0,
                "cholesterol": 0.0,
                "trans_fat": 0.0,
                "added_sugar": 0.0,
                "calories": 0,
                "food_class1": "사용자추가",
                "food_class2": None
            }
        except Exception as e:
            print(f"❌ LLM 영양소 추정 실패: {e}")
            raise


def get_nutrient_estimator() -> NutrientEstimatorService:
    """NutrientEstimatorService 싱글톤 인스턴스 반환"""
    return NutrientEstimatorService()

