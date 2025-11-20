# UserFoodHistory meal_type 컬럼 추가

## 개요

음식 섭취 기록에 식사 유형 (아침/점심/저녁/간식) 구분을 추가하기 위한 마이그레이션입니다.

## 변경 사항

### 1. 데이터베이스 스키마 변경

**테이블:** `UserFoodHistory`

**추가 컬럼:**
- `meal_type`: ENUM('breakfast', 'lunch', 'dinner', 'snack') NOT NULL DEFAULT 'lunch'
  - `breakfast`: 아침
  - `lunch`: 점심 (기본값)
  - `dinner`: 저녁
  - `snack`: 간식

**추가 인덱스:**
- `idx_meal_type`: meal_type 단일 인덱스
- `idx_user_consumed_meal`: (user_id, consumed_at, meal_type) 복합 인덱스

### 2. 적용 방법

#### MySQL Workbench 사용
1. MySQL Workbench 실행
2. `add_meal_type_to_user_food_history.sql` 파일 열기
3. 전체 스크립트 실행

#### CLI 사용
```bash
mysql -u root -p tempdb < migrations/add_meal_type_to_user_food_history.sql
```

#### Python 스크립트 사용
```bash
cd food-calorie-vision-backend
python -m alembic upgrade head
```

### 3. 롤백 방법

만약 변경사항을 되돌려야 하는 경우:

```sql
USE tempdb;

-- 인덱스 삭제
DROP INDEX `idx_meal_type` ON `UserFoodHistory`;
DROP INDEX `idx_user_consumed_meal` ON `UserFoodHistory`;

-- 컬럼 삭제
ALTER TABLE `UserFoodHistory`
DROP COLUMN `meal_type`;
```

## 영향 받는 코드

### 1. 백엔드 모델 (SQLAlchemy)
- `app/db/models.py` - `UserFoodHistory` 모델에 `meal_type` 필드 추가

### 2. API 스키마 (Pydantic)
- `app/api/v1/schemas/vision.py` - `SaveFoodRequest`에 `meal_type` 추가
- `app/api/v1/schemas/recipe.py` - `SaveRecipeRequest`에 `meal_type` 추가
- `app/api/v1/schemas/ingredient.py` - 식재료 레시피 저장 스키마에 `meal_type` 추가

### 3. API 라우트
- `app/api/v1/routes/vision.py` - 음식 저장 API에 `meal_type` 처리 추가
- `app/api/v1/routes/recipes.py` - 레시피 저장 API에 `meal_type` 처리 추가
- `app/api/v1/routes/ingredients.py` - 식재료 레시피 저장 API에 `meal_type` 처리 추가

### 4. 프론트엔드
- `src/types/index.ts` - 타입 정의에 `mealType` 추가
- 음식 분석 페이지 - 식사 유형 선택 UI 추가
- 레시피 페이지 - 식사 유형 선택 UI 추가

## 사용 예시

### API 요청 예시

#### 음식 저장 (POST /api/v1/food/save-food)
```json
{
  "userId": 1,
  "foodName": "김치찌개",
  "mealType": "lunch",
  "ingredients": ["김치", "돼지고기", "두부"],
  "portionSizeG": 300.0
}
```

#### 레시피 저장 (POST /api/v1/recipes/save)
```json
{
  "recipeName": "닭가슴살 샐러드",
  "mealType": "dinner",
  "ingredients": ["닭가슴살", "양상추", "토마토"],
  "actualServings": 1.0,
  "nutritionInfo": {
    "calories": 350,
    "protein": "35g",
    "carbs": "20g",
    "fat": "10g"
  }
}
```

### 조회 예시

#### 특정 식사 유형 조회
```sql
SELECT * FROM UserFoodHistory
WHERE user_id = 1
  AND DATE(consumed_at) = CURDATE()
  AND meal_type = 'breakfast'
ORDER BY consumed_at DESC;
```

#### 일일 식사 유형별 칼로리 집계
```sql
SELECT 
  meal_type,
  COUNT(*) as meal_count,
  SUM(hs.kcal) as total_calories
FROM UserFoodHistory ufh
JOIN health_score hs ON ufh.history_id = hs.history_id
WHERE ufh.user_id = 1
  AND DATE(ufh.consumed_at) = CURDATE()
GROUP BY meal_type
ORDER BY FIELD(meal_type, 'breakfast', 'lunch', 'dinner', 'snack');
```

## 주의사항

1. **기존 데이터**: 기존에 저장된 데이터는 모두 `meal_type = 'lunch'`로 설정됩니다.
2. **NOT NULL 제약**: `meal_type`은 필수 값이므로 API 요청 시 반드시 포함해야 합니다.
3. **ENUM 값**: 'breakfast', 'lunch', 'dinner', 'snack' 중 하나만 사용 가능합니다.
4. **대소문자**: ENUM 값은 소문자로 저장됩니다.

## 테스트 체크리스트

- [ ] 마이그레이션 스크립트 실행 성공
- [ ] 컬럼 및 인덱스 생성 확인
- [ ] 음식 저장 API 테스트 (meal_type 포함)
- [ ] 레시피 저장 API 테스트 (meal_type 포함)
- [ ] 식재료 레시피 저장 API 테스트 (meal_type 포함)
- [ ] 기존 데이터 조회 정상 동작 확인
- [ ] 프론트엔드 UI 테스트

## 버전 정보

- **작성일**: 2025-11-20
- **작성자**: AI Assistant
- **버전**: 1.0.0

