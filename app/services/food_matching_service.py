"""음식 매칭 서비스 - GPT 추천 음식을 food_nutrients DB와 매칭"""
from typing import Optional, List, Dict, Union
from sqlalchemy import select, or_, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage

from app.db.models_food_nutrients import FoodNutrient
from app.db.models_user_contributed import UserContributedFood
from app.core.config import get_settings

settings = get_settings()


class FoodMatchingService:
    """GPT 추천 음식을 DB의 실제 음식과 매칭하는 서비스"""
    
    # 핵심 키워드 목록 (음식 카테고리)
    FOOD_KEYWORDS = [
        "샐러드", "볶음", "구이", "찜", "조림", "튀김",
        "국", "탕", "찌개", "전골",
        "김밥", "밥", "덮밥", "비빔밥", "볶음밥",
        "면", "국수", "파스타", "라면",
        "빵", "케이크", "쿠키",
        "스테이크", "커틀릿", "돈까스",
        "수프", "스튜", "카레"
    ]
    
    # 재료 → 카테고리 매핑
    INGREDIENT_CATEGORY_MAP = {
        # 채소류
        "당근": "채소", "양파": "채소", "양상추": "채소", "토마토": "채소",
        "오이": "채소", "배추": "채소", "양배추": "채소", "브로콜리": "채소",
        "시금치": "채소", "상추": "채소", "깻잎": "채소", "파": "채소",
        "마늘": "채소", "생강": "채소", "고추": "채소", "피망": "채소",
        "새싹": "채소", "콩나물": "채소", "숙주": "채소",
        
        # 육류
        "닭가슴살": "닭가슴살", "닭고기": "닭고기", "닭": "닭고기",
        "돼지고기": "돼지고기", "삼겹살": "돼지고기", "목살": "돼지고기",
        "소고기": "소고기", "쇠고기": "소고기", "등심": "소고기",
        
        # 해산물
        "참치": "참치", "연어": "연어", "새우": "새우",
        "오징어": "오징어", "낙지": "낙지", "문어": "문어",
        
        # 기타
        "계란": "계란", "달걀": "계란", "에그": "계란",
        "치즈": "치즈", "베이컨": "베이컨", "햄": "햄",
        "감자": "감자", "고구마": "고구마", "옥수수": "옥수수",
        "버섯": "버섯", "두부": "두부"
    }
    
    def __init__(self):
        if settings.openai_api_key:
            self.llm = ChatOpenAI(
                api_key=settings.openai_api_key,
                model="gpt-4o-mini",
                temperature=0.2,
            )
        else:
            self.llm = None
    
    async def match_food_to_db(
        self,
        session: AsyncSession,
        food_name: str,
        ingredients: List[str] = None,
        food_class_hint: str = None,
        user_id: int = None
    ) -> Optional[Union[FoodNutrient, UserContributedFood]]:
        """
        음식명과 재료를 기반으로 food_nutrients 또는 user_contributed_foods에서 가장 적합한 음식 찾기
        
        매칭 우선순위:
        1. 정확한 이름 매칭 (nutrient_name == food_name)
        2. 사용자 기여 음식 검색 (user_contributed_foods) - NEW
        3. 재료 기반 매칭 (food_class1, food_class2 활용)
        4. GPT 기반 유사도 매칭 (토큰 절약)
        
        Args:
            session: DB 세션
            food_name: 음식 이름 (예: "닭가슴살 샐러드", "연어 덮밥")
            ingredients: 재료 리스트 (예: ["닭가슴살", "양상추", "토마토"])
            food_class_hint: 음식 분류 힌트 (예: "샐러드", "밥류")
            user_id: 사용자 ID (사용자 기여 음식 우선 검색용)
        
        Returns:
            매칭된 FoodNutrient 또는 UserContributedFood 또는 None
        """
        ingredients = ingredients or []
        
        print(f"\n🔍 음식 매칭 시작: '{food_name}' (재료: {ingredients})")
        
        # ========== STEP 1: 정확한 이름 매칭 (공식 DB) ==========
        exact_match = await self._exact_name_match(session, food_name)
        if exact_match:
            print(f"✅ [STEP 1] 정확한 이름 매칭 성공: {exact_match.food_id} - {exact_match.nutrient_name}")
            return exact_match
        
        # ========== STEP 2: 사용자 기여 음식 검색 (NEW) ==========
        if user_id:
            contributed_match = await self._search_user_contributed_foods(
                session, food_name, ingredients, user_id
            )
            if contributed_match:
                print(f"✅ [STEP 2] 사용자 기여 음식 매칭 성공: {contributed_match.food_id} - {contributed_match.food_name}")
                # 사용 횟수 증가
                contributed_match.usage_count += 1
                await session.commit()
                return contributed_match
        
        # ========== STEP 3: 재료 기반 매칭 (공식 DB) ==========
        ingredient_match = await self._ingredient_based_match(
            session, food_name, ingredients, food_class_hint
        )
        if ingredient_match:
            print(f"✅ [STEP 3] 재료 기반 매칭 성공: {ingredient_match.food_id} - {ingredient_match.nutrient_name}")
            return ingredient_match
        
        # ========== STEP 4: GPT 기반 유사 음식 찾기 (최후의 수단) ==========
        if self.client:
            gpt_match = await self._gpt_similarity_match(session, food_name, ingredients)
            if gpt_match:
                print(f"✅ [STEP 4] GPT 유사도 매칭 성공: {gpt_match.food_id} - {gpt_match.nutrient_name}")
                return gpt_match
        
        print(f"❌ 매칭 실패: '{food_name}'에 대한 적합한 음식을 찾을 수 없음")
        return None
    
    async def _exact_name_match(
        self,
        session: AsyncSession,
        food_name: str
    ) -> Optional[FoodNutrient]:
        """정확한 이름 매칭"""
        stmt = select(FoodNutrient).where(
            or_(
                FoodNutrient.nutrient_name == food_name,
                FoodNutrient.representative_food_name == food_name
            )
        ).limit(1)
        
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def _ingredient_based_match(
        self,
        session: AsyncSession,
        food_name: str,
        ingredients: List[str],
        food_class_hint: str = None
    ) -> Optional[FoodNutrient]:
        """
        재료 기반 매칭 (DB 구조에 최적화)
        
        DB 구조:
        - nutrient_name: "국밥_덮치마리", "김밥_낙지칼" (언더스코어 구분)
        - food_class1: "곡밥류", "볶음밥류" (한글 + "류")
        - food_class2: "덮치마리", "낙지칼" (구체적 재료/음식명)
        
        매칭 점수 시스템:
        - nutrient_name 정확 일치: +100점
        - nutrient_name 언더스코어 패턴 일치: +80점
        - food_class1 정확 일치 (류 제거): +60점
        - food_class2 정확 일치: +50점
        - 부분 매칭: +20~40점
        - 재료 매칭: +15점
        """
        # 1. 음식명 전처리 및 키워드 추출
        food_name_clean = self._clean_food_name(food_name)
        food_keywords = self._extract_food_keywords(food_name)
        ingredient_categories = self._map_ingredients_to_categories(ingredients)
        
        print(f"  → 추출된 키워드: {food_keywords}")
        print(f"  → 재료 카테고리: {ingredient_categories}")
        
        # 2. 후보 검색 (우선순위 전략)
        candidates = []
        
        # 2-1. 핵심 키워드로 우선 검색
        if food_keywords:
            for keyword in food_keywords:
                keyword_candidates = await self._search_candidates(
                    session, keyword, food_class_hint, limit=30
                )
                candidates.extend(keyword_candidates)
                if candidates:
                    print(f"  → 키워드 '{keyword}'로 {len(keyword_candidates)}개 후보 발견")
        
        # 2-2. 키워드 검색 실패 시 전체 음식명으로 검색
        if not candidates:
            candidates = await self._search_candidates(
                session, food_name_clean, food_class_hint, limit=30
            )
        
        # 2-3. 여전히 실패 시 재료 카테고리로 검색
        if not candidates and ingredient_categories:
            for category in ingredient_categories:
                category_candidates = await self._search_candidates(
                    session, category, food_class_hint, limit=20
                )
                candidates.extend(category_candidates)
                if category_candidates:
                    print(f"  → 카테고리 '{category}'로 {len(category_candidates)}개 후보 발견")
        
        # 2-4. 마지막으로 주재료로 검색
        if not candidates and ingredients:
            main_ingredient = ingredients[0]
            candidates = await self._search_candidates(
                session, main_ingredient, food_class_hint, limit=20
            )
        
        # 중복 제거
        seen_ids = set()
        unique_candidates = []
        for food in candidates:
            if food.food_id not in seen_ids:
                seen_ids.add(food.food_id)
                unique_candidates.append(food)
        
        candidates = unique_candidates
        
        if not candidates:
            return None
        
        print(f"  → {len(candidates)}개 후보 발견, 점수 계산 중...")
        
        # 3. 점수 계산
        best_match = None
        best_score = 0
        
        for food in candidates:
            score = self._calculate_match_score(
                food=food,
                food_name=food_name_clean,
                ingredients=ingredients,
                food_class_hint=food_class_hint,
                food_keywords=food_keywords,
                ingredient_categories=ingredient_categories
            )
            
            if score > best_score:
                best_score = score
                best_match = food
        
        # 최소 점수 기준 (너무 낮으면 매칭 안함)
        if best_score >= 20:
            print(f"  ✅ 최고 점수: {best_score}점 ({best_match.nutrient_name})")
            return best_match
        
        print(f"  ⚠️ 최고 점수 {best_score}점으로 기준 미달 (최소 20점 필요)")
        return None
    
    def _clean_food_name(self, food_name: str) -> str:
        """음식명 전처리 (공백 제거, 소문자 변환 등)"""
        return food_name.strip().replace(" ", "")
    
    def _extract_food_keywords(self, food_name: str) -> List[str]:
        """
        음식명에서 핵심 키워드 추출
        
        Args:
            food_name: 음식 이름 (예: "기본 그린 샐러드", "매콤한 닭가슴살 볶음")
        
        Returns:
            추출된 키워드 리스트 (예: ["샐러드"], ["닭가슴살", "볶음"])
        """
        keywords = []
        food_name_clean = food_name.replace(" ", "")
        
        # FOOD_KEYWORDS에서 매칭되는 키워드 찾기
        for keyword in self.FOOD_KEYWORDS:
            if keyword in food_name_clean:
                keywords.append(keyword)
        
        return keywords
    
    def _map_ingredients_to_categories(self, ingredients: List[str]) -> List[str]:
        """
        재료를 카테고리로 변환
        
        Args:
            ingredients: 재료 리스트 (예: ["당근", "양파", "올리브오일"])
        
        Returns:
            카테고리 리스트 (예: ["채소", "채소"])
        """
        categories = []
        seen = set()
        
        for ingredient in ingredients:
            ingredient_clean = ingredient.replace(" ", "")
            
            # 매핑에서 카테고리 찾기
            category = self.INGREDIENT_CATEGORY_MAP.get(ingredient_clean)
            
            if category and category not in seen:
                categories.append(category)
                seen.add(category)
        
        return categories
    
    def _calculate_match_score(
        self,
        food: FoodNutrient,
        food_name: str,
        ingredients: List[str],
        food_class_hint: str = None,
        food_keywords: List[str] = None,
        ingredient_categories: List[str] = None
    ) -> int:
        """
        음식 매칭 점수 계산
        
        점수 체계:
        - 정확한 일치: 80~100점
        - 패턴 일치: 50~80점
        - 부분 일치: 20~50점
        - 핵심 키워드 매칭: +30점 (NEW)
        - 재료 카테고리 매칭: +25점 (NEW)
        - 재료 일치: 15점씩 추가
        """
        score = 0
        food_keywords = food_keywords or []
        ingredient_categories = ingredient_categories or []
        
        # ========== nutrient_name 매칭 (가장 중요) ==========
        if food.nutrient_name:
            nutrient_name_clean = food.nutrient_name.replace(" ", "")
            
            # 정확히 일치
            if nutrient_name_clean == food_name:
                score += 100
                print(f"    [{food.food_id}] nutrient_name 정확 일치 (+100): {food.nutrient_name}")
            
            # 언더스코어 패턴 매칭 (예: "국밥_덮치마리" vs "국밥" 또는 "덮치마리")
            elif "_" in nutrient_name_clean:
                parts = nutrient_name_clean.split("_")
                # 앞부분 일치 (예: "국밥_덮치마리"에서 "국밥")
                if parts[0] == food_name:
                    score += 80
                    print(f"    [{food.food_id}] nutrient_name 앞부분 일치 (+80): {food.nutrient_name}")
                # 뒷부분 일치 (예: "국밥_덮치마리"에서 "덮치마리")
                elif len(parts) > 1 and parts[1] == food_name:
                    score += 70
                    print(f"    [{food.food_id}] nutrient_name 뒷부분 일치 (+70): {food.nutrient_name}")
                # 부분 포함
                elif food_name in nutrient_name_clean:
                    score += 40
                    print(f"    [{food.food_id}] nutrient_name 부분 포함 (+40): {food.nutrient_name}")
            
            # 일반 부분 매칭
            elif food_name in nutrient_name_clean:
                score += 40
                print(f"    [{food.food_id}] nutrient_name 부분 포함 (+40): {food.nutrient_name}")
            elif nutrient_name_clean in food_name:
                score += 30
                print(f"    [{food.food_id}] nutrient_name이 검색어에 포함 (+30): {food.nutrient_name}")
        
        # ========== food_class1 매칭 (대분류) ==========
        if food.food_class1:
            food_class1_clean = food.food_class1.replace(" ", "")
            
            # "류" 제거하고 비교 (예: "곡밥류" → "곡밥")
            food_class1_base = food_class1_clean.rstrip("류")
            food_name_base = food_name.rstrip("류")
            
            # 정확히 일치
            if food_class1_base == food_name_base:
                score += 60
                print(f"    [{food.food_id}] food_class1 일치 (+60): {food.food_class1}")
            # 힌트와 일치
            elif food_class_hint and food_class1_base == food_class_hint.rstrip("류"):
                score += 50
                print(f"    [{food.food_id}] food_class1 힌트 일치 (+50): {food.food_class1}")
            # 부분 포함
            elif food_name in food_class1_clean or food_class1_base in food_name:
                score += 30
                print(f"    [{food.food_id}] food_class1 부분 포함 (+30): {food.food_class1}")
        
        # ========== food_class2 매칭 (중분류/재료) ==========
        # 주의: food_class2가 "도넛", "해당없음", "없음" 또는 비어있을 수 있음
        if food.food_class2:
            food_class2_clean = food.food_class2.replace(" ", "")
            
            # 일반적인 값 또는 비어있는 값은 무시
            generic_values = ["도넛", "해당없음", "기타", "일반", "없음", ""]
            is_generic = any(gv == food_class2_clean or gv in food_class2_clean for gv in generic_values)
            
            if not is_generic and food_class2_clean:
                # 정확히 일치
                if food_class2_clean == food_name:
                    score += 50
                    print(f"    [{food.food_id}] food_class2 일치 (+50): {food.food_class2}")
                # 부분 포함
                elif food_name in food_class2_clean:
                    score += 35
                    print(f"    [{food.food_id}] food_class2 부분 포함 (+35): {food.food_class2}")
            else:
                # food_class2가 일반값/비어있으면 nutrient_name의 뒷부분 활용
                if food.nutrient_name and "_" in food.nutrient_name:
                    parts = food.nutrient_name.split("_")
                    if len(parts) > 1:
                        detail_part = parts[1].replace(" ", "")
                        if food_name in detail_part:
                            score += 40
                            print(f"    [{food.food_id}] nutrient_name 뒷부분('{parts[1]}')에 검색어 포함 (+40)")
        
        # ========== representative_food_name 매칭 ==========
        if food.representative_food_name:
            rep_name_clean = food.representative_food_name.replace(" ", "")
            
            if rep_name_clean == food_name:
                score += 90
                print(f"    [{food.food_id}] representative_food_name 일치 (+90): {food.representative_food_name}")
            elif food_name in rep_name_clean:
                score += 45
                print(f"    [{food.food_id}] representative_food_name 부분 포함 (+45): {food.representative_food_name}")
        
        # ========== 재료 매칭 ==========
        for ingredient in ingredients:
            ingredient_clean = ingredient.replace(" ", "")
            matched = False
            
            # food_class2에 재료 포함 (일반값이 아닐 때만)
            if food.food_class2:
                food_class2_clean = food.food_class2.replace(" ", "")
                generic_values = ["도넛", "해당없음", "기타", "일반", "없음"]
                is_generic = any(gv in food_class2_clean for gv in generic_values)
                
                if not is_generic and ingredient_clean in food_class2_clean:
                    score += 15
                    print(f"    [{food.food_id}] food_class2에 재료 '{ingredient}' 포함 (+15)")
                    matched = True
            
            # nutrient_name에 재료 포함 (우선순위 높음)
            if not matched and food.nutrient_name:
                nutrient_name_clean = food.nutrient_name.replace(" ", "")
                if ingredient_clean in nutrient_name_clean:
                    # 언더스코어 뒷부분에 있으면 더 높은 점수
                    if "_" in nutrient_name_clean:
                        parts = nutrient_name_clean.split("_")
                        if len(parts) > 1 and ingredient_clean in parts[1]:
                            score += 18
                            print(f"    [{food.food_id}] nutrient_name 뒷부분에 재료 '{ingredient}' 포함 (+18)")
                            matched = True
                    
                    if not matched:
                        score += 12
                        print(f"    [{food.food_id}] nutrient_name에 재료 '{ingredient}' 포함 (+12)")
                        matched = True
            
            # representative_food_name에 재료 포함
            if not matched and food.representative_food_name:
                rep_name_clean = food.representative_food_name.replace(" ", "")
                if ingredient_clean in rep_name_clean:
                    score += 10
                    print(f"    [{food.food_id}] representative_food_name에 재료 '{ingredient}' 포함 (+10)")
                    matched = True
        
        # ========== 핵심 키워드 보너스 (NEW) ==========
        if food_keywords and food.nutrient_name:
            nutrient_name_clean = food.nutrient_name.replace(" ", "")
            for keyword in food_keywords:
                if keyword in nutrient_name_clean:
                    score += 30
                    print(f"    [{food.food_id}] 핵심 키워드 '{keyword}' 매칭 (+30)")
                    break  # 중복 방지
        
        # ========== 재료 카테고리 보너스 (NEW) ==========
        if ingredient_categories and food.food_class2:
            food_class2_clean = food.food_class2.replace(" ", "")
            for category in ingredient_categories:
                if category == food_class2_clean:
                    score += 25
                    print(f"    [{food.food_id}] 재료 카테고리 '{category}' 일치 (+25)")
                    break  # 중복 방지
                elif category in food_class2_clean:
                    score += 15
                    print(f"    [{food.food_id}] 재료 카테고리 '{category}' 포함 (+15)")
                    break  # 중복 방지
        
        return score
    
    async def _search_candidates(
        self,
        session: AsyncSession,
        search_term: str,
        food_class_hint: str = None,
        limit: int = 50
    ) -> List[FoodNutrient]:
        """
        후보 음식 검색 (DB 구조에 최적화)
        
        검색 전략:
        1. food_class_hint가 있으면 해당 분류 내에서 우선 검색
        2. 언더스코어 패턴 고려 (nutrient_name)
        3. "류" 제거하고 검색 (food_class1)
        """
        search_term_clean = search_term.replace(" ", "")
        
        # 검색 조건 (공백 제거 후 검색)
        conditions = [
            FoodNutrient.nutrient_name.like(f"%{search_term_clean}%"),
            FoodNutrient.food_class1.like(f"%{search_term_clean}%"),
            FoodNutrient.food_class2.like(f"%{search_term_clean}%"),
            FoodNutrient.representative_food_name.like(f"%{search_term_clean}%")
        ]
        
        # "류" 제거 버전도 검색 (예: "밥" → "곡밥류", "볶음밥류" 찾기)
        if not search_term_clean.endswith("류"):
            conditions.append(FoodNutrient.food_class1.like(f"%{search_term_clean}류%"))
        
        # food_class_hint가 있으면 우선 검색
        if food_class_hint:
            hint_clean = food_class_hint.replace(" ", "")
            
            # "류" 제거 버전도 시도
            hint_patterns = [hint_clean]
            if not hint_clean.endswith("류"):
                hint_patterns.append(f"{hint_clean}류")
            
            for pattern in hint_patterns:
                stmt = select(FoodNutrient).where(
                    FoodNutrient.food_class1.like(f"%{pattern}%"),
                    or_(*conditions)
                ).limit(limit)
                
                result = await session.execute(stmt)
                candidates = list(result.scalars().all())
                
                if candidates:
                    print(f"  → food_class_hint '{food_class_hint}'로 {len(candidates)}개 후보 검색")
                    return candidates
        
        # 일반 검색
        stmt = select(FoodNutrient).where(
            or_(*conditions)
        ).limit(limit)
        
        result = await session.execute(stmt)
        candidates = list(result.scalars().all())
        print(f"  → 일반 검색으로 {len(candidates)}개 후보 검색")
        return candidates
    
    async def _gpt_similarity_match(
        self,
        session: AsyncSession,
        food_name: str,
        ingredients: List[str]
    ) -> Optional[FoodNutrient]:
        """
        GPT를 활용한 유사 음식 찾기 (최후의 수단)
        
        토큰 절약 전략:
        1. DB에서 관련 음식 목록만 가져오기 (food_id, nutrient_name)
        2. GPT에게 "이 중 가장 유사한 음식의 food_id를 선택하세요" 요청
        3. 선택된 food_id로 DB 조회
        
        DB 구조 고려:
        - nutrient_name: "국밥_덮치마리" 형식
        - food_class1: "곡밥류" 형식
        """
        if not self.llm:
            return None
        
        try:
            print(f"  🤖 GPT 유사도 매칭 시작...")
            
            # 1. 주재료 추출 (공백 제거)
            food_name_clean = food_name.replace(" ", "")
            main_ingredient = ingredients[0].replace(" ", "") if ingredients else food_name_clean[:2]
            
            # 2. 관련 음식 목록 조회 (더 넓은 범위)
            search_terms = [food_name_clean, main_ingredient]
            if ingredients and len(ingredients) > 1:
                search_terms.append(ingredients[1].replace(" ", ""))
            
            # 여러 검색어로 후보 수집
            all_candidates = []
            seen_ids = set()
            
            for term in search_terms[:2]:  # 최대 2개 검색어
                stmt = select(
                    FoodNutrient.food_id,
                    FoodNutrient.nutrient_name,
                    FoodNutrient.food_class1,
                    FoodNutrient.food_class2
                ).where(
                    or_(
                        FoodNutrient.nutrient_name.like(f"%{term}%"),
                        FoodNutrient.food_class1.like(f"%{term}%"),
                        FoodNutrient.food_class2.like(f"%{term}%")
                    )
                ).limit(15)
                
                result = await session.execute(stmt)
                candidates = result.fetchall()
                
                for row in candidates:
                    if row[0] not in seen_ids:
                        all_candidates.append(row)
                        seen_ids.add(row[0])
            
            if not all_candidates:
                print(f"  ❌ GPT 매칭용 후보 없음")
                return None
            
            # 최대 20개로 제한
            all_candidates = all_candidates[:20]
            print(f"  → GPT에게 {len(all_candidates)}개 후보 제공")
            
            # 3. GPT에게 유사도 판단 요청 (한글 설명 추가)
            candidate_list = "\n".join([
                f"- {row[0]}: {row[1]} (대분류: {row[2]}, 중분류: {row[3]})"
                for row in all_candidates
            ])
            
            prompt = f"""다음 음식 목록에서 "{food_name}"와 가장 유사한 음식의 food_id를 선택하세요.

검색 정보:
- 음식명: {food_name}
- 재료: {', '.join(ingredients) if ingredients else '없음'}

음식 목록:
{candidate_list}

**중요:** food_id만 정확히 답변하세요. (예: D101-00431000D-0001)
설명 없이 food_id만 출력하세요."""
            
            response = await self.llm.ainvoke([
                SystemMessage(content="당신은 한국 음식 분류 전문가입니다. food_id만 정확히 답변하세요."),
                HumanMessage(content=prompt)
            ])
            
            selected_food_id = response.content.strip()
            print(f"  → GPT 선택: {selected_food_id}")
            
            # 4. 선택된 food_id로 조회
            stmt = select(FoodNutrient).where(FoodNutrient.food_id == selected_food_id)
            result = await session.execute(stmt)
            matched = result.scalar_one_or_none()
            
            if matched:
                print(f"  ✅ GPT 매칭 성공: {matched.nutrient_name}")
            else:
                print(f"  ⚠️ GPT가 선택한 food_id를 DB에서 찾을 수 없음")
            
            return matched
            
        except Exception as e:
            print(f"  ❌ GPT 매칭 오류: {e}")
            return None
    
    async def get_food_categories_for_gpt(
        self,
        session: AsyncSession,
        user_preferences: List[str] = None
    ) -> Dict[str, List[Dict[str, str]]]:
        """
        GPT에게 제공할 음식 카테고리 목록 생성 (DB 구조 최적화)
        
        레시피/식단 추천 시 GPT에게 DB의 실제 음식 목록을 제공하여
        직접 food_id를 선택하게 함 (가장 정확한 방법)
        
        DB 구조:
        - food_class1: "곡밥류", "볶음밥류" (한글 + "류")
        
        Args:
            session: DB 세션
            user_preferences: 사용자 선호 카테고리 (예: ["고기", "채소"])
        
        Returns:
            {
                "곡밥류": [{"food_id": "D101-...", "name": "국밥_덮치마리"}, ...],
                "볶음밥류": [{"food_id": "D101-...", "name": "볶음밥_낙지"}, ...],
                ...
            }
        """
        user_preferences = user_preferences or []
        
        # 주요 카테고리 목록 (DB 실제 구조에 맞게)
        main_categories = [
            "곡밥류", "볶음밥류", "김밥류", "면류", "빵류",
            "육류", "닭고기류", "돼지고기류", "소고기류",
            "어패류", "생선류", "해산물류",
            "채소류", "과일류", "유제품류", "두류",
            "국탕류", "찌개류", "조림류", "구이류"
        ]
        
        # 사용자 선호 카테고리 전처리 ("류" 추가)
        processed_preferences = []
        for pref in user_preferences:
            pref_clean = pref.strip()
            if not pref_clean.endswith("류"):
                processed_preferences.append(f"{pref_clean}류")
            else:
                processed_preferences.append(pref_clean)
        
        # 사용자 선호 카테고리 우선
        categories_to_fetch = processed_preferences + main_categories
        categories_to_fetch = list(dict.fromkeys(categories_to_fetch))[:10]  # 중복 제거, 최대 10개
        
        result_dict = {}
        
        for category in categories_to_fetch:
            # "류" 제거 버전도 시도
            search_patterns = [category]
            if category.endswith("류"):
                search_patterns.append(category[:-1])
            
            for pattern in search_patterns:
                stmt = select(
                    FoodNutrient.food_id,
                    FoodNutrient.nutrient_name,
                    FoodNutrient.food_class1,
                    FoodNutrient.representative_food_name
                ).where(
                    FoodNutrient.food_class1.like(f"%{pattern}%")
                ).limit(15)  # 카테고리당 15개
                
                result = await session.execute(stmt)
                foods = result.fetchall()
                
                if foods:
                    # 실제 DB의 food_class1 사용 (정확한 카테고리명)
                    actual_category = foods[0][2] if foods[0][2] else category
                    
                    result_dict[actual_category] = [
                        {
                            "food_id": row[0],
                            "name": row[1] or row[3] or "이름 없음"
                        }
                        for row in foods
                    ]
                    break  # 찾았으면 다음 카테고리로
        
        return result_dict
    
    async def _search_user_contributed_foods(
        self,
        session: AsyncSession,
        food_name: str,
        ingredients: List[str],
        user_id: int
    ) -> Optional[UserContributedFood]:
        """
        사용자 기여 음식 테이블에서 검색
        
        우선순위:
        1. 해당 사용자가 추가한 음식 우선
        2. 다른 사용자가 추가한 인기 음식 (usage_count >= 3)
        
        Args:
            session: DB 세션
            food_name: 음식 이름
            ingredients: 재료 리스트
            user_id: 사용자 ID
        
        Returns:
            매칭된 UserContributedFood 또는 None
        """
        food_name_clean = self._clean_food_name(food_name)
        
        # 1. 해당 사용자가 추가한 음식 우선 검색
        stmt = select(UserContributedFood).where(
            UserContributedFood.user_id == user_id,
            or_(
                UserContributedFood.food_name.like(f"%{food_name_clean}%"),
                UserContributedFood.nutrient_name.like(f"%{food_name_clean}%")
            )
        ).order_by(UserContributedFood.usage_count.desc()).limit(1)
        
        result = await session.execute(stmt)
        user_food = result.scalar_one_or_none()
        
        if user_food:
            print(f"  → 사용자 기여 음식 발견 (본인): {user_food.food_name} (사용 {user_food.usage_count}회)")
            return user_food
        
        # 2. 다른 사용자의 인기 음식 검색 (usage_count >= 3)
        stmt = select(UserContributedFood).where(
            UserContributedFood.usage_count >= 3,
            or_(
                UserContributedFood.food_name.like(f"%{food_name_clean}%"),
                UserContributedFood.nutrient_name.like(f"%{food_name_clean}%")
            )
        ).order_by(UserContributedFood.usage_count.desc()).limit(1)
        
        result = await session.execute(stmt)
        popular_food = result.scalar_one_or_none()
        
        if popular_food:
            print(f"  → 사용자 기여 음식 발견 (인기): {popular_food.food_name} (사용 {popular_food.usage_count}회)")
            return popular_food
        
        return None


# 싱글톤 인스턴스
_food_matching_service: Optional[FoodMatchingService] = None


def get_food_matching_service() -> FoodMatchingService:
    """FoodMatchingService 싱글톤 인스턴스 반환"""
    global _food_matching_service
    if _food_matching_service is None:
        _food_matching_service = FoodMatchingService()
    return _food_matching_service
