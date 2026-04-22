from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_
from sqlmodel import Session, select

from app.database import get_session
from app.models import Tool, ToolDisplayConfig, ToolRelease, User
from app.schemas import PaginatedToolReleases, ToolInDB, ToolReleaseInDB
from app.api.v1.users import get_current_active_user
from app.api.v1.tools_common import ensure_tool_access, get_tool_or_404
from app.core.tool_visibility import get_visible_tool_keys
from app.tools.plugins.service_id_registry.routes import router as service_id_plugin_router
from app.tools.plugins.mos_integration_toolbox.routes import router as mos_plugin_router
from app.tools.plugins.rsa_token_livestream.routes import router as rsa_token_livestream_plugin_router

router = APIRouter()


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
        created_at=tool.created_at,
    )


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


router.include_router(service_id_plugin_router)
router.include_router(mos_plugin_router)
router.include_router(rsa_token_livestream_plugin_router)
