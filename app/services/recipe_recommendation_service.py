"""레시피 추천 서비스 - GPT 기반 개인화 레시피 추천 및 단계별 조리법"""
from typing import Optional, List, Dict
from openai import AsyncOpenAI
import json

from app.core.config import get_settings
from app.db.models import User

settings = get_settings()


class RecipeRecommendationService:
    """GPT를 활용한 개인 맞춤 레시피 추천 및 조리법 서비스"""
    
    def __init__(self):
        if not settings.openai_api_key:
            raise ValueError("❌ OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.")
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
    
    async def get_recipe_recommendations(
        self,
        user: User,
        user_request: str = "",
        conversation_history: List[Dict[str, str]] = None,
        diseases: List[str] = None,
        allergies: List[str] = None,
        user_nickname: str = "",
        has_eaten_today: bool = True,
        deficient_nutrients: List[Dict[str, any]] = None,
        excess_warnings: List[str] = None
    ) -> dict:
        """
        사용자 정보를 기반으로 GPT가 레시피 3개를 추천
        
        Args:
            user: User 객체 (gender, age, weight, health_goal 포함)
            user_request: 사용자의 요청사항 (예: "매콤한 음식 먹고 싶어요")
            conversation_history: 대화 히스토리 (선택사항)
            diseases: 사용자의 질병 목록 (예: ["고지혈증", "고혈압"])
            allergies: 사용자의 알레르기 목록
            user_nickname: 사용자 닉네임 (메시지 생성용)
        
        Returns:
            dict: {
                "recommendations": [레시피 3개],
                "health_warning": 건강 경고 메시지 (있으면),
                "inferred_preference": 추론된 선호도 (시스템용),
                "user_friendly_message": 사용자에게 보여줄 친화적 메시지
            }
        """
        # 건강 목표에 따른 한글 설명
        health_goal_kr = {
            "loss": "체중 감량",
            "maintain": "체중 유지",
            "gain": "체중 증가"
        }.get(user.health_goal, "체중 유지")
        
        # 질병 및 알레르기 정보 구성
        health_info_parts = []
        if diseases:
            health_info_parts.append(f"질병: {', '.join(diseases)}")
        if allergies:
            health_info_parts.append(f"알레르기: {', '.join(allergies)}")
        health_info_text = "\n- " + "\n- ".join(health_info_parts) if health_info_parts else "\n- 없음"
        
        # 오늘 식사 현황 및 부족 영양소 정보 구성
        today_status_text = ""
        if not has_eaten_today:
            today_status_text = "\n\n**오늘 식사 현황:**\n- 오늘 아직 아무것도 먹지 않았습니다."
        elif deficient_nutrients:
            deficient_list = [f"- {n['name']}: 권장량의 {n['percentage']}%만 섭취 (부족)" for n in deficient_nutrients]
            today_status_text = f"\n\n**오늘 식사 현황 및 부족 영양소:**\n" + "\n".join(deficient_list)
            today_status_text += "\n\n**중요:** 사용자가 요청한 재료에 추가로 부족한 영양소를 보완할 수 있는 재료를 포함한 레시피를 추천해주세요."
            today_status_text += "\n예: 단백질이 부족하면 닭가슴살, 계란, 두부 등을 추가하고, 식이섬유가 부족하면 채소, 과일, 견과류 등을 추가하세요."
        
        # GPT 프롬프트 생성
        prompt = f"""당신은 영양사이자 요리 전문가입니다. 사용자의 건강 정보와 선호도를 기반으로 레시피를 추천해주세요.

**사용자 정보:**
- 성별: {'남성' if user.gender == 'M' else '여성' if user.gender == 'F' else '기타'}
- 나이: {user.age or 30}세
- 체중: {float(user.weight or 70.0)}kg
- 건강 목표: {health_goal_kr}
- 건강 상태:{health_info_text}{today_status_text}

**사용자 요청:**
{user_request if user_request else "특별한 요청 없음"}

**중요 지시사항:**
1. 사용자의 요청에서 식감, 맛, 음식 종류 등의 선호도를 추론하세요.
2. **건강 상태(질병, 알레르기)를 반드시 고려하세요. 사용자가 원하는 음식이 건강에 해로울 경우, 그 음식을 직접 추천하지 말고 건강한 대안을 추천하세요.**
   예: 고지혈증이 있는 사용자가 대창을 원하면, 대창 대신 저지방 단백질(닭가슴살, 생선 등)을 사용한 건강한 레시피를 추천하세요.
3. **부족한 영양소가 있으면, 사용자가 요청한 재료에 추가로 부족한 영양소를 보완할 수 있는 재료를 포함한 레시피를 추천하세요.**
   예: 단백질이 부족하면 닭가슴살, 계란, 두부 등을 추가하고, 식이섬유가 부족하면 채소, 과일, 견과류 등을 추가하세요.
4. 건강 목표와 선호도를 고려하여 레시피 3개를 추천하세요.
5. 각 레시피는 제목, 설명, 예상 칼로리, 조리 시간, 난이도를 포함하세요.
6. 사용자가 원하는 음식이 건강에 부적합한 경우, health_warning에 자연스럽고 친절한 설명을 포함하세요.

**응답 형식 (JSON):**
{{
  "inferred_preference": "추론된 선호도 설명 (시스템용, 예: '고지방 고기류 선호')",
  "health_warning": "건강 경고 또는 대안 제시 메시지 (없으면 null)",
  "recommendations": [
    {{
      "name": "레시피 제목",
      "description": "간단한 설명",
      "calories": 450,
      "cooking_time": "30분",
      "difficulty": "보통",
      "suitable_reason": "이 레시피가 적합한 이유"
    }},
    ...
  ]
}}

JSON 형식만 반환하세요. 다른 텍스트는 포함하지 마세요."""

        print(f"🤖 GPT에게 레시피 추천 요청 중...")
        
        # 대화 히스토리가 있으면 포함
        messages = [
            {"role": "system", "content": "당신은 전문 영양사이자 요리 전문가입니다. JSON 형식으로만 응답합니다."}
        ]
        
        if conversation_history:
            messages.extend(conversation_history)
        
        messages.append({"role": "user", "content": prompt})
        
        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=1500,
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        
        gpt_response = response.choices[0].message.content
        print(f"✅ GPT 응답 수신 완료")
        
        # JSON 파싱
        try:
            result = json.loads(gpt_response)
            
            # 사용자 친화적 메시지 생성
            user_friendly_message = self._generate_user_friendly_message(
                user_request=user_request,
                inferred_preference=result.get("inferred_preference", ""),
                health_warning=result.get("health_warning"),
                diseases=diseases,
                user_nickname=user_nickname,
                has_eaten_today=has_eaten_today,
                deficient_nutrients=deficient_nutrients
            )
            
            result["user_friendly_message"] = user_friendly_message
            return result
        except json.JSONDecodeError:
            # 파싱 실패 시 기본값 반환
            default_result = {
                "inferred_preference": "다양한 영양소가 골고루 들어간 음식",
                "health_warning": None,
                "recommendations": [
                    {
                        "name": "닭가슴살 샐러드",
                        "description": "고단백 저칼로리 건강식",
                        "calories": 350,
                        "cooking_time": "20분",
                        "difficulty": "쉬움",
                        "suitable_reason": "건강 목표에 적합한 균형 잡힌 식단"
                    },
                    {
                        "name": "연어 덮밥",
                        "description": "오메가-3가 풍부한 영양식",
                        "calories": 480,
                        "cooking_time": "25분",
                        "difficulty": "보통",
                        "suitable_reason": "필수 지방산과 단백질이 풍부"
                    },
                    {
                        "name": "두부 스테이크",
                        "description": "식물성 단백질이 풍부한 요리",
                        "calories": 320,
                        "cooking_time": "15분",
                        "difficulty": "쉬움",
                        "suitable_reason": "저칼로리 고단백 식품"
                    }
                ]
            }
            default_result["user_friendly_message"] = self._generate_user_friendly_message(
                user_request=user_request,
                inferred_preference=default_result["inferred_preference"],
                health_warning=None,
                diseases=diseases,
                user_nickname=user_nickname
            )
            return default_result
    
    def _generate_user_friendly_message(
        self,
        user_request: str,
        inferred_preference: str,
        health_warning: Optional[str],
        diseases: List[str] = None,
        user_nickname: str = "",
        has_eaten_today: bool = True,
        deficient_nutrients: List[Dict[str, any]] = None
    ) -> str:
        """
        사용자에게 보여줄 친화적 메시지 생성
        추론된 선호도를 자연스럽게 표현하고, 건강 상태를 고려한 안내를 포함
        """
        # 사용자 요청에서 음식 키워드 추출 시도
        food_keywords = []
        common_foods = ["대창", "삼겹살", "치킨", "피자", "햄버거", "라면", "떡볶이", "족발", "보쌈"]
        for food in common_foods:
            if food in user_request:
                food_keywords.append(food)
        
        # 닉네임 설정
        name_prefix = f"{user_nickname}님, " if user_nickname else ""
        
        # 메시지 구성
        message_parts = []
        
        # 사용자 요청이 실제로 있는지 확인 (빈 문자열이나 의미 없는 텍스트 제외)
        has_meaningful_request = user_request and len(user_request.strip()) > 0 and not user_request.strip().startswith("오늘")
        
        # 1. 오늘 식사 현황 안내
        if not has_eaten_today:
            message_parts.append(f"{name_prefix}오늘 아직 아무것도 드시지 않으셨네요!")
            message_parts.append("건강한 식사를 시작할 수 있도록 레시피를 추천해드릴게요! 🍳")
        elif has_meaningful_request:
            # 사용자가 실제로 음식 요청을 한 경우에만 인정
            if food_keywords:
                food_text = ", ".join(food_keywords)
                message_parts.append(f"{name_prefix}{food_text} 관련 음식을 드시고 싶으시군요!")
            else:
                # 사용자 요청을 자연스럽게 반영
                clean_request = user_request.strip()
                message_parts.append(f"{name_prefix}{clean_request}")
        
        # 2. 부족한 영양소 안내
        if deficient_nutrients and len(deficient_nutrients) > 0:
            nutrient_names = [n['name'] for n in deficient_nutrients]
            nutrient_text = ", ".join(nutrient_names)
            message_parts.append(f"\n오늘 섭취한 영양소를 확인해보니 {nutrient_text}이(가) 부족하시네요!")
            message_parts.append("요청하신 재료에 추가로 부족한 영양소를 보완할 수 있는 재료가 들어간 레시피를 추천해드릴게요! 💚")
        
        # 3. 건강 상태 고려 안내 (질병이 있는 경우)
        if diseases and health_warning:
            disease_text = ", ".join(diseases)
            if name_prefix:
                # "홍길동님, " -> "홍길동님의 "
                name_for_health = name_prefix.replace("님, ", "님의 ")
            else:
                name_for_health = ""
            message_parts.append(f"\n또한 {name_for_health}건강을 살펴보니 {disease_text}이(가) 있으시네요!")
            message_parts.append(f"{health_warning}")
        elif health_warning:
            message_parts.append(f"\n{health_warning}")
        
        # 4. 마무리 메시지
        if not has_eaten_today or deficient_nutrients or health_warning or diseases:
            message_parts.append("\n건강을 고려한 레시피를 추천해드릴게요! 아래에서 원하시는 레시피를 선택해주세요 🍳")
        else:
            message_parts.append("\n아래에서 원하시는 레시피를 선택해주세요! 🍳")
        
        return "\n".join(message_parts)
    
    async def get_recipe_detail(
        self,
        recipe_name: str,
        user: User
    ) -> dict:
        """
        선택한 레시피의 상세 단계별 조리법을 제공
        
        Args:
            recipe_name: 선택한 레시피 이름
            user: User 객체
        
        Returns:
            dict: {
                "recipe_name": 레시피 이름,
                "intro": 레시피 소개,
                "total_steps": 총 단계 수,
                "estimated_time": 예상 조리 시간,
                "ingredients": [재료 목록],
                "steps": [
                    {
                        "step_number": 1,
                        "title": "단계 제목",
                        "description": "상세 설명",
                        "tip": "팁 (선택사항)",
                        "image_suggestion": "이미지 설명"
                    },
                    ...
                ],
                "nutrition_info": {
                    "calories": 450,
                    "protein": "35g",
                    "carbs": "45g",
                    "fat": "12g"
                }
            }
        """
        health_goal_kr = {
            "loss": "체중 감량",
            "maintain": "체중 유지",
            "gain": "체중 증가"
        }.get(user.health_goal, "체중 유지")
        
        prompt = f"""당신은 요리 전문가입니다. "{recipe_name}" 레시피의 상세한 단계별 조리법을 제공해주세요.

**사용자 정보:**
- 건강 목표: {health_goal_kr}

**지시사항:**
1. 레시피 소개를 작성하세요.
2. 필요한 재료 목록을 작성하세요.
3. 조리 과정을 5~8단계로 나누어 상세하게 설명하세요.
4. 각 단계마다 제목, 상세 설명, 팁(선택사항)을 포함하세요.
5. 영양 정보를 제공하세요.

**응답 형식 (JSON):**
{{
  "recipe_name": "{recipe_name}",
  "intro": "레시피 소개 (2-3문장)",
  "estimated_time": "30분",
  "ingredients": [
    {{"name": "재료명", "amount": "양"}},
    ...
  ],
  "steps": [
    {{
      "step_number": 1,
      "title": "재료 준비",
      "description": "상세한 설명",
      "tip": "팁 (선택사항)",
      "image_suggestion": "이 단계를 나타내는 이미지 설명"
    }},
    ...
  ],
  "nutrition_info": {{
    "calories": 450,
    "protein": "35g",
    "carbs": "45g",
    "fat": "12g",
    "fiber": "8g",
    "sodium": "800mg"
  }}
}}

JSON 형식만 반환하세요."""

        print(f"🤖 GPT에게 '{recipe_name}' 레시피 상세 요청 중...")
        
        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "당신은 전문 요리사입니다. JSON 형식으로만 응답합니다."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2500,
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        
        gpt_response = response.choices[0].message.content
        print(f"✅ 레시피 상세 정보 수신 완료")
        
        # JSON 파싱
        try:
            result = json.loads(gpt_response)
            result["total_steps"] = len(result.get("steps", []))
            return result
        except json.JSONDecodeError as e:
            print(f"❌ JSON 파싱 오류: {e}")
            # 파싱 실패 시 기본 레시피 반환
            return self._get_fallback_recipe(recipe_name)
    
    def _get_fallback_recipe(self, recipe_name: str) -> dict:
        """JSON 파싱 실패 시 기본 레시피 반환"""
        return {
            "recipe_name": recipe_name,
            "intro": f"{recipe_name}는 건강하고 맛있는 요리입니다.",
            "estimated_time": "30분",
            "total_steps": 5,
            "ingredients": [
                {"name": "주재료", "amount": "적당량"},
                {"name": "양념", "amount": "적당량"}
            ],
            "steps": [
                {
                    "step_number": 1,
                    "title": "재료 준비",
                    "description": "필요한 재료들을 준비합니다.",
                    "tip": "신선한 재료를 사용하세요.",
                    "image_suggestion": "준비된 재료들"
                },
                {
                    "step_number": 2,
                    "title": "조리 시작",
                    "description": "재료를 조리합니다.",
                    "tip": "중불에서 천천히 조리하세요.",
                    "image_suggestion": "조리 중인 모습"
                },
                {
                    "step_number": 3,
                    "title": "간 맞추기",
                    "description": "기호에 맞게 간을 맞춥니다.",
                    "tip": "소금은 조금씩 넣으며 맛을 봅니다.",
                    "image_suggestion": "양념을 추가하는 모습"
                },
                {
                    "step_number": 4,
                    "title": "마무리",
                    "description": "요리를 마무리합니다.",
                    "tip": "불을 끄기 전에 한 번 더 간을 확인하세요.",
                    "image_suggestion": "완성된 요리"
                },
                {
                    "step_number": 5,
                    "title": "플레이팅",
                    "description": "접시에 예쁘게 담아냅니다.",
                    "tip": "허브나 고명으로 장식하면 더 좋습니다.",
                    "image_suggestion": "플레이팅된 완성 요리"
                }
            ],
            "nutrition_info": {
                "calories": 400,
                "protein": "30g",
                "carbs": "40g",
                "fat": "15g",
                "fiber": "5g",
                "sodium": "800mg"
            }
        }


# 싱글톤 인스턴스
_recipe_recommendation_service: Optional[RecipeRecommendationService] = None


def get_recipe_recommendation_service() -> RecipeRecommendationService:
    """RecipeRecommendationService 싱글톤 인스턴스 반환"""
    global _recipe_recommendation_service
    if _recipe_recommendation_service is None:
        _recipe_recommendation_service = RecipeRecommendationService()
    return _recipe_recommendation_service


