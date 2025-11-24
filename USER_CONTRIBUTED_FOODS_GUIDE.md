# 사용자 기여 음식 시스템 가이드

## 날짜: 2025-11-21

---

## 📋 개요

사용자가 추가한 음식을 공식 `food_nutrients` DB와 분리하여 관리하는 시스템입니다.

### 목적:
1. ✅ **데이터 품질 관리**: 공식 DB와 사용자 데이터 분리
2. ✅ **개인화**: 사용자가 자주 먹는 음식 학습
3. ✅ **확장성**: 인기 음식은 공식 DB로 승격 가능
4. ✅ **정확한 추적**: 같은 음식을 다시 먹을 때 자동 매칭

---

## 🗄️ 테이블 구조

### `user_contributed_foods` 테이블

```sql
CREATE TABLE user_contributed_foods (
    -- 기본 정보
    food_id VARCHAR(200) PRIMARY KEY,  -- USER_{user_id}_{timestamp}
    user_id BIGINT NOT NULL,
    
    -- 음식 정보
    food_name VARCHAR(200) NOT NULL,
    nutrient_name VARCHAR(255),
    food_class1 VARCHAR(255),
    food_class2 VARCHAR(255),
    representative_food_name VARCHAR(200),
    
    -- 재료
    ingredients VARCHAR(500),
    
    -- 영양소 (NRF9.3 기준)
    protein FLOAT,
    carb FLOAT,
    fat FLOAT,
    fiber FLOAT,
    vitamin_a FLOAT,
    vitamin_c FLOAT,
    calcium FLOAT,
    iron FLOAT,
    potassium FLOAT,
    magnesium FLOAT,
    saturated_fat FLOAT,
    added_sugar FLOAT,
    sodium FLOAT,
    
    -- 메타데이터
    usage_count INT DEFAULT 1,  -- 사용 횟수 (중요!)
    created_at DATETIME,
    updated_at DATETIME,
    
    -- 승인 (향후 기능)
    is_approved BOOLEAN DEFAULT FALSE,
    approved_at DATETIME,
    
    INDEX idx_user_id (user_id),
    INDEX idx_nutrient_name (nutrient_name),
    INDEX idx_usage_count (usage_count)
);
```

---

## 🔄 매칭 플로우

### 전체 과정:

```
사용자가 음식 저장 요청
    ↓
[STEP 1] food_nutrients에서 정확한 이름 매칭
    ↓ (실패 시)
[STEP 2] user_contributed_foods에서 검색
    - 본인이 추가한 음식 우선
    - 다른 사용자의 인기 음식 (usage_count >= 3)
    ↓ (실패 시)
[STEP 3] food_nutrients에서 재료 기반 매칭
    ↓ (실패 시)
[STEP 4] GPT 기반 유사도 매칭
    ↓ (실패 시)
[NEW] user_contributed_foods에 새로 추가
    - food_id: USER_{user_id}_{timestamp}
    - usage_count: 1
```

---

## 💡 주요 기능

### 1. 자동 매칭

**시나리오 1: 처음 먹는 음식**
```
사용자 A: "엄마표 김치찌개" 저장
→ 매칭 실패
→ user_contributed_foods에 추가
   food_id: USER_1_1732185600
   food_name: 엄마표 김치찌개
   usage_count: 1
```

**시나리오 2: 같은 음식 다시 먹기**
```
사용자 A: "엄마표 김치찌개" 다시 저장
→ STEP 2에서 매칭 성공!
→ usage_count: 1 → 2 (자동 증가)
```

**시나리오 3: 다른 사용자가 인기 음식 먹기**
```
사용자 B: "엄마표 김치찌개" 저장
→ STEP 2에서 매칭 성공! (usage_count >= 3)
→ 사용자 A의 음식 재사용
→ usage_count: 3 → 4
```

---

### 2. 사용 횟수 추적

```python
# 매칭 성공 시 자동 증가
if matched_food:
    matched_food.usage_count += 1
    await session.commit()
```

**활용:**
- 자주 먹는 음식 Top 10 조회
- 인기 음식 (usage_count >= 5) 공식 DB 승격 후보
- 개인화 추천 시스템

---

### 3. 검색 우선순위

```python
# 1. 본인이 추가한 음식 우선
SELECT * FROM user_contributed_foods
WHERE user_id = {user_id}
  AND (food_name LIKE '%{search}%' OR nutrient_name LIKE '%{search}%')
ORDER BY usage_count DESC
LIMIT 1;

# 2. 다른 사용자의 인기 음식
SELECT * FROM user_contributed_foods
WHERE usage_count >= 3
  AND (food_name LIKE '%{search}%' OR nutrient_name LIKE '%{search}%')
ORDER BY usage_count DESC
LIMIT 1;
```

---

## 📝 코드 예시

### API 호출 (식재료 기반 추천)

**요청:**
```json
POST /api/v1/meals/save-recommended
{
  "food_name": "기본 그린 샐러드",
  "ingredients_used": ["당근", "양파", "올리브오일"],
  "meal_type": "점심",
  "portion_size_g": 300
}
```

**응답 (첫 번째 저장):**
```json
{
  "success": true,
  "data": {
    "history_id": 123,
    "food_id": "USER_1_1732185600",  // 새로 생성
    "food_name": "기본 그린 샐러드",
    "health_score": 85
  }
}
```

