# 환경 변수 설정 가이드

## 📋 .env 파일 생성

프로젝트 루트(`food-calorie-vision-backend/`)에 `.env` 파일을 생성하고 아래 내용을 복사하세요.

```env
# 애플리케이션 환경 설정
APP_ENV=local
API_PREFIX=/api
API_VERSION=v1
PORT=8000

# 데이터베이스 설정
DATABASE_URL=mysql+asyncmy://username:password@host:port/database_name

# CORS 설정 (쉼표로 구분)
CORS_ALLOW_ORIGINS=http://localhost:3000,http://localhost:3001

# 세션 설정
SESSION_SECRET_KEY=your-secret-key-here-change-in-production
SESSION_COOKIE_NAME=fcv_session
SESSION_MAX_AGE=3600
SESSION_HTTPS_ONLY=false
SESSION_SAME_SITE=lax

# Redis 설정 (선택사항 - 분산 세션 스토리지)
# REDIS_URL=redis://localhost:6379/0

# OpenAI API 설정 (GPT-Vision) ⭐ 필수!
OPENAI_API_KEY=your-openai-api-key-here

# YOLO 모델 경로
VISION_MODEL_PATH=yolo11n.pt
```

## 🔑 OpenAI API 키 발급 방법

1. **OpenAI 계정 생성**
   - https://platform.openai.com/ 접속
   - 계정 생성 또는 로그인

2. **API 키 생성**
   - https://platform.openai.com/api-keys 접속
   - "Create new secret key" 클릭
   - 키 이름 입력 (예: "food-calorie-vision")
   - 생성된 키 복사 (⚠️ 한 번만 표시됨!)

3. **`.env` 파일에 추가**
   ```env
   OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```

## ⚠️ 주의사항

- `.env` 파일은 **절대 Git에 커밋하지 마세요!**
- `.gitignore`에 `.env`가 포함되어 있는지 확인하세요.
- 프로덕션 환경에서는 환경 변수를 안전하게 관리하세요.

## ✅ 설정 확인

서버 실행 시 다음 로그가 출력되면 성공:

```
✅ YOLO 모델 로드 완료!
✅ OpenAI GPT-Vision 클라이언트 초기화 완료!
```

만약 다음 로그가 출력되면 API 키 확인:

```
⚠️ OPENAI_API_KEY가 설정되지 않았습니다.
```

