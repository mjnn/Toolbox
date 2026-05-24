from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy import func, or_
from sqlmodel import Session, select
import httpx
import json

from app.database import get_session
from app.models import Tool, ToolDisplayConfig, ToolRelease, User
from app.schemas import PaginatedToolReleases, ToolInDB, ToolReleaseInDB, ToolVersionMetaResponse
from app.api.v1.users import get_current_active_user
import os

from app.api.v1.tools_common import ensure_tool_access, get_tool_or_404
from app.core.tool_visibility import get_visible_tool_keys
from app.tools.plugins.service_id_registry.routes import router as service_id_plugin_router
from app.tools.plugins.mos_integration_toolbox.routes import router as mos_plugin_router
from app.tools.plugins.rsa_token_livestream.routes import router as rsa_token_livestream_plugin_router
from app.tools.plugins.data_secure_manage.routes import router as data_secure_manage_plugin_router

router = APIRouter()

_TOOL_PLUGIN_SPECS: list[tuple[str, APIRouter]] = [
    ("service-id-registry", service_id_plugin_router),
    ("mos-integration-toolbox", mos_plugin_router),
    ("rsa-token-livestream", rsa_token_livestream_plugin_router),
    ("data-secure-manage", data_secure_manage_plugin_router),
]


_HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "host",
}


def _parse_tool_upstreams() -> dict[str, str]:
    """
    解析工具上游地址：
    TOOLBOX_TOOL_UPSTREAMS="service-id-registry=http://toolbox-tool-service-id:3000,m1=http://x:3000"
    """
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


def _include_conditional_plugin_routers() -> None:
    """
    默认不加载本地插件（宿主解耦模式）。
    仅当显式设置 TOOLBOX_LOAD_TOOL_PLUGINS 时，按工具名加载对应插件：
    - none/-/0: 不加载
    - all/*: 全加载
    - a,b,c: 按名单加载
    """
    raw = (os.getenv("TOOLBOX_LOAD_TOOL_PLUGINS") or "").strip()
    if not raw or raw.lower() in ("none", "-", "0"):
        return
    if raw in ("*", "all", "ALL"):
        for _, r in _TOOL_PLUGIN_SPECS:
            router.include_router(r)
        return
    allow = {x.strip() for x in raw.split(",") if x.strip()}
    for name, r in _TOOL_PLUGIN_SPECS:
        if name in allow:
            router.include_router(r)


def _to_tool_schema(tool: Tool, display_cfg: ToolDisplayConfig | None = None) -> ToolInDB:
    return ToolInDB(
        id=tool.id,
        name=tool.name,
        description=tool.description,
        display_name=display_cfg.display_name if display_cfg else None,
        display_description=display_cfg.display_description if display_cfg else None,
        version=tool.version,
        spec_revision=tool.spec_revision,
        behavior_catalog_json=tool.behavior_catalog_json,
        is_active=tool.is_active,
        runtime_status=tool.runtime_status,
        created_at=tool.created_at,
    )


def _version_meta_from_env() -> ToolVersionMetaResponse:
    version = str(os.getenv("TOOLBOX_VERSION") or "0.0.0").strip() or "0.0.0"
    spec_revision = str(os.getenv("TOOLBOX_SPEC_REVISION") or "").strip() or None
    title = str(os.getenv("TOOLBOX_VERSION_TITLE") or "工具版本更新").strip() or "工具版本更新"
    raw = str(os.getenv("TOOLBOX_CHANGELOG") or "").strip()
    if not raw:
        raw = "本次发布未提供详细变更说明。"
    # Accept either multiline text or JSON array string for deployment convenience.
    if raw.startswith("[") and raw.endswith("]"):
        try:
            rows = json.loads(raw)
            if isinstance(rows, list):
                lines = [str(x).strip() for x in rows if str(x).strip()]
                if lines:
                    raw = "\n".join(f"- {line}" for line in lines)
        except Exception:
            pass
    return ToolVersionMetaResponse(
        version=version,
        spec_revision=spec_revision,
        title=title,
        changelog=raw,
    )