**응답 (두 번째 저장):**
```json
{
  "success": true,
  "data": {
    "history_id": 124,
    "food_id": "USER_1_1732185600",  // 같은 ID (매칭 성공!)
    "food_name": "기본 그린 샐러드",
    "health_score": 85
  }
}
```

---

## 🔍 자주 먹는 음식 조회

```sql
-- 사용자별 자주 먹는 음식 Top 10
SELECT 
    food_name,
    usage_count,
    created_at
FROM user_contributed_foods
WHERE user_id = 1
ORDER BY usage_count DESC
LIMIT 10;
```

**결과:**
```
엄마표 김치찌개    | 15회
기본 그린 샐러드   | 12회
닭가슴살 볶음      | 8회
...
```

---

## 🎯 향후 기능

### 1. 관리자 승인 시스템

```sql
-- 인기 음식 조회 (승인 대기)
SELECT * FROM user_contributed_foods
WHERE usage_count >= 5
  AND is_approved = FALSE
ORDER BY usage_count DESC;
```

**프로세스:**
1. 사용 횟수 5회 이상 음식 자동 추천
2. 관리자가 영양소 정보 검증
3. `is_approved = TRUE` 설정
4. `food_nutrients`로 이동 (선택)

---

### 2. 음식 병합

```sql
-- 같은 음식 다른 이름 병합
-- 예: "엄마표 김치찌개" + "집밥 김치찌개" → "김치찌개"
UPDATE user_food_history
SET food_id = 'D101-...'  -- 공식 DB ID
WHERE food_id IN ('USER_1_...', 'USER_2_...');

DELETE FROM user_contributed_foods
WHERE food_id IN ('USER_1_...', 'USER_2_...');
```

---

### 3. 개인화 추천

```python
# 사용자가 자주 먹는 음식 기반 추천
user_favorites = await session.execute(
    select(UserContributedFood)
    .where(UserContributedFood.user_id == user_id)
    .order_by(UserContributedFood.usage_count.desc())
    .limit(5)
)

# 비슷한 음식 추천
for fav in user_favorites:
    similar_foods = find_similar_foods(fav.food_class1, fav.ingredients)
```

---

## 📊 통계

### 예상 효과:

| 지표 | Before | After |
|---|---|---|
| 음식 매칭 성공률 | ~60% | ~90% |
| 중복 음식 ID | 많음 | 적음 (자동 매칭) |
| 자주 먹는 음식 추적 | 불가능 | 가능 |
| DB 크기 | 작음 | 중간 (관리 가능) |

---

## 🚀 마이그레이션 가이드

### 1. 테이블 생성

```bash
# MySQL 접속
mysql -u root -p food_calorie_db

# SQL 실행
source migrations/create_user_contributed_foods_table.sql
```

### 2. 모델 확인

```python
from app.db.models_user_contributed import UserContributedFood

# 테이블 생성 확인
print(UserContributedFood.__tablename__)  # user_contributed_foods
```

### 3. 테스트

```bash
# 백엔드 서버 실행
uvicorn app.main:app --reload

# API 테스트
curl -X POST http://localhost:8000/api/v1/meals/save-recommended \
  -H "Content-Type: application/json" \
  -d '{
    "food_name": "테스트 음식",
    "ingredients_used": ["재료1", "재료2"],
    "meal_type": "점심"
  }'
```

---

## 🔧 트러블슈팅

### Q1: 매칭이 너무 자주 실패해요

**A:** 키워드와 카테고리 매핑을 추가하세요.

```python
# food_matching_service.py
FOOD_KEYWORDS = [
    "샐러드", "볶음", "구이", ...
    "새로운키워드"  # 추가
]

INGREDIENT_CATEGORY_MAP = {
    "새재료": "카테고리",  # 추가
}
```

---

### Q2: usage_count가 증가하지 않아요

**A:** 매칭 후 commit 확인

```python
if matched_food:
    matched_food.usage_count += 1
    await session.commit()  # 필수!
```

---

### Q3: 같은 음식인데 다른 ID로 저장돼요

**A:** 음식명을 정확히 입력하거나, 검색 로직 개선

```python
# 공백 제거, 대소문자 통일
food_name_clean = food_name.strip().lower().replace(" ", "")
```

---

## 📚 관련 파일

1. **모델**: `app/db/models_user_contributed.py`
2. **마이그레이션**: `migrations/create_user_contributed_foods_table.sql`
3. **매칭 서비스**: `app/services/food_matching_service.py`
4. **API 라우트**:
   - `app/api/v1/routes/vision.py` (음식 분석 후 저장)
   - `app/api/v1/routes/meals.py` (식재료 기반 추천)
   - `app/api/v1/routes/recipes.py` (레시피 저장)

---

## ✅ 체크리스트

- [x] `user_contributed_foods` 테이블 생성
- [x] `UserContributedFood` 모델 정의
- [x] 매칭 로직에 검색 추가 (STEP 2)
- [x] 매칭 실패 시 자동 저장
- [x] 사용 횟수 자동 증가
- [ ] 관리자 승인 시스템 (향후)
- [ ] 음식 병합 기능 (향후)
- [ ] 개인화 추천 (향후)

---

**사용자 기여 음식 시스템 구축 완료!** 🎉

이제 DB에 없는 음식도 자동으로 저장되고, 다음에 같은 음식을 먹을 때 자동으로 매칭됩니다!

