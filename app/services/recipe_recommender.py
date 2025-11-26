"""레시피 추천 전략 (토큰 효율화)"""
from typing import Protocol

class RecommendationStrategy(Protocol):
    """추천 전략 인터페이스"""
    def build_prompt(self, user_ingredients: list[tuple[str, int]], health_info: dict) -> str:
        ...

class AvailableFirstStrategy:
    """보유 재료 우선 추천 전략"""
    
    def build_prompt(self, user_ingredients: list[str], health_info: dict) -> str:
        """
        보유 재료 80% 이상 활용 우선
        부족한 재료는 대체 제안 또는 생략
        """
        if not user_ingredients:
            return self._empty_ingredients_prompt()
        
        # 재료 목록 생성 (count 제거됨)
        ingredient_text = ", ".join(user_ingredients)
        
        # 건강 정보 문자열
        health_text = self._build_health_text(health_info)
        
        # 재료 부족 경고
        shortage_note = ""
        if len(user_ingredients) < 3:
            shortage_note = f"\n\n⚠️ 재료 {len(user_ingredients)}개로 적음. 간단한 레시피 우선 추천."
        
        return f"""당신은 전문 영양사입니다.

{health_text}

보유 식재료:
{ingredient_text}{shortage_note}

**제약사항:**
{self._build_constraints(health_info)}

**추천 전략:**
1. 보유 재료 80% 이상 활용 우선
2. 부족 재료는 missing_ingredients에 명시 + 대체 제안
3. 건강 목표({health_info.get('goal', '유지')})에 적합한 메뉴
4. 3-5가지 다양한 음식 (아침/점심/저녁/간식)

**JSON 응답 (코드블록 없이):**
{{"foods":[{{"name":"음식명","description":"설명","calories":450,"recommended_meal_type":"lunch","ingredients":["재료1"],"missing_ingredients":[],"steps":["단계1","단계2"]}}]}}

주의:
- 알러지 금지
- ```json 마크다운 사용 금지
- 순수 JSON만 응답"""

    def _empty_ingredients_prompt(self) -> str:
        """재료 없을 때 기본 레시피"""
        return """간단한 재료로 만들 수 있는 요리 3가지 추천 (JSON 형식)"""
    
    def _build_health_text(self, health_info: dict) -> str:
        """건강 정보 문자열 생성"""
        goal_map = {'gain': '체중 증가', 'maintain': '체중 유지', 'loss': '체중 감소'}
        goal = goal_map.get(health_info.get('goal'), '체중 유지')
        
        text = f"""사용자 정보:
- 건강 목표: {goal}
- 나이: {health_info.get('age', '정보 없음')}세
- 체중: {health_info.get('weight', '정보 없음')}kg"""
        
        if health_info.get('allergies'):
            text += f"\n- ⚠️ 알러지: {', '.join(health_info['allergies'])}"
        if health_info.get('diseases'):
            text += f"\n- 🏥 질병: {', '.join(health_info['diseases'])}"
        
        return text
    
    def _build_constraints(self, health_info: dict) -> str:
        """제약사항 문자열 생성"""
        constraints = []
        
        if health_info.get('allergies'):
            constraints.append(f"⚠️ 알러지 금지: {', '.join(health_info['allergies'])}")
        if health_info.get('diseases'):
            constraints.append(f"🏥 질병 고려: {', '.join(health_info['diseases'])}")
        
        goal_map = {'gain': '체중 증가', 'maintain': '체중 유지', 'loss': '체중 감소'}
        goal = goal_map.get(health_info.get('goal'), '체중 유지')
        constraints.append(f"🎯 목표: {goal}")
        
        return "\n".join(f"{i+1}. {c}" for i, c in enumerate(constraints))


def get_recommendation_strategy() -> RecommendationStrategy:
    """전략 팩토리"""
    return AvailableFirstStrategy()