@router.get("/meta/version", response_model=ToolVersionMetaResponse)
async def get_tool_version_meta():
    """
    Tool self-reported release metadata for host-side version governance.
    Host admin sync endpoint consumes this contract.
    """
    return _version_meta_from_env()


@router.get("/", response_model=List[ToolInDB])
def read_tools(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    db: Session = Depends(get_session),
):
    limit = min(max(limit, 1), 500)
    statement = (
        select(Tool, ToolDisplayConfig)
        .outerjoin(ToolDisplayConfig, ToolDisplayConfig.tool_id == Tool.id)
    )
    visible_keys = get_visible_tool_keys()
    if visible_keys:
        statement = statement.where(Tool.name.in_(visible_keys))
    if search and search.strip():
        pattern = f"%{search.strip()}%"
        statement = statement.where(
            or_(Tool.name.ilike(pattern), Tool.description.ilike(pattern))
        )
    rows = db.exec(statement.order_by(Tool.id).offset(skip).limit(limit)).all()
    if not rows:
        return []
    return [_to_tool_schema(tool, display_cfg) for tool, display_cfg in rows]


@router.get("/{tool_id}", response_model=ToolInDB)
async def read_tool(
    tool_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    ensure_tool_access(db, current_user, tool_id)
    display_cfg = db.exec(
        select(ToolDisplayConfig).where(ToolDisplayConfig.tool_id == tool_id)
    ).first()
    return _to_tool_schema(tool, display_cfg)


@router.get("/{tool_id}/releases", response_model=PaginatedToolReleases)
async def list_tool_releases(
    tool_id: int,
    skip: int = 0,
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    get_tool_or_404(db, tool_id)
    ensure_tool_access(db, current_user, tool_id)
    count_stmt = select(func.count(ToolRelease.id)).where(ToolRelease.tool_id == tool_id)
    raw_total = db.exec(count_stmt).first()
    total = int(raw_total) if raw_total is not None else 0
    rows = db.exec(
        select(ToolRelease)
        .where(ToolRelease.tool_id == tool_id)
        .order_by(ToolRelease.published_at.desc())
        .offset(skip)
        .limit(limit)
    ).all()
    items = [ToolReleaseInDB.model_validate(r) for r in rows]
    return PaginatedToolReleases(total=total, items=items)


_include_conditional_plugin_routers()


@router.api_route(
    "/{tool_id}/features/{feature_path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    include_in_schema=False,
)
async def proxy_tool_feature_request(
    tool_id: int,
    feature_path: str,
    request: Request,
    db: Session = Depends(get_session),
):
    """
    本地无命中路由时，把 /tools/{id}/features/* 透明转发到对应工具容器。
    映射来源：TOOLBOX_TOOL_UPSTREAMS（key=Tool.name）。
    """
    if not _TOOL_UPSTREAMS:
        raise HTTPException(status_code=404, detail="功能不存在")
    tool = db.get(Tool, tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail="工具不存在")
    upstream = _TOOL_UPSTREAMS.get(tool.name)
    if not upstream:
        raise HTTPException(status_code=404, detail="功能不存在")

    target_url = f"{upstream}/api/v1/tools/{tool_id}/features/{feature_path}"
    if request.url.query:
        target_url = f"{target_url}?{request.url.query}"

    body = await request.body()
    headers = {
        k: v
        for k, v in request.headers.items()
        if k.lower() not in _HOP_BY_HOP_HEADERS
    }
    timeout = httpx.Timeout(60.0, connect=10.0)
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
            upstream_resp = await client.request(
                request.method,
                target_url,
                headers=headers,
                content=body,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"工具转发失败: {exc}") from exc

    resp_headers = {
        k: v
        for k, v in upstream_resp.headers.items()
        if k.lower() not in _HOP_BY_HOP_HEADERS
    }
    return Response(
        content=upstream_resp.content,
        status_code=upstream_resp.status_code,
        headers=resp_headers,
        media_type=upstream_resp.headers.get("content-type"),
    )
