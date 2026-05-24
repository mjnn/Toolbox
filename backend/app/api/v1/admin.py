import io
import json
import os
import re
import subprocess
import threading
import time
from typing import List, Literal
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import func, or_
from sqlmodel import Session, select

from app.database import get_session
from app.models import (
    Tool,
    User,
    PermissionStatus,
    Notification,
    ToolDisplayConfig,
    Role,
    UserRole,
    APIAccessLog,
    ToolAnnouncement,
    ToolRuntimeStatus,
)
from app.schemas import (
    SuccessResponse,
    ToolInDB,
    ToolStatusUpdate,
    UserInDB,
    ToolAnnouncementCreate,
    ToolAnnouncementInDB,
    ToolAnnouncementUpdate,
    PaginatedToolAnnouncements,
    ToolDisplayConfigUpdate,
    MosDbOptimizationUpdateRequest,
    ToolVisibilityConfigUpdate,
    ToolVisibilityConfigResponse,
    ToolTrafficDashboardResponse,
    ToolTrafficRow,
    EnvFilePayload,
    BackendRestartRequest,
)
from app.core.config_simple import BACKEND_ROOT
from app.api.v1.users import get_current_active_user
from app.api.v1.rbac import ensure_platform_staff, ensure_super_admin, has_role
from app.api.v1.admin_common import ensure_tool_governance, recipient_user_ids_for_tool
from app.core.tool_visibility import (
    load_tool_visibility_config,
    resolve_runtime_environment,
    save_tool_visibility_config,
)
from app.services import db_optimization_runtime
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

router = APIRouter()

_TZ_CN = ZoneInfo("Asia/Shanghai")
_ANNOUNCEMENT_PRIORITIES = {"urgent", "notice", "reminder"}
_GLOBAL_ANNOUNCEMENT_TOOL_NAME = "mos-integration-toolbox"


def _is_announcement_active(row: ToolAnnouncement, now: datetime) -> bool:
    if not row.is_enabled:
        return False
    if row.start_at and row.start_at > now:
        return False
    if row.end_at and row.end_at < now:
        return False
    return True


def _normalize_announcement_priority(raw: str | None) -> str:
    level = str(raw or "notice").strip().lower()
    if level not in _ANNOUNCEMENT_PRIORITIES:
        raise HTTPException(status_code=400, detail="公告优先级仅支持 urgent / notice / reminder")
    return level


def _priority_colors(priority: str) -> tuple[str, str]:
    if priority == "urgent":
        return "#ffffff", "#c62828"
    if priority == "reminder":
        return "#5f370e", "#fff4e5"
    return "#102a43", "#e8f4fd"


