from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlmodel import Session, select

from app.api.v1.admin_common import ensure_tool_governance
from app.api.v1.pagination import normalize_count_result
from app.api.v1.rbac import ensure_platform_staff
from app.api.v1.users import get_current_active_user
from app.database import get_session
from app.models import Feedback, FeedbackCategory, Tool, User
from app.schemas import FeedbackCountsResponse, FeedbackWithUser, PaginatedFeedbackWithUser, UserInDB

router = APIRouter()


def build_feedback_items_with_users(db: Session, feedback_rows: list[Feedback]) -> list[FeedbackWithUser]:
    user_ids = {row.user_id for row in feedback_rows}
    users_by_id: dict[int, User] = {}
    if user_ids:
        users_by_id = {
            user.id: user for user in db.exec(select(User).where(User.id.in_(list(user_ids)))).all()
        }

    items: list[FeedbackWithUser] = []
    for row in feedback_rows:
        user = users_by_id.get(row.user_id)
        if user is None:
            continue
        items.append(
            FeedbackWithUser(
                id=row.id,
                user_id=row.user_id,
                tool_id=row.tool_id,
                category=row.category,
                title=row.title,
                content=row.content,
                created_at=row.created_at,
                user=UserInDB.model_validate(user),
            )
        )
    return items


def feedback_count_by_category(db: Session, category: str) -> int:
    raw_total = db.exec(
        select(func.count(Feedback.id)).where(Feedback.category == category)
    ).first()
    return normalize_count_result(raw_total)


@router.get("/tools/{tool_id}/feedback", response_model=PaginatedFeedbackWithUser)
async def list_tool_feedback(
    tool_id: int,
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = db.get(Tool, tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail="工具不存在")
    ensure_tool_governance(db, current_user, tool_id)

    limit = min(max(limit, 1), 500)
    raw_total = db.exec(
        select(func.count(Feedback.id)).where(
            Feedback.tool_id == tool_id,
            Feedback.category == FeedbackCategory.TOOL_USAGE.value,
        )
    ).first()
    total = normalize_count_result(raw_total)

    rows = db.exec(
        select(Feedback)
        .where(
            Feedback.tool_id == tool_id,
            Feedback.category == FeedbackCategory.TOOL_USAGE.value,
        )
        .order_by(Feedback.created_at.desc())
        .offset(skip)
        .limit(limit)
    ).all()
    return PaginatedFeedbackWithUser(total=total, items=build_feedback_items_with_users(db, rows))


@router.get("/feedback", response_model=PaginatedFeedbackWithUser)
async def list_global_feedback(
    category: Literal["system_feedback", "new_tool_suggestion"],
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    ensure_platform_staff(db, current_user)
    limit = min(max(limit, 1), 500)
    total = feedback_count_by_category(db, category)

    rows = db.exec(
        select(Feedback)
        .where(Feedback.category == category)
        .order_by(Feedback.created_at.desc())
        .offset(skip)
        .limit(limit)
    ).all()
    return PaginatedFeedbackWithUser(total=total, items=build_feedback_items_with_users(db, rows))


@router.get("/feedback/counts", response_model=FeedbackCountsResponse)
async def feedback_counts(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    ensure_platform_staff(db, current_user)
    n_sf = feedback_count_by_category(db, FeedbackCategory.SYSTEM_FEEDBACK.value)
    n_ns = feedback_count_by_category(db, FeedbackCategory.NEW_TOOL_SUGGESTION.value)
    return FeedbackCountsResponse(
        system_feedback=n_sf,
        new_tool_suggestion=n_ns,
        total=n_sf + n_ns,
    )
