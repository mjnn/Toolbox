import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import delete, func, or_
from sqlmodel import Session, select

from app.database import get_session
from app.models import Feedback, FeedbackCategory, Notification, Tool, ToolAnnouncement, User
from app.schemas import (
    AccountDeleteConfirm,
    FeedbackCreate,
    FeedbackInDB,
    NotificationInDB,
    PaginatedToolAnnouncements,
    PaginatedUsers,
    PasswordChangeRequest,
    SuccessResponse,
    UserInDB,
    UserUpdate,
    ToolAnnouncementInDB,
)
from app.services.user_deletion import delete_user_and_related
from app.api.v1.auth import verify_token, oauth2_scheme

router = APIRouter()

# 获取当前用户
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_session)
) -> User:
    username = verify_token(token)
    if not username:
        raise HTTPException(
            status_code=401,
            detail="认证信息无效，请重新登录"
        )
    
    statement = select(User).where(User.username == username)
    user = db.exec(statement).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="用户已被停用")
    
    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    if not current_user.is_approved:
        raise HTTPException(
            status_code=403,
            detail="账号待管理员审核",
        )
    return current_user


ALLOWED_AVATAR_TYPES = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",  # 部分客户端会发送非标准 MIME
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}
MAX_AVATAR_BYTES = 2 * 1024 * 1024


def _avatar_content_type_from_bytes(data: bytes) -> Optional[str]:
    """当 UploadFile 未带可靠 MIME 时，用魔数识别（与 Pillow 无关，仅看文件头）。"""
    if len(data) < 12:
        return None
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None

# API端点
@router.get("/me", response_model=UserInDB)
async def read_user_me(current_user: User = Depends(get_current_active_user)):
    return current_user

