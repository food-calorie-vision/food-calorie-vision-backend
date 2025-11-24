# 🔗 음식 매칭 시스템 (Food Matching System)

## 📋 개요

GPT 추천 음식, 레시피, 식재료 기반 추천 음식을 `food_nutrients` 테이블의 실제 음식과 매칭하여 **자주 먹은 음식 count를 정확하게 추적**하는 시스템입니다.

## 🎯 해결한 문제

### 기존 문제점:
1. **UUID 사용**: GPT 추천/레시피 저장 시 UUID(`0378b7a2-...`)로 `food_id` 생성
2. **매칭 실패**: `food_nutrients`의 실제 `food_id`(`D101`, `D2-201` 등)와 연결 안됨
3. **Count 불가**: 같은 음식을 여러 번 먹어도 다른 `food_id`로 저장되어 자주 먹은 음식 통계 불가능
4. **영양소 정보 누락**: `nutrient_name`, `food_class1` 등이 null로 나옴

### 해결 방안:
✅ **통합 매칭 서비스** (`FoodMatchingService`) 구현  
✅ **3단계 매칭 전략** (정확한 이름 → 재료 기반 → GPT 유사도)  
✅ **실제 food_id 사용**: `food_nutrients`의 PK를 그대로 사용  
✅ **자주 먹은 음식 count 가능**: 같은 음식은 같은 `food_id`로 저장됨

---

## 🏗️ 시스템 구조

### 1. **FoodMatchingService** (`app/services/food_matching_service.py`)

음식 매칭의 핵심 서비스입니다.

#### 주요 메서드:

```python
async def match_food_to_db(
    session: AsyncSession,
    food_name: str,
    ingredients: List[str] = None,
    food_class_hint: str = None
) -> Optional[FoodNutrient]:
    """
    음식명과 재료를 기반으로 food_nutrients에서 가장 적합한 음식 찾기
    
    매칭 우선순위:
    1. 정확한 이름 매칭 (nutrient_name == food_name)
    2. 재료 기반 매칭 (food_class1, food_class2 활용)
    3. GPT 기반 유사도 매칭 (토큰 절약)
    """
```

---

## 🔍 3단계 매칭 전략

### **STEP 1: 정확한 이름 매칭**
- `nutrient_name` 또는 `representative_food_name`이 정확히 일치하는 음식 찾기
- 예: "사과" → `food_nutrients`의 "사과" 찾기

### **STEP 2: 재료 기반 매칭 (점수 시스템)**
- 후보 음식을 검색하고 점수를 계산하여 가장 적합한 음식 선택

**점수 계산:**
- `food_class1` 정확 일치: **+50점**
- `nutrient_name` 정확 일치: **+100점**
- `nutrient_name`에 음식명 포함: **+30점**
- 재료 매칭 (각 재료당): **+15점**
- 최소 점수 기준: **20점 이상**

**예시:**
```
음식명: "닭가슴살 샐러드"
재료: ["닭가슴살", "양상추", "토마토"]

후보 1: nutrient_name="닭가슴살", food_class1="육류"
  → 점수: 30 (음식명 포함) + 15 (재료 매칭) = 45점

후보 2: nutrient_name="샐러드", food_class1="채소류"
  → 점수: 30 (음식명 포함) + 15 (재료 매칭) = 45점

후보 3: nutrient_name="닭가슴살_구이", food_class1="육류"
  → 점수: 30 (음식명 포함) + 15 (재료 매칭) = 45점

→ 가장 높은 점수의 음식 선택
```

### **STEP 3: GPT 기반 유사도 매칭 (최후의 수단)**
- STEP 1, 2에서 매칭 실패 시 GPT에게 유사한 음식 선택 요청
- **토큰 절약 전략**: DB에서 관련 음식 목록(food_id, nutrient_name)만 가져와서 GPT에게 제공
- GPT가 가장 유사한 `food_id`를 선택

**프롬프트 예시:**
```
다음 음식 중에서 "닭가슴살 샐러드"와 가장 유사한 음식의 food_id를 선택하세요.
재료: 닭가슴살, 양상추, 토마토

음식 목록:
- D101: 닭가슴살 (분류: 육류)
- D201: 샐러드 (분류: 채소류)
- D301: 닭가슴살_구이 (분류: 육류)

가장 유사한 음식의 food_id만 답변하세요. (예: D101)
```

---

## 🛠️ 적용된 엔드포인트

