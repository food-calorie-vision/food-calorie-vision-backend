# Food Calorie Vision - Backend API

FastAPI 기반 음식 칼로리 비전 백엔드 서비스

> 📝 **최신 업데이트 (2024-11-19)**: 추천 식단 전용 테이블 추가 (DietPlan, DietPlanMeal)  
> 자세한 내용은 [migrations/README_DIET_PLAN_TABLES.md](./migrations/README_DIET_PLAN_TABLES.md)를 참고하세요.

## 개요

이 백엔드는 ERDCloud 설계 기반으로 재구성되었으며, **GPT-4o Vision 음식 분석**, **GPT-4o 식단 추천**, **식약처 영양 데이터**를 결합한 통합 헬스케어 시스템을 제공합니다.

## 주요 기능

- 🔐 **이메일 기반 인증**: 안전한 사용자 로그인/로그아웃 관리 (세션 기반)
- 👤 **사용자 관리**: ERDCloud 스키마 기반 사용자 정보 관리 (gender, age, weight, height, health_goal)
- 📸 **AI 음식 분석**: GPT-4o Vision 기반 이미지 분석
  - 음식명, 재료, 영양소 자동 인식
  - 4개 후보 제공 + 사용자 선택 기능
  - 식약처 DB 매칭으로 정확한 영양소 조회
- 🍽️ **음식 섭취 기록**: UserFoodHistory를 통한 식단 기록
- 🥗 **AI 식단 추천**: 사용자 맞춤형 식단 추천 시스템
  - Harris-Benedict 공식 기반 BMR/TDEE 계산
  - 건강 목표별 목표 칼로리 산출 (증량/유지/감량)
  - GPT-4o가 3가지 식단 옵션 제공
  - 전용 테이블(DietPlan, DietPlanMeal)로 체계적 관리
- 📊 **영양소 점수**: NRF9.3 기반 음식 건강 점수 계산
- 📈 **건강 리포트**: 일일/주간/월간 건강 리포트 생성

## 기술 스택

- **Framework**: FastAPI 0.115.4
- **Python**: 3.12+
- **Database**: MySQL + SQLAlchemy (비동기)
- **Migration**: Alembic
- **Testing**: pytest
- **Documentation**: OpenAPI/Swagger

## 설치 및 실행

### 1. 가상환경 생성 및 활성화

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

### 2. 의존성 설치

```bash
pip install -r requirements.txt
```

**주요 의존성:**
- `fastapi==0.115.4`: 웹 프레임워크
- `sqlalchemy[asyncio]==2.0.36`: ORM (비동기)
- `asyncmy==0.2.9`: MySQL 비동기 드라이버
- `pydantic[email]==2.9.2`: 데이터 검증 (이메일 포함)
- `email-validator==2.2.0`: 이메일 유효성 검사
- `passlib[bcrypt]==1.7.4`: 비밀번호 해싱
- `ultralytics==8.3.0`: YOLO11n 객체 detection
- `openai==1.54.3`: GPT-Vision 이미지 분석
- `langchain==0.3.4`: 대화형 에이전트 오케스트레이션
- `langchain-openai==0.2.2`: OpenAI ChatGPT 모델 연동
- `opencv-python==4.10.0.84`: 이미지 처리
- `torch==2.5.1`: PyTorch (YOLO 백엔드)

### 3. 환경 변수 설정

**⚠️ 중요: OpenAI API 키 설정 필수!**

`.env` 파일을 생성하고 다음 내용을 추가하세요:

