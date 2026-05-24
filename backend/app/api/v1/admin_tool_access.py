from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlmodel import Session, select

from app.api.v1.admin_common import ensure_tool_governance, get_role_by_name
from app.api.v1.rbac import ensure_platform_staff
from app.api.v1.users import get_current_active_user
from app.database import get_session
from app.models import APIAccessLog, Notification, PermissionStatus, Role, Tool, ToolOwner, User, UserRole, UserToolPermission
from app.schemas import (
    PaginatedToolLicenseCandidates,
    PaginatedToolLicenseUsers,
    SuccessResponse,
    ToolLicenseBatchUpdateRequest,
    ToolLicenseBatchUpdateResult,
    ToolLicenseCandidateRow,
    ToolLicenseUserRow,
    ToolOwnerWithUser,
)

router = APIRouter()


@router.get("/tools/{tool_id}/owners", response_model=List[ToolOwnerWithUser])
async def list_tool_owners(
    tool_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    ensure_platform_staff(db, current_user)
    tool = db.get(Tool, tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail="工具不存在")

    owners = db.exec(select(ToolOwner).where(ToolOwner.tool_id == tool_id)).all()
    owner_user_ids = [owner.user_id for owner in owners]
    users_by_id: dict[int, User] = {}
    if owner_user_ids:
        users_by_id = {
            user.id: user
            for user in db.exec(select(User).where(User.id.in_(owner_user_ids))).all()
        }
    return [
        ToolOwnerWithUser(**owner.dict(), user=users_by_id[owner.user_id])
        for owner in owners
        if owner.user_id in users_by_id
    ]


@router.post("/tools/{tool_id}/owners/{user_id}", response_model=SuccessResponse)
async def assign_tool_owner(
    tool_id: int,
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    ensure_platform_staff(db, current_user)
    tool = db.get(Tool, tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail="工具不存在")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    exists = db.exec(
        select(ToolOwner).where(ToolOwner.tool_id == tool_id, ToolOwner.user_id == user_id)
    ).first()
    if exists:
        return SuccessResponse(message="工具负责人已分配")

    db.add(ToolOwner(tool_id=tool_id, user_id=user_id))

    role = get_role_by_name(db, "tool_owner")
    role_exists = db.exec(
        select(UserRole).where(UserRole.user_id == user_id, UserRole.role_id == role.id)
    ).first()
    if not role_exists:
        db.add(UserRole(user_id=user_id, role_id=role.id))

    db.commit()
    return SuccessResponse(message="工具负责人分配成功")


@router.delete("/tools/{tool_id}/owners/{user_id}", response_model=SuccessResponse)
async def remove_tool_owner(
    tool_id: int,
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    ensure_platform_staff(db, current_user)
    mapping = db.exec(
        select(ToolOwner).where(ToolOwner.tool_id == tool_id, ToolOwner.user_id == user_id)
    ).first()
    if not mapping:
        raise HTTPException(status_code=404, detail="未找到工具负责人分配关系")

    db.delete(mapping)
    db.commit()
    return SuccessResponse(message="工具负责人移除成功")


@router.get("/my-owner-tools", response_model=List[int])
async def get_my_owner_tools(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    if current_user.is_superuser:
        return []
    tool_ids = db.exec(
        select(ToolOwner.tool_id).where(ToolOwner.user_id == current_user.id)
    ).all()
    return tool_ids


@router.get("/tools/{tool_id}/license-users", response_model=PaginatedToolLicenseUsers)
async def list_tool_license_users(
    tool_id: int,
    skip: int = 0,
    limit: int = 20,
    search: str | None = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = db.get(Tool, tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail="工具不存在")
    ensure_tool_governance(db, current_user, tool_id)

    perms = db.exec(
        select(UserToolPermission).where(
            UserToolPermission.tool_id == tool_id,
            UserToolPermission.status == PermissionStatus.APPROVED,
        )
    ).all()

    last_by_user: dict[int, datetime] = {}
    agg_rows = db.exec(
        select(APIAccessLog.user_id, func.max(APIAccessLog.created_at))
        .where(
            APIAccessLog.tool_id == tool_id,
            APIAccessLog.feature_name != None,
            APIAccessLog.user_id != None,
        )
        .group_by(APIAccessLog.user_id)
    ).all()
    for row in agg_rows:
        cells = tuple(row)
        if len(cells) < 2:
            continue
        uid, ts = cells[0], cells[1]
        if uid is not None and ts is not None:
            last_by_user[int(uid)] = ts

    user_ids = {perm.user_id for perm in perms}
    users_by_id: dict[int, User] = {}
    if user_ids:
        users_by_id = {
            user.id: user for user in db.exec(select(User).where(User.id.in_(list(user_ids)))).all()
        }
    result: List[ToolLicenseUserRow] = []
    for p in perms:
        user = users_by_id.get(p.user_id)
        if user is None:
            continue
        granted_at = p.reviewed_at or p.applied_at
        result.append(
            ToolLicenseUserRow(
                user=user,
                granted_at=granted_at,
                expires_at=p.expires_at,
                last_used_at=last_by_user.get(p.user_id),
            )
        )

    limit = min(max(limit, 1), 500)
    result.sort(key=lambda r: r.user.username.lower())
    if search and search.strip():
        q = search.strip().lower()
        result = [
            r
            for r in result
            if q in r.user.username.lower()
            or q in (r.user.email or "").lower()
            or (r.user.full_name and q in r.user.full_name.lower())
        ]
    total = len(result)
    return PaginatedToolLicenseUsers(
        total=total,
        items=result[skip: skip + limit],
    )


@router.delete("/tools/{tool_id}/license-users/{user_id}", response_model=SuccessResponse)
async def revoke_tool_user_license(
    tool_id: int,
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = db.get(Tool, tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail="工具不存在")
    ensure_tool_governance(db, current_user, tool_id)

    perm = db.exec(
        select(UserToolPermission).where(
            UserToolPermission.tool_id == tool_id,
            UserToolPermission.user_id == user_id,
            UserToolPermission.status == PermissionStatus.APPROVED,
        )
    ).first()
    if not perm:
        raise HTTPException(
            status_code=404,
            detail="未找到该用户在该工具下的已批准权限",
        )

    db.delete(perm)
    db.commit()

    db.add(
        Notification(
            user_id=user_id,
            title=f"工具「{tool.name}」使用权限已取消",
            message=f"管理员或工具负责人已取消您对「{tool.name}」的使用权限。",
            notification_type="permission",
            related_id=tool_id,
        )
    )
    db.commit()
    return SuccessResponse(message="权限已撤销")


@router.get("/tools/{tool_id}/license-users/candidates", response_model=PaginatedToolLicenseCandidates)
async def list_tool_license_candidates(
    tool_id: int,
    skip: int = 0,
    limit: int = 200,
    search: str | None = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = db.get(Tool, tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail="工具不存在")
    ensure_tool_governance(db, current_user, tool_id)

    role_names = {"platform_admin", "tool_owner"}
    admin_role_ids = {
        role.id for role in db.exec(select(Role).where(Role.name.in_(role_names))).all() if role.id is not None
    }
    admin_user_ids = set()
    if admin_role_ids:
        admin_user_ids = {
            row.user_id
            for row in db.exec(select(UserRole).where(UserRole.role_id.in_(list(admin_role_ids)))).all()
            if row.user_id is not None
        }

    approved_perm_user_ids = {
        p.user_id
        for p in db.exec(
            select(UserToolPermission).where(
                UserToolPermission.tool_id == tool_id,
                UserToolPermission.status == PermissionStatus.APPROVED,
            )
        ).all()
    }

    users = db.exec(
        select(User).where(
            User.is_active == True,
            User.is_approved == True,
            User.id != current_user.id,
        )
    ).all()

    result: List[ToolLicenseCandidateRow] = []
    query = (search or "").strip().lower()
    for user in users:
        if user.is_superuser or user.id in admin_user_ids:
            continue
        if query:
            fields = [user.username or "", user.email or "", user.full_name or ""]
            if not any(query in field.lower() for field in fields):
                continue
        result.append(
            ToolLicenseCandidateRow(
                user=user,
                currently_authorized=user.id in approved_perm_user_ids,
            )
        )

    result.sort(key=lambda r: r.user.username.lower())
    limit = min(max(limit, 1), 500)
    total = len(result)
    return PaginatedToolLicenseCandidates(total=total, items=result[skip : skip + limit])


@router.post("/tools/{tool_id}/license-users/batch-update", response_model=ToolLicenseBatchUpdateResult)
async def batch_update_tool_user_license(
    tool_id: int,
    payload: ToolLicenseBatchUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = db.get(Tool, tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail="工具不存在")
    ensure_tool_governance(db, current_user, tool_id)

    user_ids = sorted({uid for uid in payload.user_ids if uid > 0})
    if not user_ids:
        return ToolLicenseBatchUpdateResult(
            action=payload.action, requested_count=0, changed_count=0, skipped_count=0
        )

    role_names = {"platform_admin", "tool_owner"}
    admin_role_ids = {
        role.id for role in db.exec(select(Role).where(Role.name.in_(role_names))).all() if role.id is not None
    }
    admin_user_ids = set()
    if admin_role_ids:
        admin_user_ids = {
            row.user_id
            for row in db.exec(select(UserRole).where(UserRole.role_id.in_(list(admin_role_ids)))).all()
            if row.user_id is not None
        }

    users = db.exec(select(User).where(User.id.in_(user_ids))).all()
    users_by_id = {u.id: u for u in users if u.id is not None}

    changed_count = 0
    skipped_count = 0
    now = datetime.utcnow()
    for user_id in user_ids:
        user = users_by_id.get(user_id)
        if not user:
            skipped_count += 1
            continue
        if (
            user.id == current_user.id
            or user.is_superuser
            or user.id in admin_user_ids
            or (not user.is_active)
            or (not user.is_approved)
        ):
            skipped_count += 1
            continue

        perm = db.exec(
            select(UserToolPermission).where(
                UserToolPermission.tool_id == tool_id,
                UserToolPermission.user_id == user.id,
            )
        ).first()
        if payload.action == "grant":
            if perm and perm.status == PermissionStatus.APPROVED:
                skipped_count += 1
                continue
            if perm:
                perm.status = PermissionStatus.APPROVED
                perm.reviewed_by = current_user.id
                perm.reviewed_at = now
                perm.review_notes = "批量授权通过"
                db.add(perm)
            else:
                db.add(
                    UserToolPermission(
                        user_id=user.id,
                        tool_id=tool_id,
                        status=PermissionStatus.APPROVED,
                        applied_reason="管理员批量授权",
                        reviewed_by=current_user.id,
                        reviewed_at=now,
                        review_notes="批量授权通过",
                    )
                )
            db.add(
                Notification(
                    user_id=user.id,
                    title=f"已开通工具「{tool.name}」使用权限",
                    message=f"管理员或工具负责人已批量开通您对「{tool.name}」的使用权限。",
                    notification_type="permission",
                    related_id=tool_id,
                )
            )
            changed_count += 1
            continue

        # revoke
        if not perm or perm.status != PermissionStatus.APPROVED:
            skipped_count += 1
            continue
        db.delete(perm)
        db.add(
            Notification(
                user_id=user.id,
                title=f"工具「{tool.name}」使用权限已取消",
                message=f"管理员或工具负责人已批量取消您对「{tool.name}」的使用权限。",
                notification_type="permission",
                related_id=tool_id,
            )
        )
        changed_count += 1

    db.commit()
    return ToolLicenseBatchUpdateResult(
        action=payload.action,
        requested_count=len(user_ids),
        changed_count=changed_count,
        skipped_count=skipped_count,
    )
