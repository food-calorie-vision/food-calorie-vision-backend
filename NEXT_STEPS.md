# 추가 구현 사항 제안

음식 저장 API가 성공적으로 구현되었습니다! 다음은 시스템을 더욱 완성도 있게 만들기 위한 추가 구현 사항입니다.

## 🎯 우선순위 높음 (High Priority)

### 1. 음식 섭취 기록 조회 API
**목적**: 사용자가 자신의 음식 섭취 기록을 조회할 수 있도록 함

**엔드포인트**:
- `GET /api/v1/user/food-history` - 전체 기록 조회 (페이지네이션)
- `GET /api/v1/user/food-history/daily` - 특정 날짜 기록 조회
- `GET /api/v1/user/food-history/{history_id}` - 특정 기록 상세 조회

**응답 예시**:
```json
{
  "success": true,
  "data": {
    "histories": [
      {
        "historyId": 123,
        "foodName": "마르게리타 피자",
        "portionSizeG": 150.0,
        "consumedAt": "2025-11-17T10:30:00",
        "nutrients": {
          "calories": 800,
          "protein": 30,
          "carbs": 80,
          "fat": 40
        }
      }
    ],
    "total": 50,
    "page": 1,
    "pageSize": 10
  }
}
```

**구현 위치**: `app/api/v1/routes/users.py`

---

### 2. 음식 섭취 기록 수정/삭제 API
**목적**: 사용자가 잘못 입력한 기록을 수정하거나 삭제할 수 있도록 함

**엔드포인트**:
- `PATCH /api/v1/food/history/{history_id}` - 섭취량 수정
- `DELETE /api/v1/food/history/{history_id}` - 기록 삭제

**요청 예시 (수정)**:
```json
{
  "portionSizeG": 200.0
}
```

---

### 3. 영양소 정보 포함한 저장 API 개선
**목적**: 음식 저장 시 영양소 정보도 함께 저장하여 나중에 재계산 없이 조회 가능

**개선 방안**:
1. `food_nutrients` 테이블에서 조회한 영양소 정보를 `UserFoodHistory`와 연결
2. 또는 `health_score` 테이블에 영양소 정보 저장

**현재 문제점**:
- 음식 저장 시 영양소 정보가 저장되지 않음
- 조회 시 매번 `food_nutrients` 테이블을 다시 검색해야 함

**해결 방안**:
```python
# SaveFoodRequest에 영양소 정보 추가
class SaveFoodRequest(BaseModel):
    # ... 기존 필드
    calories: int | None = None
    protein: float | None = None
    carbs: float | None = None
    fat: float | None = None
    sodium: float | None = None
    fiber: float | None = None
```

---

### 4. 일일 영양소 합계 API
**목적**: 사용자의 하루 영양소 섭취량을 집계

**엔드포인트**:
- `GET /api/v1/user/daily-summary?date=2025-11-17`

**응답 예시**:
```json
{
  "success": true,
  "data": {
    "date": "2025-11-17",
    "totalCalories": 2100,
    "totalProtein": 85.5,
    "totalCarbs": 250.0,
    "totalFat": 70.0,
    "totalSodium": 3500,
    "mealsCount": 3,
    "meals": [
      {
        "foodName": "마르게리타 피자",
        "consumedAt": "2025-11-17T12:30:00",
        "calories": 800
      }
    ]
  }
}
```

---

## 📊 우선순위 중간 (Medium Priority)

### 5. 건강 점수 계산 및 저장
**목적**: `health_score` 테이블을 활용하여 음식의 건강 점수 계산

**구현 내용**:
- 음식 저장 시 자동으로 건강 점수 계산
- 권장 영양소 점수 (positive_score)
- 제한 영양소 점수 (negative_score)
- 최종 점수 (final_score)

**참고**: `app/services/health_score_service.py` 이미 존재

---

### 6. 음식 검색 API
**목적**: 사용자가 음식을 직접 검색하여 추가할 수 있도록 함

**엔드포인트**:
- `GET /api/v1/food/search?q=피자&limit=10`

**응답 예시**:
```json
{
  "success": true,
  "data": {
    "results": [
      {
        "foodId": "pizza_abc123",
        "foodName": "마르게리타 피자",
        "foodClass1": "피자",
        "calories": 800,
        "nutrients": { ... }
      }
    ]
  }
}
```

---

### 7. 즐겨찾기 음식 기능
**목적**: 자주 먹는 음식을 즐겨찾기에 추가하여 빠르게 기록

**새 테이블 필요**:
```sql
CREATE TABLE `UserFavoriteFoods` (
    `favorite_id` BIGINT NOT NULL AUTO_INCREMENT,
    `user_id` BIGINT NOT NULL,
    `food_id` VARCHAR(200) NOT NULL,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`favorite_id`),
    UNIQUE KEY `unique_user_food` (`user_id`, `food_id`)
);
```

**엔드포인트**:
- `POST /api/v1/user/favorites` - 즐겨찾기 추가
- `GET /api/v1/user/favorites` - 즐겨찾기 목록
- `DELETE /api/v1/user/favorites/{food_id}` - 즐겨찾기 제거

---

