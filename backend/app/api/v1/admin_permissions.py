from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.api.v1.admin_common import ensure_permission_reviewer
from app.api.v1.users import get_current_active_user
from app.database import get_session
from app.models import Notification, PermissionStatus, Tool, ToolOwner, User, UserToolPermission
from app.schemas import PermissionUpdate, PermissionWithDetails, SuccessResponse

router = APIRouter()


@router.get("/permissions/pending", response_model=List[PermissionWithDetails])
async def get_pending_permissions(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    if current_user.is_superuser:
        statement = select(UserToolPermission).where(
            UserToolPermission.status == PermissionStatus.PENDING
        ).offset(skip).limit(limit)
    else:
        owner_assignments = db.exec(
            select(ToolOwner.tool_id).where(ToolOwner.user_id == current_user.id)
        ).all()
        if not owner_assignments:
            raise HTTPException(status_code=403, detail="仅工具负责人可审核权限")
        statement = select(UserToolPermission).where(
            UserToolPermission.status == PermissionStatus.PENDING,
            UserToolPermission.tool_id.in_(owner_assignments),
        ).offset(skip).limit(limit)

    permissions = db.exec(statement).all()
    user_ids = {perm.user_id for perm in permissions}
    reviewer_ids = {perm.reviewed_by for perm in permissions if perm.reviewed_by}
    tool_ids = {perm.tool_id for perm in permissions}
    all_user_ids = list(user_ids | reviewer_ids)

    users_by_id: dict[int, User] = {}
    if all_user_ids:
        users_by_id = {
            user.id: user
            for user in db.exec(select(User).where(User.id.in_(all_user_ids))).all()
        }
    tools_by_id: dict[int, Tool] = {}
    if tool_ids:
        tools_by_id = {
            tool.id: tool for tool in db.exec(select(Tool).where(Tool.id.in_(list(tool_ids)))).all()
        }

    result: list[PermissionWithDetails] = []
    for perm in permissions:
        user = users_by_id.get(perm.user_id)
        tool = tools_by_id.get(perm.tool_id)
        if not user or not tool:
            continue
        reviewer = users_by_id.get(perm.reviewed_by) if perm.reviewed_by else None
        result.append(
            PermissionWithDetails(
                **perm.dict(),
                user=user,
                tool=tool,
                reviewer=reviewer,
            )
        )

    return result


@router.post("/permissions/{permission_id}/approve", response_model=SuccessResponse)
async def approve_permission(
    permission_id: int,
    update_data: PermissionUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    permission = db.get(UserToolPermission, permission_id)
    if not permission:
        raise HTTPException(status_code=404, detail="权限申请不存在")

    ensure_permission_reviewer(db, current_user, permission.tool_id)

    if permission.status != PermissionStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail="该权限申请不处于待审核状态"
        )

    applicant = db.get(User, permission.user_id)
    account_just_activated = bool(applicant and not applicant.is_approved)

    permission.status = PermissionStatus.APPROVED
    permission.reviewed_by = current_user.id
    permission.reviewed_at = datetime.utcnow()
    if update_data.review_notes:
        permission.review_notes = update_data.review_notes
    if update_data.expires_at:
        permission.expires_at = update_data.expires_at

    if applicant and account_just_activated:
        applicant.is_approved = True
        db.add(applicant)

    db.add(permission)
    db.commit()

    tool = db.get(Tool, permission.tool_id)
    tool_name = tool.name if tool else f"ID {permission.tool_id}"

    perm_msg = f"您对工具「{tool_name}」的权限申请已被批准。"
    if account_just_activated:
        perm_msg += " 您的账号已同步开通，可以登录系统。"

    notification = Notification(
        user_id=permission.user_id,
        title="权限申请已批准",
        message=perm_msg,
        notification_type="permission",
        related_id=permission_id
    )
    db.add(notification)
    notification_tool = Notification(
        user_id=permission.user_id,
        title=f"工具「{tool_name}」已就绪",
        message="请在「我的工具」或「所有工具」中打开该工具开始使用。",
        notification_type="tool",
        related_id=permission.tool_id,
    )
    db.add(notification_tool)
    db.commit()

    return SuccessResponse(message="权限申请已批准")


@router.post("/permissions/{permission_id}/reject", response_model=SuccessResponse)
async def reject_permission(
    permission_id: int,
    update_data: PermissionUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    if not update_data.review_notes:
        raise HTTPException(
            status_code=400,
            detail="拒绝时必须填写审核说明"
        )

    permission = db.get(UserToolPermission, permission_id)
    if not permission:
        raise HTTPException(status_code=404, detail="权限申请不存在")

    ensure_permission_reviewer(db, current_user, permission.tool_id)

    if permission.status != PermissionStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail="该权限申请不处于待审核状态"
        )

    permission.status = PermissionStatus.REJECTED
    permission.reviewed_by = current_user.id
    permission.reviewed_at = datetime.utcnow()
    permission.review_notes = update_data.review_notes

    db.add(permission)
    db.commit()

    tool = db.get(Tool, permission.tool_id)
    tool_name = tool.name if tool else f"ID {permission.tool_id}"

    notification = Notification(
        user_id=permission.user_id,
        title="权限申请被拒绝",
        message=f"您对工具「{tool_name}」的权限申请已被拒绝。原因：{update_data.review_notes}",
        notification_type="permission",
        related_id=permission_id
    )
    db.add(notification)
    db.commit()

    return SuccessResponse(message="权限申请已拒绝")
