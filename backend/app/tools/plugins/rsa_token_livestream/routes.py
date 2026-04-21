"""rsa-token-livestream tool feature routes."""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
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


def _build_config_response(setting: RsaTokenLivestreamSetting) -> RsaLivestreamConfigResponse:
    return RsaLivestreamConfigResponse(
        stream_page_url=setting.stream_page_url,
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
        setting.stream_page_url = body.stream_page_url.strip()
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
