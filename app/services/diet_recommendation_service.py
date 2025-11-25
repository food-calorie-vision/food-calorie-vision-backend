"""식단 추천 서비스 - LangChain 기반 건강 목표별 식단 추천"""
from __future__ import annotations

import json
from typing import Optional, Dict, Any

from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage

from app.core.config import get_settings
from app.db.models import User

settings = get_settings()


class DietRecommendationService:
    """LangChain을 활용한 개인 맞춤 식단 추천 서비스"""

    def __init__(self):
        if not settings.openai_api_key:
            raise ValueError("❌ OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.")

        self.llm = ChatOpenAI(
            api_key=settings.openai_api_key,
            model="gpt-4o-mini",
            temperature=0.4,
        )

    def calculate_bmr(self, gender: str, age: int, weight: float, height: Optional[float] = None) -> float:
        """
        기초대사량(BMR) 계산 - Harris-Benedict 공식 사용
        """
        if height is None:
            height = 170.0 if gender == "M" else 160.0

        if gender == "M":
            bmr = 88.362 + (13.397 * weight) + (4.799 * height) - (5.677 * age)
        elif gender == "F":
            bmr = 447.593 + (9.247 * weight) + (3.098 * height) - (4.330 * age)
        else:
            bmr_m = 88.362 + (13.397 * weight) + (4.799 * height) - (5.677 * age)
            bmr_f = 447.593 + (9.247 * weight) + (3.098 * height) - (4.330 * age)
            bmr = (bmr_m + bmr_f) / 2

        return round(bmr, 1)

    def calculate_tdee(self, bmr: float, activity_level: str = "moderate") -> float:
        """1일 총 에너지 소비량(TDEE) 계산"""
        activity_factors = {
            "sedentary": 1.2,
            "light": 1.375,
            "moderate": 1.55,
            "active": 1.725,
            "very_active": 1.9,
        }
        factor = activity_factors.get(activity_level, 1.55)
        return round(bmr * factor, 1)

    def calculate_target_calories(self, tdee: float, health_goal: str) -> float:
        """건강 목표에 따른 목표 칼로리 계산"""
        if health_goal == "loss":
            target = tdee - 500
        elif health_goal == "gain":
            target = tdee + 500
        else:
            target = tdee
        return round(target, 1)

    async def generate_diet_plan(
        self,
        user: User,
        user_request: str = "",
        activity_level: str = "moderate",
    ) -> dict:
        """
        사용자 정보를 기반으로 LangChain LLMChain이 식단을 추천
        """
        bmr = self.calculate_bmr(
            gender=user.gender or "M",
            age=user.age or 30,
            weight=float(user.weight or 70.0),
            height=float(user.height) if user.height else None,
        )
        tdee = self.calculate_tdee(bmr, activity_level)
        target_calories = self.calculate_target_calories(tdee, user.health_goal)

        health_goal_kr = {
            "loss": "체중 감량",
            "maintain": "체중 유지",
            "gain": "체중 증가",
        }.get(user.health_goal, "체중 유지")

        gender_text = "남성" if user.gender == "M" else "여성" if user.gender == "F" else "기타"
        prompt = f"""사용자 정보:
- 성별: {gender_text}
- 나이: {user.age or 30}세
- 체중: {float(user.weight or 70.0)}kg
- 건강 목표: {health_goal_kr}

계산된 정보:
- BMR: {bmr} kcal/day
- TDEE: {tdee} kcal/day
- 목표 칼로리: {target_calories} kcal/day

사용자 요청: {user_request or "특별한 요청 없음"}

요구사항:
1. 하루 식단 옵션 3개(A/B/C)를 제시합니다.
2. 각 옵션은 아침/점심/저녁/간식으로 구성합니다.
3. 각 끼니마다 칼로리와 단백질/탄수화물/지방(g)을 포함합니다.
4. 총 칼로리는 목표 칼로리 ±100kcal 범위로 제한합니다.
5. 아래 JSON 스키마를 정확히 따릅니다.

{{
  "bmr": {bmr},
  "tdee": {tdee},
  "target_calories": {target_calories},
  "health_goal": "{health_goal_kr}",
  "diet_plans": [
    {{
      "name": "식단 A",
      "description": "간단한 설명",
      "total_calories": 0,
      "meals": [
        {{
          "type": "breakfast",
          "menu": "...",
          "calories": 0,
          "nutrients": {{"protein": 0, "carbs": 0, "fat": 0}}
        }}
      ]
    }}
  ]
}}

JSON만 출력하세요."""

        response = await self.llm.ainvoke(
            [
                SystemMessage(content="당신은 한국 사용자의 건강 목표를 돕는 전문 영양사입니다. JSON으로만 응답하세요."),
                HumanMessage(content=prompt),
            ]
        )
        response_text = response.content

        try:
            parsed: Dict[str, Any] = json.loads(response_text)
        except json.JSONDecodeError:
            parsed = {}

        normalized_plans = self._normalize_plans(parsed.get("diet_plans") or parsed.get("dietPlans") or [])
        normalized_goal = self._normalize_health_goal_value(
            parsed.get("health_goal") or parsed.get("healthGoal"),
            user.health_goal or "maintain"
        )
        normalized_goal_kr = self._health_goal_to_kr(
            parsed.get("health_goal_kr") or parsed.get("healthGoalKr"),
            normalized_goal
        )

        return {
            "bmr": parsed.get("bmr", bmr),
            "tdee": parsed.get("tdee", tdee),
            "target_calories": parsed.get("target_calories", target_calories),
            "health_goal": normalized_goal,
            "health_goal_kr": normalized_goal_kr,
            "diet_plans": normalized_plans,
            "gpt_response": response_text,
        }

    def _normalize_plans(self, raw_plans: Any) -> list[Dict[str, Any]]:
        normalized = []
        if not isinstance(raw_plans, list):
            return normalized
        for plan in raw_plans:
            if not isinstance(plan, dict):
                continue
            meals_block = plan.get("meals")
            meal_texts = {"breakfast": "", "lunch": "", "dinner": "", "snack": ""}
            if isinstance(meals_block, dict):
                for key in meal_texts.keys():
                    value = meals_block.get(key)
                    if isinstance(value, dict):
                        meal_texts[key] = value.get("menu") or value.get("description") or ""
                    else:
                        meal_texts[key] = str(value or "")
            elif isinstance(meals_block, list):
                for entry in meals_block:
                    meal_type = entry.get("type") if isinstance(entry, dict) else None
                    if meal_type in meal_texts:
                        meal_texts[meal_type] = entry.get("menu") or entry.get("description") or entry.get("text") or ""
            total_calories = plan.get("totalCalories") or plan.get("total_calories")
            if isinstance(total_calories, (int, float)):
                total_calories = f"{total_calories} kcal"
            total_calories = str(total_calories or "")
            meal_details_raw = plan.get("meal_details") or plan.get("mealDetails")
            meal_details = {}
            if isinstance(meal_details_raw, dict):
                for meal_key, detail in meal_details_raw.items():
                    if meal_key in meal_texts and isinstance(detail, dict):
                        try:
                            meal_details[meal_key] = {
                                "calories": float(detail.get("calories", 0)),
                                "protein": float(detail.get("protein", 0)),
                                "carb": float(detail.get("carb", detail.get("carbs", 0))),
                                "fat": float(detail.get("fat", 0)),
                            }
                        except (TypeError, ValueError):
                            continue
            normalized.append(
                {
                    "name": plan.get("name", "맞춤 식단"),
                    "description": plan.get("description", "맞춤형 식단 제안"),
                    "totalCalories": total_calories,
                    "meals": meal_texts,
                    "nutrients": plan.get("nutrients"),
                    "meal_details": meal_details if meal_details else None,
                }
            )
        return normalized

    def _normalize_health_goal_value(self, raw_value: Optional[str], fallback: str) -> str:
        if not raw_value:
            return fallback
        normalized = raw_value.strip().lower()
        mapping = {
            "loss": "loss",
            "감량": "loss",
            "다이어트": "loss",
            "체중 감량": "loss",
            "gain": "gain",
            "증량": "gain",
            "체중 증가": "gain",
            "maintain": "maintain",
            "유지": "maintain",
            "체중 유지": "maintain",
        }
        for keyword, code in mapping.items():
            if keyword in normalized:
                return code
        return fallback

    def _health_goal_to_kr(self, raw_value: Optional[str], fallback_code: str) -> str:
        code = self._normalize_health_goal_value(raw_value, fallback_code)
        mapping = {
            "loss": "체중 감량",
            "gain": "체중 증가",
            "maintain": "체중 유지",
        }
        return mapping.get(code, "체중 유지")


_diet_service: DietRecommendationService | None = None


def get_diet_recommendation_service() -> DietRecommendationService:
    """기존 코드 호환성을 위한 팩토리 함수."""
    global _diet_service
    if _diet_service is None:
        _diet_service = DietRecommendationService()
    return _diet_service
