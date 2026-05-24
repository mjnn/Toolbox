import os
from datetime import datetime

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.api.v1.admin_common import ensure_tool_governance, recipient_user_ids_for_tool
from app.api.v1.users import get_current_active_user
from app.database import get_session
from app.models import Notification, Tool, ToolRelease, User
from app.schemas import ToolReleaseInDB, ToolVersionSyncRequest, ToolVersionSyncResult

router = APIRouter()


def _parse_tool_upstreams() -> dict[str, str]:
    raw = (os.getenv("TOOLBOX_TOOL_UPSTREAMS") or "").strip()
    if not raw:
        return {}
    out: dict[str, str] = {}
    for seg in raw.split(","):
        item = seg.strip()
        if not item or "=" not in item:
            continue
        key, val = item.split("=", 1)
        name = key.strip()
        base = val.strip().rstrip("/")
        if not name or not base:
            continue
        if not (base.startswith("http://") or base.startswith("https://")):
            continue
        out[name] = base
    return out


_TOOL_UPSTREAMS = _parse_tool_upstreams()


def _notification_message_for_release(tool_name: str, row: ToolRelease) -> str:
    header = f"版本：{row.version}"
    if row.spec_revision:
        header += f"　规格修订：{row.spec_revision}"
    body = f"{row.title}\n\n{row.changelog}"
    if len(body) > 2500:
        body = body[:2500] + "\n…（完整说明请在工具的「更新记录」中查看）"
    return f"{header}\n\n{body}"


def _normalize_tool_version_payload(raw: dict) -> tuple[str, str | None, str, str]:
    version = str(raw.get("version") or "").strip()
    if not version:
        raise HTTPException(status_code=502, detail="工具版本接口未返回有效 version")
    spec_revision = str(raw.get("spec_revision") or raw.get("specRevision") or "").strip() or None
    title = str(raw.get("title") or raw.get("summary") or "工具版本更新").strip() or "工具版本更新"
    changelog_value = raw.get("changelog")
    if changelog_value is None:
        changelog_value = raw.get("changes")
    if changelog_value is None:
        changelog_value = raw.get("release_notes")
    if changelog_value is None:
        changelog_value = raw.get("change_log")
    if isinstance(changelog_value, list):
        changelog = "\n".join(f"- {str(item).strip()}" for item in changelog_value if str(item).strip())
    else:
        changelog = str(changelog_value or "").strip()
    if not changelog:
        raise HTTPException(status_code=502, detail="工具版本接口未返回有效 changelog/changes")
    return version, spec_revision, title, changelog


async def _fetch_tool_version_from_upstream(tool: Tool) -> tuple[str, str | None, str, str]:
    upstream = _TOOL_UPSTREAMS.get(tool.name)
    if not upstream:
        raise HTTPException(
            status_code=400,
            detail=f"工具「{tool.name}」未配置上游地址（TOOLBOX_TOOL_UPSTREAMS）",
        )
    candidate_paths = (
        "/api/v1/meta/version",
        "/api/v1/version",
        "/api/v1/tools/meta/version",
        "/version",
    )
    timeout = httpx.Timeout(8.0, connect=3.0)
    last_error = ""
    async with httpx.AsyncClient(timeout=timeout) as client:
        for path in candidate_paths:
            target = f"{upstream}{path}"
            try:
                resp = await client.get(target)
            except httpx.HTTPError as exc:
                last_error = str(exc)
                continue
            if resp.status_code == 404:
                continue
            if resp.status_code >= 400:
                last_error = f"HTTP {resp.status_code}"
                continue
            try:
                payload = resp.json()
            except ValueError as exc:
                last_error = f"invalid json: {exc}"
                continue
            if not isinstance(payload, dict):
                last_error = "response json is not object"
                continue
            return _normalize_tool_version_payload(payload)
    raise HTTPException(
        status_code=502,
        detail=(
            f"无法从工具「{tool.name}」读取版本信息。"
            f"请确保上游实现 /api/v1/meta/version（或 /api/v1/version）。{last_error}"
        ),
    )


@router.post("/tools/{tool_id}/version-records/sync", response_model=ToolVersionSyncResult)
async def sync_tool_version_record(
    tool_id: int,
    body: ToolVersionSyncRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = db.get(Tool, tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail="工具不存在")
    ensure_tool_governance(db, current_user, tool_id)

    version, spec_revision, title, changelog = await _fetch_tool_version_from_upstream(tool)
    latest = db.exec(
        select(ToolRelease)
        .where(ToolRelease.tool_id == tool_id)
        .order_by(ToolRelease.published_at.desc())
    ).first()
    no_change = bool(
        latest
        and latest.version == version
        and (latest.spec_revision or "") == (spec_revision or "")
        and latest.changelog.strip() == changelog.strip()
    )

    if no_change and latest:
        tool.version = version
        tool.spec_revision = spec_revision
        db.add(tool)
        db.commit()
        return ToolVersionSyncResult(
            status="no_change",
            message="与最新版本记录一致，无需新增记录",
            release=ToolReleaseInDB.model_validate(latest),
        )

    row = ToolRelease(
        tool_id=tool_id,
        version=version,
        spec_revision=spec_revision,
        title=title,
        changelog=changelog,
        published_at=datetime.utcnow(),
        published_by=current_user.id,
    )
    tool.version = version
    tool.spec_revision = spec_revision
    db.add(row)
    db.add(tool)
    db.commit()
    db.refresh(row)

    if body.notify_users:
        notify_title = f"工具「{tool.name}」版本同步 {row.version}"
        notify_msg = _notification_message_for_release(tool.name, row)
        for uid in recipient_user_ids_for_tool(db, tool_id):
            db.add(
                Notification(
                    user_id=uid,
                    title=notify_title,
                    message=notify_msg,
                    notification_type="tool_release",
                    related_id=tool_id,
                )
            )
        db.commit()

    return ToolVersionSyncResult(
        status="recorded",
        message="已从工具接口同步并记录新版本",
        release=ToolReleaseInDB.model_validate(row),
    )
