# Food Calorie Vision Backend

Food Calorie Vision 프로젝트의 FastAPI 기반 백엔드 소스 코드입니다. 현재는 영양 정보 REST API를 제공하며, 앞으로는 YOLO 이미지 분석과 LangChain 챗봇 기능을 통합할 예정입니다.

## 요구 사항
- Python 3.11 이상
- MySQL 8.x
- 가상환경 도구(`python -m venv` 권장)

## 빠른 시작
```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env           # macOS/Linux: cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

## 디렉터리 요약
```
app/                 FastAPI 애플리케이션 모듈
alembic/             SQL 마이그레이션 스크립트
models/              YOLO 가중치 및 관련 리소스
tests/               pytest 테스트 코드
docs/                구조 문서와 온보딩 자료
.env.example         환경 변수 템플릿
requirements.txt     고정된 Python 의존성 목록
```

## 자주 사용하는 명령
| 목적 | 명령 |
| --- | --- |
| 개발 서버 실행 | `uvicorn app.main:app --reload --port 8000` |
| 테스트 실행 | `pytest` |
| 커버리지 테스트 | `pytest --cov=app` |
| 린트 | `ruff check app tests` |
| 포맷팅 | `black app tests && isort app tests` |
| 마이그레이션 생성 | `alembic revision --autogenerate -m "message"` |
| 마이그레이션 적용 | `alembic upgrade head` |

## 참고 문서
- `BACKEND_SETUP.md`: 환경 구성, 협업 절차, LangChain/YOLO 계획
- `docs/overview.md`: 백엔드 디렉터리별 역할 요약
