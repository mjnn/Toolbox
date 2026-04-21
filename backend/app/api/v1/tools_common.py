"""Shared tool API helpers (authz, tool guards, HTTP mapping for feature errors)."""
import requests
from datetime import datetime
from fastapi import HTTPException
from sqlmodel import Session, select

from app.models import Tool, ToolOwner, User, UserToolPermission, PermissionStatus

SERVICE_ID_REGISTRY_TOOL_NAME = "service-id-registry"
MOS_INTEGRATION_TOOLBOX_TOOL_NAME = "mos-integration-toolbox"
RSA_TOKEN_LIVESTREAM_TOOL_NAME = "rsa-token-livestream"


def get_tool_or_404(db: Session, tool_id: int) -> Tool:
    tool = db.get(Tool, tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail="工具不存在")
    return tool


def ensure_tool_available_and_accessible(db: Session, user: User, tool: Tool) -> None:
    ensure_tool_active_or_superuser(user, tool)
    ensure_tool_access(db, user, tool.id)


def ensure_tool_active_or_superuser(user: User, tool: Tool) -> None:
    if not tool.is_active and not user.is_superuser:
        raise HTTPException(status_code=403, detail="工具暂不可用")


def ensure_tool_access(db: Session, user: User, tool_id: int) -> None:
    if user.is_superuser:
        return

    is_owner = db.exec(
        select(ToolOwner).where(ToolOwner.tool_id == tool_id, ToolOwner.user_id == user.id)
    ).first()
    if is_owner:
        return

    permission = db.exec(
        select(UserToolPermission).where(
            UserToolPermission.tool_id == tool_id,
            UserToolPermission.user_id == user.id,
            UserToolPermission.status == PermissionStatus.APPROVED,
        )
    ).first()
    if not permission:
        raise HTTPException(status_code=403, detail="您没有使用该工具的权限")

    if permission.expires_at and permission.expires_at <= datetime.utcnow():
        raise HTTPException(status_code=403, detail="您的工具使用权限已过期")


def ensure_service_id_registry_tool(tool: Tool) -> None:
    if tool.name != SERVICE_ID_REGISTRY_TOOL_NAME:
        raise HTTPException(status_code=400, detail="当前功能仅支持 service-id-registry 工具")


def ensure_mos_integration_toolbox_tool(tool: Tool) -> None:
    if tool.name != MOS_INTEGRATION_TOOLBOX_TOOL_NAME:
        raise HTTPException(status_code=400, detail="当前功能仅支持 mos-integration-toolbox 工具")


def ensure_rsa_token_livestream_tool(tool: Tool) -> None:
    if tool.name != RSA_TOKEN_LIVESTREAM_TOOL_NAME:
        raise HTTPException(status_code=400, detail="当前功能仅支持 rsa-token-livestream 工具")


def raise_feature_http_exception(prefix: str, exc: Exception) -> None:
    if isinstance(exc, requests.Timeout):
        raise HTTPException(status_code=504, detail=f"{prefix}: 请求超时，请稍后重试")
    if isinstance(exc, requests.ConnectionError):
        raise HTTPException(status_code=502, detail=f"{prefix}: 网络连接失败，请检查内网连通性")
    if isinstance(exc, requests.HTTPError):
        response = exc.response
        status = response.status_code if response is not None else 502
        raise HTTPException(status_code=502, detail=f"{prefix}: 下游服务返回异常({status})")
    raise HTTPException(status_code=500, detail=f"{prefix}: {exc}")


def can_manage_all_records(db: Session, user: User, tool_id: int) -> bool:
    if user.is_superuser:
        return True
    owner = db.exec(
        select(ToolOwner).where(ToolOwner.tool_id == tool_id, ToolOwner.user_id == user.id)
    ).first()
    return owner is not None


def ensure_manage_permission(db: Session, user: User, tool_id: int) -> None:
    if can_manage_all_records(db, user, tool_id):
        return
    raise HTTPException(status_code=403, detail="仅工具负责人可管理该功能")
