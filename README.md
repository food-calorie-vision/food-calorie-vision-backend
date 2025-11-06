# Food Calorie Vision - Backend API

FastAPI 기반 음식 칼로리 비전 백엔드 서비스

## 개요

이 백엔드는 프론트엔드 우선 접근 방식으로 개발되었으며, Next.js 프론트엔드의 API 계약에 맞춰 설계되었습니다.

## 주요 기능

- 🔐 **세션 기반 인증**: 안전한 사용자 로그인/로그아웃 관리
- 🏥 **사용자 건강 관리**: 건강 정보 및 섭취 현황 조회
- 🍽️ **식단 추천**: AI 기반 개인화된 식단 추천
- 📸 **음식 이미지 분석**: 비전 AI를 통한 음식 인식 및 영양 정보 분석
- 💬 **챗봇**: 음식 및 영양 관련 대화형 어시스턴트

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

### 3. 환경 변수 설정

`.env` 파일을 생성하고 데이터베이스 연결 정보를 입력하세요:

```bash
# Database (필수)
DATABASE_URL=mysql+asyncmy://user:password@host:port/database

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

**중요**: `.env` 파일은 Git에 커밋하지 마세요! (이미 `.gitignore`에 포함됨)

### 4. 데이터베이스 마이그레이션

데이터베이스 테이블을 생성합니다:

```bash
# 마이그레이션 실행 (테이블 생성)
python -m alembic upgrade head

# (선택) 마이그레이션 파일 생성 (모델 변경 시)
python -m alembic revision --autogenerate -m "설명"
```

생성되는 테이블:
- `users` - 사용자 정보
- `user_health_info` - 건강 정보
- `meal_records` - 식사 기록
- `daily_scores` - 일일 식단 점수
- `food_analyses` - 음식 이미지 분석 결과
- `chat_messages` - 챗봇 대화 기록
- `meal_recommendations` - 식단 추천

**참고**: `food_nutrients` 테이블은 다른 팀원이 관리하므로 자동 생성되지 않습니다.

### 5. 서버 실행

```bash
uvicorn app.main:app --reload --port 8000
```

서버가 실행되면 다음 URL에서 확인할 수 있습니다:
- API: http://localhost:8000
- Swagger 문서: http://localhost:8000/docs
- ReDoc 문서: http://localhost:8000/redoc

## API 엔드포인트

### 건강 체크
- `GET /healthz` - 기본 헬스 체크
- `GET /api/v1/health` - 상세 헬스 체크

### 인증 (세션 기반)
- `POST /api/v1/auth/login` - 로그인
- `POST /api/v1/auth/logout` - 로그아웃
- `GET /api/v1/auth/session` - 세션 정보 조회
- `GET /api/v1/auth/me` - 현재 사용자 정보

### 사용자
- `GET /api/v1/user/intake-data` - 사용자 섭취 현황 조회
- `GET /api/v1/user/health-info` - 사용자 건강 정보 조회

### 식단
- `GET /api/v1/meals/recommendations` - 식단 추천 조회
- `POST /api/v1/meals/selection` - 식단 선택

### 음식 이미지 분석
- `POST /api/v1/food/analysis` - 음식 이미지 분석

### 챗봇
- `POST /api/v1/chat` - 챗봇 메시지 처리

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
- [x] API 라우터 및 스키마 정의
- [x] 메모리 기반 스텁 핸들러
- [x] 세션 기반 인증 시스템
- [x] CORS 설정
- [x] 단위 테스트 (23개 테스트 모두 통과)
- [x] Next.js 프론트엔드와 통합
- [x] 데이터베이스 모델 정의 (SQLAlchemy)
- [x] 데이터베이스 마이그레이션 설정 (Alembic)
- [x] MySQL 비동기 연결 설정

### 진행 예정 🚧
- [ ] 데이터베이스 CRUD 서비스 구현
- [ ] 회원가입 및 비밀번호 해싱
- [ ] 실제 DB 데이터 사용 (현재는 스텁)
- [ ] Redis 세션 스토리지 (분산 환경용)
- [ ] 실제 AI 비전 모델 통합
- [ ] LLM 챗봇 통합 (OpenAI 등)
- [ ] 로깅 및 모니터링
- [ ] 통합 테스트
- [ ] Docker 컨테이너화

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
