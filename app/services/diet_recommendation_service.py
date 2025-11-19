"""식단 추천 서비스 - GPT 기반 건강 목표별 식단 추천"""
from typing import Optional
from openai import AsyncOpenAI

from app.core.config import get_settings
from app.db.models import User

settings = get_settings()


class DietRecommendationService:
    """GPT를 활용한 개인 맞춤 식단 추천 서비스"""
    
    def __init__(self):
        if not settings.openai_api_key:
            raise ValueError("❌ OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.")
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
    
    def calculate_bmr(self, gender: str, age: int, weight: float, height: Optional[float] = None) -> float:
        """
        기초대사량(BMR) 계산 - Harris-Benedict 공식 사용
        
        Args:
            gender: 'M' (남성), 'F' (여성), 'Other'
            age: 나이 (세)
            weight: 체중 (kg)
            height: 키 (cm) - 없으면 평균값 사용
        
        Returns:
            기초대사량 (kcal/day)
        """
        # height가 없으면 평균값 사용
        if height is None:
            height = 170.0 if gender == 'M' else 160.0
        
        # Harris-Benedict 공식 (수정판)
        if gender == 'M':
            # 남성: BMR = 88.362 + (13.397 × 체중kg) + (4.799 × 키cm) - (5.677 × 나이)
            bmr = 88.362 + (13.397 * weight) + (4.799 * height) - (5.677 * age)
        elif gender == 'F':
            # 여성: BMR = 447.593 + (9.247 × 체중kg) + (3.098 × 키cm) - (4.330 × 나이)
            bmr = 447.593 + (9.247 * weight) + (3.098 * height) - (4.330 * age)
        else:
            # Other: 평균값 사용
            bmr_m = 88.362 + (13.397 * weight) + (4.799 * height) - (5.677 * age)
            bmr_f = 447.593 + (9.247 * weight) + (3.098 * height) - (4.330 * age)
            bmr = (bmr_m + bmr_f) / 2
        
        return round(bmr, 1)
    
    def calculate_tdee(self, bmr: float, activity_level: str = "moderate") -> float:
        """
        1일 총 에너지 소비량(TDEE) 계산
        
        Args:
            bmr: 기초대사량 (kcal/day)
            activity_level: 활동 수준 (sedentary, light, moderate, active, very_active)
        
        Returns:
            TDEE (kcal/day)
        """
        # 활동 계수 (Activity Factor)
        activity_factors = {
            "sedentary": 1.2,      # 거의 운동 안 함
            "light": 1.375,        # 가벼운 운동 (주 1-3회)
            "moderate": 1.55,      # 보통 운동 (주 3-5회)
            "active": 1.725,       # 심한 운동 (주 6-7회)
            "very_active": 1.9     # 매우 심한 운동 (하루 2회)
        }
        
        factor = activity_factors.get(activity_level, 1.55)
        tdee = bmr * factor
        
        return round(tdee, 1)
    
    def calculate_target_calories(self, tdee: float, health_goal: str) -> float:
        """
        건강 목표에 따른 목표 칼로리 계산
        
        Args:
            tdee: 1일 총 에너지 소비량 (kcal/day)
            health_goal: 건강 목표 ('gain', 'maintain', 'loss')
        
        Returns:
            목표 칼로리 (kcal/day)
        """
        if health_goal == "loss":
            # 체중 감량: TDEE - 500kcal (주당 0.5kg 감량 목표)
            target = tdee - 500
        elif health_goal == "gain":
            # 체중 증가: TDEE + 500kcal (주당 0.5kg 증량 목표)
            target = tdee + 500
        else:  # maintain
            # 체중 유지: TDEE 그대로
            target = tdee
        
        return round(target, 1)
    
    async def generate_diet_plan(
        self,
        user: User,
        user_request: str = "",
        activity_level: str = "moderate"
    ) -> dict:
        """
        사용자 정보를 기반으로 GPT가 식단을 추천
        
        Args:
            user: User 객체 (gender, age, weight, health_goal 포함)
            user_request: 사용자의 추가 요청사항 (예: "고기류를 먹고 싶어요")
            activity_level: 활동 수준 (기본값: moderate)
        
        Returns:
            dict: {
                "bmr": 기초대사량,
                "tdee": 1일 총 에너지 소비량,
                "target_calories": 목표 칼로리,
                "health_goal": 건강 목표,
                "diet_plans": [식단 옵션 3개],
                "gpt_response": GPT 원문
            }
        """
        # 1. 기초대사량 계산
        bmr = self.calculate_bmr(
            gender=user.gender or 'M',
            age=user.age or 30,
            weight=float(user.weight or 70.0),
            height=float(user.height) if user.height else None  # height 컬럼 사용
        )
        
        # 2. TDEE 계산
        tdee = self.calculate_tdee(bmr, activity_level)
        
        # 3. 목표 칼로리 계산
        target_calories = self.calculate_target_calories(tdee, user.health_goal)
        
        # 4. 건강 목표에 따른 한글 설명
        health_goal_kr = {
            "loss": "체중 감량",
            "maintain": "체중 유지",
            "gain": "체중 증가"
        }.get(user.health_goal, "체중 유지")
        
        # 5. GPT 프롬프트 생성
        prompt = f"""당신은 영양사입니다. 사용자의 건강 정보를 기반으로 하루 식단을 추천해주세요.

**사용자 정보:**
- 성별: {'남성' if user.gender == 'M' else '여성' if user.gender == 'F' else '기타'}
- 나이: {user.age or 30}세
- 체중: {float(user.weight or 70.0)}kg
- 건강 목표: {health_goal_kr}

**계산된 영양 정보:**
- 기초대사량(BMR): {bmr} kcal/day
- 1일 총 에너지 소비량(TDEE): {tdee} kcal/day
- 목표 칼로리: {target_calories} kcal/day

**사용자 요청:**
{user_request if user_request else "특별한 요청 없음"}

**지시사항:**
1. 위 목표 칼로리를 기준으로 하루 식단 옵션 3개를 추천해주세요.
2. 각 식단은 아침/점심/저녁/간식으로 구성하세요.
3. 각 식단의 총 칼로리는 목표 칼로리 ±100 kcal 이내로 맞춰주세요.
4. 각 식단의 영양소 비율(단백질/탄수화물/지방)을 명시하세요.
5. 건강 목표에 맞는 식단을 추천하세요:
   - 체중 감량: 저칼로리, 고단백, 저탄수화물
   - 체중 유지: 균형 잡힌 영양소
   - 체중 증가: 고칼로리, 고단백, 적절한 탄수화물
6. 사용자 요청사항을 고려하세요.

**응답 형식:**
아래 형식을 **정확히** 따라주세요. 특히 각 끼니별 칼로리를 반드시 명시해야 합니다:

[식단 A]
이름: [식단 이름]
설명: [간단한 설명]
총 칼로리: [숫자] kcal
아침: [메뉴] ([칼로리]kcal)
아침 영양소: 단백질 [숫자]g / 탄수화물 [숫자]g / 지방 [숫자]g
점심: [메뉴] ([칼로리]kcal)
점심 영양소: 단백질 [숫자]g / 탄수화물 [숫자]g / 지방 [숫자]g
저녁: [메뉴] ([칼로리]kcal)
저녁 영양소: 단백질 [숫자]g / 탄수화물 [숫자]g / 지방 [숫자]g
간식: [메뉴] ([칼로리]kcal)
간식 영양소: 단백질 [숫자]g / 탄수화물 [숫자]g / 지방 [숫자]g

[식단 B]
이름: [식단 이름]
설명: [간단한 설명]
총 칼로리: [숫자] kcal
아침: [메뉴] ([칼로리]kcal)
아침 영양소: 단백질 [숫자]g / 탄수화물 [숫자]g / 지방 [숫자]g
점심: [메뉴] ([칼로리]kcal)
점심 영양소: 단백질 [숫자]g / 탄수화물 [숫자]g / 지방 [숫자]g
저녁: [메뉴] ([칼로리]kcal)
저녁 영양소: 단백질 [숫자]g / 탄수화물 [숫자]g / 지방 [숫자]g
간식: [메뉴] ([칼로리]kcal)
간식 영양소: 단백질 [숫자]g / 탄수화물 [숫자]g / 지방 [숫자]g

[식단 C]
이름: [식단 이름]
설명: [간단한 설명]
총 칼로리: [숫자] kcal
아침: [메뉴] ([칼로리]kcal)
아침 영양소: 단백질 [숫자]g / 탄수화물 [숫자]g / 지방 [숫자]g
점심: [메뉴] ([칼로리]kcal)
점심 영양소: 단백질 [숫자]g / 탄수화물 [숫자]g / 지방 [숫자]g
저녁: [메뉴] ([칼로리]kcal)
저녁 영양소: 단백질 [숫자]g / 탄수화물 [숫자]g / 지방 [숫자]g
간식: [메뉴] ([칼로리]kcal)
간식 영양소: 단백질 [숫자]g / 탄수화물 [숫자]g / 지방 [숫자]g

**예시:**
[식단 A]
이름: 고단백 식단
설명: 근육 생성에 최적화된 고단백 식단
총 칼로리: 1500 kcal
아침: 현미밥 1공기 + 닭가슴살 구이 100g + 시금치 무침 (350kcal)
아침 영양소: 단백질 30g / 탄수화물 40g / 지방 8g
점심: 연어 덮밥 1인분 + 계란국 (500kcal)
점심 영양소: 단백질 40g / 탄수화물 50g / 지방 15g
저녁: 고등어 구이 1마리 + 두부조림 + 배추김치 (450kcal)
저녁 영양소: 단백질 35g / 탄수화물 35g / 지방 18g
간식: 그릭요거트 1컵 + 아몬드 10알 (200kcal)
간식 영양소: 단백질 15g / 탄수화물 25g / 지방 4g
"""
        
        # 6. GPT API 호출
        print(f"🤖 GPT에게 식단 추천 요청 중...")
        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "당신은 전문 영양사입니다. 사용자의 건강 목표에 맞는 식단을 추천합니다."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0.7
        )
        
        gpt_response = response.choices[0].message.content
        print(f"✅ GPT 응답 수신 완료")
        
        # 7. GPT 응답 파싱
        diet_plans = self._parse_diet_plans(gpt_response)
        
        return {
            "bmr": bmr,
            "tdee": tdee,
            "target_calories": target_calories,
            "health_goal": user.health_goal,
            "health_goal_kr": health_goal_kr,
            "diet_plans": diet_plans,
            "gpt_response": gpt_response
        }
    
    def _parse_diet_plans(self, gpt_response: str) -> list[dict]:
        """
        GPT 응답에서 식단 정보 추출
        
        Args:
            gpt_response: GPT의 원문 응답
        
        Returns:
            list[dict]: 파싱된 식단 목록 (최대 3개)
        """
        plans = []
        
        # [식단 A], [식단 B], [식단 C]로 분리
        sections = []
        current_section = ""
        
        for line in gpt_response.split('\n'):
            if line.startswith('[식단'):
                if current_section:
                    sections.append(current_section)
                current_section = line + '\n'
            else:
                current_section += line + '\n'
        
        if current_section:
            sections.append(current_section)
        
        # 각 섹션 파싱
        for section in sections:
            plan = self._parse_single_plan(section)
            if plan:
                plans.append(plan)
        
        return plans
    
    def _parse_single_plan(self, section: str) -> Optional[dict]:
        """
        단일 식단 섹션 파싱
        
        Args:
            section: [식단 A] ~ [식단 C] 중 하나의 섹션
        
        Returns:
            dict or None: 파싱된 식단 정보
        """
        import re
        
        lines = section.split('\n')
        plan = {}
        meals = {}
        meal_details = {}  # 끼니별 상세 정보 (칼로리, 영양소)
        
        current_meal_type = None  # 현재 파싱 중인 끼니 타입
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('[식단'):
                continue
            
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                
                if key == "이름":
                    plan["name"] = value
                elif key == "설명":
                    plan["description"] = value
                elif key == "총 칼로리":
                    plan["totalCalories"] = value
                elif key == "아침":
                    current_meal_type = "breakfast"
                    # 메뉴 텍스트에서 칼로리 추출 시도 (예: "메뉴 (350kcal)")
                    menu_text, calories = self._extract_menu_and_calories(value)
                    meals["breakfast"] = menu_text
                    if "breakfast" not in meal_details:
                        meal_details["breakfast"] = {}
                    meal_details["breakfast"]["calories"] = calories
                elif key == "아침 영양소":
                    if "breakfast" not in meal_details:
                        meal_details["breakfast"] = {}
                    protein, carb, fat = self._extract_nutrients(value)
                    meal_details["breakfast"]["protein"] = protein
                    meal_details["breakfast"]["carb"] = carb
                    meal_details["breakfast"]["fat"] = fat
                elif key == "점심":
                    current_meal_type = "lunch"
                    menu_text, calories = self._extract_menu_and_calories(value)
                    meals["lunch"] = menu_text
                    if "lunch" not in meal_details:
                        meal_details["lunch"] = {}
                    meal_details["lunch"]["calories"] = calories
                elif key == "점심 영양소":
                    if "lunch" not in meal_details:
                        meal_details["lunch"] = {}
                    protein, carb, fat = self._extract_nutrients(value)
                    meal_details["lunch"]["protein"] = protein
                    meal_details["lunch"]["carb"] = carb
                    meal_details["lunch"]["fat"] = fat
                elif key == "저녁":
                    current_meal_type = "dinner"
                    menu_text, calories = self._extract_menu_and_calories(value)
                    meals["dinner"] = menu_text
                    if "dinner" not in meal_details:
                        meal_details["dinner"] = {}
                    meal_details["dinner"]["calories"] = calories
                elif key == "저녁 영양소":
                    if "dinner" not in meal_details:
                        meal_details["dinner"] = {}
                    protein, carb, fat = self._extract_nutrients(value)
                    meal_details["dinner"]["protein"] = protein
                    meal_details["dinner"]["carb"] = carb
                    meal_details["dinner"]["fat"] = fat
                elif key == "간식":
                    current_meal_type = "snack"
                    menu_text, calories = self._extract_menu_and_calories(value)
                    meals["snack"] = menu_text
                    if "snack" not in meal_details:
                        meal_details["snack"] = {}
                    meal_details["snack"]["calories"] = calories
                elif key == "간식 영양소":
                    if "snack" not in meal_details:
                        meal_details["snack"] = {}
                    protein, carb, fat = self._extract_nutrients(value)
                    meal_details["snack"]["protein"] = protein
                    meal_details["snack"]["carb"] = carb
                    meal_details["snack"]["fat"] = fat
        
        if plan.get("name") and meals:
            plan["meals"] = meals
            # meal_details를 dict 형식으로 변환 (Pydantic이 자동으로 AllMealDetails로 변환)
            if meal_details:
                plan["meal_details"] = meal_details
            return plan
        
        return None
    
    def _extract_menu_and_calories(self, text: str) -> tuple[str, float]:
        """
        메뉴 텍스트에서 메뉴명과 칼로리를 추출
        
        Args:
            text: "메뉴 설명 (350kcal)" 형식
        
        Returns:
            (메뉴명, 칼로리)
        """
        import re
        
        # 칼로리 패턴 찾기: (숫자kcal) 또는 (숫자 kcal)
        calorie_pattern = r'\((\d+(?:\.\d+)?)\s*kcal\)'
        match = re.search(calorie_pattern, text, re.IGNORECASE)
        
        if match:
            calories = float(match.group(1))
            # 칼로리 부분 제거하고 메뉴명만 추출
            menu_text = re.sub(calorie_pattern, '', text, flags=re.IGNORECASE).strip()
            return menu_text, calories
        else:
            # 칼로리 정보가 없으면 0으로 반환
            return text, 0.0
    
    def _extract_nutrients(self, text: str) -> tuple[float, float, float]:
        """
        영양소 텍스트에서 단백질/탄수화물/지방 추출
        
        Args:
            text: "단백질 30g / 탄수화물 40g / 지방 8g" 형식
        
        Returns:
            (단백질, 탄수화물, 지방)
        """
        import re
        
        protein = 0.0
        carb = 0.0
        fat = 0.0
        
        # 단백질 추출
        protein_match = re.search(r'단백질\s*(\d+(?:\.\d+)?)\s*g', text, re.IGNORECASE)
        if protein_match:
            protein = float(protein_match.group(1))
        
        # 탄수화물 추출
        carb_match = re.search(r'탄수화물\s*(\d+(?:\.\d+)?)\s*g', text, re.IGNORECASE)
        if carb_match:
            carb = float(carb_match.group(1))
        
        # 지방 추출
        fat_match = re.search(r'지방\s*(\d+(?:\.\d+)?)\s*g', text, re.IGNORECASE)
        if fat_match:
            fat = float(fat_match.group(1))
        
        return protein, carb, fat


# 싱글톤 인스턴스
_diet_recommendation_service: Optional[DietRecommendationService] = None


def get_diet_recommendation_service() -> DietRecommendationService:
    """DietRecommendationService 싱글톤 인스턴스 반환"""
    global _diet_recommendation_service
    if _diet_recommendation_service is None:
        _diet_recommendation_service = DietRecommendationService()
    return _diet_recommendation_service

