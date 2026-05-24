"""平台级 RBAC：超级管理员（唯一 is_superuser）与管理员角色 platform_admin。"""

from __future__ import annotations

from fastapi import HTTPException
from sqlmodel import Session, select

from app.models import Role, User, UserRole


def has_role(db: Session, user_id: int, role_name: str) -> bool:
    role = db.exec(select(Role).where(Role.name == role_name)).first()
    if not role:
        return False
    return (
        db.exec(
            select(UserRole).where(UserRole.user_id == user_id, UserRole.role_id == role.id)
        ).first()
        is not None
    )


def is_platform_staff(db: Session, user: User) -> bool:
    """超级管理员或已分配「管理员」角色的用户。"""
    if user.is_superuser:
        return True
    return has_role(db, user.id, "platform_admin")


def ensure_super_admin(user: User) -> None:
    if not user.is_superuser:
        raise HTTPException(status_code=403, detail="仅超级管理员可执行该操作")


def ensure_platform_staff(db: Session, user: User) -> None:
    if not is_platform_staff(db, user):
        raise HTTPException(status_code=403, detail="仅超级管理员或管理员可执行该操作")


def admin_notification_recipient_user_ids(db: Session) -> list[int]:
    """注册/系统类通知：超级管理员 + 管理员（platform_admin）。"""
    ids: set[int] = set()
    for u in db.exec(select(User).where(User.is_superuser == True)).all():  # noqa: E712
        if u.id is not None:
            ids.add(int(u.id))
    role = db.exec(select(Role).where(Role.name == "platform_admin")).first()
    if role:
        for ur in db.exec(select(UserRole).where(UserRole.role_id == role.id)).all():
            ids.add(int(ur.user_id))
    return sorted(ids)
