# 음식 직접 입력 기능 가이드

## 날짜: 2025-11-21

---

## 📋 개요

사용자가 GPT 추천 4개 음식 중에 원하는 음식이 없을 때, **직접 입력**할 수 있는 기능입니다.

### 목적:
1. ✅ **사용자 경험 개선**: 강제 선택 → 자유 입력
2. ✅ **데이터 수집**: 사용자가 실제로 먹는 음식 학습
3. ✅ **자동 매칭**: 다음에 같은 음식 먹을 때 자동 추천
4. ✅ **개인화**: 나만의 음식 DB 구축

---

## 🔄 사용자 플로우

### Before (기존):
```
음식 사진 분석
  ↓
GPT 4개 추천
  ↓
반드시 1개 선택 (강제) ❌
  ↓
저장
```

### After (개선):
```
음식 사진 분석
  ↓
GPT 4개 추천
  ↓
┌─────────────────────────┐
│ [선택 1] 4개 중 1개 선택 │
│ [선택 2] 직접 입력하기 ⭐│
└─────────────────────────┘
  ↓
직접 입력 화면
  - 음식 이름 입력 (필수)
  - 재료 입력 (선택)
  ↓
user_contributed_foods에 자동 저장 ✅
  ↓
다음에 같은 음식 먹으면 자동 매칭!
```

---

## 🎨 UI 구현

### 1. 음식 선택 화면

```tsx
// MealPeekSwiper.tsx

{/* GPT 추천 4개 */}
{current.predictions.map((pred) => (
  <button onClick={() => selectFood(pred.name)}>
    {pred.name}
  </button>
))}

{/* 직접 입력 버튼 (NEW) */}
<button onClick={openCustomInput}>
  ✏️ 해당 음식이 없나요? 직접 입력하기
</button>
```

**스타일:**
- 점선 테두리 (`border-dashed`)
- 회색 배경 (`bg-slate-50`)
- 호버 시 파란색 (`hover:bg-blue-50`)

---

### 2. 직접 입력 화면

```tsx
<div className="flex flex-col h-full">
  {/* 제목 */}
  <p className="text-lg font-bold">음식 직접 입력</p>
  
  {/* 음식 이름 입력 (필수) */}
  <label>음식 이름 *</label>
  <input
    type="text"
    value={customFoodName}
    onChange={(e) => setCustomFoodName(e.target.value)}
    placeholder="예: 엄마표 김치찌개"
  />
  
  {/* 재료 입력 (선택) */}
  <label>주재료 (선택)</label>
  <input
    type="text"
    value={customIngredients}
    onChange={(e) => setCustomIngredients(e.target.value)}
    placeholder="예: 김치, 돼지고기, 두부"
  />
  <p className="text-xs">콤마(,)로 구분하여 입력해주세요</p>
  
  {/* 안내 메시지 */}
  <div className="bg-blue-50">
    💡 직접 입력한 음식은 나만의 음식 DB에 저장되어,
    다음에 같은 음식을 먹을 때 자동으로 추천됩니다!
  </div>
  
  {/* 버튼 */}
  <button onClick={confirmCustomFood}>확인</button>
  <button onClick={goBackToNameSelection}>뒤로 가기</button>
</div>
```

---

## 🔧 프론트엔드 로직

### Phase 추가

```tsx
type Phase = 'name' | 'custom_input' | 'ingredients' | 'done';
```

### State 추가

```tsx
const [customFoodName, setCustomFoodName] = useState<string>('');
const [customIngredients, setCustomIngredients] = useState<string>('');
```

### 함수 구현

```tsx
// 직접 입력 화면 열기
const openCustomInput = () => {
  setPhaseById((prev) => ({ ...prev, [current.id]: 'custom_input' }));
  setCustomFoodName('');
  setCustomIngredients('');
};

// 직접 입력 확인
const confirmCustomFood = () => {
  if (!customFoodName.trim()) {
    alert('음식 이름을 입력해주세요.');
    return;
  }
  
  // 음식명 저장
  setPickedNameById((prev) => ({ 
    ...prev, 
    [current.id]: customFoodName.trim() 
  }));
  
  // 재료 파싱 (콤마 또는 공백으로 구분)
  const ingredients = customIngredients
    .split(/[,\s]+/)
    .map(i => i.trim())
    .filter(i => i.length > 0);
  
  setPickedIngrById((prev) => ({ 
    ...prev, 
    [current.id]: ingredients 
  }));
  
  // 완료 처리
  setPhaseById((prev) => ({ ...prev, [current.id]: 'done' }));
  
  onConfirmItem?.({
    id: current.id,
    name: customFoodName.trim(),
    ingredients: ingredients,
  });
  
  // 다음 이미지로 이동
  if (images.length > 1) {
    setTimeout(() => goNext(), autoSwipeDelayMs);
  }
};
```

---

## 🔌 백엔드 처리

### API: `/api/v1/vision/save-food`

**요청:**
```json
{
  "user_id": 1,
  "food_name": "엄마표 김치찌개",  // 직접 입력한 이름
  "ingredients": ["김치", "돼지고기", "두부"],
  "portion_size_g": 300,
  "protein": 15.0,
  "carbs": 20.0,
  "fat": 10.0,
  "sodium": 800.0,
  "fiber": 3.0,
  "meal_type": "점심"
}
```

**처리 과정:**

