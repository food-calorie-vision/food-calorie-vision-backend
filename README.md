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
- **Database**: MySQL (준비 중)
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

`.env.example` 파일을 참고하여 `.env` 파일을 생성하세요:

```bash
# Application
app_env=local
api_prefix=/api
api_version=v1
port=8000

# CORS (프론트엔드 URL)
cors_allow_origins=http://localhost:3000

# Session (세션 기반 인증)
session_secret_key=your-session-secret-key-min-32-chars
session_cookie_name=fcv_session
session_max_age=3600
session_https_only=false
session_same_site=lax
```

### 4. 서버 실행

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
│   ├── db/                      # 데이터베이스 (향후 구현)
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

### 진행 예정 🚧
- [ ] 데이터베이스 연동 (MySQL)
- [ ] 회원가입 및 비밀번호 해싱
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
`.env` 파일에서 `cors_allow_origins`를 확인하세요.

### 포트 충돌
다른 포트로 실행: `uvicorn app.main:app --port 8001`

### 모듈 import 오류
가상환경이 활성화되었는지 확인하세요.

## 기여

1. 이슈 생성
2. 브랜치 생성
3. 변경 사항 커밋
4. 테스트 작성 및 실행
5. Pull Request 제출

## 라이센스

MIT License
