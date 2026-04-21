"""删除用户及其关联数据（保留匿名化的访问日志）。"""

from sqlalchemy import delete
from sqlmodel import Session, select

from app.models import (
    APIAccessLog,
    Feedback,
    Notification,
    ToolOwner,
    User,
    UserRole,
    UserToolPermission,
)


def delete_user_and_related(db: Session, user_id: int) -> None:
    for p in db.exec(
        select(UserToolPermission).where(UserToolPermission.reviewed_by == user_id)
    ).all():
        p.reviewed_by = None
        db.add(p)

    db.exec(delete(UserRole).where(UserRole.user_id == user_id))
    db.exec(delete(ToolOwner).where(ToolOwner.user_id == user_id))
    db.exec(delete(UserToolPermission).where(UserToolPermission.user_id == user_id))
    db.exec(delete(Notification).where(Notification.user_id == user_id))
    db.exec(delete(Feedback).where(Feedback.user_id == user_id))

    for log in db.exec(select(APIAccessLog).where(APIAccessLog.user_id == user_id)).all():
        log.user_id = None
        db.add(log)

    u = db.get(User, user_id)
    if u:
        db.delete(u)
    db.commit()
