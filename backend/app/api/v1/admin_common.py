from fastapi import HTTPException
from sqlmodel import Session, select

from app.api.v1.rbac import has_role
from app.models import PermissionStatus, Role, ToolOwner, User, UserToolPermission


def get_role_by_name(db: Session, role_name: str) -> Role:
    role = db.exec(select(Role).where(Role.name == role_name)).first()
    if not role:
        raise HTTPException(status_code=404, detail=f"角色不存在：{role_name}")
    return role


def user_is_tool_owner(db: Session, user_id: int, tool_id: int) -> bool:
    return db.exec(
        select(ToolOwner).where(ToolOwner.user_id == user_id, ToolOwner.tool_id == tool_id)
    ).first() is not None


def ensure_tool_governance(db: Session, current_user: User, tool_id: int) -> None:
    """工具维度治理：超管、平台管理员或该工具负责人。"""
    if current_user.is_superuser:
        return
    if has_role(db, current_user.id, "platform_admin"):
        return
    if user_is_tool_owner(db, current_user.id, tool_id):
        return
    raise HTTPException(status_code=403, detail="仅超级管理员、管理员或工具负责人可操作")


def ensure_permission_reviewer(db: Session, current_user: User, tool_id: int) -> None:
    """权限审核：仅工具负责人或超级管理员（平台管理员不可代审）。"""
    if current_user.is_superuser:
        return
    if user_is_tool_owner(db, current_user.id, tool_id):
        return
    raise HTTPException(status_code=403, detail="仅工具负责人或超级管理员可审核该工具的使用申请")


def recipient_user_ids_for_tool(db: Session, tool_id: int) -> set[int]:
    """已获批用户 + 工具负责人（用于状态变更/版本通知）。"""
    targets: set[int] = set()
    for perm in db.exec(
        select(UserToolPermission).where(
            UserToolPermission.tool_id == tool_id,
            UserToolPermission.status == PermissionStatus.APPROVED,
        )
    ).all():
        targets.add(perm.user_id)
    for owner in db.exec(select(ToolOwner).where(ToolOwner.tool_id == tool_id)).all():
        targets.add(owner.user_id)
    return targets
