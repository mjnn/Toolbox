"""rsa-token-livestream tool feature routes."""
from datetime import datetime
from urllib.parse import parse_qs, urlparse, urlunparse

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select

from app.database import get_session
from app.models import RsaTokenLivestreamSetting, Tool, User
from app.schemas import RsaLivestreamConfigResponse, RsaLivestreamConfigUpdateRequest
from app.api.v1.users import get_current_active_user
from app.api.v1.tools_common import (
    ensure_manage_permission,
    ensure_rsa_token_livestream_tool,
    ensure_tool_access,
    get_tool_or_404,
)

router = APIRouter()

_DEFAULT_STREAM_PAGE_URL = (
    "http://47.116.180.173:8080/players/srs_player.html?autostart=true&app=live&stream=livestream.flv"
    "&server=47.116.180.173&port=8080&vhost=47.116.180.173&schema=http"
)
_DEFAULT_STREAM_SERVER = "rtmp://47.116.180.173:1935/live"
_DEFAULT_STREAM_KEY = "livestream"
_DEFAULT_PLACEHOLDER_TITLE = "直播暂时关闭"
_DEFAULT_PLACEHOLDER_MESSAGE = "当前 RSA Token 直播暂未开放，请联系工具负责人确认直播时间。"


def _ensure_tool_feature_access(db: Session, current_user: User, tool: Tool) -> None:
    if not tool.is_active and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="工具暂不可用")
    ensure_tool_access(db, current_user, tool.id)


def _get_or_create_livestream_setting(
    db: Session, *, tool_id: int, current_user: User
) -> RsaTokenLivestreamSetting:
    setting = db.exec(
        select(RsaTokenLivestreamSetting).where(RsaTokenLivestreamSetting.tool_id == tool_id)
    ).first()
    if setting:
        return setting
    setting = RsaTokenLivestreamSetting(
        tool_id=tool_id,
        stream_page_url=_DEFAULT_STREAM_PAGE_URL,
        stream_server=_DEFAULT_STREAM_SERVER,
        stream_key=_DEFAULT_STREAM_KEY,
        placeholder_enabled=True,
        placeholder_title=_DEFAULT_PLACEHOLDER_TITLE,
        placeholder_message=_DEFAULT_PLACEHOLDER_MESSAGE,
        updated_by=current_user.id,
        updated_at=datetime.utcnow(),
    )
    db.add(setting)
    db.commit()
    db.refresh(setting)
    return setting


def _build_resolved_flv_url(stream_page_url: str) -> str | None:
    parsed = urlparse(stream_page_url)
    if parsed.path.lower().endswith(".flv"):
        return parsed._replace(query="").geturl()
    q = parse_qs(parsed.query)
    stream_raw = str((q.get("stream", [""])[0] or "")).strip()
    app_raw = str((q.get("app", [""])[0] or "")).strip()
    if not stream_raw:
        return None
    stream_name = stream_raw
    app_name = app_raw or "live"
    server = str((q.get("server", [parsed.hostname or ""])[0] or parsed.hostname or "")).strip()
    if not server:
        return None
    schema = str((q.get("schema", [parsed.scheme or "http"])[0] or parsed.scheme or "http")).strip().lower()
    if schema not in {"http", "https"}:
        schema = "http"
    port_raw = str((q.get("port", [str(parsed.port or 8080)])[0] or str(parsed.port or 8080))).strip()
    try:
        port = int(port_raw)
    except ValueError:
        return None
    path = f"/{app_name}/{stream_name}"
    return urlunparse((schema, f"{server}:{port}", path, "", "", ""))


def _build_config_response(setting: RsaTokenLivestreamSetting) -> RsaLivestreamConfigResponse:
    return RsaLivestreamConfigResponse(
        stream_page_url=setting.stream_page_url,
        resolved_stream_flv_url=_build_resolved_flv_url(setting.stream_page_url),
        internal_flv_proxy_url=f"/api/v1/tools/{setting.tool_id}/features/livestream/flv-proxy",
        stream_server=setting.stream_server,
        stream_key=setting.stream_key,
        placeholder_enabled=setting.placeholder_enabled,
        placeholder_title=setting.placeholder_title,
        placeholder_message=setting.placeholder_message,
        updated_at=setting.updated_at,
    )


@router.get("/{tool_id}/features/livestream/config", response_model=RsaLivestreamConfigResponse)
async def get_livestream_config(
    tool_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    ensure_rsa_token_livestream_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    setting = _get_or_create_livestream_setting(db, tool_id=tool_id, current_user=current_user)
    return _build_config_response(setting)


def _validate_http_url(value: str, field_name: str) -> str:
    normalized = value.strip()
    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise HTTPException(status_code=400, detail=f"{field_name} 必须是有效的 HTTP/HTTPS 地址")
    return normalized


@router.put("/{tool_id}/features/livestream/manage-config", response_model=RsaLivestreamConfigResponse)
async def update_livestream_manage_config(
    tool_id: int,
    body: RsaLivestreamConfigUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    ensure_rsa_token_livestream_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    ensure_manage_permission(db, current_user, tool_id)

    if (
        body.stream_page_url is None
        and body.stream_server is None
        and body.stream_key is None
        and body.placeholder_enabled is None
        and body.placeholder_title is None
        and body.placeholder_message is None
    ):
        raise HTTPException(status_code=400, detail="请至少提供一个要更新的配置项")

    setting = _get_or_create_livestream_setting(db, tool_id=tool_id, current_user=current_user)

    if body.stream_page_url is not None:
        setting.stream_page_url = _validate_http_url(body.stream_page_url, "直播页面地址")
    if body.stream_server is not None:
        setting.stream_server = body.stream_server.strip()
    if body.stream_key is not None:
        setting.stream_key = body.stream_key.strip()
    if body.placeholder_enabled is not None:
        setting.placeholder_enabled = body.placeholder_enabled
    if body.placeholder_title is not None:
        setting.placeholder_title = body.placeholder_title.strip()
    if body.placeholder_message is not None:
        setting.placeholder_message = body.placeholder_message.strip()

    setting.updated_by = current_user.id
    setting.updated_at = datetime.utcnow()
    db.add(setting)
    db.commit()
    db.refresh(setting)
    return _build_config_response(setting)


@router.get("/{tool_id}/features/livestream/flv-proxy")
async def relay_livestream_flv(
    tool_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    ensure_rsa_token_livestream_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    setting = _get_or_create_livestream_setting(db, tool_id=tool_id, current_user=current_user)
    stream_flv_url = _build_resolved_flv_url(setting.stream_page_url)
    if not stream_flv_url:
        raise HTTPException(
            status_code=400,
            detail="当前直播页面地址无法解析为 FLV 源地址，请在管理页改为可访问的 .flv 地址或标准 SRS 播放页地址",
        )

    async def iter_stream():
        timeout = httpx.Timeout(connect=10.0, read=None, write=10.0, pool=30.0)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            async with client.stream("GET", stream_flv_url) as resp:
                if resp.status_code >= 400:
                    raise HTTPException(status_code=502, detail="直播源暂不可用，请稍后重试")
                async for chunk in resp.aiter_bytes():
                    if chunk:
                        yield chunk

    return StreamingResponse(
        iter_stream(),
        media_type="video/x-flv",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Pragma": "no-cache",
        },
    )