```python
# 1. 매칭 시도
matched = await match_food_to_db(
    food_name="엄마표 김치찌개",
    ingredients=["김치", "돼지고기", "두부"],
    user_id=1
)

# 2-1. 매칭 성공 (이전에 먹었던 음식)
if matched:
    food_id = matched.food_id  # USER_1_1732185600
    matched.usage_count += 1  # 자동 증가
    
# 2-2. 매칭 실패 (처음 먹는 음식)
else:
    # user_contributed_foods에 새로 추가
    new_food = UserContributedFood(
        food_id=f"USER_{user_id}_{timestamp}",
        user_id=1,
        food_name="엄마표 김치찌개",
        ingredients="김치, 돼지고기, 두부",
        protein=15.0,
        carb=20.0,
        fat=10.0,
        sodium=800.0,
        fiber=3.0,
        usage_count=1
    )
    session.add(new_food)
```

**응답:**
```json
{
  "success": true,
  "data": {
    "history_id": 123,
    "food_id": "USER_1_1732185600",
    "food_name": "엄마표 김치찌개",
    "health_score": 75
  }
}
```

---

## 🧪 테스트 시나리오

### 시나리오 1: 처음 직접 입력

**Step 1: 음식 분석**
```
사용자: 사진 업로드
GPT: "김치찌개", "된장찌개", "순두부찌개", "부대찌개"
```

**Step 2: 직접 입력**
```
사용자: "해당 음식이 없나요? 직접 입력하기" 클릭
입력: 음식명 = "엄마표 김치찌개"
      재료 = "김치, 돼지고기, 두부"
```

**Step 3: 저장**
```
✅ user_contributed_foods에 저장
   food_id: USER_1_1732185600
   food_name: 엄마표 김치찌개
   usage_count: 1
```

**DB 확인:**
```sql
SELECT * FROM user_contributed_foods WHERE user_id = 1;
-- USER_1_1732185600 | 엄마표 김치찌개 | 김치, 돼지고기, 두부 | 1
```

---

### 시나리오 2: 같은 음식 다시 먹기

**Step 1: 음식 분석**
```
사용자: 같은 음식 사진 업로드
GPT: "김치찌개", "된장찌개", ...
```

**Step 2: 직접 입력**
```
사용자: "직접 입력하기" 클릭
입력: 음식명 = "엄마표 김치찌개"
```

**Step 3: 자동 매칭 성공!**
```
✅ STEP 2에서 매칭 성공!
   food_id: USER_1_1732185600 (동일!)
   usage_count: 1 → 2 (자동 증가)
```

**DB 확인:**
```sql
SELECT food_name, usage_count FROM user_contributed_foods WHERE user_id = 1;
-- 엄마표 김치찌개 | 2
```

---

### 시나리오 3: 자주 먹는 음식 자동 추천

**Step 1: 5번 먹기**
```
usage_count: 1 → 2 → 3 → 4 → 5
```

**Step 2: 다른 사용자도 먹기**
```
사용자 B: "엄마표 김치찌개" 입력
→ STEP 2에서 매칭 성공! (usage_count >= 3)
→ 사용자 A의 음식 재사용
→ usage_count: 5 → 6
```

---

## 📊 개선 효과

| 항목 | Before | After |
|---|---|---|
| 음식 선택 | 강제 선택 (4개 중 1개) | 자유 입력 가능 |
| 사용자 만족도 | 낮음 (원하는 음식 없음) | 높음 (직접 입력) |
| 데이터 정확도 | 낮음 (억지로 선택) | 높음 (실제 음식) |
| 재사용 | 불가능 | 자동 매칭 |

---

## 🎯 향후 개선

### 1. 자동 완성 기능

```tsx
// 입력 중 자동 완성
<input
  type="text"
  value={customFoodName}
  onChange={(e) => {
    setCustomFoodName(e.target.value);
    // 자주 먹는 음식 검색
    searchUserFoods(e.target.value);
  }}
/>

{/* 자동 완성 목록 */}
{suggestions.map(food => (
  <button onClick={() => setCustomFoodName(food.name)}>
    {food.name} (먹은 횟수: {food.usage_count}회)
  </button>
))}
```

---

### 2. 최근 입력한 음식 표시

```tsx
{/* 최근 입력 */}
<div className="mb-4">
  <p className="text-sm font-semibold mb-2">최근 입력한 음식</p>
  {recentFoods.map(food => (
    <button onClick={() => selectRecentFood(food)}>
      {food.name}
    </button>
  ))}
</div>
```

---

### 3. 재료 자동 추천

```tsx
// 음식명 입력 시 재료 자동 추천
if (customFoodName === "김치찌개") {
  suggestedIngredients = ["김치", "돼지고기", "두부", "고춧가루"];
}
```

---

## 📚 수정된 파일

1. ✅ `food-calorie-vision-frontend/src/components/MealPeekSwiper.tsx`
   - Phase에 `custom_input` 추가
   - `customFoodName`, `customIngredients` state 추가
   - `openCustomInput()`, `confirmCustomFood()` 함수 추가
   - 직접 입력 UI 추가

2. ✅ `food-calorie-vision-backend/app/api/v1/routes/vision.py`
   - 이미 `user_contributed_foods` 지원 (수정 불필요)

3. ✅ `CUSTOM_FOOD_INPUT_FEATURE.md` (신규)
   - 기능 가이드 문서

---

## ✅ 체크리스트

- [x] 프론트엔드: 직접 입력 버튼 추가
- [x] 프론트엔드: 직접 입력 화면 구현
- [x] 프론트엔드: 재료 파싱 로직
- [x] 백엔드: user_contributed_foods 저장 (이미 구현됨)
- [x] 백엔드: 자동 매칭 로직 (이미 구현됨)
- [ ] 테스트: 실제 사용자 플로우 확인
- [ ] 개선: 자동 완성 기능 (향후)
- [ ] 개선: 최근 입력 음식 표시 (향후)

---

**음식 직접 입력 기능 구현 완료!** 🎉

이제 사용자는 GPT 추천에 없는 음식도 자유롭게 입력할 수 있고, 다음에 같은 음식을 먹을 때 자동으로 매칭됩니다!

