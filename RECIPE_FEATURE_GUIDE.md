# 레시피 추천 기능 가이드

## 📋 개요

사용자의 건강 정보와 선호도를 기반으로 개인화된 레시피를 추천하고, 단계별 조리법을 채팅창 내에서 제공하는 기능입니다.

## 🎯 주요 기능

### 1. 개인화 레시피 추천
- LLM을 활용한 사용자 선호도 추론
- 건강 목표에 맞는 레시피 3개 추천
- 건강 경고 메시지 제공

### 2. 단계별 조리법
- 재료 목록 제공
- 상세한 조리 단계 (5-8단계)
- 각 단계별 팁 제공

### 3. 식단 기록 연동
- 조리 완료 후 자동 식단 기록
- NRF9.3 건강 점수 자동 계산
- 영양 정보 저장

## 🔧 API 엔드포인트

### 1. 레시피 추천
```
POST /api/v1/recipes/recommendations?user_id={user_id}
```

**Request Body:**
```json
{
  "user_request": "매콤한 음식 먹고 싶어요",
  "conversation_history": null
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "inferred_preference": "매콤하고 자극적인 맛",
    "health_warning": null,
    "recommendations": [
      {
        "name": "닭가슴살 샐러드",
        "description": "고단백 저칼로리 건강식",
        "calories": 350,
        "cooking_time": "20분",
        "difficulty": "쉬움",
        "suitable_reason": "건강 목표에 적합"
      }
    ]
  }
}
```

### 2. 레시피 상세
```
POST /api/v1/recipes/detail?user_id={user_id}
```

**Request Body:**
```json
{
  "recipe_name": "닭가슴살 샐러드"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "recipe_name": "닭가슴살 샐러드",
    "intro": "건강하고 맛있는 샐러드입니다.",
    "estimated_time": "20분",
    "total_steps": 5,
    "ingredients": [
      {"name": "닭가슴살", "amount": "200g"},
      {"name": "양상추", "amount": "100g"}
    ],
    "steps": [
      {
        "step_number": 1,
        "title": "재료 준비",
        "description": "재료를 깨끗이 씻습니다.",
        "tip": "신선한 재료를 사용하세요."
      }
    ],
    "nutrition_info": {
      "calories": 350,
      "protein": "35g",
      "carbs": "20g",
      "fat": "10g"
    }
  }
}
```

### 3. 레시피 식단 기록
```
POST /api/v1/recipes/save
```

**Request Body:**
```json
{
  "recipe_name": "닭가슴살 샐러드",
  "actual_servings": 1.0,
  "meal_type": "lunch",
  "nutrition_info": {
    "calories": 350,
    "protein": "35g",
    "carbs": "20g",
    "fat": "10g",
    "fiber": "5g",
    "sodium": "800mg"
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "history_id": 123,
    "food_name": "닭가슴살 샐러드",
    "nrf_score": 85.5,
    "calories": 350
  }
}
```

## 💻 프론트엔드 사용법

### 채팅창에서 레시피 요청
1. 사용자가 "닭가슴살 요리법 알려줘" 입력
2. 백엔드에서 레시피 3개 추천
3. 채팅창에 레시피 카드 표시

### 레시피 선택 및 조리
1. 레시피 카드 클릭
2. 레시피 상세 정보 표시 (재료, 소개)
3. "조리 시작하기" 버튼 클릭
4. 단계별로 조리법 표시
5. "이전" / "다음" 버튼으로 네비게이션
6. 마지막 단계 후 "완료" 버튼

### 식단 기록
1. 조리 완료 후 영양 정보 표시
2. "식단에 기록하기" 버튼 클릭
3. 자동으로 식단 저장 및 NRF9.3 점수 계산
4. 대시보드로 리다이렉트

## 🎨 UI/UX 특징

- ✅ 모든 작업이 채팅창 내에서 완료
- ✅ 로딩 상태 표시 (스피너 애니메이션)
- ✅ 단계별 진행 표시 (1/5, 2/5 등)
- ✅ 직관적인 버튼 배치
- ✅ 매끄러운 전환 애니메이션

## 🔐 인증

모든 API는 세션 기반 인증이 필요합니다.
- `credentials: 'include'` 설정 필수
- 로그인되지 않은 경우 자동으로 로그인 페이지로 리다이렉트

## 📝 TODO

- [ ] 사용자가 섭취량(인분) 입력 가능하도록 개선
- [ ] 식사 유형(아침/점심/저녁/간식) 선택 UI 추가
- [ ] 대화 히스토리 저장 기능 추가
- [ ] 레시피 즐겨찾기 기능
- [ ] 레시피 공유 기능




