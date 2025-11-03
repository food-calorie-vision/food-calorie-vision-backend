from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title="Food Calorie Vision API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_prefix = f"{settings.api_prefix}/{settings.api_version}".rstrip("/")
app.include_router(api_router, prefix=api_prefix)


@app.get("/healthz", tags=["health"])
async def root_health_check() -> dict[str, str]:
    """Basic readiness probe for infrastructure monitors."""
    return {"status": "ok"}
