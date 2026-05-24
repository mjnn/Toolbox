from fastapi import APIRouter
from app.api.v1 import auth, users, tools, permissions, admin, admin_feedback, admin_audit, admin_permissions, admin_tool_access, admin_releases, admin_users, version_meta

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(version_meta.router, tags=["version"])
api_router.include_router(tools.router, prefix="/tools", tags=["tools"])
api_router.include_router(permissions.router, prefix="/permissions", tags=["permissions"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(admin_feedback.router, prefix="/admin", tags=["admin"])
api_router.include_router(admin_audit.router, prefix="/admin", tags=["admin"])
api_router.include_router(admin_permissions.router, prefix="/admin", tags=["admin"])
api_router.include_router(admin_tool_access.router, prefix="/admin", tags=["admin"])
api_router.include_router(admin_releases.router, prefix="/admin", tags=["admin"])
api_router.include_router(admin_users.router, prefix="/admin", tags=["admin"])
