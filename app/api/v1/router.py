from fastapi import APIRouter

from app.api.v1.routes import auth, chat, health, meals, users, vision

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/user", tags=["users"])
api_router.include_router(meals.router, prefix="/meals", tags=["meals"])
api_router.include_router(vision.router, prefix="/food", tags=["vision"])
api_router.include_router(chat.router, prefix="", tags=["chat"])

