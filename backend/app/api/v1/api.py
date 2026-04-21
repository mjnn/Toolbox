from fastapi import APIRouter
from app.api.v1 import auth, users, tools, permissions, admin

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(tools.router, prefix="/tools", tags=["tools"])
api_router.include_router(permissions.router, prefix="/permissions", tags=["permissions"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
