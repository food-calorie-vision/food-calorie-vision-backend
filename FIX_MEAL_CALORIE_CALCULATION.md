# 끼니별 칼로리 계산 문제 수정 완료

## 📋 문제 분석

### 발견된 문제
- **증상**: 식단 추천 API에서 받은 식단을 저장할 때, 각 끼니(아침/점심/저녁/간식)의 칼로리가 정확하지 않음
- **원인**: 
  1. GPT 프롬프트에서 끼니별 상세 칼로리를 요청하지 않음
  2. 백엔드 파싱 로직이 끼니별 칼로리를 추출하지 않음
  3. 프론트엔드에서 **총 칼로리를 끼니 수로 단순 균등 분배**
  
  ```typescript
  // 기존 문제 코드 (프론트엔드)
  const caloriesPerMeal = mealCount > 0 ? totalCalories / mealCount : 0;
  // 예: 총 1500kcal ÷ 4끼니 = 375kcal (모든 끼니에 동일)
  // 실제로는 아침 350kcal, 점심 500kcal, 저녁 450kcal, 간식 200kcal로 다름
  ```

## ✅ 해결 방안

### 1. GPT 프롬프트 개선 (백엔드)

**파일**: `food-calorie-vision-backend/app/services/diet_recommendation_service.py`

**변경 내용**:
- 각 끼니별로 칼로리와 영양소를 명시하도록 프롬프트 수정
- 기존 응답 형식:
  ```
  아침: 현미밥 1공기 + 닭가슴살 구이 100g + 시금치 무침
  영양소: 단백질 120g / 탄수화물 150g / 지방 45g  (전체 합계)
  ```

- 새로운 응답 형식:
  ```
  아침: 현미밥 1공기 + 닭가슴살 구이 100g + 시금치 무침 (350kcal)
  아침 영양소: 단백질 30g / 탄수화물 40g / 지방 8g
  점심: 연어 덮밥 1인분 + 계란국 (500kcal)
  점심 영양소: 단백질 40g / 탄수화물 50g / 지방 15g
  ...
  ```

### 2. 백엔드 파싱 로직 개선

**파일**: `food-calorie-vision-backend/app/services/diet_recommendation_service.py`

**추가된 함수**:

```python
def _extract_menu_and_calories(self, text: str) -> tuple[str, float]:
    """
    메뉴 텍스트에서 메뉴명과 칼로리를 추출
    예: "메뉴 설명 (350kcal)" → ("메뉴 설명", 350.0)
    """
    calorie_pattern = r'\((\d+(?:\.\d+)?)\s*kcal\)'
    match = re.search(calorie_pattern, text, re.IGNORECASE)
    
    if match:
        calories = float(match.group(1))
        menu_text = re.sub(calorie_pattern, '', text, flags=re.IGNORECASE).strip()
        return menu_text, calories
    else:
        return text, 0.0

def _extract_nutrients(self, text: str) -> tuple[float, float, float]:
    """
    영양소 텍스트에서 단백질/탄수화물/지방 추출
    예: "단백질 30g / 탄수화물 40g / 지방 8g" → (30.0, 40.0, 8.0)
    """
    protein_match = re.search(r'단백질\s*(\d+(?:\.\d+)?)\s*g', text, re.IGNORECASE)
    carb_match = re.search(r'탄수화물\s*(\d+(?:\.\d+)?)\s*g', text, re.IGNORECASE)
    fat_match = re.search(r'지방\s*(\d+(?:\.\d+)?)\s*g', text, re.IGNORECASE)
    
    return (
        float(protein_match.group(1)) if protein_match else 0.0,
        float(carb_match.group(1)) if carb_match else 0.0,
        float(fat_match.group(1)) if fat_match else 0.0
    )
```

**`_parse_single_plan` 함수 수정**:
- `meal_details` 필드 추가하여 끼니별 상세 정보 저장
- 응답 구조:
  ```python
  {
    "name": "고단백 식단",
    "meals": {
      "breakfast": "현미밥 1공기 + 닭가슴살 구이 100g + 시금치 무침",
      "lunch": "연어 덮밥 1인분 + 계란국",
      ...
    },
    "meal_details": {
      "breakfast": { "calories": 350, "protein": 30, "carb": 40, "fat": 8 },
      "lunch": { "calories": 500, "protein": 40, "carb": 50, "fat": 15 },
      ...
    }
  }
  ```

### 3. 프론트엔드 수정

**파일**: `food-calorie-vision-frontend/src/app/recommend/page.tsx`

**타입 정의 확장**:
```typescript
type DietPlan = {
  name: string;
  description: string;
  totalCalories: string;
  meals: { ... };
  nutrients?: string;
  meal_details?: {  // 신규 추가
    breakfast?: { calories: number; protein: number; carb: number; fat: number; };
    lunch?: { calories: number; protein: number; carb: number; fat: number; };
    dinner?: { calories: number; protein: number; carb: number; fat: number; };
    snack?: { calories: number; protein: number; carb: number; fat: number; };
  };
};
```

**저장 로직 수정**:
- `meal_details`가 있으면 **실제 끼니별 칼로리 사용**
- 없으면 Fallback으로 균등 분배 (이전 방식)

