import csv
import io
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import delete, func, or_
from sqlmodel import Session, select
from zoneinfo import ZoneInfo

from app.api.v1.admin_common import ensure_tool_governance
from app.api.v1.pagination import normalize_count_result
from app.api.v1.rbac import ensure_platform_staff, ensure_super_admin
from app.api.v1.users import get_current_active_user
from app.database import get_session
from app.models import APIAccessLog, Tool, User
from app.schemas import APIAccessLogWithUser, PaginatedAPIAccessLogs, SuccessResponse
from app.services.tool_behavior_catalog import resolve_behavior_label_from_tool

router = APIRouter()

_TZ_CN = ZoneInfo("Asia/Shanghai")


def _format_ts_cst8(dt: datetime | None) -> str:
    if dt is None:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(_TZ_CN).strftime("%Y-%m-%d %H:%M:%S")


def build_access_log_items(db: Session, logs: list[APIAccessLog]) -> list[APIAccessLogWithUser]:
    user_ids = {log.user_id for log in logs if log.user_id}
    tool_ids = {log.tool_id for log in logs if log.tool_id}

    users_by_id: dict[int, User] = {}
    if user_ids:
        users_by_id = {
            user.id: user for user in db.exec(select(User).where(User.id.in_(list(user_ids)))).all()
        }

    tools_by_id: dict[int, Tool] = {}
    if tool_ids:
        tools_by_id = {
            tool.id: tool for tool in db.exec(select(Tool).where(Tool.id.in_(list(tool_ids)))).all()
        }

    items: list[APIAccessLogWithUser] = []
    for log in logs:
        data = log.dict()
        if not data.get("behavior_label") and log.tool_id and log.feature_name:
            tool = tools_by_id.get(log.tool_id)
            data["behavior_label"] = resolve_behavior_label_from_tool(tool, log.feature_name)
        items.append(APIAccessLogWithUser(**data, user=users_by_id.get(log.user_id)))
    return items


def _audit_log_filter_conditions(
    user_id: int | None,
    tool_id: int | None,
    username: str | None,
    q: str | None = None,
):
    conditions = []
    if user_id is not None:
        conditions.append(APIAccessLog.user_id == user_id)
    if tool_id is not None:
        conditions.append(APIAccessLog.tool_id == tool_id)
    if username and username.strip():
        pattern = f"%{username.strip()}%"
        conditions.append(APIAccessLog.username.ilike(pattern))
    if q and q.strip():
        pattern = f"%{q.strip()}%"
        conditions.append(
            or_(
                APIAccessLog.path.ilike(pattern),
                APIAccessLog.feature_name.ilike(pattern),
                APIAccessLog.method.ilike(pattern),
                APIAccessLog.behavior_label.ilike(pattern),
            )
        )
    return conditions


@router.get("/tools/{tool_id}/usage-logs", response_model=PaginatedAPIAccessLogs)
async def get_tool_usage_logs(
    tool_id: int,
    skip: int = 0,
    limit: int = 100,
    username: str | None = None,
    q: str | None = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = db.get(Tool, tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail="工具不存在")
    ensure_tool_governance(db, current_user, tool_id)

    limit = min(max(limit, 1), 500)
    statement = select(APIAccessLog).where(
        APIAccessLog.tool_id == tool_id,
        APIAccessLog.feature_name != None,
    )
    count_stmt = select(func.count(APIAccessLog.id)).where(
        APIAccessLog.tool_id == tool_id,
        APIAccessLog.feature_name != None,
    )
    for cond in _audit_log_filter_conditions(None, None, username, q):
        statement = statement.where(cond)
        count_stmt = count_stmt.where(cond)
    total = normalize_count_result(db.exec(count_stmt).first())

    logs = db.exec(
        statement.order_by(APIAccessLog.created_at.desc()).offset(skip).limit(limit)
    ).all()
    return PaginatedAPIAccessLogs(total=total, items=build_access_log_items(db, logs))


@router.get("/audit-logs/export")
async def export_audit_logs_csv(
    user_id: int | None = None,
    tool_id: int | None = None,
    username: str | None = None,
    q: str | None = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    ensure_platform_staff(db, current_user)
    max_rows = 10_000
    statement = select(APIAccessLog)
    for cond in _audit_log_filter_conditions(user_id, tool_id, username, q):
        statement = statement.where(cond)
    logs = db.exec(
        statement.order_by(APIAccessLog.created_at.desc()).limit(max_rows)
    ).all()

    tool_ids = {log.tool_id for log in logs if log.tool_id}
    tools_by_id: dict[int, Tool] = {}
    if tool_ids:
        for t in db.exec(select(Tool).where(Tool.id.in_(list(tool_ids)))).all():
            tools_by_id[t.id] = t

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "id",
            "created_at",
            "username",
            "user_id",
            "method",
            "path",
            "feature_name",
            "behavior_label",
            "tool_id",
            "status_code",
            "latency_ms",
            "client_ip",
            "query_string",
        ]
    )
    for log in logs:
        bl = log.behavior_label
        if not bl and log.tool_id and log.feature_name:
            tool = tools_by_id.get(log.tool_id)
            bl = resolve_behavior_label_from_tool(tool, log.feature_name)
        writer.writerow(
            [
                log.id,
                _format_ts_cst8(log.created_at),
                log.username or "",
                log.user_id if log.user_id is not None else "",
                log.method,
                log.path,
                log.feature_name or "",
                bl or "",
                log.tool_id if log.tool_id is not None else "",
                log.status_code,
                log.latency_ms,
                log.client_ip or "",
                log.query_string or "",
            ]
        )
    payload = "\ufeff" + buf.getvalue()
    return StreamingResponse(
        iter([payload.encode("utf-8")]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="audit-logs.csv"'},
    )


@router.get("/audit-logs", response_model=PaginatedAPIAccessLogs)
async def get_all_audit_logs(
    skip: int = 0,
    limit: int = 20,
    user_id: int | None = None,
    tool_id: int | None = None,
    username: str | None = None,
    q: str | None = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    ensure_platform_staff(db, current_user)
    limit = min(max(limit, 1), 500)

    count_stmt = select(func.count(APIAccessLog.id))
    statement = select(APIAccessLog)
    for cond in _audit_log_filter_conditions(user_id, tool_id, username, q):
        count_stmt = count_stmt.where(cond)
        statement = statement.where(cond)

    total = normalize_count_result(db.exec(count_stmt).first())
    logs = db.exec(
        statement.order_by(APIAccessLog.created_at.desc()).offset(skip).limit(limit)
    ).all()
    return PaginatedAPIAccessLogs(total=total, items=build_access_log_items(db, logs))


@router.post("/audit-logs/clear", response_model=SuccessResponse)
async def clear_all_audit_logs(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    """清空全部 API 行为日志（apiaccesslog 表）。仅超级管理员。"""
    ensure_super_admin(current_user)
    count_stmt = select(func.count(APIAccessLog.id))
    total = normalize_count_result(db.exec(count_stmt).first())
    if total:
        db.exec(delete(APIAccessLog))
        db.commit()
    return SuccessResponse(message=f"已清空 {total} 条行为日志")
