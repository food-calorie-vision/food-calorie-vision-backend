"""food_nutrients 테이블 조회 서비스

테이블 구조:
- nutrient_name: 음식 전체 이름 (예: "국밥_돼지머리", "피자_페퍼로니")
- food_class1: 대분류 (예: "국밥", "피자")
- food_class2: 중분류/재료 (예: "돼지머리", "페퍼로니")
"""
from typing import List, Optional

from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models_food_nutrients import FoodNutrient


async def search_food_by_name(
    session: AsyncSession,
    food_name: str,
    limit: int = 10
) -> List[FoodNutrient]:
    """
    음식 이름으로 food_nutrients 검색
    
    Args:
        session: DB 세션
        food_name: 검색할 음식 이름 (예: "사과", "피자", "국밥")
        limit: 최대 결과 개수
        
    Returns:
        매칭되는 FoodNutrient 리스트 (정확도 순)
    """
    # 1. 정확한 매칭 우선 (food_class1 == food_name)
    exact_stmt = select(FoodNutrient).where(
        FoodNutrient.food_class1 == food_name
    ).limit(limit)
    
    exact_result = await session.execute(exact_stmt)
    exact_matches = list(exact_result.scalars().all())
    
    if exact_matches:
        return exact_matches
    
    # 2. 부분 매칭 (nutrient_name, food_class1, food_class2에서)
    partial_stmt = select(FoodNutrient).where(
        or_(
            FoodNutrient.nutrient_name.like(f"%{food_name}%"),
            FoodNutrient.food_class1.like(f"%{food_name}%"),
            FoodNutrient.food_class2.like(f"%{food_name}%")
        )
    ).limit(limit)
    
    partial_result = await session.execute(partial_stmt)
    return list(partial_result.scalars().all())