```bash
# Database (필수)
DATABASE_URL=mysql+asyncmy://user:password@host:port/database

# OpenAI API 키 (GPT-Vision) ⭐ 필수!
OPENAI_API_KEY=sk-your-openai-api-key-here

# YOLO 모델 경로 (선택사항, 자동 다운로드됨)
VISION_MODEL_PATH=yolo11n.pt

# Application
APP_ENV=local
API_PREFIX=/api
API_VERSION=v1
PORT=8000

# CORS (프론트엔드 URL)
CORS_ALLOW_ORIGINS=http://localhost:3000

# Session (세션 기반 인증)
SESSION_SECRET_KEY=your-session-secret-key-min-32-chars
SESSION_COOKIE_NAME=fcv_session
SESSION_MAX_AGE=3600
SESSION_HTTPS_ONLY=false
SESSION_SAME_SITE=lax
```

**중요**: 
- `.env` 파일은 Git에 커밋하지 마세요! (이미 `.gitignore`에 포함됨)
- OpenAI API 키 발급: https://platform.openai.com/api-keys

📖 **자세한 설정 가이드:** [ENV_SETUP_GUIDE.md](./docs/ENV_SETUP_GUIDE.md)

### LangChain 기반 에이전트 사용 안내

- 현재 LangChain 에이전트는 **기존 `OPENAI_API_KEY` 하나만** 사용합니다.  
- 추가 키가 필요하지 않으며, 에이전트 구성/메모리 전략은 [docs/agents.md](./docs/agents.md)를 참고하세요.

### 4. 데이터베이스 마이그레이션 (ERDCloud 스키마)

⚠️ **중요**: 
- User 테이블을 포함한 대부분의 테이블이 재생성됩니다
- 기존 사용자 데이터는 손실됩니다
- `food_nutrients` 테이블은 유지됩니다

#### 4-1. ERDCloud 스키마 적용

**방법 1: MySQL Workbench 사용**
1. MySQL Workbench 실행
2. `erdcloud_schema_final.sql` 파일 열기
3. 전체 스크립트 실행

**방법 2: CLI 사용**

```bash
mysql -u root -p tempdb < erdcloud_schema_final.sql
```

**생성되는 테이블:**
- ✅ `User` - 사용자 정보 (user_id: BIGINT AUTO_INCREMENT)
- ✅ `Food` - 음식 기본 정보
- ✅ `UserFoodHistory` - 음식 섭취 기록
- ✅ `health_score` - 건강 점수
- ✅ `HealthReport` - 건강 리포트
- ✅ `UserPreferences` - 사용자 선호도
- ✅ `disease_allergy_profile` - 질병/알레르기 프로필

**유지되는 테이블:**
- ✅ `food_nutrients` - 절대 수정 금지 (기존 데이터 유지)

#### 4-2. 스키마 확인

```sql
-- User 테이블 AUTO_INCREMENT 확인
DESCRIBE `User`;

-- 생성된 테이블 확인
SHOW TABLES;
```

### 5. 서버 실행

```bash
python -m uvicorn app.main:app --reload --port 8000
```

**서버 시작 로그 확인:**
```
✅ YOLO 모델 로드 완료!
✅ OpenAI GPT-Vision 클라이언트 초기화 완료!
INFO:     Uvicorn running on http://127.0.0.1:8000
```

서버가 실행되면 다음 URL에서 확인할 수 있습니다:
- API: http://localhost:8000
- Swagger 문서: http://localhost:8000/docs
- ReDoc 문서: http://localhost:8000/redoc

---

## 🤖 AI 음식 분석 파이프라인

### 처리 흐름

```
사용자 이미지 업로드
    ↓
YOLO11n Detection (음식 객체 감지)
    ↓
GPT-Vision 분석 (YOLO 결과 + 이미지)
    ↓
상세 영양 정보 반환 (칼로리, 영양소, 건강 제안)
```

### 테스트 방법

**Swagger UI에서 테스트:**
1. http://localhost:8000/docs 접속
2. `POST /api/v1/food/analysis-upload` 찾기
3. "Try it out" → 이미지 파일 업로드 → "Execute"

**cURL로 테스트:**
```bash
curl -X POST "http://localhost:8000/api/v1/food/analysis-upload" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@pizza.jpg"
```

