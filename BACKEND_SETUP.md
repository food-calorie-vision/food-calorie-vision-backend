# 백엔드 초기 설정 가이드

## 1. 프로젝트 개요
- **목표**: 영양 정보 제공, 음식 이미지 분석, LangChain 기반 챗봇을 담당할 FastAPI 서비스를 구축합니다.
- **프런트엔드**: `../food-calorie-vision-frontend` (Next.js 15)
- **백엔드 스택**: Python 3.11+ 의 FastAPI
- **데이터베이스**: MySQL 8.x
- **확장 계획**: YOLO 비전 파이프라인, LangChain 에이전트 도구 연동

## 2. 권장 도구 체인
| 구성 요소 | 선택 |
| --- | --- |
| 런타임 | Python 3.11 (pyenv 또는 시스템 Python) |
| 웹 프레임워크 | FastAPI + Uvicorn |
| ORM & 마이그레이션 | SQLAlchemy 2 (async) + Alembic |
| DB 드라이버 | asyncmy (대안: aiomysql) |
| 설정 관리 | pydantic-settings, python-dotenv |
| 테스트 | pytest, pytest-asyncio, httpx |
| 린트 & 포매터 | ruff, black, isort |

## 3. 디렉터리 구조
```
food-calorie-vision-backend/
|-- app/
|   |-- main.py             # FastAPI 진입점
|   |-- api/                # 라우터와 스키마
|   |-- core/               # 설정 도우미
|   |-- db/                 # SQLAlchemy 베이스와 세션
|   |-- services/           # 비즈니스 로직 계층
|   |-- workers/            # YOLO / LangChain 작업
|   `-- utils/              # 공용 유틸
|-- alembic/                # 마이그레이션 스크립트
|-- models/                 # YOLO 가중치 및 아티팩트
|-- tests/                  # pytest 스위트
|-- requirements.txt
`-- .env.example
```

## 4. 로컬 환경 구성 (venv)
```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env           # macOS/Linux: cp .env.example .env
```

## 5. 환경 변수 설정
`.env.example`에 기본 값이 담겨 있습니다.
```
APP_ENV=local
API_PORT=8000
API_PREFIX=/api
API_VERSION=v1
DATABASE_URL=mysql+asyncmy://fcv_user:strong_password@localhost:3306/food_calorie
JWT_SECRET=replace_me
JWT_EXPIRE_MINUTES=60
OPENAI_API_KEY=
VISION_MODEL_PATH=models/yolo11n.pt
CORS_ALLOW_ORIGINS=*
```
배포 환경에 맞춰 `DATABASE_URL`과 비밀 값은 실제 값으로 교체하고 버전에 올리지 않도록 주의하세요.

## 6. 데이터베이스 초기화
```sql
CREATE DATABASE food_calorie CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'fcv_user'@'%' IDENTIFIED BY 'strong_password';
GRANT ALL PRIVILEGES ON food_calorie.* TO 'fcv_user'@'%';
FLUSH PRIVILEGES;
```
모델을 정의한 뒤 아래 명령으로 마이그레이션을 생성·적용합니다.
```bash
alembic revision --autogenerate -m "init schema"
alembic upgrade head
```

## 7. 핵심 명령어
| 명령 | 설명 |
| --- | --- |
| `uvicorn app.main:app --reload --port 8000` | 개발 서버 실행 |
| `pytest` | 단위/통합 테스트 실행 |
| `pytest --cov=app` | 커버리지 포함 테스트 |
| `ruff check app tests` | 정적 분석 |
| `black app tests && isort app tests` | 코드 포맷팅 |
| `alembic revision --autogenerate -m "message"` | 새 마이그레이션 생성 |
| `alembic upgrade head` | 최신 마이그레이션 적용 |

## 8. 비전 & 챗봇 메모
- YOLO 가중치는 `models/` 디렉터리에 보관합니다(예: `models/yolo11n.pt`).
- 추론 로직은 `app/workers/vision.py`에 구현하고 FastAPI BackgroundTask나 작업 큐(Celery, RQ 등)로 호출합니다.
- LangChain 로직은 `app/services/chatbot.py`에 집중시키고, DB 조회나 비전 결과를 Tool로 연결합니다.
- RAG가 필요해지면 pgvector, Qdrant 같은 벡터 스토리지를 검토하세요.

## 9. 협업 체크리스트
- [ ] 헬스체크 외 API 라우트를 확장한다.
- [ ] SQLAlchemy 모델과 Alembic 마이그레이션을 추가한다.
- [ ] JWT 기반 인증/인가 흐름을 구현한다.
- [ ] YOLO 추론 PoC 엔드포인트를 작성한다.
- [ ] LangChain 챗봇을 목 데이터로 프로토타입한다.
- [ ] CI에서 린트, 테스트, 마이그레이션 검증을 자동화한다.

추가 협업 규칙은 루트 저장소의 `AGENTS.md`를 참고하세요.