```typescript
// meal_details 사용 여부 확인
const useMealDetails = selectedDietPlan.meal_details && 
                       Object.keys(selectedDietPlan.meal_details).length > 0;

// 아침 저장
if (selectedDietPlan.meals.breakfast) {
  const details = useMealDetails ? selectedDietPlan.meal_details?.breakfast : null;
  meals.push({
    food_name: `${selectedDietPlan.name} - 아침`,
    meal_type: 'breakfast',
    ingredients: [...],
    calories: details?.calories || fallbackCaloriesPerMeal,  // 실제 칼로리 우선
    protein: details?.protein || fallbackProteinPerMeal,
    carb: details?.carb || fallbackCarbPerMeal,
    fat: details?.fat || fallbackFatPerMeal,
    consumed_at: new Date().toISOString()
  });
}
```

## 🧪 테스트 방법

### 1. 백엔드 테스트

```bash
cd food-calorie-vision-backend
python -m uvicorn app.main:app --reload
```

**Swagger UI에서 테스트**:
1. http://localhost:8000/docs 접속
2. `POST /api/v1/recommend/diet-plan` 호출
3. 응답에서 `meal_details` 필드 확인

**예상 응답**:
```json
{
  "success": true,
  "data": {
    "dietPlans": [
      {
        "name": "고단백 식단",
        "meals": {
          "breakfast": "현미밥 1공기 + 닭가슴살 구이 100g + 시금치 무침"
        },
        "meal_details": {
          "breakfast": {
            "calories": 350,
            "protein": 30,
            "carb": 40,
            "fat": 8
          },
          "lunch": {
            "calories": 500,
            "protein": 40,
            "carb": 50,
            "fat": 15
          }
        }
      }
    ]
  }
}
```

### 2. 프론트엔드 테스트

```bash
cd food-calorie-vision-frontend
npm run dev
```

**테스트 시나리오**:
1. 로그인 후 `/recommend?tab=diet` 접속
2. "식단 추천해줘" 메시지 전송
3. 추천된 식단 중 하나 선택
4. "저장하기" 클릭
5. **콘솔 로그 확인**:
   ```
   ✅ meal_details 사용 - 실제 끼니별 칼로리 사용 
   { 
     breakfast: { calories: 350, protein: 30, ... },
     lunch: { calories: 500, protein: 40, ... }
   }
   ```

### 3. DB 확인

저장 후 데이터베이스에서 확인:

```sql
-- 최근 저장된 식단 조회
SELECT * FROM DietPlan ORDER BY created_at DESC LIMIT 1;

-- 끼니별 칼로리 확인
SELECT 
    meal_type,
    meal_name,
    calories,
    protein,
    carb,
    fat
FROM DietPlanMeal
WHERE diet_plan_id = 'plan_1234567890123'
ORDER BY 
    FIELD(meal_type, 'breakfast', 'lunch', 'dinner', 'snack');
```

**예상 결과**:
```
| meal_type  | meal_name           | calories | protein | carb | fat |
|------------|---------------------|----------|---------|------|-----|
| breakfast  | 고단백 식단 - 아침   | 350.00   | 30.00   | 40.0 | 8.0 |
| lunch      | 고단백 식단 - 점심   | 500.00   | 40.00   | 50.0 | 15.0|
| dinner     | 고단백 식단 - 저녁   | 450.00   | 35.00   | 35.0 | 18.0|
| snack      | 고단백 식단 - 간식   | 200.00   | 15.00   | 25.0 | 4.0 |
```

## 📊 수정 전후 비교

| 항목 | 수정 전 | 수정 후 |
|-----|--------|--------|
| **아침 칼로리** | 375 kcal (균등 분배) | 350 kcal (실제) |
| **점심 칼로리** | 375 kcal (균등 분배) | 500 kcal (실제) |
| **저녁 칼로리** | 375 kcal (균등 분배) | 450 kcal (실제) |
| **간식 칼로리** | 375 kcal (균등 분배) | 200 kcal (실제) |
| **총 칼로리** | 1500 kcal | 1500 kcal |
| **정확도** | ❌ 부정확 | ✅ 정확 |

## 🔧 Fallback 메커니즘

만약 GPT가 예전 형식으로 응답하거나 `meal_details`를 추출하지 못한 경우:
- 프론트엔드에서 자동으로 **균등 분배 방식(Fallback)**으로 전환
- 에러 발생 없이 정상 작동
- 콘솔에 경고 메시지 출력: `⚠️ meal_details 없음 - Fallback 균등 분배 사용`

## 📝 관련 파일

- ✅ `food-calorie-vision-backend/app/services/diet_recommendation_service.py`
- ✅ `food-calorie-vision-frontend/src/app/recommend/page.tsx`

## 🎯 결론

이제 식단 추천 시 **각 끼니별로 정확한 칼로리**가 저장됩니다:
- GPT가 끼니별 칼로리를 계산하여 제공
- 백엔드가 정확히 파싱
- 프론트엔드가 실제 값을 사용하여 저장
- DB에 정확한 칼로리 데이터 저장 완료 ✅

**수정 완료 일자**: 2024-11-19