async def get_food_by_id(
    session: AsyncSession,
    food_id: str
) -> Optional[FoodNutrient]:
    """
    food_id로 영양소 정보 조회
    
    Args:
        session: DB 세션
        food_id: 음식 ID
        
    Returns:
        FoodNutrient 또는 None
    """
    stmt = select(FoodNutrient).where(FoodNutrient.food_id == food_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def search_ingredients(
    session: AsyncSession,
    ingredient_names: List[str],
    limit_per_ingredient: int = 3
) -> dict[str, List[FoodNutrient]]:
    """
    여러 재료 이름으로 동시에 검색
    
    Args:
        session: DB 세션
        ingredient_names: 재료 이름 리스트 (예: ["토마토", "양파", "치즈"])
        limit_per_ingredient: 재료당 최대 결과 개수
        
    Returns:
        재료별 검색 결과 딕셔너리
        {
            "토마토": [FoodNutrient, ...],
            "양파": [FoodNutrient, ...],
            ...
        }
    """
    results = {}
    
    for ingredient in ingredient_names:
        foods = await search_food_by_name(session, ingredient, limit_per_ingredient)
        results[ingredient] = foods
    
    return results


async def get_best_match_for_food(
    session: AsyncSession,
    food_name: str,
    ingredients: List[str]
) -> Optional[FoodNutrient]:
    """
    음식명과 재료를 기반으로 가장 적합한 영양소 데이터 찾기
    
    테이블 구조 활용:
    - nutrient_name: "국밥_돼지머리" 형식
    - food_class1: "국밥" (대분류)
    - food_class2: "돼지머리" (중분류/재료)
    
    Args:
        session: DB 세션
        food_name: 음식 이름 (예: "피자", "국밥", "김치찌개")
        ingredients: 재료 리스트 (예: ["토마토소스", "치즈", "페퍼로니"])
        
    Returns:
        가장 적합한 FoodNutrient 또는 None
    """
    print(f"🔍 DB 검색: 음식명='{food_name}', 재료={ingredients}")
    
    # 1. 정확한 이름 매칭 먼저 시도 (nutrient_name == food_name)
    exact_name_stmt = select(FoodNutrient).where(
        FoodNutrient.nutrient_name == food_name
    ).limit(1)
    exact_name_result = await session.execute(exact_name_stmt)
    exact_match = exact_name_result.scalar_one_or_none()
    
    if exact_match:
        print(f"✅ 정확한 이름 매칭 성공: {exact_match.nutrient_name}")
        return exact_match
    
    # 2. 음식 이름으로 검색 (food_class1 기준)
    food_results = await search_food_by_name(session, food_name, limit=20)
    
    if not food_results:
        print(f"⚠️ '{food_name}'로 검색 결과 없음, 첫 번째 재료로 재검색")
        # 음식 이름으로 못 찾으면 첫 번째 재료로 검색
        if ingredients:
            food_results = await search_food_by_name(session, ingredients[0], limit=10)
    
    if not food_results:
        print(f"❌ DB에서 매칭되는 음식을 찾을 수 없음")
        return None
    
    print(f"✅ {len(food_results)}개의 후보 발견")
    
    # 2. 재료 매칭 점수 계산
    best_match = None
    best_score = 0
    
    for food in food_results:
        score = 0
        
        # food_class1 (대분류) 정확히 일치 시 높은 점수
        if food.food_class1 and food.food_class1.lower() == food_name.lower():
            score += 50
            print(f"  - {food.nutrient_name}: food_class1 정확 일치 (+50점)")
        
        # nutrient_name이 정확히 일치 (예: "사과" == "사과")
        if food.nutrient_name and food.nutrient_name.lower() == food_name.lower():
            score += 100
            print(f"  - {food.nutrient_name}: nutrient_name 정확 일치 (+100점)")
        # nutrient_name이 "음식명_재료" 형태로 시작 (예: "사과_주스")
        elif food.nutrient_name and food.nutrient_name.lower().startswith(f"{food_name.lower()}_"):
            score += 30
            print(f"  - {food.nutrient_name}: nutrient_name이 '{food_name}_'로 시작 (+30점)")
        # nutrient_name에 음식 이름 포함 (예: "사과파이"에 "사과" 포함)
        elif food.nutrient_name and food_name.lower() in food.nutrient_name.lower():
            score += 10
            print(f"  - {food.nutrient_name}: nutrient_name 부분 포함 (+10점)")
        
        # food_class2 (중분류/재료)와 재료 매칭
        for ingredient in ingredients:
            ingredient_lower = ingredient.lower()
            
            # food_class2에 재료 포함
            if food.food_class2 and ingredient_lower in food.food_class2.lower():
                score += 15
                print(f"  - {food.nutrient_name}: food_class2에 '{ingredient}' 포함 (+15점)")
            
            # nutrient_name에 재료 포함
            elif food.nutrient_name and ingredient_lower in food.nutrient_name.lower():
                score += 5
                print(f"  - {food.nutrient_name}: nutrient_name에 '{ingredient}' 포함 (+5점)")
        
        if score > best_score:
            best_score = score
            best_match = food
    
    if best_match:
        print(f"🎯 최종 선택: {best_match.nutrient_name} (점수: {best_score}점)")
    else:
        # 점수가 0이면 첫 번째 결과 반환
        best_match = food_results[0]
        print(f"⚠️ 매칭 점수 없음, 첫 번째 결과 사용: {best_match.nutrient_name}")
    
    return best_match


async def get_fallback_by_category(
    session: AsyncSession,
    food_name: str
) -> Optional[FoodNutrient]:
    """
    대분류(food_class1) 기반 폴백 검색
    
    특정 음식(예: "피자_페퍼로니")이 없을 때, 
    대분류(예: "피자")의 가장 기본적인 음식을 반환
    
    Args:
        session: DB 세션
        food_name: 음식 대분류 이름 (예: "피자", "국밥")
        
    Returns:
        대분류의 기본 FoodNutrient 또는 None
    """
    print(f"🔄 폴백 검색: 대분류 '{food_name}'의 기본 음식 찾기")
    
    # food_class1이 정확히 일치하는 음식 중 가장 단순한 것 선택
    # (nutrient_name 길이가 짧을수록 기본 음식)
    stmt = select(FoodNutrient).where(
        FoodNutrient.food_class1 == food_name
    ).order_by(
        func.length(FoodNutrient.nutrient_name)  # 이름이 짧은 순서
    ).limit(1)
    
    result = await session.execute(stmt)
    fallback = result.scalar_one_or_none()
    
    if fallback:
        print(f"✅ 폴백 음식 발견: {fallback.nutrient_name} (대분류: {fallback.food_class1})")
    else:
        print(f"❌ 대분류 '{food_name}'에 해당하는 음식 없음")
    
    return fallback


async def get_all_food_classes(session: AsyncSession) -> List[str]:
    """
    DB에서 모든 대분류(food_class1) 목록 조회
    
    Args:
        session: DB 세션
        
    Returns:
        중복 제거된 대분류 목록 (예: ["밥류", "피자", "국 및 탕류", ...])
    """
    stmt = select(FoodNutrient.food_class1).distinct()
    result = await session.execute(stmt)
    
    # None 값 제외하고 정렬
    classes = [row[0] for row in result.all() if row[0]]
    classes.sort()
    
    print(f"📋 DB 대분류 총 {len(classes)}개: {classes[:10]}...")
    return classes


async def get_representative_food_names(
    session: AsyncSession,
    food_class1: str
) -> List[str]:
    """
    특정 대분류의 대표식품명(representative_food_name) 유니크 목록 조회
    
    Args:
        session: DB 세션
        food_class1: 대분류 이름 (예: "빵 및 과자류")
        
    Returns:
        중복 제거된 대표식품명 목록 (예: ["피자", "빵", "케이크", ...])
    """
    stmt = select(FoodNutrient.representative_food_name).distinct().where(
        FoodNutrient.food_class1 == food_class1
    )
    result = await session.execute(stmt)
    
    # None 값 제외하고 정렬
    names = [row[0] for row in result.all() if row[0]]
    names.sort()
    
    print(f"📋 '{food_class1}' 대분류의 대표식품명 {len(names)}개: {names[:10]}...")
    return names


async def get_foods_by_representative_name(
    session: AsyncSession,
    food_class1: str,
    representative_food_name: str
) -> List[FoodNutrient]:
    """
    특정 대분류 + 대표식품명에 속하는 모든 음식 조회
    
    Args:
        session: DB 세션
        food_class1: 대분류 이름 (예: "빵 및 과자류")
        representative_food_name: 대표식품명 (예: "피자")
        
    Returns:
        해당 조건의 음식 리스트 (제한 없음 - 모든 음식 반환)
    """
    stmt = select(FoodNutrient).where(
        FoodNutrient.food_class1 == food_class1,
        FoodNutrient.representative_food_name == representative_food_name
    )
    
    result = await session.execute(stmt)
    foods = list(result.scalars().all())
    
    print(f"📋 '{food_class1}' > '{representative_food_name}': {len(foods)}개 음식 조회")
    return foods


async def get_foods_by_class(
    session: AsyncSession,
    food_class1: str,
    limit: int = 200,
    keywords: List[str] = None
) -> List[FoodNutrient]:
    """
    특정 대분류(food_class1)에 속하는 모든 음식 조회
    
    Args:
        session: DB 세션
        food_class1: 대분류 이름 (예: "피자", "밥류")
        limit: 최대 결과 개수
        keywords: 우선 정렬할 키워드 리스트 (예: ["햄버거", "치즈"])
        
    Returns:
        해당 대분류의 음식 리스트 (키워드 매칭 우선)
    """
    if keywords:
        # 키워드가 있으면 매칭되는 음식 우선
        print(f"🔍 키워드로 필터링: {keywords}")
        
        # 키워드 매칭 음식 먼저 조회 (nutrient_name + representative_food_name)
        priority_foods = []
        for keyword in keywords[:3]:  # 최대 3개 키워드만 사용
            keyword_stmt = select(FoodNutrient).where(
                FoodNutrient.food_class1 == food_class1,
                or_(
                    FoodNutrient.nutrient_name.like(f"%{keyword}%"),
                    FoodNutrient.representative_food_name.like(f"%{keyword}%")
                )
            ).limit(20)  # 키워드당 20개
            
            result = await session.execute(keyword_stmt)
            priority_foods.extend(result.scalars().all())
        
        # 중복 제거
        seen_ids = set()
        unique_priority_foods = []
        for food in priority_foods:
            if food.food_id not in seen_ids:
                seen_ids.add(food.food_id)
                unique_priority_foods.append(food)
        
        print(f"✅ 키워드 매칭: {len(unique_priority_foods)}개")
        
        # 나머지 음식 조회 (키워드 매칭 제외)
        remaining_count = limit - len(unique_priority_foods)
        if remaining_count > 0:
            remaining_stmt = select(FoodNutrient).where(
                FoodNutrient.food_class1 == food_class1,
                FoodNutrient.food_id.notin_(seen_ids)
            ).limit(remaining_count)
            
            result = await session.execute(remaining_stmt)
            remaining_foods = list(result.scalars().all())
            
            print(f"✅ 나머지 음식: {len(remaining_foods)}개")
            foods = unique_priority_foods + remaining_foods
        else:
            foods = unique_priority_foods[:limit]
    else:
        # 키워드 없으면 기존 방식
        stmt = select(FoodNutrient).where(
            FoodNutrient.food_class1 == food_class1
        ).limit(limit)
        
        result = await session.execute(stmt)
        foods = list(result.scalars().all())
    
    print(f"📋 '{food_class1}' 대분류: 총 {len(foods)}개 음식 조회")
    return foods


async def calculate_combined_nutrients(
    session: AsyncSession,
    ingredient_matches: dict[str, FoodNutrient],
    portions: dict[str, float] = None
) -> dict:
    """
    여러 재료의 영양소를 합산
    
    Args:
        session: DB 세션
        ingredient_matches: 재료별 FoodNutrient 매칭 결과
        portions: 재료별 비율 (합이 1.0, 예: {"토마토": 0.3, "치즈": 0.4, "밀가루": 0.3})
        
    Returns:
        합산된 영양소 정보
    """
    if portions is None:
        # 기본값: 균등 분배
        num_ingredients = len(ingredient_matches)
        portions = {name: 1.0 / num_ingredients for name in ingredient_matches.keys()}
    
    combined = {
        "protein": 0.0,
        "carbs": 0.0,
        "fat": 0.0,
        "fiber": 0.0,
        "sodium": 0.0,
        "calcium": 0.0,
        "iron": 0.0,
        "vitamin_a": 0.0,
        "vitamin_c": 0.0,
    }
    
    for ingredient_name, food_nutrient in ingredient_matches.items():
        portion = portions.get(ingredient_name, 0.0)
        
        if food_nutrient:
            combined["protein"] += (food_nutrient.protein or 0.0) * portion
            combined["carbs"] += (food_nutrient.carb or 0.0) * portion
            combined["fat"] += (food_nutrient.fat or 0.0) * portion
            combined["fiber"] += (food_nutrient.fiber or 0.0) * portion
            combined["sodium"] += (food_nutrient.sodium or 0.0) * portion
            combined["calcium"] += (food_nutrient.calcium or 0.0) * portion
            combined["iron"] += (food_nutrient.iron or 0.0) * portion
            combined["vitamin_a"] += (food_nutrient.vitamin_a or 0.0) * portion
            combined["vitamin_c"] += (food_nutrient.vitamin_c or 0.0) * portion
    
    return combined