### 8. 이미지 업로드 및 저장
**목적**: 사용자가 업로드한 음식 이미지를 서버에 저장

**구현 방안**:
1. 로컬 파일 시스템에 저장 (`uploads/food_images/`)
2. 또는 AWS S3, Google Cloud Storage 등 클라우드 스토리지 사용

**개선 사항**:
```python
# vision.py에서 이미지 저장 로직 추가
import uuid
from pathlib import Path

async def save_uploaded_image(file: UploadFile) -> str:
    """업로드된 이미지를 저장하고 경로 반환"""
    upload_dir = Path("uploads/food_images")
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    file_extension = file.filename.split(".")[-1]
    unique_filename = f"{uuid.uuid4()}.{file_extension}"
    file_path = upload_dir / unique_filename
    
    with open(file_path, "wb") as f:
        f.write(await file.read())
    
    return str(file_path)
```

---

## 🔧 우선순위 낮음 (Low Priority)

### 9. 음식 추천 시스템
**목적**: 사용자의 건강 목표와 섭취 기록을 기반으로 음식 추천

**구현 내용**:
- 부족한 영양소를 채울 수 있는 음식 추천
- 건강 목표(gain/maintain/loss)에 맞는 음식 추천

---

### 10. 주간/월간 리포트
**목적**: `HealthReport` 테이블을 활용한 기간별 통계

**엔드포인트**:
- `GET /api/v1/user/report/weekly`
- `GET /api/v1/user/report/monthly`

**참고**: `app/services/health_report_service.py` 이미 존재

---

### 11. 알레르기 및 질병 프로필 연동
**목적**: `disease_allergy_profile` 테이블을 활용하여 경고 메시지 표시

**구현 내용**:
- 음식 저장 시 사용자의 알레르기 정보 확인
- 해당 재료가 포함된 경우 경고 메시지 반환

---

### 12. 음식 비교 기능
**목적**: 여러 음식의 영양소를 비교

**엔드포인트**:
- `POST /api/v1/food/compare`

**요청 예시**:
```json
{
  "foodIds": ["pizza_abc123", "salad_def456"]
}
```

---

## 🧪 테스트 및 품질 개선

### 13. 단위 테스트 작성
**위치**: `tests/` 디렉토리

**테스트 대상**:
- `food_service.py` - Food 생성/조회 로직
- `food_history_service.py` - 섭취 기록 생성/조회 로직
- `food_nutrients_service.py` - 영양소 매칭 로직

---

### 14. API 문서 자동화
**도구**: FastAPI의 자동 문서 기능 활용

**접속 URL**:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

### 15. 에러 핸들링 개선
**개선 사항**:
- 더 구체적인 에러 메시지
- 에러 코드 체계화
- 로깅 강화

---

## 📱 프론트엔드 연동

### 16. 음식 저장 버튼 연동
**위치**: `food-calorie-vision-frontend/src/app/food-image-analysis/page.tsx`

**구현 예시**:
```typescript
const handleSaveFood = async () => {
  try {
    const response = await fetch('/api/v1/food/save-food', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        userId: currentUser.id,
        foodName: analysisResult.foodName,
        foodClass1: analysisResult.foodClass1,
        foodClass2: analysisResult.foodClass2,
        ingredients: analysisResult.ingredients,
        portionSizeG: portionSize,
      }),
    });
    
    const result = await response.json();
    
    if (result.success) {
      alert('음식이 저장되었습니다!');
      // 기록 페이지로 이동
      router.push('/food-history');
    }
  } catch (error) {
    console.error('음식 저장 실패:', error);
    alert('음식 저장에 실패했습니다.');
  }
};
```

---

## 🎨 UI/UX 개선

### 17. 섭취량 입력 UI
**개선 사항**:
- 그램(g) 단위 입력 필드 추가
- 일반적인 섭취량 프리셋 제공 (1인분, 2인분 등)
- 슬라이더 또는 증감 버튼

---

### 18. 음식 기록 페이지
**새 페이지**: `/food-history`

**기능**:
- 날짜별 섭취 기록 표시
- 영양소 차트 (원형 그래프, 막대 그래프)
- 일일 목표 대비 달성률

---

## 📝 요약

### 즉시 구현 권장 (1-2주 내)
1. ✅ **음식 섭취 기록 조회 API** - 기본 기능
2. ✅ **영양소 정보 포함한 저장** - 데이터 완성도
3. ✅ **일일 영양소 합계 API** - 사용자 가치 제공

### 중기 구현 권장 (1개월 내)
4. 음식 검색 API
5. 건강 점수 계산
6. 프론트엔드 연동

### 장기 구현 권장 (2-3개월 내)
7. 음식 추천 시스템
8. 주간/월간 리포트
9. 알레르기 프로필 연동

---

## 💡 기술적 개선 사항

### 성능 최적화
- 데이터베이스 인덱스 최적화
- 캐싱 도입 (Redis)
- 이미지 최적화 (압축, 리사이징)

### 보안 강화
- API 인증/인가 강화
- Rate limiting
- Input validation 강화

### 모니터링
- 로깅 시스템 구축
- 에러 추적 (Sentry)
- 성능 모니터링 (New Relic, DataDog)


