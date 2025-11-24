# 세션 기반 인증 가이드

## 개요

이 프로젝트는 **세션 기반 인증**을 사용합니다. JWT 대신 서버 측 세션을 사용하여 사용자 인증 상태를 관리합니다.

## 세션 vs JWT

### 세션 기반 인증 (현재 사용)
- ✅ 서버가 세션 상태를 직접 관리
- ✅ 즉시 세션 무효화 가능 (로그아웃)
- ✅ 클라이언트에 민감한 정보 저장 안 함
- ⚠️ 서버 메모리 사용 (Redis로 확장 가능)
- ⚠️ 수평 확장 시 세션 스토리지 필요

### JWT 기반 인증
- ✅ Stateless (서버 메모리 사용 없음)
- ✅ 수평 확장 용이
- ⚠️ 토큰 무효화 어려움
- ⚠️ 토큰에 정보 노출 가능

## 아키텍처

```
┌──────────────┐
│   클라이언트   │
│  (브라우저)    │
└──────┬───────┘
       │ 쿠키 (세션 ID)
       ▼
┌──────────────┐
│   FastAPI    │
│ SessionMiddleware │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ 세션 스토리지  │
│ (메모리/Redis)│
└──────────────┘
```

## 설정

### 환경 변수 (.env)

```bash
# 세션 시크릿 키 (최소 32자 권장)
session_secret_key=your-very-long-secret-key-min-32-chars

# 세션 쿠키 이름
session_cookie_name=fcv_session

# 세션 만료 시간 (초)
session_max_age=3600

# HTTPS 전용 (프로덕션에서 true)
session_https_only=false

# SameSite 설정 (lax, strict, none)
session_same_site=lax

# Redis (선택사항 - 분산 환경용)
# redis_url=redis://localhost:6379/0
```

### 미들웨어 설정

`app/main.py`에 SessionMiddleware가 자동으로 설정되어 있습니다:

```python
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret_key,
    session_cookie=settings.session_cookie_name,
    max_age=settings.session_max_age,
    same_site=settings.session_same_site,
    https_only=settings.session_https_only,
)
```

## API 사용법

### 1. 로그인

```bash
POST /api/v1/auth/login
Content-Type: application/json

{
  "user_id": "test_user",
  "password": "password123"
}
```

**응답:**
```json
{
  "success": true,
  "message": "로그인 성공",
  "user_id": "test_user"
}
```

**Set-Cookie 헤더로 세션 쿠키 전달**

### 2. 세션 정보 조회

```bash
GET /api/v1/auth/session
Cookie: fcv_session=...
```

**응답:**
```json
{
  "authenticated": true,
  "user_id": "test_user"
}
```

### 3. 현재 사용자 정보

```bash
GET /api/v1/auth/me
Cookie: fcv_session=...
```

**응답:**
```json
{
  "user_id": "test_user",
  "username": "test_user",
  "email": "test_user@example.com"
}
```

### 4. 로그아웃

```bash
POST /api/v1/auth/logout
Cookie: fcv_session=...
```

**응답:**
```json
{
  "success": true,
  "message": "로그아웃 성공"
}
```

## 개발자 가이드

### 세션 유틸리티 사용

```python
from fastapi import Request
from app.utils.session import (
    login_user,
    logout_user,
    is_authenticated,
    get_current_user_id,
    get_session_value,
    set_session_value,
)

@router.post("/some-endpoint")
async def some_endpoint(request: Request):
    # 인증 확인
    if not is_authenticated(request):
        raise HTTPException(status_code=401)
    
    # 사용자 ID 조회
    user_id = get_current_user_id(request)
    
    # 세션 값 설정
    set_session_value(request, "last_action", "some_action")
    
    # 세션 값 조회
    last_action = get_session_value(request, "last_action")
    
    return {"user_id": user_id}
```

### 인증 의존성 사용

#### 필수 인증

