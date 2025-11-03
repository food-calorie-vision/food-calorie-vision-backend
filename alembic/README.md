# Alembic 사용 가이드

1. 가상환경을 활성화한 뒤 의존성을 설치합니다.
2. `alembic revision --autogenerate -m "your message"` 명령으로 새 마이그레이션 파일을 생성합니다.
3. `alembic upgrade head` 명령으로 데이터베이스에 적용합니다.
4. 설정은 `app/core/config.py`의 `DATABASE_URL` 값을 사용하며, 필요 시 `.env`에서 덮어쓸 수 있습니다.

