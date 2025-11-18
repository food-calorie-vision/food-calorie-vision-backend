# YOLO + GPT-Vision 음식 분석 파이프라인 설정 가이드

## 📋 개요

이 프로젝트는 **YOLO11n** 객체 detection과 **GPT-Vision** 이미지 분석을 결합하여 음식 이미지를 분석합니다.

### 🔄 처리 흐름

```
사용자 이미지 업로드
    ↓
YOLO11n Detection (음식 객체 감지)
    ↓
GPT-Vision 분석 (YOLO 결과 + 이미지)
    ↓
상세 영양 정보 반환
```

---

## 🚀 설치 및 설정

### 1️⃣ 필수 패키지 설치

```bash
cd food-calorie-vision-backend
pip install -r requirements.txt
```

**주요 패키지:**
- `ultralytics==8.3.0` - YOLO11n 모델
- `openai==1.54.3` - GPT-Vision API
- `opencv-python==4.10.0.84` - 이미지 처리
- `torch==2.5.1` - PyTorch (YOLO 백엔드)
- `pillow==10.4.0` - 이미지 처리

### 2️⃣ YOLO 모델 준비

**옵션 A: 자동 다운로드 (권장)**
- 서버 실행 시 자동으로 `yolo11n.pt` 다운로드됨
- 별도 작업 불필요

**옵션 B: 수동 설치**
```bash
# 프로젝트 루트에 yolo11n.pt 파일 배치
# 또는 원하는 경로에 배치 후 .env에서 경로 설정
```

### 3️⃣ OpenAI API 키 설정

1. **OpenAI API 키 발급**
   - https://platform.openai.com/api-keys 에서 API 키 생성
   - GPT-4 Vision 모델 사용 권한 확인

2. **.env 파일 생성**
   ```bash
   cp .env.example .env
   ```

3. **.env 파일 수정**
   ```env
   # OpenAI API 설정
   OPENAI_API_KEY=sk-your-actual-api-key-here
   
   # YOLO 모델 경로 (선택사항)
   VISION_MODEL_PATH=yolo11n.pt
   ```

---

## 🧪 테스트

### 1️⃣ 서버 실행

```bash
cd food-calorie-vision-backend
python -m uvicorn app.main:app --reload
```

**서버 시작 로그 확인:**
```
✅ YOLO 모델 로드 완료!
✅ OpenAI GPT-Vision 클라이언트 초기화 완료!
INFO:     Uvicorn running on http://127.0.0.1:8000
```

### 2️⃣ Swagger UI 테스트

1. **Swagger UI 접속**
   ```
   http://localhost:8000/docs
   ```

2. **`POST /api/v1/food/analysis-upload` 엔드포인트 찾기**

3. **이미지 업로드 테스트**
   - "Try it out" 클릭
   - 음식 이미지 파일 선택 (JPEG, PNG)
   - "Execute" 클릭

4. **응답 확인**
   ```json
   {
     "success": true,
     "data": {
       "analysis": {
         "foodName": "페퍼로니 피자",
         "calories": 800,
         "nutrients": {
           "protein": 30.0,
           "carbs": 80.0,
           "fat": 40.0,
           "sodium": 1500.0,
           "fiber": 3.0
         },
         "confidence": 0.9,
         "suggestions": [
           "피자는 칼로리가 높으니 적당히 섭취하세요.",
           "채소를 추가하여 영양 균형을 맞추세요.",
           "물을 충분히 마시세요."
         ]
       },
       "timestamp": "2025-11-10T...",
       "processingTime": 3500
     },
     "message": "✅ 분석 완료: 페퍼로니 피자 (건강점수: 65점)"
   }
   ```

### 3️⃣ cURL 테스트

```bash
curl -X POST "http://localhost:8000/api/v1/food/analysis-upload" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@/path/to/your/food-image.jpg"
```

---

## 🏗️ 아키텍처

### 파일 구조

```
food-calorie-vision-backend/
├── app/
│   ├── services/
│   │   ├── yolo_service.py          # YOLO detection 서비스
│   │   └── gpt_vision_service.py    # GPT-Vision 분석 서비스
│   ├── api/v1/routes/
│   │   └── vision.py                # 이미지 분석 API 엔드포인트
│   └── core/
│       └── config.py                # 설정 (API 키, 모델 경로)
├── yolo11n.pt                       # YOLO 모델 파일 (자동 다운로드)
├── .env                             # 환경 변수 (API 키)
└── requirements.txt                 # Python 패키지
```

### 서비스 설명

#### 1. **YOLOService** (`yolo_service.py`)
- YOLO11n 모델로 음식 객체 detection
- 바운딩 박스 좌표 및 클래스 반환
- 신뢰도(confidence) 임계값: 25%

**주요 메서드:**
```python
detect_food(image_bytes: bytes) -> dict
```

**반환 값:**
```python
{
    "detected_objects": [
        {
            "class_name": "pizza",
            "confidence": 0.87,
            "bbox": [x1, y1, x2, y2]
        }
    ],
    "summary": "피자 1개 감지됨",
    "total_objects": 1
}
```

