<div align="center">

# 🌿 K-Calculator Backend

### ⚙️ AI 기반 건강 관리 시스템의 심장부

<img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=12,15,18,21,24&height=200&section=header&text=Backend%20API&fontSize=70&fontAlignY=35&animation=twinkling&fontColor=fff" />

[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.4-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![MySQL](https://img.shields.io/badge/MySQL-8.0+-4479A1?style=for-the-badge&logo=mysql&logoColor=white)](https://www.mysql.com/)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o-412991?style=for-the-badge&logo=openai&logoColor=white)](https://openai.com/)

<br/>

**🤖 GPT-4o Vision으로 음식 자동 인식**  
**📊 과학적 계산으로 맞춤 식단 추천**  
**🔒 안전한 세션 기반 인증**

[🚀 빠른 시작](#-빠른-시작) • [📡 API 문서](#-api-엔드포인트) • [🛠 기술 스택](#-기술-스택) • [🔧 설정 가이드](#-환경-설정)

</div>

---

<br/>

## 🌟 프로젝트 소개

> *"사진 한 장으로 영양 분석부터 식단 추천까지!"*

**K-Calculator Backend**는 **FastAPI** 기반의 고성능 헬스케어 API 서버입니다.  
GPT-4o Vision AI와 식약처 공식 데이터를 결합하여 정확하고 신뢰할 수 있는 건강 관리 서비스를 제공합니다.

<div align="center">

### 🎯 핵심 특징

```
🤖 AI 분석 → 📊 영양 데이터 → 🎯 맞춤 추천 → 📈 건강 관리
```

</div>

<br/>

---

<br/>

## ✨ 주요 기능

<div align="center">

<table align="center">
<tr>
<td width="50%" align="center">

### 🤖 AI 음식 분석
<img src="https://img.icons8.com/color/96/000000/artificial-intelligence.png" width="60"/>

**YOLO11-large + Roboflow + GPT-4o Vision**

음식 사진 업로드 → YOLO11-large / Roboflow로 음식·식재료 탐지 →  
GPT-4o Vision이 후보 분석 및 4가지 후보 제시 →  
식약처 DB 매칭으로 정확한 영양소 제공

```python
POST /api/v1/food/analysis-upload
→ 칼로리, 단백질, 탄수화물, 지방 등
```

</td>
<td width="50%" align="center">

### 🥗 맞춤 식단 추천
<img src="https://img.icons8.com/color/96/000000/healthy-food-calories-calculator.png" width="60"/>

**Harris-Benedict 공식 기반**

개인 정보 입력 → BMR/TDEE 자동 계산 →  
건강 목표 설정 → GPT가 3가지 식단 제안 →  
영양소 균형 맞춤

```python
POST /api/v1/recommend/diet-plan
→ 아침/점심/저녁/간식 구성
```

</td>
</tr>
<tr>
<td width="50%" align="center">

### 🔒 안전한 인증
<img src="https://img.icons8.com/color/96/000000/security-checked.png" width="60"/>

**세션 기반 + 비밀번호 암호화**

이메일 로그인 → 세션 쿠키 발급 →  
bcrypt 해싱 → 안전한 인증 유지

```python
POST /api/v1/auth/login
→ 세션 기반 인증 (쿠키)
```

</td>
<td width="50%" align="center">

### 📊 건강 리포트
<img src="https://img.icons8.com/color/96/000000/combo-chart.png" width="60"/>

**NRF9.3 기반 건강 점수**

식단 기록 → 영양소 분석 →  
건강 점수 계산 → 개선 제안 제공

```python
GET /api/v1/health-report
→ 일일/주간/월간 리포트
```

</td>
</tr>
</table>

</div>

<br/>

---

<br/>

## 🛠 기술 스택

<div align="center">

### Core Framework

<img src="https://img.shields.io/badge/FastAPI-0.115.4-009688?style=for-the-badge&logo=fastapi&logoColor=white"/>
<img src="https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white"/>
<img src="https://img.shields.io/badge/Pydantic-2.9.2-E92063?style=for-the-badge&logo=pydantic&logoColor=white"/>
<img src="https://img.shields.io/badge/Uvicorn-ASGI-499848?style=for-the-badge&logo=gunicorn&logoColor=white"/>

### Database & ORM

<img src="https://img.shields.io/badge/MySQL-8.0+-4479A1?style=for-the-badge&logo=mysql&logoColor=white"/>
<img src="https://img.shields.io/badge/SQLAlchemy-2.0.36-D71F00?style=for-the-badge&logo=sqlalchemy&logoColor=white"/>
<img src="https://img.shields.io/badge/Alembic-Migration-6BA81E?style=for-the-badge&logo=alembic&logoColor=white"/>
<img src="https://img.shields.io/badge/AsyncMy-0.2.9-00758F?style=for-the-badge&logo=mysql&logoColor=white"/>

### AI & Machine Learning

<img src="https://img.shields.io/badge/OpenAI-GPT--4o-412991?style=for-the-badge&logo=openai&logoColor=white"/>
<img src="https://img.shields.io/badge/YOLO-11_large-00FFFF?style=for-the-badge&logo=yolo&logoColor=black"/>
<img src="https://img.shields.io/badge/LangChain-0.3.4-1C3C3C?style=for-the-badge&logo=chainlink&logoColor=white"/>
<img src="https://img.shields.io/badge/PyTorch-2.5.1-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white"/>
<img src="https://img.shields.io/badge/OpenCV-4.10.0-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white"/>

### Security & Auth

<img src="https://img.shields.io/badge/Passlib-bcrypt-2B7489?style=for-the-badge&logo=lock&logoColor=white"/>
<img src="https://img.shields.io/badge/Email_Validator-2.2.0-EA4335?style=for-the-badge&logo=gmail&logoColor=white"/>
<img src="https://img.shields.io/badge/Session-Cookie_Based-4CAF50?style=for-the-badge&logo=session&logoColor=white"/>

### Testing & Documentation

<img src="https://img.shields.io/badge/pytest-Testing-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white"/>
<img src="https://img.shields.io/badge/Swagger-API_Docs-85EA2D?style=for-the-badge&logo=swagger&logoColor=black"/>
<img src="https://img.shields.io/badge/ReDoc-API_Docs-8CA1AF?style=for-the-badge&logo=redoc&logoColor=white"/>

</div>

<br/>

---

<br/>

## 🚀 빠른 시작

<div align="center">

### 📦 5분만에 시작하기!

</div>

```bash
# 1️⃣ 저장소 클론
git clone https://github.com/food-calorie-vision/food-calorie-vision-backend.git
cd food-calorie-vision-backend

# 2️⃣ 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3️⃣ 패키지 설치
pip install -r requirements.txt

# 4️⃣ 환경 변수 설정
cp .env.example .env
# .env 파일 편집 (DATABASE_URL, OPENAI_API_KEY 설정)

# 5️⃣ 데이터베이스 마이그레이션
mysql -u root -p tempdb < erdcloud_schema_final.sql

# 6️⃣ 서버 실행
python -m uvicorn app.main:app --reload --port 8000

# 7️⃣ API 문서 확인
# 🌐 http://localhost:8000/docs (Swagger UI)
# 📚 http://localhost:8000/redoc (ReDoc)
```

<div align="center">

### 🎉 서버가 정상적으로 실행되었습니다!

```
✅ YOLO 모델 로드 완료!
✅ OpenAI GPT-Vision 클라이언트 초기화 완료!
INFO: Uvicorn running on http://127.0.0.1:8000
```

</div>

<br/>

---

<br/>

## 🔧 환경 설정

### 📝 필수 환경 변수

`.env` 파일을 생성하고 다음 내용을 입력하세요:

```bash
# 🗄️ Database (필수)
DATABASE_URL=mysql+asyncmy://user:password@localhost:3306/your_database

# 🤖 OpenAI API (필수 ⭐)
OPENAI_API_KEY=sk-your-openai-api-key-here

# 🎯 YOLO 모델 (선택사항)
VISION_MODEL_PATH=yolo11l.pt  # 현재는 YOLOv11-large 가중치 사용

# ⚙️ Application
APP_ENV=local
API_PREFIX=/api
API_VERSION=v1
PORT=8000

# 🌐 CORS (프론트엔드 URL)
CORS_ALLOW_ORIGINS=http://localhost:3000

# 🔐 Session (세션 기반 인증)
SESSION_SECRET_KEY=your-super-secret-key-minimum-32-characters
SESSION_COOKIE_NAME=kcalc_session
SESSION_MAX_AGE=3600
SESSION_HTTPS_ONLY=false
SESSION_SAME_SITE=lax
```

<div align="center">

### ⚠️ 중요 사항

| 항목 | 설명 |
|:---:|:---|
| 🔑 **OPENAI_API_KEY** | [OpenAI 플랫폼](https://platform.openai.com/api-keys)에서 발급 |
| 🗄️ **DATABASE_URL** | MySQL 데이터베이스 연결 정보 |
| 🔒 **.env 파일** | **절대 Git에 커밋하지 마세요!** |

</div>

<br/>

---

<br/>

## 📡 API 엔드포인트

<div align="center">

### 🗂️ API 구조

</div>

<details>
<summary><b>🔐 인증 (Authentication)</b></summary>

<br/>

| Method | Endpoint | 설명 |
|:---:|:---|:---|
| `POST` | `/api/v1/auth/signup` | 회원가입 (이메일, username, password) |
| `POST` | `/api/v1/auth/login` | 로그인 (세션 쿠키 발급) |
| `POST` | `/api/v1/auth/logout` | 로그아웃 (세션 삭제) |
| `GET` | `/api/v1/auth/session` | 세션 정보 조회 |
| `GET` | `/api/v1/auth/me` | 현재 사용자 정보 |

**예시:**
```bash
# 회원가입
curl -X POST http://localhost:8000/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "username": "홍길동",
    "password": "secure123!@#"
  }'
```

</details>

<details>
<summary><b>👤 사용자 (User)</b></summary>

<br/>

| Method | Endpoint | 설명 |
|:---:|:---|:---|
| `GET` | `/api/v1/user/info` | 사용자 기본 정보 |
| `GET` | `/api/v1/user/health-info` | 건강 정보 (나이, 체중, 키, 목표) |
| `GET` | `/api/v1/user/intake-data` | 7일간 섭취 데이터 |
| `PUT` | `/api/v1/user/profile` | 프로필 수정 |

</details>

<details>
<summary><b>📸 AI 음식 분석 (Vision)</b></summary>

<br/>

| Method | Endpoint | 설명 |
|:---:|:---|:---|
| `POST` | `/api/v1/food/analysis-upload` | 음식 사진 분석 (4개 후보 반환) |
| `POST` | `/api/v1/food/reanalyze-with-selection` | 선택한 후보 재분석 |
| `POST` | `/api/v1/food/save-food` | 음식 섭취 기록 저장 |

**파이프라인:**
```
📸 이미지 업로드
    ↓
🎯 YOLO11-large / Roboflow 재료 탐지
    ↓
🤖 GPT-4o Vision 분석
    ↓
🗄️ 식약처 DB 매칭
    ↓
📊 영양 정보 반환
```

**응답 예시:**
```json
{
  "success": true,
  "data": {
    "foodName": "닭가슴살 샐러드",
    "calories": 250,
    "nutrients": {
      "protein": 35.0,
      "carbs": 15.0,
      "fat": 8.0,
      "fiber": 5.0
    },
    "healthScore": 85,
    "suggestions": [
      "단백질이 풍부한 건강한 식사입니다!",
      "식이섬유가 충분히 포함되어 있어요."
    ]
  }
}
```

</details>

<details>
<summary><b>🥗 AI 식단 추천 (Recommendation)</b></summary>

<br/>

| Method | Endpoint | 설명 |
|:---:|:---|:---|
| `POST` | `/api/v1/recommend/diet-plan` | 맞춤 식단 추천 (3가지 옵션) |
| `POST` | `/api/v1/recommend/save-diet-plan` | 선택한 식단 저장 |
| `GET` | `/api/v1/recommend/my-diet-plans` | 내 식단 목록 |
| `GET` | `/api/v1/recommend/diet-plans/{id}` | 식단 상세 조회 |

**추천 프로세스:**
```
👤 사용자 정보 입력
    ↓
🧮 Harris-Benedict 공식
    ↓
📊 BMR/TDEE 계산
    ↓
🎯 목표 칼로리 산출
    ↓
🤖 GPT-4o 식단 생성
    ↓
🍽️ 3가지 옵션 제공
```

</details>

<details>
<summary><b>🥕 재료 기반 레시피 (Ingredients)</b></summary>

<br/>

| Method | Endpoint | 설명 |
|:---:|:---|:---|
| `POST` | `/api/v1/ingredients/analyze` | 재료 사진 분석 |
| `POST` | `/api/v1/ingredients/recommend-recipes` | 레시피 추천 |

</details>

<details>
<summary><b>📊 건강 리포트 (Health)</b></summary>

<br/>

| Method | Endpoint | 설명 |
|:---:|:---|:---|
| `GET` | `/api/v1/health-report` | 건강 리포트 조회 |
| `POST` | `/api/v1/health-score` | NRF9.3 건강 점수 계산 |
| `GET` | `/api/v1/meals/dashboard-stats` | 대시보드 통계 |
| `GET` | `/api/v1/meals/score-detail` | 점수 상세 분석 |

</details>

<details>
<summary><b>💬 고객 센터 (Customer Service)</b></summary>

<br/>

| Method | Endpoint | 설명 |
|:---:|:---|:---|
| `GET` | `/api/v1/announcements` | 공지사항 목록 |
| `POST` | `/api/v1/inquiries` | 문의하기 |
| `GET` | `/api/v1/inquiries` | 내 문의 내역 |

</details>

<br/>

<div align="center">

### 📚 자동 생성 API 문서

| 도구 | URL | 설명 |
|:---:|:---|:---|
| 📖 **Swagger UI** | http://localhost:8000/docs | 대화형 API 테스트 |
| 📘 **ReDoc** | http://localhost:8000/redoc | 깔끔한 문서 형식 |

</div>

<br/>

---

<br/>

## 📂 프로젝트 구조

```
🌳 food-calorie-vision-backend/
│
├── 📁 app/                          # 애플리케이션 루트
│   ├── 📄 main.py                  # FastAPI 앱 진입점
│   │
│   ├── 📁 api/                      # API 라우터
│   │   └── 📁 v1/
│   │       ├── 📁 routes/          # 엔드포인트 핸들러
│   │       │   ├── 🔐 auth.py     # 인증
│   │       │   ├── 👤 users.py    # 사용자
│   │       │   ├── 📸 vision.py   # AI 음식 분석
│   │       │   ├── 🥗 recommend.py # 식단 추천
│   │       │   ├── 🥕 ingredients.py # 재료 레시피
│   │       │   ├── 📊 meals.py    # 식사 기록
│   │       │   ├── 💬 chat.py     # 챗봇
│   │       │   └── 📧 customer_service.py
│   │       │
│   │       ├── 📁 schemas/         # Pydantic 스키마
│   │       │   ├── 📝 common.py
│   │       │   ├── 🔐 auth.py
│   │       │   ├── 👤 users.py
│   │       │   ├── 📸 vision.py
│   │       │   ├── 🥗 recipe.py
│   │       │   └── 📊 meal.py
│   │       │
│   │       └── 📄 router.py        # 메인 라우터
│   │
│   ├── 📁 core/                     # 핵심 설정
│   │   └── ⚙️ config.py
│   │
│   ├── 📁 db/                       # 데이터베이스
│   │   ├── 🗄️ base.py
│   │   ├── 📊 models.py            # SQLAlchemy 모델
│   │   ├── 🔗 session.py           # DB 세션
│   │   ├── 📋 models_food_nutrients.py
│   │   └── 🍽️ models_user_contributed.py
│   │
│   ├── 📁 services/                 # 비즈니스 로직
│   │   ├── 🔐 auth_service.py
│   │   ├── 📸 vision_service.py
│   │   ├── 🥗 recipe_recommendation_service.py
│   │   ├── 📊 health_score_service.py
│   │   ├── 💾 user_context_cache.py
│   │   └── ...
│   │
│   ├── 📁 utils/                    # 유틸리티
│   │   ├── 🔒 session.py
│   │   └── 🔧 helpers.py
│   │
│   └── 📁 workers/                  # 백그라운드 작업
│
├── 📁 tests/                        # 테스트
│   ├── 📁 unit/
│   └── 📄 conftest.py
│
├── 📁 alembic/                      # DB 마이그레이션
│   ├── 📁 versions/
│   └── ⚙️ env.py
│
├── 📁 docs/                         # 문서
│   ├── 📚 ENV_SETUP_GUIDE.md
│   ├── 🤖 YOLO_GPT_VISION_SETUP.md
│   ├── 🥗 RECIPE_FEATURE_GUIDE.md
│   └── ...
│
├── 📁 migrations/                   # SQL 마이그레이션
│   └── 📝 *.sql
│
├── 📁 models/                       # AI 모델 파일
│   └── 🎯 yolo11l.pt   # YOLOv11-large 가중치
│
├── ⚙️ alembic.ini
├── 📦 requirements.txt              # Python 의존성
├── 🔒 .env.example
├── 📖 README.md
└── 🐍 .gitignore
```

<br/>

---

<br/>

## 🤖 AI 시스템 상세

<div align="center">

### 🎯 음식 인식 파이프라인

</div>

```mermaid
graph LR
    A[📸 이미지 업로드] --> B[🎯 YOLO Detection]
    B --> C[🔍 대분류 추출]
    C --> D[🤖 1차 GPT Vision]
    D --> E[📋 대분류 선택]
    E --> F[🗄️ DB 음식 목록 조회]
    F --> G[🤖 2차 GPT Vision]
    G --> H[🎯 4개 후보 제시]
    H --> I[✅ 사용자 선택]
    I --> J[📊 영양 정보 반환]
```

<details>
<summary><b>🔍 상세 처리 과정</b></summary>

<br/>

### 1단계: YOLO / Roboflow 객체 탐지
- **모델**: YOLO11-large + Roboflow 재료 탐지 API
- **역할**: 이미지에서 음식/식재료 위치 파악
- **출력**: Bounding box + confidence score + class(label)

### 2단계: GPT Vision 1차 분석
- **입력**: 원본 이미지 + YOLO 결과
- **처리**: 식약처 DB의 대분류 목록 제공
- **출력**: 가장 가능성 높은 대분류 선택

### 3단계: 데이터베이스 쿼리
- **입력**: 선택된 대분류
- **처리**: 해당 대분류의 모든 음식 조회
- **출력**: 음식 목록 (최대 수백 개)

### 4단계: GPT Vision 2차 분석
- **입력**: 원본 이미지 + 음식 목록
- **처리**: 가장 유사한 음식 4개 선택
- **출력**: 순위별 후보 (1~4순위)

### 5단계: 사용자 확인
- **입력**: 4개 후보 제시
- **처리**: 사용자가 가장 정확한 것 선택
- **출력**: 최종 확정된 음식

### 6단계: 영양 정보 제공
- **입력**: 확정된 음식 ID
- **처리**: 식약처 DB에서 영양소 조회
- **출력**: 칼로리, 단백질, 탄수화물, 지방 등

</details>

<br/>

<div align="center">

### 🥗 식단 추천 알고리즘

</div>

```python
# Harris-Benedict 공식
BMR (남성) = 88.362 + (13.397 × 체중kg) + (4.799 × 키cm) - (5.677 × 나이)
BMR (여성) = 447.593 + (9.247 × 체중kg) + (3.098 × 키cm) - (4.330 × 나이)

# 총 에너지 소비량
TDEE = BMR × 활동계수

# 목표 칼로리
증량: TDEE + 300~500 kcal
유지: TDEE
감량: TDEE - 300~500 kcal
```

<details>
<summary><b>📊 영양소 배분 전략</b></summary>

<br/>

| 목표 | 탄수화물 | 단백질 | 지방 |
|:---:|:---:|:---:|:---:|
| 🔥 **감량** | 40% | 35% | 25% |
| ⚖️ **유지** | 50% | 25% | 25% |
| 💪 **증량** | 55% | 25% | 20% |

**추천 시스템 특징:**
- ✅ 개인 맞춤형 칼로리 계산
- ✅ 3가지 스타일 식단 제공
- ✅ 아침/점심/저녁/간식 구성
- ✅ 재료 및 레시피 포함
- ✅ 알레르기 정보 고려

</details>

<br/>

---

<br/>

## 🗄️ 데이터베이스 스키마

<div align="center">

### 📊 ERDCloud 기반 설계

</div>

<details>
<summary><b>🗂️ 주요 테이블</b></summary>

<br/>

### 👤 사용자 관련

| 테이블 | 설명 | 주요 컬럼 |
|:---|:---|:---|
| **User** | 사용자 기본 정보 | user_id, email, username, password_hash |
| **UserPreferences** | 사용자 선호도 | goal_calories, activity_level |
| **disease_allergy_profile** | 질병/알레르기 | diseases, allergies |

### 🍽️ 음식 관련

| 테이블 | 설명 | 주요 컬럼 |
|:---|:---|:---|
| **Food** | 음식 기본 정보 | food_id, food_name, food_category |
| **food_nutrients** | 영양소 정보 (식약처) | calories, protein, carbs, fat |
| **UserFoodHistory** | 섭취 기록 | user_id, food_id, consumed_at, meal_type |
| **UserContributedFood** | 사용자 등록 음식 | custom_food_id, food_name, nutrients |

### 🥗 식단 추천

| 테이블 | 설명 | 주요 컬럼 |
|:---|:---|:---|
| **DietPlan** | 추천 식단 | diet_plan_id, user_id, target_calories |
| **DietPlanMeal** | 식단 상세 | meal_id, meal_type, food_items |
| **Recipe** | 레시피 정보 | recipe_id, ingredients, steps |

### 📊 건강 관리

| 테이블 | 설명 | 주요 컬럼 |
|:---|:---|:---|
| **health_score** | 건강 점수 | score_id, user_id, nrf_score, date |
| **HealthReport** | 건강 리포트 | report_id, user_id, report_type |

### 💬 고객 지원

| 테이블 | 설명 | 주요 컬럼 |
|:---|:---|:---|
| **Announcement** | 공지사항 | announcement_id, title, content |
| **Inquiry** | 문의사항 | inquiry_id, user_id, question, answer |

</details>

<br/>

---

<br/>

## 🧪 테스트

<div align="center">

### ✅ 품질 보증

</div>

```bash
# 전체 테스트 실행
pytest

# 상세 출력
pytest -v

# 커버리지 리포트
pytest --cov=app tests/

# 특정 파일만 테스트
pytest tests/unit/test_auth.py

# 특정 함수만 테스트
pytest tests/unit/test_auth.py::test_login_success
```

<br/>

---

<br/>

## 🔍 문제 해결

<details>
<summary><b>❌ CORS 오류</b></summary>

<br/>

**증상:**
```
Access to fetch at 'http://localhost:8000/api/v1/...' from origin 'http://localhost:3000' 
has been blocked by CORS policy
```

**해결:**
`.env` 파일에서 `CORS_ALLOW_ORIGINS` 확인
```bash
CORS_ALLOW_ORIGINS=http://localhost:3000
```

</details>

<details>
<summary><b>❌ 데이터베이스 연결 오류</b></summary>

<br/>

**증상:**
```
sqlalchemy.exc.OperationalError: (pymysql.err.OperationalError) 
(2003, "Can't connect to MySQL server...")
```

**해결 방법:**
1. MySQL 서버 실행 확인
2. `.env`의 `DATABASE_URL` 확인
3. 데이터베이스 생성 확인
```bash
mysql -u root -p
CREATE DATABASE your_database;
```

</details>

<details>
<summary><b>❌ OpenAI API 오류</b></summary>

<br/>

**증상:**
```
openai.error.AuthenticationError: Invalid API key provided
```

**해결:**
1. `.env`에 올바른 API 키 설정
2. [OpenAI 플랫폼](https://platform.openai.com/api-keys)에서 키 확인
3. API 크레딧 잔액 확인

</details>

<details>
<summary><b>❌ YOLO 모델 로드 오류</b></summary>

<br/>

**증상:**
```
FileNotFoundError: [Errno 2] No such file or directory: 'yolo11-large.pt'
```

**해결:**
모델이 자동으로 다운로드됩니다. 인터넷 연결 확인 후 재시작

</details>

<br/>

---

<br/>

## 📚 추가 문서

<div align="center">

| 문서 | 설명 |
|:---|:---|
| 📖 [ENV_SETUP_GUIDE.md](./docs/ENV_SETUP_GUIDE.md) | 환경 변수 상세 가이드 |
| 🤖 [YOLO_GPT_VISION_SETUP.md](./docs/YOLO_GPT_VISION_SETUP.md) | AI 모델 설정 가이드 |
| 🥗 [RECIPE_FEATURE_GUIDE.md](./docs/RECIPE_FEATURE_GUIDE.md) | 레시피 기능 가이드 |
| 🔐 [SESSION_AUTH_GUIDE.md](./docs/SESSION_AUTH_GUIDE.md) | 인증 시스템 가이드 |
| 📊 [NRF93_IMPLEMENTATION_GUIDE.md](./docs/NRF93_IMPLEMENTATION_GUIDE.md) | 건강 점수 가이드 |
| 🔧 [트러블슈팅.md](./docs/트러블슈팅.md) | 문제 해결 모음 |

</div>

<br/>

---

<br/>

## 👥 팀 & 기여

<div align="center">

### 🌱 K-Calculator Backend Team

*안전하고 빠른 API를 만드는 사람들*

<br/>

| Role | Developer | GitHub |
|:---:|:---:|:---:|
| 🔧 **Backend Lead** | 권혁 | [@Hyuk-CBRN4](https://github.com/Hyuk-CBRN4) |
| 🤖 **AI Engineer** | 김준호 | [@Junho](https://github.com/zpzlzmz) |
| 📊 **Data Engineer** | 주연석 | [@YeonSeok-Joo](https://github.com/YeonSeok-Joo) |
| 🎨 **Frontend Lead** | 김은진 | [@eunjinlo](https://github.com/eunjinlo) |

<br/>

## 📧 문의

<div align="center">

### 💌 Contact

질문이나 제안사항이 있으신가요?

📧 **Email:** backend@k-calculator.com  
💬 **Issues:** [GitHub Issues](https://github.com/food-calorie-vision/food-calorie-vision-backend/issues)  
📚 **API Docs:** [Swagger UI](http://localhost:8000/docs)

<br/>

### 🌟 Star 주시면 큰 힘이 됩니다!

[![Star](https://img.shields.io/github/stars/food-calorie-vision/food-calorie-vision-backend?style=social)](https://github.com/food-calorie-vision/food-calorie-vision-backend/stargazers)

</div>

<br/>

---

<br/>

<div align="center">

### 🌿 건강한 내일을 만드는 기술

<br/>

**Made with 💚 by K-Calculator Backend Team**

<br/>

<img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=12,15,18,21,24&height=150&section=footer" />

</div>