### 1. **비전 분석 음식 저장** (`/api/v1/vision/save-food`)
```python
# food-calorie-vision-backend/app/api/v1/routes/vision.py

from app.services.food_matching_service import get_food_matching_service

matching_service = get_food_matching_service()
food_nutrient = await matching_service.match_food_to_db(
    session=session,
    food_name=request.food_name,
    ingredients=request.ingredients,
    food_class_hint=request.food_class_1
)

if food_nutrient:
    actual_food_id = food_nutrient.food_id  # ✅ 실제 food_id 사용
else:
    actual_food_id = generate_food_id(...)  # ⚠️ 매칭 실패 시 생성
```

### 2. **레시피 저장** (`/api/v1/recipes/save`)
```python
# food-calorie-vision-backend/app/api/v1/routes/recipes.py

matched_food_nutrient = await matching_service.match_food_to_db(
    session=session,
    food_name=save_request.recipe_name,
    ingredients=ingredient_list,
    food_class_hint=save_request.food_class_1
)

if matched_food_nutrient:
    actual_food_id = matched_food_nutrient.food_id  # ✅ 실제 food_id 사용
else:
    # 매칭 실패 시: 레시피는 "recipe_" 접두사 사용
    actual_food_id = f"recipe_{save_request.recipe_name[:50]}_{timestamp}"
```

### 3. **추천 음식 저장** (`/api/v1/meals/save-recommended`)
```python
# food-calorie-vision-backend/app/api/v1/routes/meals.py

matched_food_nutrient = await matching_service.match_food_to_db(
    session=session,
    food_name=request.food_name,
    ingredients=request.ingredients_used,
    food_class_hint=None
)

if matched_food_nutrient:
    actual_food_id = matched_food_nutrient.food_id  # ✅ 실제 food_id 사용
else:
    # 매칭 실패 시: 추천 음식은 "recommended_" 접두사 사용
    actual_food_id = f"recommended_{request.food_name[:50]}_{timestamp}"
```

---

## 📊 food_id 패턴

### ✅ **우선순위 1: food_nutrients의 실제 food_id**
```
D101, D2-201, D301-A, ...
```
- `food_nutrients` 테이블의 PK
- 영양소 정보 완벽하게 연결됨
- 자주 먹은 음식 count 가능

### ⚠️ **우선순위 2: 매칭 실패 시 생성되는 ID**

#### 레시피:
```
recipe_닭가슴살샐러드_1700000000
```
- 접두사: `recipe_`
- 레시피는 일반 음식과 구분

#### 추천 음식:
```
recommended_연어덮밥_1700000001
```
- 접두사: `recommended_`
- GPT 추천 음식

#### 일반 음식 (비전 분석):
```
pizza_abc123, 김치찌개_def456
```
- 해시 기반 ID
- 비전 분석으로 감지된 음식

---

## 🎯 자주 먹은 음식 Count 방법

### SQL 쿼리 예시:

```sql
-- 사용자가 가장 자주 먹은 음식 TOP 10
SELECT 
    ufh.food_id,
    fn.nutrient_name,
    fn.food_class1,
    COUNT(*) as eat_count
FROM UserFoodHistory ufh
LEFT JOIN food_nutrients fn ON ufh.food_id = fn.food_id
WHERE ufh.user_id = 1
GROUP BY ufh.food_id
ORDER BY eat_count DESC
LIMIT 10;
```

### Python 코드 예시:

```python
from sqlalchemy import select, func
from app.db.models import UserFoodHistory
from app.db.models_food_nutrients import FoodNutrient

# 자주 먹은 음식 조회
stmt = select(
    UserFoodHistory.food_id,
    FoodNutrient.nutrient_name,
    FoodNutrient.food_class1,
    func.count(UserFoodHistory.history_id).label('eat_count')
).join(
    FoodNutrient,
    UserFoodHistory.food_id == FoodNutrient.food_id,
    isouter=True
).where(
    UserFoodHistory.user_id == user_id
).group_by(
    UserFoodHistory.food_id
).order_by(
    func.count(UserFoodHistory.history_id).desc()
).limit(10)

result = await session.execute(stmt)
frequent_foods = result.fetchall()

for food in frequent_foods:
    print(f"{food.nutrient_name} ({food.food_class1}): {food.eat_count}회")
```

---

## 🔧 토큰 절약 전략

### 1. **매칭 우선순위**
- DB 검색 우선 (무료)
- GPT는 최후의 수단 (유료)

### 2. **GPT 사용 시 최소화**
- 전체 영양소 정보를 보내지 않음
- `food_id`, `nutrient_name`, `food_class1`만 전송
- 최대 20개 후보만 제공

### 3. **짧은 프롬프트**
```python
prompt = f"""다음 음식 중에서 "{food_name}"와 가장 유사한 음식의 food_id를 선택하세요.
재료: {', '.join(ingredients)}

음식 목록:
{candidate_list}

가장 유사한 음식의 food_id만 답변하세요. (예: D101)"""

# max_tokens=50 (매우 짧은 응답)
# temperature=0.3 (일관성 있는 선택)
```