#### 2. **GPTVisionService** (`gpt_vision_service.py`)
- YOLO detection 결과 + 원본 이미지를 GPT-Vision으로 전송
- 음식명, 칼로리, 영양소, 건강 제안 분석
- GPT-4 Vision 모델 사용

**주요 메서드:**
```python
analyze_food_with_detection(
    image_bytes: bytes,
    yolo_detection_result: dict
) -> dict
```

**반환 값:**
```python
{
    "food_name": "페퍼로니 피자",
    "description": "...",
    "calories": 800,
    "nutrients": {
        "protein": 30.0,
        "carbs": 80.0,
        "fat": 40.0,
        "sodium": 1500.0,
        "fiber": 3.0
    },
    "portion_size": "1조각 (약 150g)",
    "health_score": 65,
    "suggestions": [...]
}
```

---

## 🔧 트러블슈팅

### ❌ "YOLO 모델 로드 실패"

**원인:** YOLO 모델 파일이 없거나 경로가 잘못됨

**해결:**
1. 자동 다운로드 대기 (첫 실행 시 시간 소요)
2. 수동으로 `yolo11n.pt` 다운로드 후 프로젝트 루트에 배치
3. `.env`에서 `VISION_MODEL_PATH` 확인

### ❌ "OpenAI 클라이언트 초기화 실패"

**원인:** OPENAI_API_KEY가 설정되지 않았거나 잘못됨

**해결:**
1. `.env` 파일에 `OPENAI_API_KEY` 추가
2. API 키 유효성 확인: https://platform.openai.com/api-keys
3. GPT-4 Vision 모델 사용 권한 확인

### ❌ "음식이 감지되지 않았습니다"

**원인:** YOLO가 이미지에서 음식을 인식하지 못함

**해결:**
1. 더 선명한 이미지 사용
2. 음식이 이미지 중앙에 위치하도록 촬영
3. YOLO가 인식 가능한 객체 클래스 확인 (COCO 데이터셋 기준)

### ❌ "GPT-Vision 분석 실패"

**원인:** OpenAI API 호출 실패 또는 응답 파싱 오류

**해결:**
1. 인터넷 연결 확인
2. OpenAI API 사용량 및 크레딧 확인
3. 서버 로그에서 `raw_response` 확인 (디버깅용)

---

## 💰 비용 고려사항

### OpenAI GPT-4 Vision API 비용

- **입력 비용:** 이미지 크기에 따라 다름
- **출력 비용:** 생성된 텍스트 토큰 수에 따라 다름
- **예상 비용:** 이미지 1장당 약 $0.01 ~ $0.05

**비용 절감 팁:**
1. 이미지 크기 최적화 (1024x1024 이하 권장)
2. `max_tokens` 제한 설정 (현재 1500)
3. 캐싱 활용 (동일 이미지 재분석 방지)

---

## 📊 성능 최적화

### 1. YOLO 모델 최적화
- GPU 사용 (CUDA 설치 시 자동 활성화)
- 신뢰도 임계값 조정 (`conf=0.25`)
- 이미지 크기 조정 (640x640 기본)

### 2. GPT-Vision 최적화
- 이미지 압축 (JPEG 품질 80-90%)
- 프롬프트 최적화 (토큰 수 감소)
- 비동기 처리 (여러 요청 동시 처리)

### 3. 캐싱 전략
- Redis를 활용한 분석 결과 캐싱
- 동일 이미지 해시값 기반 캐싱
- TTL: 24시간 권장

---

## 🚀 프로덕션 배포

### 환경 변수 설정

```env
# 프로덕션 설정
APP_ENV=production
SESSION_HTTPS_ONLY=true
SESSION_SECRET_KEY=strong-random-secret-key

# OpenAI API
OPENAI_API_KEY=sk-prod-api-key

# YOLO 모델
VISION_MODEL_PATH=/app/models/yolo11n.pt
```

### Docker 배포 (예정)

```dockerfile
# Dockerfile 예시
FROM python:3.11-slim

# YOLO 모델 복사
COPY yolo11n.pt /app/models/yolo11n.pt

# 환경 변수
ENV VISION_MODEL_PATH=/app/models/yolo11n.pt
ENV OPENAI_API_KEY=${OPENAI_API_KEY}

# 애플리케이션 실행
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 📚 참고 자료

- **YOLO 공식 문서:** https://docs.ultralytics.com/
- **OpenAI Vision API:** https://platform.openai.com/docs/guides/vision
- **FastAPI 공식 문서:** https://fastapi.tiangolo.com/

---

## 🆘 지원

문제가 발생하면 다음을 확인하세요:

1. 서버 로그 (`uvicorn` 출력)
2. `.env` 파일 설정
3. Python 패키지 버전 (`pip list`)
4. OpenAI API 상태: https://status.openai.com/

---

**마지막 업데이트:** 2025-11-10

