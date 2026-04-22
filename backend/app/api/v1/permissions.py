from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.models import (
    UserToolPermission,
    Tool,
    ToolOwner,
    User,
    Role,
    UserRole,
    PermissionStatus,
    Notification,
)
from app.schemas import (
    PermissionCreate, PermissionInDB, PermissionWithDetails,
    SuccessResponse
)
from app.api.v1.users import get_current_active_user
from app.core.tool_visibility import is_tool_visible

router = APIRouter()


def _notify_pending_reviewers(
    db: Session,
    tool: Tool,
    permission_id: int,
    applicant_id: int,
    applicant_name: str,
) -> None:
    """通知工具负责人与超级管理员：有新的待审核申请（申请人本人除外）"""
    recipients: set[int] = set()
    for o in db.exec(select(ToolOwner).where(ToolOwner.tool_id == tool.id)).all():
        recipients.add(o.user_id)
    for u in db.exec(select(User).where(User.is_superuser == True)).all():
        recipients.add(u.id)
    recipients.discard(applicant_id)
    for uid in recipients:
        db.add(
            Notification(
                user_id=uid,
                title="待审核的权限申请",
                message=f"用户 {applicant_name} 申请使用工具「{tool.name}」，请前往「权限管理」处理。",
                notification_type="permission",
                related_id=permission_id,
            )
        )
    db.commit()


def has_role(db: Session, user_id: int, role_name: str) -> bool:
    role = db.exec(select(Role).where(Role.name == role_name)).first()
    if not role:
        return False
    return db.exec(
        select(UserRole).where(
            UserRole.user_id == user_id,
            UserRole.role_id == role.id
        )
    ).first() is not None

@router.post("/apply/{tool_id}", response_model=PermissionInDB)
async def apply_for_permission(
    tool_id: int,
    permission_data: PermissionCreate,
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_session)
):
    if not (current_user.is_superuser or has_role(db, current_user.id, "tool_user")):
        raise HTTPException(status_code=403, detail="仅工具用户可申请权限")

    # 检查工具是否存在
    tool = db.get(Tool, tool_id)
    if not tool or not tool.is_active or not is_tool_visible(tool.name):
        raise HTTPException(status_code=404, detail="工具不存在或暂不可用")
    
    # 检查是否已有申请记录
    statement = select(UserToolPermission).where(
        UserToolPermission.user_id == current_user.id,
        UserToolPermission.tool_id == tool_id
    )
    existing_permission = db.exec(statement).first()
    
    if existing_permission:
        if existing_permission.status == PermissionStatus.PENDING:
            raise HTTPException(
                status_code=400,
                detail="您已存在该工具的待审核申请"
            )
        elif existing_permission.status == PermissionStatus.APPROVED:
            raise HTTPException(
                status_code=400,
                detail="您已拥有该工具权限"
            )
        # 如果之前被拒绝，可以重新申请
        # 更新现有记录
        existing_permission.status = PermissionStatus.PENDING
        existing_permission.applied_reason = permission_data.applied_reason
        existing_permission.reviewed_by = None
        existing_permission.reviewed_at = None
        existing_permission.review_notes = None
        db.add(existing_permission)
        db.commit()
        db.refresh(existing_permission)
        _notify_pending_reviewers(
            db,
            tool,
            existing_permission.id,
            current_user.id,
            current_user.username,
        )
        return existing_permission
    
    # 创建新的申请
    db_permission = UserToolPermission(
        user_id=current_user.id,
        tool_id=tool_id,
        applied_reason=permission_data.applied_reason
    )
    
    db.add(db_permission)
    db.commit()
    db.refresh(db_permission)

    _notify_pending_reviewers(
        db,
        tool,
        db_permission.id,
        current_user.id,
        current_user.username,
    )

    return db_permission

@router.get("/my-permissions", response_model=List[PermissionWithDetails])
async def get_my_permissions(
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_session)
):
    statement = select(UserToolPermission).where(
        UserToolPermission.user_id == current_user.id
    )
    permissions = db.exec(statement).all()
    
    # 加载关联数据
    result = []
    for perm in permissions:
        tool = db.get(Tool, perm.tool_id)
        if not tool or not is_tool_visible(tool.name):
            continue
        reviewer = db.get(User, perm.reviewed_by) if perm.reviewed_by else None
        
        # 创建包含详细信息的对象
        perm_with_details = PermissionWithDetails(
            **perm.dict(),
            user=current_user,
            tool=tool,
            reviewer=reviewer
        )
        result.append(perm_with_details)
    
    return result
