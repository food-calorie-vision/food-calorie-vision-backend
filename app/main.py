import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv

# .env 파일 로드 (최우선!)
load_dotenv()

from app.api.v1.router import api_router
from app.core.config import get_settings


def configure_sqlalchemy_logging() -> None:
    """Format SQLAlchemy engine logs with extra spacing for readability."""
    sql_logger = logging.getLogger("sqlalchemy.engine")
    sql_logger.setLevel(logging.INFO)
    sql_logger.handlers.clear()

    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s\n%(message)s\n",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    sql_logger.addHandler(handler)
    sql_logger.propagate = False


configure_sqlalchemy_logging()

settings = get_settings()

app = FastAPI(
    title="Food Calorie Vision API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS 미들웨어 (SessionMiddleware보다 먼저 추가)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 세션 미들웨어
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret_key,
    session_cookie=settings.session_cookie_name,
    max_age=settings.session_max_age,
    same_site=settings.session_same_site,
    https_only=settings.session_https_only,
)

api_prefix = f"{settings.api_prefix}/{settings.api_version}".rstrip("/")
app.include_router(api_router, prefix=api_prefix)


@app.get("/healthz", tags=["health"])
async def root_health_check() -> dict[str, str]:
    """Basic readiness probe for infrastructure monitors."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    from app.core.config import get_settings
    
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=settings.port,
        reload=True,
        reload_dirs=["app"],
    )