**응답 예시:**
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
        "채소를 추가하여 영양 균형을 맞추세요."
      ]
    },
    "timestamp": "2025-11-10T...",
    "processingTime": 3500
  },
  "message": "✅ 분석 완료: 페퍼로니 피자 (건강점수: 65점)"
}
```

📖 **자세한 설정 가이드:** [YOLO_GPT_VISION_SETUP.md](./docs/YOLO_GPT_VISION_SETUP.md)

---

## API 엔드포인트

### 건강 체크
- `GET /healthz` - 기본 헬스 체크
- `GET /api/v1/health` - 상세 헬스 체크

### 인증 (이메일 기반, 세션)
- `POST /api/v1/auth/signup` - 회원가입 (이메일, username, password)
- `POST /api/v1/auth/login` - 로그인 (이메일 기반)
- `POST /api/v1/auth/logout` - 로그아웃
- `GET /api/v1/auth/session` - 세션 정보 조회
- `GET /api/v1/auth/me` - 현재 사용자 정보 (닉네임, username 등)

### 사용자
- `GET /api/v1/user/info` - 사용자 기본 정보
- `GET /api/v1/user/health-info` - 사용자 건강 정보 (gender, age, weight, height, health_goal)
- `GET /api/v1/user/intake-data` - 사용자 섭취 데이터 (7일간)
- `PUT /api/v1/user/profile` - 사용자 프로필 수정

### 음식 이미지 분석 (GPT-4o Vision)
- `POST /api/v1/food/analyze` - 음식 이미지 분석 (4개 후보 반환)
- `POST /api/v1/food/reanalyze-with-selection` - 후보 선택 시 재분석
- `POST /api/v1/food/save-food` - 음식 섭취 기록 저장

### 재료 기반 레시피 추천
- `POST /api/v1/ingredients/analyze` - 재료 이미지 분석
- `POST /api/v1/ingredients/recommend-recipes` - 재료 기반 레시피 추천

### AI 식단 추천 (GPT-4o) ✨ NEW
- `POST /api/v1/recommend/diet-plan` - 사용자 맞춤 식단 추천 (3가지 옵션)
- `POST /api/v1/recommend/save-diet-plan` - 추천 식단 저장
- `GET /api/v1/recommend/my-diet-plans` - 내 추천 식단 목록 조회
- `GET /api/v1/recommend/diet-plans/{diet_plan_id}` - 식단 상세 조회

### 건강 리포트
- `GET /api/v1/health-report` - 건강 리포트 조회
- `POST /api/v1/health-score` - 건강 점수 계산 (NRF9.3)

## 테스트

```bash
# 모든 테스트 실행
pytest

# 상세 출력으로 테스트 실행
pytest -v

# 특정 테스트 파일 실행
pytest tests/unit/test_users.py