@router.get("/me/notifications", response_model=List[NotificationInDB])
async def list_my_notifications(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    items = db.exec(
        select(Notification)
        .where(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(200)
    ).all()
    return items


@router.get("/me/announcements", response_model=PaginatedToolAnnouncements)
async def list_my_announcements(
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    _ = current_user
    now = datetime.utcnow()
    limit = min(max(limit, 1), 200)
    rows = db.exec(
        select(ToolAnnouncement)
        .where(
            ToolAnnouncement.is_enabled == True,  # noqa: E712
            ToolAnnouncement.visibility == "global",
        )
        .order_by(ToolAnnouncement.created_at.desc())
    ).all()
    priority_rank = {"urgent": 0, "notice": 1, "reminder": 2}
    items: list[ToolAnnouncementInDB] = []
    for row in rows:
        if row.start_at and row.start_at > now:
            continue
        if row.end_at and row.end_at < now:
            continue
        try:
            disable_feature_slugs = json.loads(row.disable_feature_slugs_json or "[]")
        except Exception:
            disable_feature_slugs = []
        if not isinstance(disable_feature_slugs, list):
            disable_feature_slugs = []
        items.append(
            ToolAnnouncementInDB(
                id=row.id,
                tool_id=row.tool_id,
                title=row.title,
                content=row.content,
                is_enabled=row.is_enabled,
                start_at=row.start_at,
                end_at=row.end_at,
                visibility=row.visibility or "global",
                priority=row.priority or "notice",
                scroll_speed_seconds=int(row.scroll_speed_seconds or 45),
                font_family=row.font_family,
                font_size_px=int(row.font_size_px or 14),
                text_color=row.text_color,
                background_color=row.background_color,
                disable_feature_slugs=[str(v) for v in disable_feature_slugs if str(v).strip()],
                created_by=row.created_by,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
        )
    items.sort(
        key=lambda x: (
            priority_rank.get(x.priority, 99),
            -(x.created_at.timestamp() if x.created_at else 0),
        )
    )
    total = len(items)
    return PaginatedToolAnnouncements(total=total, items=items[skip : skip + limit])


@router.patch("/me/notifications/{notification_id}", response_model=NotificationInDB)
async def mark_my_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    notif = db.get(Notification, notification_id)
    if not notif or notif.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="通知不存在")
    notif.is_read = True
    db.add(notif)
    db.commit()
    db.refresh(notif)
    return notif


@router.delete("/me/notifications/{notification_id}", response_model=SuccessResponse)
async def delete_my_notification(
    notification_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    notif = db.get(Notification, notification_id)
    if not notif or notif.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="通知不存在")
    db.delete(notif)
    db.commit()
    return SuccessResponse(message="通知已删除")


@router.delete("/me/notifications", response_model=SuccessResponse)
async def clear_my_notifications(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    db.exec(delete(Notification).where(Notification.user_id == current_user.id))
    db.commit()
    return SuccessResponse(message="已清空全部通知")


@router.post("/me/feedback", response_model=FeedbackInDB)
async def submit_feedback(
    payload: FeedbackCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    content = (payload.content or "").strip()
    if len(content) < 5:
        raise HTTPException(status_code=400, detail="反馈内容至少 5 个字符")

    if payload.category == FeedbackCategory.TOOL_USAGE.value:
        if current_user.is_superuser:
            raise HTTPException(status_code=403, detail="管理员不通过该入口提交工具反馈")
        if payload.tool_id is None:
            raise HTTPException(status_code=400, detail="工具相关反馈必须指定 tool_id")
        tool = db.get(Tool, payload.tool_id)
        if not tool:
            raise HTTPException(status_code=404, detail="工具不存在")
        tool_id = payload.tool_id
    else:
        if payload.tool_id is not None:
            raise HTTPException(status_code=400, detail="此类反馈不应携带 tool_id")
        tool_id = None

    title = (payload.title or "").strip() or None

    fb = Feedback(
        user_id=current_user.id,
        tool_id=tool_id,
        category=payload.category,
        title=title,
        content=content,
    )
    db.add(fb)
    db.commit()
    db.refresh(fb)
    return fb


@router.put("/me", response_model=UserInDB)
async def update_user_me(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session)
):
    update_data = user_update.model_dump(exclude_unset=True)

    if "department" in update_data and update_data["department"] is not None:
        update_data["department"] = (update_data["department"] or "").strip() or None

    # 检查邮箱是否已被其他用户使用
    if "email" in update_data and update_data["email"] != current_user.email:
        statement = select(User).where(User.email == update_data["email"])
        existing_user = db.exec(statement).first()
        if existing_user:
            raise HTTPException(
                status_code=400,
                detail="邮箱已被其他用户注册"
            )
    
    for field, value in update_data.items():
        setattr(current_user, field, value)
    current_user.updated_at = datetime.utcnow()

    db.add(current_user)
    db.commit()
    db.refresh(current_user)

    return current_user


@router.delete("/me", response_model=SuccessResponse)
async def delete_my_account(
    body: AccountDeleteConfirm,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    from app.api.v1.auth import verify_password

    if not verify_password(body.password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="密码错误")

    if current_user.is_superuser:
        sups = db.exec(select(User).where(User.is_superuser == True)).all()  # noqa: E712
        if len(sups) <= 1:
            raise HTTPException(
                status_code=400,
                detail="不能删除唯一的超级管理员账号",
            )

    uid = current_user.id
    delete_user_and_related(db, uid)
    return SuccessResponse(message="账号已注销")


@router.post("/me/password", response_model=SuccessResponse)
async def change_my_password(
    body: PasswordChangeRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    from app.api.v1.auth import get_password_hash, verify_password

    if len(body.new_password) < 8:
        raise HTTPException(
            status_code=400,
            detail="新密码至少 8 位",
        )
    if not verify_password(body.old_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="当前密码错误")
    current_user.hashed_password = get_password_hash(body.new_password)
    db.add(current_user)
    db.commit()
    return SuccessResponse(message="密码已更新")


@router.post("/me/avatar", response_model=UserInDB)
async def upload_my_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    data = await file.read()
    if len(data) > MAX_AVATAR_BYTES:
        raise HTTPException(status_code=400, detail="文件过大（最大 2MB）")

    ct = (file.content_type or "").split(";")[0].strip()
    if ct not in ALLOWED_AVATAR_TYPES:
        sniffed = _avatar_content_type_from_bytes(data)
        if sniffed in ALLOWED_AVATAR_TYPES:
            ct = sniffed
        else:
            raise HTTPException(
                status_code=400,
                detail="不支持的图片类型（仅支持 JPEG、PNG、WebP、GIF）",
            )

    av_dir = Path("static") / "avatars"
    av_dir.mkdir(parents=True, exist_ok=True)
    ext = ALLOWED_AVATAR_TYPES[ct]
    fname = f"{current_user.id}{ext}"
    out_path = av_dir / fname
    out_path.write_bytes(data)

    current_user.avatar_url = f"/static/avatars/{fname}"
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user


# 管理员接口
@router.get("/", response_model=PaginatedUsers)
async def read_users(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    approval: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="权限不足")

    limit = min(max(limit, 1), 500)
    statement = select(User)
    count_stmt = select(func.count(User.id))
    if search and search.strip():
        pattern = f"%{search.strip()}%"
        filt = or_(
            User.username.ilike(pattern),
            User.email.ilike(pattern),
            User.full_name.ilike(pattern),
        )
        statement = statement.where(filt)
        count_stmt = count_stmt.where(filt)

    if approval == "pending":
        statement = statement.where(User.is_approved == False)  # noqa: E712
        count_stmt = count_stmt.where(User.is_approved == False)  # noqa: E712
    elif approval == "approved":
        statement = statement.where(User.is_approved == True)  # noqa: E712
        count_stmt = count_stmt.where(User.is_approved == True)  # noqa: E712

    raw_total = db.exec(count_stmt).first()
    if raw_total is None:
        total = 0
    elif isinstance(raw_total, int):
        total = raw_total
    else:
        total = int(raw_total[0])

    users = db.exec(
        statement.order_by(User.id).offset(skip).limit(limit)
    ).all()
    return PaginatedUsers(total=total, items=users)

@router.get("/{user_id}", response_model=UserInDB)
async def read_user(
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session)
):
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="权限不足")
    
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user
