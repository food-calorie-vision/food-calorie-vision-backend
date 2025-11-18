# DB 매칭 실패 시 폴백 처리 가이드

## 개요

GPT-Vision이 인식한 음식이 `food_nutrients` 테이블에 정확히 매칭되지 않을 경우, 대분류(food_class1) 기반 폴백 메커니즘을 사용하여 사용자에게 유사한 영양 정보를 제공합니다.

## 처리 흐름

### 1단계: 정확한 매칭 시도
```
GPT-Vision 인식: "페퍼로니 피자"
↓
DB 검색: nutrient_name, food_class1, food_class2에서 "페퍼로니 피자" 검색
↓
점수 계산:
- food_class1 정확 일치: +20점
- nutrient_name 포함: +15점
- food_class2에 재료 포함: +10점
- nutrient_name에 재료 포함: +5점
```

### 2단계: 매칭 실패 시 폴백
```
정확한 매칭 실패
↓
음식명에서 대분류 추출: "페퍼로니 피자" → "피자"
↓
food_class1 = "피자"인 음식 중 가장 기본적인 것 선택
(nutrient_name 길이가 짧은 순서)
↓
예: "피자_마르게리타 피자" 또는 "피자_치즈 피자"
```

### 3단계: 폴백도 실패 시
```
대분류 폴백 실패
↓
모든 영양소를 0으로 설정
↓
사용자에게 경고 메시지 표시:
"⚠️ 이 음식의 영양 정보가 데이터베이스에 없습니다."
```

## 코드 구현

### 1. 폴백 함수 (`food_nutrients_service.py`)

```python
async def get_fallback_by_category(
    session: AsyncSession,
    food_name: str
) -> Optional[FoodNutrient]:
    """
    대분류(food_class1) 기반 폴백 검색
    
    특정 음식(예: "피자_페퍼로니")이 없을 때, 
    대분류(예: "피자")의 가장 기본적인 음식을 반환
    """
    print(f"🔄 폴백 검색: 대분류 '{food_name}'의 기본 음식 찾기")
    
    stmt = select(FoodNutrient).where(
        FoodNutrient.food_class1 == food_name
    ).order_by(
        func.length(FoodNutrient.nutrient_name)  # 이름이 짧은 순서
    ).limit(1)
    
    result = await session.execute(stmt)
    fallback = result.scalar_one_or_none()
    
    if fallback:
        print(f"✅ 폴백 음식 발견: {fallback.nutrient_name}")
    else:
        print(f"❌ 대분류 '{food_name}'에 해당하는 음식 없음")
    
    return fallback
```

### 2. API에서 폴백 사용 (`vision.py`)

```python
# 4. 정확한 매칭 시도
food_nutrient = await get_best_match_for_food(
    session,
    food_name=gpt_result["food_name"],
    ingredients=gpt_result["ingredients"]
)

# 4-1. 매칭 실패 시 대분류 기반 폴백
is_fallback = False
if not food_nutrient:
    # 음식명에서 대분류 추출 (예: "페퍼로니 피자" → "피자")
    food_name_parts = gpt_result["food_name"].split()
    category = food_name_parts[-1]
    
    food_nutrient = await get_fallback_by_category(session, category)
    
    if food_nutrient:
        is_fallback = True
        # 사용자에게 폴백 사용 안내
        gpt_result["suggestions"].insert(0, 
            f"ℹ️ '{gpt_result['food_name']}'의 정확한 영양 정보가 없어 "
            f"'{food_nutrient.nutrient_name}' 기준으로 표시됩니다."
        )
```

## 테스트 시나리오

### 시나리오 1: 정확한 매칭 성공
```
입력: "마르게리타 피자" 이미지
↓
DB 검색: "피자_마르게리타 피자" 발견
↓
결과: 정확한 영양 정보 제공
```

### 시나리오 2: 폴백 사용
```
입력: "토마토 피자" 이미지 (DB에 없음)
↓
정확한 매칭 실패
↓
폴백: "피자" 대분류에서 "피자_치즈 피자" 선택
↓
결과: 기본 피자 영양 정보 제공 + 안내 메시지
로그: "ℹ️ '토마토 피자'의 정확한 영양 정보가 없어 '피자_치즈 피자' 기준으로 표시됩니다."
```

### 시나리오 3: 완전 실패
```
입력: "스테이크" 이미지 (DB에 "스테이크" 대분류 없음)
↓
정확한 매칭 실패
↓
폴백 실패
↓
결과: 영양소 0 + 경고 메시지
로그: "⚠️ 이 음식의 영양 정보가 데이터베이스에 없습니다."
```

## 로그 예시

### 성공 케이스
```
🔍 DB 검색: 음식명='마르게리타 피자', 재료=['토마토소스', '치즈', '바질']
✅ 7개의 후보 발견
  - 피자_마르게리타 피자: nutrient_name 포함 (+15점)
  - 피자_마르게리타 피자 오리지널 (L): nutrient_name 포함 (+15점)
🎯 최종 선택: 피자_마르게리타 피자 (점수: 15점)
✅ DB 매칭 성공: 피자_마르게리타 피자
```

### 폴백 케이스
```
🔍 DB 검색: 음식명='토마토 피자', 재료=['토마토', '치즈', '밀가루']
❌ DB에서 매칭되는 음식을 찾을 수 없음
⚠️ 정확한 매칭 실패, 대분류 기반 폴백 시도...
🔄 폴백 검색: 대분류 '피자'의 기본 음식 찾기
✅ 폴백 음식 발견: 피자_치즈 피자 (대분류: 피자)
✅ 폴백 성공: 피자_치즈 피자 사용
```

### 완전 실패 케이스
```
🔍 DB 검색: 음식명='스테이크', 재료=['소고기', '후추', '소금']
❌ DB에서 매칭되는 음식을 찾을 수 없음
⚠️ 정확한 매칭 실패, 대분류 기반 폴백 시도...
🔄 폴백 검색: 대분류 '스테이크'의 기본 음식 찾기
❌ 대분류 '스테이크'에 해당하는 음식 없음
❌ 폴백도 실패: 기본값 사용
⚠️ DB 매칭 완전 실패: 기본값 사용
```

## 향후 개선 사항

### 1. 여러 후보 제공 (다음 단계)
- GPT-Vision이 여러 가능성 있는 음식을 신뢰도 순으로 제공
- 사용자가 UI에서 올바른 음식 선택
- 선택된 음식으로 DB 재검색

### 2. 대분류 추출 개선
현재: 마지막 단어를 대분류로 가정
```python
category = food_name_parts[-1]  # "페퍼로니 피자" → "피자"
```

개선안: 더 정교한 NLP 기반 추출
- "김치 볶음밥" → "볶음밥" (O) vs "밥" (X)
- "돼지고기 김치찌개" → "찌개" (O) vs "김치찌개" (X)

### 3. 유사도 기반 매칭
- 음식명의 문자열 유사도 계산 (Levenshtein distance)
- 재료 기반 영양소 추정
- 음식 카테고리별 평균값 사용

## 관련 파일

- `app/services/food_nutrients_service.py`: DB 검색 및 폴백 로직
- `app/api/v1/routes/vision.py`: API 엔드포인트 및 폴백 적용
- `app/db/models_food_nutrients.py`: FoodNutrient 모델 정의

## 참고

- 점수 체계는 `get_best_match_for_food` 함수에서 정의
- 폴백은 `nutrient_name` 길이가 짧은 순서로 선택 (가장 기본적인 음식)
- 사용자에게는 항상 안내 메시지를 통해 폴백 사용 여부를 알림