# 커버리지 포함 실행
pytest --cov=app tests/
```

## 프로젝트 구조

```
food-calorie-vision-backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── routes/          # API 라우트 핸들러
│   │       │   ├── users.py
│   │       │   ├── meals.py
│   │       │   ├── vision.py
│   │       │   └── chat.py
│   │       ├── schemas/         # Pydantic 스키마
│   │       │   ├── common.py
│   │       │   ├── users.py
│   │       │   ├── meals.py
│   │       │   ├── vision.py
│   │       │   └── chat.py
│   │       └── router.py        # 메인 라우터
│   ├── core/
│   │   └── config.py            # 설정 관리
│   ├── db/
│   │   ├── base.py              # SQLAlchemy Base
│   │   ├── models.py            # 데이터베이스 모델
│   │   ├── session.py           # DB 세션 관리
│   │   └── __init__.py
│   ├── services/                # 비즈니스 로직 (향후 구현)
│   └── main.py                  # FastAPI 앱 진입점
├── tests/
│   └── unit/                    # 단위 테스트
├── alembic/                     # 데이터베이스 마이그레이션
├── .env.example                 # 환경 변수 예제
├── requirements.txt             # Python 의존성
└── README.md
```

## 개발 현황

### 완료됨 ✅
- [x] 기본 프로젝트 구조
- [x] ERDCloud 기반 DB 스키마 적용
- [x] 세션 기반 인증 시스템 (이메일 로그인)
- [x] MySQL 비동기 연결 설정 (SQLAlchemy + asyncmy)
- [x] GPT-4o Vision 음식 이미지 분석
  - [x] 4개 후보 제공 + 사용자 선택 기능
  - [x] 식약처 DB 매칭으로 영양소 조회
  - [x] 재료 추출 및 저장
- [x] GPT-4o 기반 재료 레시피 추천
- [x] GPT-4o 기반 AI 식단 추천 시스템
  - [x] Harris-Benedict 공식 BMR/TDEE 계산
  - [x] 건강 목표별 목표 칼로리 산출
  - [x] 3가지 식단 옵션 제공
  - [x] 추천 식단 전용 테이블 (DietPlan, DietPlanMeal)
  - [x] 식단 저장 및 조회 API
- [x] 음식 섭취 기록 저장 (UserFoodHistory)
- [x] 사용자 건강 정보 조회 (gender, age, weight, height, health_goal)
- [x] CORS 설정 (Next.js 프론트엔드 통합)
- [x] Swagger/ReDoc API 문서화

### 진행 예정 🚧
- [ ] NRF9.3 영양 점수 시스템 완성
- [ ] 건강 리포트 생성 (일일/주간/월간)
- [ ] 식단 진행률 추적 (섭취 여부 업데이트)
- [ ] 대시보드 통계 API
- [ ] Redis 세션 스토리지 (분산 환경용)
- [ ] 로깅 및 모니터링
- [ ] Docker 컨테이너화
- [ ] 통합 테스트

## 개발 가이드

### 프론트엔드 우선 원칙

이 백엔드는 프론트엔드 우선 접근 방식을 따릅니다:
1. 프론트엔드 타입 (`frontend/src/types/index.ts`)에 맞춰 Pydantic 스키마 정의
2. API 응답 형식은 프론트엔드 기대에 정확히 일치
3. 변경 사항은 가급적 추가적(additive)으로 진행
4. 파괴적 변경 시 프론트엔드와 조율 필수

### API 응답 형식

일부 엔드포인트는 `ApiResponse` 래퍼를 사용:
```python
{
  "success": bool,
  "data": T,
  "error": str | None
}
```

일부는 직접 데이터 반환:
- `/user/intake-data`
- `/user/health-info`

### 코드 스타일

```bash
# 코드 포맷팅
black app/ tests/

# Import 정렬
isort app/ tests/

# 린팅
ruff check app/ tests/
```

## 문제 해결

### CORS 오류
`.env` 파일에서 `CORS_ALLOW_ORIGINS`를 확인하세요.

### 데이터베이스 연결 오류
1. `.env` 파일의 `DATABASE_URL`이 올바른지 확인
2. MySQL 서버가 실행 중인지 확인
3. 데이터베이스와 사용자 권한 확인

### 마이그레이션 오류
```bash
# 마이그레이션 히스토리 확인
python -m alembic current

# 마이그레이션 되돌리기
python -m alembic downgrade -1
```

### 포트 충돌
다른 포트로 실행: `uvicorn app.main:app --port 8001`

### 모듈 import 오류
가상환경이 활성화되었는지 확인하세요.

### asyncmy 설치 오류 (Windows)
asyncmy가 설치되지 않으면 대신 aiomysql 사용:
```bash
pip install aiomysql
# config.py의 database_url을 mysql+aiomysql://로 변경
```

## 기여

1. 이슈 생성
2. 브랜치 생성
3. 변경 사항 커밋
4. 테스트 작성 및 실행
5. Pull Request 제출

## 라이센스

MIT License