```python
from fastapi import Depends
from app.api.dependencies import require_authentication

@router.get("/protected")
async def protected_route(user_id: str = Depends(require_authentication)):
    """로그인한 사용자만 접근 가능"""
    return {"message": f"Hello {user_id}"}
```

#### 선택적 인증

```python
from fastapi import Depends
from app.api.dependencies import optional_authentication

@router.get("/public")
async def public_route(user_id: str | None = Depends(optional_authentication)):
    """누구나 접근 가능하지만, 로그인 시 개인화 가능"""
    if user_id:
        return {"message": f"Welcome back {user_id}"}
    return {"message": "Welcome guest"}
```

## 테스트

### pytest에서 세션 테스트

```python
from fastapi.testclient import TestClient

def test_login():
    client = TestClient(app)
    
    # 로그인
    response = client.post("/api/v1/auth/login", json={
        "user_id": "test_user",
        "password": "password123"
    })
    assert response.status_code == 200
    
    # 쿠키 자동 저장됨
    # 인증 필요한 엔드포인트 접근
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 200
    assert response.json()["user_id"] == "test_user"
```

## 프론트엔드 통합

### fetch API 사용 시

```typescript
// 로그인
const response = await fetch('http://localhost:8000/api/v1/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  credentials: 'include', // 쿠키 전송 필수!
  body: JSON.stringify({
    user_id: 'test_user',
    password: 'password123'
  })
});

// 이후 모든 요청에 credentials: 'include' 필요
const userResponse = await fetch('http://localhost:8000/api/v1/auth/me', {
  credentials: 'include'
});
```

### Next.js API 라우트에서

```typescript
// src/app/api/auth/login/route.ts
export async function POST(request: NextRequest) {
  const body = await request.json();
  const apiEndpoint = process.env.FASTAPI_URL || 'http://localhost:8000';
  
  const response = await fetch(`${apiEndpoint}/api/v1/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(body)
  });
  
  const data = await response.json();
  
  // 백엔드의 Set-Cookie 헤더를 프론트엔드로 전달
  const cookies = response.headers.get('set-cookie');
  const nextResponse = NextResponse.json(data);
  if (cookies) {
    nextResponse.headers.set('Set-Cookie', cookies);
  }
  
  return nextResponse;
}
```

## 프로덕션 배포

### 1. HTTPS 필수

```bash
session_https_only=true
```

### 2. 강력한 시크릿 키

```bash
# 랜덤 키 생성
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 3. Redis 사용 (다중 서버 환경)

```bash
redis_url=redis://your-redis-server:6379/0
```

추후 Redis 세션 스토어 구현 필요

### 4. SameSite 설정

```bash
# 크로스 도메인 시
session_same_site=none
session_https_only=true
```

## 하드코딩된 테스트 사용자

현재 개발 단계에서는 다음 사용자들이 하드코딩되어 있습니다:

| 사용자 ID | 비밀번호 |
|----------|---------|
| test_user | password123 |
| admin | admin123 |
| user1 | user123 |

**향후 DB 연동 시 제거 예정**

## 보안 고려사항

1. ✅ HTTPS 사용 (프로덕션)
2. ✅ 강력한 시크릿 키
3. ✅ 세션 만료 시간 설정
4. ✅ CSRF 보호 (SameSite 설정)
5. ⚠️ 세션 재생성 (로그인 후)
6. ⚠️ Rate limiting
7. ⚠️ 비밀번호 해싱 (bcrypt)

## 다음 단계

1. [ ] DB 연동 후 실제 사용자 인증
2. [ ] Redis 세션 스토어 구현
3. [ ] 비밀번호 해싱 (passlib)
4. [ ] 회원가입 기능
5. [ ] 비밀번호 재설정
6. [ ] 2FA (선택사항)

---

**참고 문서:**
- [Starlette Sessions](https://www.starlette.io/middleware/#sessionmiddleware)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)

