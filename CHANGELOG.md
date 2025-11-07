# 변경 이력 (Changelog)

## 2025-11-07 - ERDCloud 스키마 전환 및 이메일 기반 인증

### 🎯 주요 변경사항

#### 1. 데이터베이스 스키마 완전 재구성
- **ERDCloud 스키마 적용**: 기존 스키마를 ERDCloud 설계 기반으로 완전 교체
- **User 테이블 재설계**:
  - `user_id`: `VARCHAR(50)` → `BIGINT AUTO_INCREMENT`
  - `gender`: `ENUM('M', 'F', 'Other')` → `ENUM('M', 'F')`
  - `email`, `username`에 UNIQUE 제약조건 추가
  - `created_at`, `updated_at` 자동 타임스탬프 설정

#### 2. 인증 시스템 개선
- **이메일 기반 로그인**: `user_id` 로그인 → `email` 로그인
- **회원가입 간소화**: 
  - `user_id` 자동 생성 (BIGINT AUTO_INCREMENT)
  - 건강 정보 입력 간소화 (기본 정보만)
  - 닉네임 선택 사항으로 변경

#### 3. 새로운 ERDCloud 테이블
- ✅ `User`: 사용자 기본 정보
- ✅ `Food`: 음식 기본 정보
- ✅ `UserFoodHistory`: 음식 섭취 기록
- ✅ `health_score`: 음식 건강 점수
- ✅ `HealthReport`: 건강 리포트
- ✅ `UserPreferences`: 사용자 선호도
- ✅ `disease_allergy_profile`: 질병/알레르기 프로필

#### 4. 삭제된 테이블
- ❌ `UserHealthInfo` (→ `HealthReport`, `UserPreferences`, `disease_allergy_profile`로 대체)
- ❌ `MealRecord` (→ `UserFoodHistory`로 대체)
- ❌ `DailyScore` (→ `health_score`로 대체)
- ❌ `FoodAnalysis` (→ `UserFoodHistory`로 통합)
- ❌ `ChatMessage` (기능 제거)
- ❌ `MealRecommendation` (기능 제거)

---

### 📦 백엔드 변경사항

#### 의존성 추가
```txt
pydantic[email]==2.9.2
email-validator==2.2.0
asyncmy==0.2.9  # aiomysql 대체
```

#### 수정된 파일

**인증 관련:**
- `app/services/auth_service.py`: 이메일 기반 인증, user_id 자동생성
- `app/utils/session.py`: user_id 타입 변경 (str → int)
- `app/api/v1/schemas/auth.py`: SignupRequest, LoginRequest 스키마 변경
- `app/api/v1/routes/auth.py`: 회원가입/로그인 로직 변경

**데이터베이스:**
- `app/db/models.py`: ERDCloud 스키마 기반 모델 재정의
- `app/db/__init__.py`: 새 모델 export
- `alembic/env.py`: User 테이블만 관리, ERDCloud 테이블 제외

**서비스:**
- ✅ `app/services/food_history_service.py`: 신규 생성
- ✅ `app/services/health_score_service.py`: 신규 생성
- ✅ `app/services/health_report_service.py`: 신규 생성
- ❌ `app/services/health_service.py`: 삭제
- ❌ `app/services/meal_service.py`: 삭제
- ❌ `app/services/score_service.py`: 삭제
- ❌ `app/services/chat_service.py`: 삭제
- ❌ `app/services/recommendation_service.py`: 삭제

**라우트:**
- `app/api/v1/router.py`: auth, users, vision만 포함
- ❌ 6개 라우트 파일 삭제 (health_info, health, meal_records, meals, scores, chat)

**SQL 스크립트:**
- `erdcloud_schema_final.sql`: 완전히 재작성 (AUTO_INCREMENT, PRIMARY KEY, INDEX 포함)

---

### 🎨 프론트엔드 변경사항

#### 회원가입/로그인
- `src/app/signup/page.tsx`: 
  - user_id 입력 제거 (자동생성)
  - 이메일 필수 입력
  - 간소화된 폼 (기본 정보만)
  
- `src/app/page.tsx`:
  - 이메일 기반 로그인
  - 로그인 후 사용자 정보 가져오기 (닉네임 확인)
  - sessionStorage 완전 정리

#### UI 개선
- `src/components/MyScore.tsx`:
  - health_goal 한글 표시 ('gain' → '벌크업', 'maintain' → '유지', 'loss' → '다이어트')
  
- `src/components/MobileHeader.tsx`:
  - 사용자 이름 표시 (닉네임 우선, 없으면 username)
  - `hideAuthButtons` 옵션 추가
  
- `src/app/dashboard/page.tsx`:
  - 닉네임 또는 username 표시
  - 로그아웃 시 sessionStorage 완전 정리

#### 유틸리티
- ✅ `src/utils/healthGoalTranslator.ts`: 신규 생성 (health_goal 한글 변환)

---

### 🗄️ 데이터베이스 마이그레이션

#### 실행 순서

1. **기존 테이블 백업** (선택사항)
```sql
-- 필요시 데이터 백업
```

2. **ERDCloud 스키마 적용**
```bash
# MySQL Workbench 또는 CLI에서 실행
mysql -u root -p tempdb < erdcloud_schema_final.sql
```

3. **확인**
```sql
-- User 테이블 AUTO_INCREMENT 확인
DESCRIBE `User`;

-- 생성된 테이블 확인
SHOW TABLES;
```

---

### ⚠️ 주의사항

1. **User 테이블 재생성**
   - 기존 User 테이블이 완전히 재생성됩니다
   - 기존 사용자 데이터는 손실됩니다
   - 필요시 마이그레이션 스크립트 작성 필요

2. **food_nutrients 테이블**
   - 절대 수정하지 않습니다
   - 기존 데이터 유지

3. **호환성**
   - `user_id`: BIGINT (프론트엔드에서 number로 처리)
   - `food_id`: VARCHAR(200) (food_nutrients와 호환)

---

### 🧪 테스트 항목

- [x] 이메일 기반 회원가입
- [x] 이메일 기반 로그인
- [x] 로그아웃 (sessionStorage 정리)
- [x] 닉네임/username 표시
- [x] health_goal 한글 표시
- [x] User 테이블 AUTO_INCREMENT
- [x] 메인 페이지 로그인/회원가입 버튼 숨김

---

### 📝 다음 단계

1. **새로운 API 개발**
   - UserFoodHistory API 라우트
   - health_score API 라우트
   - HealthReport API 라우트
   - UserPreferences API 라우트
   - DiseaseAllergyProfile API 라우트

2. **프론트엔드 연동**
   - 대시보드에서 새 API 사용
   - 음식 섭취 기록 기능
   - 건강 점수 계산 및 표시
   - 리포트 생성 및 조회

3. **데이터 마이그레이션**
   - 기존 사용자 데이터 마이그레이션 스크립트 (필요시)

---

### 🔗 관련 파일

- `erdcloud_schema_final.sql`: 최종 DB 스키마
- `SCHEMA_CHANGES.md`: 상세 스키마 변경사항
- `ERDCloud_Migration_Guide.md`: 마이그레이션 가이드
- `requirements.txt`: 업데이트된 의존성