def _build_announcement_schema(row: ToolAnnouncement) -> ToolAnnouncementInDB:
    try:
        disable_feature_slugs = json.loads(row.disable_feature_slugs_json or "[]")
    except Exception:
        disable_feature_slugs = []
    if not isinstance(disable_feature_slugs, list):
        disable_feature_slugs = []
    return ToolAnnouncementInDB(
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


def _resolve_global_announcement_tool_id(db: Session) -> int:
    tool = db.exec(select(Tool).where(Tool.name == _GLOBAL_ANNOUNCEMENT_TOOL_NAME)).first()
    if not tool or not tool.id:
        raise HTTPException(status_code=500, detail="未找到全局公告绑定工具，请联系管理员")
    return int(tool.id)


def _split_hosts(raw_hosts: list[str] | None) -> list[str]:
    if not raw_hosts:
        return []
    out: list[str] = []
    for item in raw_hosts:
        for token in re.split(r"[,\n;\s]+", str(item or "").strip()):
            value = token.strip().lower()
            if value:
                out.append(value)
    return sorted({h for h in out if h})


def _extract_request_host(request: Request) -> str | None:
    return (
        request.headers.get("X-Forwarded-Host")
        or request.headers.get("Host")
        or request.url.hostname
    )


def _load_all_tools_sorted(db: Session) -> list[Tool]:
    return db.exec(select(Tool).order_by(Tool.id)).all()


def _tool_visibility_response(
    db: Session,
    request: Request,
    cfg: dict,
) -> ToolVisibilityConfigResponse:
    current_host = _extract_request_host(request)
    runtime_env, source = resolve_runtime_environment(current_host)
    all_tools = [_build_tool_schema(db, tool) for tool in _load_all_tools_sorted(db)]
    return ToolVisibilityConfigResponse(
        current_runtime_env=runtime_env,  # type: ignore[arg-type]
        runtime_env_source=source,
        external_hosts=[str(v) for v in cfg.get("external_hosts", [])],
        internal_visible_tool_keys=[str(v) for v in cfg.get("internal_visible_tool_keys", [])],
        external_visible_tool_keys=[str(v) for v in cfg.get("external_visible_tool_keys", [])],
        all_tools=all_tools,
    )


def _build_tool_schema(db: Session, tool: Tool) -> ToolInDB:
    cfg = db.exec(select(ToolDisplayConfig).where(ToolDisplayConfig.tool_id == tool.id)).first()
    return ToolInDB(
        id=tool.id,
        name=tool.name,
        description=tool.description,
        display_name=cfg.display_name if cfg else None,
        display_description=cfg.display_description if cfg else None,
        version=tool.version,
        spec_revision=tool.spec_revision,
        behavior_catalog_json=tool.behavior_catalog_json,
        is_active=tool.is_active,
        runtime_status=tool.runtime_status,
        created_at=tool.created_at,
    )


@router.get("/announcements/global", response_model=PaginatedToolAnnouncements)
async def list_global_announcements(
    skip: int = 0,
    limit: int = 20,
    only_active: bool = False,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    ensure_super_admin(current_user)
    limit = min(max(limit, 1), 200)
    rows = db.exec(
        select(ToolAnnouncement)
        .where(ToolAnnouncement.visibility == "global")
        .order_by(ToolAnnouncement.created_at.desc())
    ).all()
    if only_active:
        now = datetime.utcnow()
        rows = [row for row in rows if _is_announcement_active(row, now)]
    total = len(rows)
    page_items = rows[skip : skip + limit]
    return PaginatedToolAnnouncements(
        total=total,
        items=[_build_announcement_schema(row) for row in page_items],
    )


@router.post("/announcements/global", response_model=ToolAnnouncementInDB)
async def create_global_announcement(
    body: ToolAnnouncementCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    ensure_super_admin(current_user)
    tool_id = _resolve_global_announcement_tool_id(db)
    if body.end_at and body.start_at and body.end_at < body.start_at:
        raise HTTPException(status_code=400, detail="结束时间不能早于开始时间")
    now = datetime.utcnow()
    priority = _normalize_announcement_priority(body.priority)
    text_color, background_color = _priority_colors(priority)
    row = ToolAnnouncement(
        tool_id=tool_id,
        visibility="global",
        priority=priority,
        title=body.title.strip(),
        content=body.content.strip(),
        is_enabled=body.is_enabled,
        start_at=body.start_at,
        end_at=body.end_at,
        scroll_speed_seconds=body.scroll_speed_seconds,
        font_family=(body.font_family or "").strip() or None,
        font_size_px=body.font_size_px,
        text_color=text_color,
        background_color=background_color,
        disable_feature_slugs_json="[]",
        created_by=current_user.id,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    if row.is_enabled:
        users = db.exec(
            select(User).where(
                User.is_active == True,  # noqa: E712
                User.is_approved == True,  # noqa: E712
            )
        ).all()
        for u in users:
            db.add(
                Notification(
                    user_id=u.id,
                    title=f"系统公告：{row.title}",
                    message=row.content,
                    notification_type="system",
                    related_id=row.id,
                )
            )
        db.commit()
    return _build_announcement_schema(row)


@router.patch("/announcements/global/{announcement_id}", response_model=ToolAnnouncementInDB)
async def update_global_announcement(
    announcement_id: int,
    body: ToolAnnouncementUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    ensure_super_admin(current_user)
    tool_id = _resolve_global_announcement_tool_id(db)
    row = db.get(ToolAnnouncement, announcement_id)
    if not row or (row.visibility or "global") != "global":
        raise HTTPException(status_code=404, detail="公告不存在")
    if body.title is not None:
        row.title = body.title.strip()
    if body.content is not None:
        row.content = body.content.strip()
    if body.is_enabled is not None:
        row.is_enabled = body.is_enabled
    if body.start_at is not None:
        row.start_at = body.start_at
    if body.end_at is not None:
        row.end_at = body.end_at
    if row.end_at and row.start_at and row.end_at < row.start_at:
        raise HTTPException(status_code=400, detail="结束时间不能早于开始时间")
    if body.priority is not None:
        row.priority = _normalize_announcement_priority(body.priority)
    text_color, background_color = _priority_colors(row.priority or "notice")
    if body.scroll_speed_seconds is not None:
        row.scroll_speed_seconds = body.scroll_speed_seconds
    if body.font_family is not None:
        row.font_family = (body.font_family or "").strip() or None
    if body.font_size_px is not None:
        row.font_size_px = body.font_size_px
    row.text_color = text_color
    row.background_color = background_color
    row.visibility = "global"
    row.tool_id = tool_id
    row.disable_feature_slugs_json = "[]"
    row.updated_at = datetime.utcnow()
    db.add(row)
    db.commit()
    db.refresh(row)
    return _build_announcement_schema(row)


@router.get("/system/db-optimization", response_model=dict)
async def get_system_db_optimization(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    _ = db
    ensure_super_admin(current_user)
    return db_optimization_runtime.build_db_optimization_read_payload(
        note="调参请在「系统配置」编辑 .env 并按规定重启后端，或维护期人工编辑部署机配置；修改后需重启后端进程生效。",
    )


@router.put("/system/db-optimization", response_model=dict)
async def update_system_db_optimization(
    body: MosDbOptimizationUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    _ = db
    ensure_super_admin(current_user)
    return db_optimization_runtime.apply_db_optimization_update(body)


@router.post("/system/db-optimization/ping", response_model=dict)
async def ping_system_db_optimization(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    ensure_super_admin(current_user)
    return {"elapsed_ms": db_optimization_runtime.ping_database_ms(db)}


@router.get("/system/tool-visibility", response_model=ToolVisibilityConfigResponse)
async def get_system_tool_visibility(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    ensure_super_admin(current_user)
    cfg = load_tool_visibility_config()
    return _tool_visibility_response(db, request, cfg)


@router.put("/system/tool-visibility", response_model=ToolVisibilityConfigResponse)
async def update_system_tool_visibility(
    payload: ToolVisibilityConfigUpdate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    ensure_super_admin(current_user)
    cfg = load_tool_visibility_config()

    existing_names = {str(t.name).strip() for t in _load_all_tools_sorted(db)}
    if payload.internal_visible_tool_keys is not None:
        unknown = sorted(
            {k for k in payload.internal_visible_tool_keys if str(k).strip() not in existing_names}
        )
        if unknown:
            raise HTTPException(status_code=400, detail=f"内网可见工具不存在：{', '.join(unknown)}")
        cfg["internal_visible_tool_keys"] = sorted(
            {str(k).strip() for k in payload.internal_visible_tool_keys if str(k).strip()}
        )

    if payload.external_visible_tool_keys is not None:
        unknown = sorted(
            {k for k in payload.external_visible_tool_keys if str(k).strip() not in existing_names}
        )
        if unknown:
            raise HTTPException(status_code=400, detail=f"外网可见工具不存在：{', '.join(unknown)}")
        cfg["external_visible_tool_keys"] = sorted(
            {str(k).strip() for k in payload.external_visible_tool_keys if str(k).strip()}
        )

    if payload.external_hosts is not None:
        cfg["external_hosts"] = _split_hosts(payload.external_hosts)
        if not cfg["external_hosts"]:
            cfg["external_hosts"] = ["47.116.180.173"]

    saved = save_tool_visibility_config(
        external_hosts=cfg.get("external_hosts", []),
        internal_visible_tool_keys=cfg.get("internal_visible_tool_keys", []),
        external_visible_tool_keys=cfg.get("external_visible_tool_keys", []),
    )
    return _tool_visibility_response(db, request, saved)


def _staff_excluded_user_ids(db: Session) -> set[int]:
    """工具访问量统计需排除：超级管理员 + 平台管理员（自身操作不计入业务流量）。"""
    ids: set[int] = set()
    for u in db.exec(select(User).where(User.is_superuser == True)).all():  # noqa: E712
        if u.id is not None:
            ids.add(int(u.id))
    role = db.exec(select(Role).where(Role.name == "platform_admin")).first()
    if role:
        for ur in db.exec(select(UserRole).where(UserRole.role_id == role.id)).all():
            ids.add(int(ur.user_id))
    return ids


_ENV_FILE_PATH = Path(BACKEND_ROOT) / ".env"


@router.get("/analytics/tool-traffic", response_model=ToolTrafficDashboardResponse)
async def get_tool_traffic_dashboard(
    period: Literal["day", "week", "month"] = "day",
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    """按日/周/月汇总各工具 API 请求量（有 tool_id 的访问日志），排除超管与平台管理员自身。"""
    ensure_platform_staff(db, current_user)
    end = datetime.utcnow()
    if period == "day":
        start = end - timedelta(days=1)
    elif period == "week":
        start = end - timedelta(days=7)
    else:
        start = end - timedelta(days=30)

    excluded = _staff_excluded_user_ids(db)
    stmt = (
        select(APIAccessLog.tool_id, func.count(APIAccessLog.id))
        .where(
            APIAccessLog.tool_id != None,  # noqa: E711
            APIAccessLog.created_at >= start,
            APIAccessLog.created_at <= end,
        )
    )
    if excluded:
        stmt = stmt.where(
            or_(APIAccessLog.user_id == None, ~APIAccessLog.user_id.in_(list(excluded)))  # noqa: E711
        )
    stmt = stmt.group_by(APIAccessLog.tool_id).order_by(func.count(APIAccessLog.id).desc())
    raw_rows = db.exec(stmt).all()
    out: list[ToolTrafficRow] = []
    for row in raw_rows:
        tid = int(row[0])
        cnt = int(row[1])
        tool = db.get(Tool, tid)
        out.append(
            ToolTrafficRow(
                tool_id=tid,
                tool_name=tool.name if tool else str(tid),
                request_count=cnt,
            )
        )
    return ToolTrafficDashboardResponse(
        period=period,
        range_start=start,
        range_end=end,
        rows=out,
    )


@router.get("/system/env-file", response_model=EnvFilePayload)
async def get_env_file(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    _ = db
    ensure_super_admin(current_user)
    path = _ENV_FILE_PATH
    if not path.exists():
        return EnvFilePayload(content="")
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"读取 .env 失败：{exc}") from exc
    return EnvFilePayload(content=text)


@router.put("/system/env-file", response_model=SuccessResponse)
async def put_env_file(
    body: EnvFilePayload,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    _ = db
    ensure_super_admin(current_user)
    path = _ENV_FILE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    try:
        tmp.write_text(body.content, encoding="utf-8", newline="\n")
        tmp.replace(path)
    except OSError as exc:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass
        raise HTTPException(status_code=500, detail=f"写入 .env 失败：{exc}") from exc
    return SuccessResponse(message=".env 已保存；部分配置需重启后端进程后生效。")


def _run_backend_restart_command() -> None:
    time.sleep(0.5)
    cmd = (os.environ.get("TOOLBOX_BACKEND_RESTART_CMD") or "").strip()
    if not cmd:
        return
    try:
        subprocess.Popen(cmd, shell=True)  # noqa: S602
    except OSError:
        pass


@router.post("/system/backend/restart", response_model=SuccessResponse)
async def restart_backend_process(
    body: BackendRestartRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    """触发外部重启命令（需配置 TOOLBOX_BACKEND_RESTART_CMD，如 nssm/systemctl 包装脚本）。"""
    _ = db
    ensure_super_admin(current_user)
    expected = "CONFIRM_BACKEND_RESTART"
    if (body.confirmation or "").strip() != expected:
        raise HTTPException(
            status_code=400,
            detail=f'确认码不正确，请提交 confirmation="{expected}"',
        )
    cmd = (os.environ.get("TOOLBOX_BACKEND_RESTART_CMD") or "").strip()
    if not cmd:
        raise HTTPException(
            status_code=400,
            detail="未配置环境变量 TOOLBOX_BACKEND_RESTART_CMD，无法从页面触发自动重启。请在服务器进程管理器中手动重启后端。",
        )
    threading.Thread(target=_run_backend_restart_command, daemon=True).start()
    return SuccessResponse(message="重启命令已提交，请稍候由外部拉起新进程。")


@router.patch("/tools/{tool_id}/status", response_model=ToolInDB)
async def update_tool_status(
    tool_id: int,
    body: ToolStatusUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = db.get(Tool, tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail="工具不存在")
    ensure_tool_governance(db, current_user, tool_id)

    changed = False
    if body.is_active is not None and tool.is_active != body.is_active:
        tool.is_active = body.is_active
        changed = True
    if body.runtime_status is not None and tool.runtime_status != body.runtime_status:
        tool.runtime_status = body.runtime_status
        changed = True
    if not changed:
        return _build_tool_schema(db, tool)

    db.add(tool)
    db.commit()
    db.refresh(tool)

    parts: list[str] = []
    if body.is_active is not None:
        parts.append("可用" if tool.is_active else "暂不可用")
    if body.runtime_status is not None:
        parts.append(
            "运行中" if tool.runtime_status == ToolRuntimeStatus.ACTIVE else "更新中"
        )
    status_label = "；".join(parts) if parts else "已更新"
    for uid in recipient_user_ids_for_tool(db, tool_id):
        db.add(
            Notification(
                user_id=uid,
                title=f"工具「{tool.name}」状态变更",
                message=f"工具「{tool.name}」当前状态：{status_label}。",
                notification_type="tool",
                related_id=tool_id,
            )
        )
    db.commit()
    return _build_tool_schema(db, tool)


@router.put("/tools/{tool_id}/display-config", response_model=ToolInDB)
async def update_tool_display_config(
    tool_id: int,
    body: ToolDisplayConfigUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = db.get(Tool, tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail="工具不存在")
    ensure_tool_governance(db, current_user, tool_id)

    display_name = body.display_name.strip() if body.display_name is not None else None
    display_description = body.display_description.strip() if body.display_description is not None else None
    if display_name == "":
        display_name = None
    if display_description == "":
        display_description = None

    row = db.exec(select(ToolDisplayConfig).where(ToolDisplayConfig.tool_id == tool_id)).first()
    if not display_name and not display_description:
        if row:
            db.delete(row)
            db.commit()
        return _build_tool_schema(db, tool)

    now = datetime.utcnow()
    if not row:
        row = ToolDisplayConfig(
            tool_id=tool_id,
            display_name=display_name,
            display_description=display_description,
            updated_by=current_user.id,
            updated_at=now,
        )
    else:
        row.display_name = display_name
        row.display_description = display_description
        row.updated_by = current_user.id
        row.updated_at = now
    db.add(row)
    db.commit()
    return _build_tool_schema(db, tool)


