# 음식 저장 API 문서

## 개요
사용자가 선택한 음식을 `Food` 테이블과 `UserFoodHistory` 테이블에 저장하는 API입니다.

## 엔드포인트

### POST `/api/v1/food/save-food`

사용자가 음식 분석 결과를 확인한 후, 선택한 음식과 재료를 저장합니다.

## 요청 (Request)

### Headers
```
Content-Type: application/json
```

### Body (JSON)
```json
{
  "userId": 1,
  "foodName": "마르게리타 피자",
  "foodClass1": "피자",
  "foodClass2": "마르게리타",
  "ingredients": ["밀가루", "토마토소스", "모차렐라 치즈", "토마토"],
  "portionSizeG": 150.0,
  "imageRef": "https://example.com/pizza.jpg",
  "category": "양식"
}
```

### 필드 설명

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `userId` | integer | ✅ | 사용자 ID (BIGINT) |
| `foodName` | string | ✅ | 음식 이름 |
| `foodClass1` | string | ❌ | 음식 대분류 (예: "피자", "국밥") |
| `foodClass2` | string | ❌ | 음식 중분류 (예: "페퍼로니", "돼지머리") |
| `ingredients` | array[string] | ❌ | 주요 재료 리스트 |
| `portionSizeG` | float | ❌ | 섭취량 (그램) |
| `imageRef` | string | ❌ | 이미지 URL 또는 참조 |
| `category` | string | ❌ | 음식 카테고리 |

## 응답 (Response)

### 성공 (200 OK)

```json
{
  "success": true,
  "data": {
    "historyId": 123,
    "foodId": "마르게리타 피자_a1b2c3d4",
    "foodName": "마르게리타 피자",
    "consumedAt": "2025-11-17T10:30:00",
    "portionSizeG": 150.0
  },
  "message": "✅ 음식이 성공적으로 저장되었습니다: 마르게리타 피자"
}
```

### 응답 필드 설명

| 필드 | 타입 | 설명 |
|------|------|------|
| `historyId` | integer | 생성된 섭취 기록 ID (UserFoodHistory.history_id) |
| `foodId` | string | 음식 ID (Food.food_id) |
| `foodName` | string | 음식 이름 |
| `consumedAt` | string (ISO 8601) | 섭취 시간 |
| `portionSizeG` | float | 섭취량 (그램) |

### 오류 응답 (500 Internal Server Error)

```json
{
  "detail": "음식 저장 중 오류가 발생했습니다: [에러 메시지]"
}
```

## 처리 과정

1. **Food 테이블 처리**
   - `food_id` 생성: 음식명 + 재료 기반 해시
   - 동일한 `food_id`가 있으면 기존 레코드 사용
   - 없으면 새로운 Food 레코드 생성

2. **UserFoodHistory 테이블 처리**
   - 사용자의 음식 섭취 기록 생성
   - `history_id`는 자동 증가 (AUTO_INCREMENT)
   - `consumed_at`은 현재 시간으로 자동 설정

3. **데이터베이스 커밋**
   - 모든 변경사항을 데이터베이스에 저장

## 사용 예시

### cURL
```bash
curl -X POST "http://localhost:8000/api/v1/food/save-food" \
  -H "Content-Type: application/json" \
  -d '{
    "userId": 1,
    "foodName": "마르게리타 피자",
    "foodClass1": "피자",
    "foodClass2": "마르게리타",
    "ingredients": ["밀가루", "토마토소스", "모차렐라 치즈", "토마토"],
    "portionSizeG": 150.0
  }'
```

### JavaScript (Fetch API)
```javascript
const response = await fetch('http://localhost:8000/api/v1/food/save-food', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    userId: 1,
    foodName: '마르게리타 피자',
    foodClass1: '피자',
    foodClass2: '마르게리타',
    ingredients: ['밀가루', '토마토소스', '모차렐라 치즈', '토마토'],
    portionSizeG: 150.0,
  }),
});

const result = await response.json();
console.log(result);
```

### Python (requests)
```python
import requests

response = requests.post(
    'http://localhost:8000/api/v1/food/save-food',
    json={
        'userId': 1,
        'foodName': '마르게리타 피자',
        'foodClass1': '피자',
        'foodClass2': '마르게리타',
        'ingredients': ['밀가루', '토마토소스', '모차렐라 치즈', '토마토'],
        'portionSizeG': 150.0,
    }
)

result = response.json()
print(result)
```

## 데이터베이스 스키마

### Food 테이블
```sql
CREATE TABLE `Food` (
    `food_id` VARCHAR(200) NOT NULL,
    `image_ref` VARCHAR(255) NULL,
    `category` VARCHAR(100) NULL,
    `food_class_1` VARCHAR(100) NULL,
    `food_class_2` VARCHAR(100) NULL,
    `food_name` VARCHAR(200) NULL,
    PRIMARY KEY (`food_id`)
);
```

### UserFoodHistory 테이블
```sql
CREATE TABLE `UserFoodHistory` (
    `history_id` BIGINT NOT NULL AUTO_INCREMENT,
    `user_id` BIGINT NOT NULL,
    `food_id` VARCHAR(200) NOT NULL,
    `consumed_at` DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
    `portion_size_g` DECIMAL(10,2) NULL,
    `food_name` VARCHAR(200) NOT NULL,
    PRIMARY KEY (`history_id`),
    INDEX `idx_user_id` (`user_id`),
    INDEX `idx_food_id` (`food_id`),
    INDEX `idx_consumed_at` (`consumed_at`),
    CONSTRAINT `FK_User_TO_UserFoodHistory` FOREIGN KEY (`user_id`) 
        REFERENCES `User` (`user_id`) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT `FK_Food_TO_UserFoodHistory` FOREIGN KEY (`food_id`) 
        REFERENCES `Food` (`food_id`) ON DELETE CASCADE ON UPDATE CASCADE
);
```

## 주의사항

1. **food_id 생성 로직**
   - 음식명과 재료를 조합하여 해시 생성
   - 동일한 음식+재료 조합은 같은 `food_id`를 가짐
   - 최대 200자 제한

2. **외래 키 제약**
   - `user_id`는 `User` 테이블에 존재해야 함
   - `food_id`는 `Food` 테이블에 자동으로 생성됨

3. **트랜잭션 처리**
   - 오류 발생 시 자동 롤백
   - Food와 UserFoodHistory는 원자적으로 처리됨

## 관련 API

- `POST /api/v1/food/analysis-upload` - 음식 이미지 분석
- `POST /api/v1/food/reanalyze-with-selection` - 다른 후보 음식으로 재분석
- `GET /api/v1/user/food-history` - 사용자 음식 섭취 기록 조회 (구현 필요)