---

## 📈 개선 효과

### Before (기존):
```
UserFoodHistory:
  history_id | user_id | food_id                              | food_name
  1          | 1       | 0378b7a2-5aeb-4a30-84d3-c44be1d2de8d | 닭가슴살 샐러드
  2          | 1       | f9a8c3d1-2b4e-5f6a-7c8d-9e0f1a2b3c4d | 닭가슴살 샐러드
  3          | 1       | a1b2c3d4-e5f6-7890-abcd-ef1234567890 | 닭가슴살 샐러드

→ 같은 음식인데 food_id가 다름 ❌
→ 자주 먹은 음식 count 불가능 ❌
→ food_nutrients와 연결 안됨 ❌
```

### After (개선):
```
UserFoodHistory:
  history_id | user_id | food_id | food_name
  1          | 1       | D101    | 닭가슴살 샐러드
  2          | 1       | D101    | 닭가슴살 샐러드
  3          | 1       | D101    | 닭가슴살 샐러드

→ 같은 음식은 같은 food_id ✅
→ 자주 먹은 음식 count 가능 ✅
→ food_nutrients와 완벽하게 연결 ✅
```

---

## 🚀 향후 개선 방안

### 1. **FoodMapping 캐시 테이블 추가** (선택사항)
```sql
CREATE TABLE FoodMapping (
    mapping_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    gpt_food_name VARCHAR(200),      -- GPT가 추천한 음식명
    matched_food_id VARCHAR(50),     -- food_nutrients의 food_id
    confidence_score FLOAT,          -- 매칭 신뢰도
    created_at DATETIME,
    usage_count INT DEFAULT 1,       -- 사용 횟수
    INDEX idx_gpt_food_name (gpt_food_name)
);
```

**장점:**
- 한 번 매칭한 결과를 캐싱하여 재사용
- GPT 호출 횟수 감소 (토큰 절약)
- 매칭 속도 향상

### 2. **GPT에게 DB 음식 목록 직접 제공**
- 레시피/식단 추천 시 GPT에게 `food_nutrients`의 실제 음식 목록을 제공
- GPT가 추천할 때부터 실제 `food_id`를 선택하게 함
- 매칭 과정 자체가 불필요해짐

```python
# 예시
categories = await matching_service.get_food_categories_for_gpt(
    session=session,
    user_preferences=["고기류", "채소류"]
)

# GPT 프롬프트에 포함
"""
다음 음식 목록에서 선택하여 추천하세요:

고기류:
- D101: 닭가슴살
- D102: 소고기
- D103: 돼지고기

채소류:
- D201: 브로콜리
- D202: 시금치
- D203: 양배추

추천 시 반드시 food_id를 포함하세요.
"""
```

---

## 📝 사용 예시

### 예시 1: 비전 분석 음식 저장
```python
# 사용자가 사진으로 "닭가슴살 샐러드" 감지
request = SaveFoodRequest(
    user_id=1,
    food_name="닭가슴살 샐러드",
    ingredients=["닭가슴살", "양상추", "토마토"],
    food_class_1="샐러드"
)

# 매칭 결과: D101 (food_nutrients의 실제 ID)
# UserFoodHistory에 food_id=D101로 저장
```

### 예시 2: 레시피 저장
```python
# GPT가 "연어 덮밥" 레시피 추천
request = SaveRecipeRequest(
    recipe_name="연어 덮밥",
    ingredients=["연어", "밥", "간장", "참기름"],
    food_class_1="밥류"
)

# 매칭 결과: D2-301 (food_nutrients의 "연어덮밥")
# UserFoodHistory에 food_id=D2-301로 저장
```

### 예시 3: 추천 음식 저장
```python
# GPT가 "고등어 구이" 추천
request = SaveRecommendedMealRequest(
    food_name="고등어 구이",
    ingredients_used=["고등어", "소금"]
)

# 매칭 결과: D401 (food_nutrients의 "고등어_구이")
# UserFoodHistory에 food_id=D401로 저장
```

---

## 🎉 결론

이제 GPT 추천 음식, 레시피, 식재료 기반 추천이 모두 `food_nutrients`의 실제 `food_id`와 매칭되어:

✅ **자주 먹은 음식 count 가능**  
✅ **영양소 정보 완벽하게 연결**  
✅ **DB 용량 최소화**  
✅ **토큰 사용량 최적화**

사용자가 사용할수록 데이터가 정확해지고, 추천 품질도 향상됩니다! 🚀

