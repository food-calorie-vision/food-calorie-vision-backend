# 프론트엔드-백엔드 통합 가이드

이 문서는 `food-calorie-vision-frontend`와 `food-calorie-vision-backend`의 통합을 설명합니다.

## 아키텍처 개요

```
┌─────────────────┐
│   Next.js 앱    │
│  (포트 3000)    │
└────────┬────────┘
         │
         │ Next.js API 라우트 (/api/*)
         │ (프록시 역할)
         ▼
┌─────────────────┐
│  FastAPI 백엔드  │
│  (포트 8000)    │
│   /api/v1/*     │
└─────────────────┘
```

## 실행 순서

### 1. 백엔드 실행

```bash
cd food-calorie-vision-backend

# 가상환경 생성 (최초 1회)
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# 의존성 설치
pip install -r requirements.txt

# .env 파일 생성
# .env.example을 참고하여 작성
# 필수: cors_allow_origins=http://localhost:3000

# 서버 실행
uvicorn app.main:app --reload --port 8000
```

백엔드가 http://localhost:8000 에서 실행됩니다.
- Swagger: http://localhost:8000/docs

### 2. 프론트엔드 실행

```bash
cd food-calorie-vision-frontend

# 의존성 설치 (최초 1회)
npm install

# .env.local 파일 생성
echo "FASTAPI_URL=http://localhost:8000" > .env.local

# 개발 서버 실행
npm run dev
```

프론트엔드가 http://localhost:3000 에서 실행됩니다.

## API 매핑

### Next.js API 라우트 → FastAPI 엔드포인트

| 프론트엔드 경로 | FastAPI 경로 | 메서드 | 설명 |
|----------------|--------------|--------|------|
| `/api/intake-data` | `/api/v1/user/intake-data` | GET | 섭취 현황 조회 |
| `/api/health-info` | `/api/v1/user/health-info` | GET | 건강 정보 조회 |
| `/api/meal-recommendations` | `/api/v1/meals/recommendations` | GET | 식단 추천 조회 |
| `/api/meal-recommendations` | `/api/v1/meals/selection` | POST | 식단 선택 |
| `/api/food-analysis` | `/api/v1/food/analysis` | POST | 음식 이미지 분석 |
| `/api/chat` | `/api/v1/chat` | POST | 챗봇 메시지 |

## 데이터 타입 매핑

프론트엔드 타입(`src/types/index.ts`)과 백엔드 스키마가 정확히 일치합니다.

### UserIntakeData
```typescript
// Frontend (TypeScript)
{
  totalCalories: number;
  targetCalories: number;
  nutrients: {
    sodium: number;
    carbs: number;
    protein: number;
    fat: number;
    sugar: number;
  };
}
```

```python
# Backend (Pydantic)
{
  "totalCalories": int,
  "targetCalories": int,
  "nutrients": {
    "sodium": int,
    "carbs": int,
    "protein": int,
    "fat": int,
    "sugar": int
  }
}
```

### ApiResponse<T> 래핑

일부 엔드포인트는 응답을 래핑합니다:

```typescript
{
  success: boolean;
  data?: T;
  error?: string;
}
```

**래핑되는 엔드포인트:**
- `/meals/recommendations`
- `/meals/selection`
- `/food/analysis`
- `/chat`

**래핑되지 않는 엔드포인트:**
- `/user/intake-data`
- `/user/health-info`

## 프록시 설정

Next.js API 라우트는 단순 프록시로 동작합니다:

```typescript
// src/app/api/intake-data/route.ts
export async function GET() {
  const apiEndpoint = process.env.FASTAPI_URL || 'http://localhost:8000';
  
  const response = await fetch(`${apiEndpoint}/api/v1/user/intake-data`, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
    cache: 'no-store',
  });

  const data = await response.json();
  return NextResponse.json(data);
}
```

## CORS 설정

백엔드 `.env` 파일:
```bash
cors_allow_origins=http://localhost:3000
```

FastAPI는 자동으로 CORS 헤더를 설정합니다.

## 디버깅

### 백엔드 로그 확인
```bash
# 백엔드 터미널에서 로그 확인
# FastAPI는 자동으로 모든 요청을 로그로 출력
```

### 프론트엔드 네트워크 요청 확인
```bash
# 브라우저 개발자 도구 > Network 탭
# /api/* 요청 확인
```

### API 직접 테스트
```bash
# curl 사용
curl http://localhost:8000/api/v1/user/intake-data

# Swagger UI 사용
# http://localhost:8000/docs
```

## 일반적인 오류

### 1. CORS 오류
**증상**: `Access-Control-Allow-Origin` 오류

**해결**:
- 백엔드 `.env`에 `cors_allow_origins=http://localhost:3000` 추가
- 백엔드 재시작

### 2. 연결 거부
**증상**: `ECONNREFUSED` 오류

**해결**:
- 백엔드가 실행 중인지 확인
- 포트 8000이 사용 중인지 확인

### 3. 타입 불일치
**증상**: 프론트엔드에서 undefined 속성 접근

**해결**:
- 백엔드 Pydantic 스키마가 프론트엔드 타입과 일치하는지 확인
- `Field(alias=...)` 설정 확인

## 현재 스텁 데이터

현재 백엔드는 메모리 기반 스텁 데이터를 반환합니다:

- **사용자 섭취 현황**: 하드코딩된 1850/2000 칼로리
- **건강 정보**: 고혈압, 고지혈증 샘플 데이터
- **식단 추천**: 연어 덮밥, 제육볶음, 고등어 구이 3가지
- **음식 분석**: 파일명 기반 규칙 기반 분석
- **챗봇**: 키워드 기반 간단한 응답

## 다음 단계

1. **데이터베이스 연동**: MySQL 연결 및 실제 데이터 저장
2. **인증**: JWT 기반 사용자 인증
3. **AI 통합**: 실제 비전 모델 및 LLM 연결
4. **배포**: Docker 컨테이너화 및 클라우드 배포

## 참고 자료

- [FastAPI 문서](https://fastapi.tiangolo.com/)
- [Next.js API Routes](https://nextjs.org/docs/api-routes/introduction)
- [Pydantic 문서](https://docs.pydantic.dev/)

