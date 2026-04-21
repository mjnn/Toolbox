"""mos-integration-toolbox tool feature routes."""
import json
import re
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlmodel import Session, select

from app.database import get_session
from app.models import (
    ConfigChangeLog,
    Notification,
    PermissionStatus,
    Tool,
    ToolAnnouncement,
    User,
    UserToolPermission,
)
from app.schemas import (
    PaginatedToolAnnouncements,
    ToolAnnouncementCreate,
    ToolAnnouncementInDB,
    ToolAnnouncementUpdate,
    ToolFeatureResponse,
    X509FeatureRequest,
    SimQueryRequest,
    UatAfDpQueryRequest,
    UatSpQueryRequest,
    UatVehicleImportRequest,
    UatVehicleConfigGenerateRequest,
    MosVehicleRuleRequest,
    MosVehicleRuleBulkImportRequest,
    MosRuntimeCredentialsUpdateRequest,
    MosTokenPreloadRequest,
)
from app.api.v1.users import get_current_active_user
from app.api.v1.tools_common import (
    ensure_tool_access,
    ensure_tool_active_or_superuser,
    get_tool_or_404,
    ensure_mos_integration_toolbox_tool,
    raise_feature_http_exception,
    ensure_manage_permission,
    can_manage_all_records,
)
from app.services.legacy_toolbox_adapter import (
    handle_x509_feature,
    query_unicom_sim,
    query_ctcc_sim,
    query_uat_af_dp,
    query_uat_sp_vehicle,
    bind_uat_enrollment,
    unbind_uat_enrollment,
    import_uat_vehicle_config,
    generate_uat_vehicle_import_data,
    list_uat_vehicle_config_rules,
    get_vehicle_rules_with_index,
    add_vehicle_rule,
    bulk_add_vehicle_rules,
    update_vehicle_rule,
    delete_vehicle_rule,
    get_runtime_credentials_masked,
    update_runtime_credentials,
    preload_mos_tokens,
)

router = APIRouter()
_FEATURE_SLUG_REGEX = re.compile(r"^[a-zA-Z0-9_/-]+$")
_HEX_COLOR_REGEX = re.compile(r"^#[0-9a-fA-F]{6}$")
_ANNOUNCEMENT_PRIORITIES = {"urgent", "notice", "reminder"}


def _record_mos_manage_change(
    db: Session,
    *,
    tool_id: int,
    current_user: User,
    action: str,
    target: str,
    summary: str | None = None,
) -> None:
    db.add(
        ConfigChangeLog(
            tool_id=tool_id,
            changed_by=current_user.id,
            action=action,
            target=target,
            summary=summary,
            created_at=datetime.utcnow(),
        )
    )
    db.commit()


def _is_announcement_active(row: ToolAnnouncement, now: datetime) -> bool:
    if not row.is_enabled:
        return False
    if row.start_at and row.start_at > now:
        return False
    if row.end_at and row.end_at < now:
        return False
    return True


def _normalize_disable_feature_slugs(items: list[str] | None) -> list[str]:
    rows = items or []
    uniq: set[str] = set()
    for raw in rows:
        slug = str(raw or "").strip()
        if not slug:
            continue
        if not _FEATURE_SLUG_REGEX.match(slug):
            raise HTTPException(status_code=400, detail=f"非法功能路径：{slug}")
        uniq.add(slug)
    return sorted(uniq)


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
        visibility=(row.visibility or "tool"),
        priority=(row.priority or "notice"),
        scroll_speed_seconds=int(row.scroll_speed_seconds or 45),
        font_family=row.font_family,
        font_size_px=int(row.font_size_px or 14),
        text_color=row.text_color,
        background_color=row.background_color,
        disable_feature_slugs=[str(item) for item in disable_feature_slugs if str(item).strip()],
        created_by=row.created_by,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _normalize_hex_color(raw: str | None, field_name: str) -> str | None:
    text = str(raw or "").strip()
    if not text:
        return None
    if not _HEX_COLOR_REGEX.match(text):
        raise HTTPException(status_code=400, detail=f"{field_name} 必须是 #RRGGBB 格式")
    return text


def _normalize_priority(raw: str | None) -> str:
    level = str(raw or "notice").strip().lower()
    if level not in _ANNOUNCEMENT_PRIORITIES:
        raise HTTPException(status_code=400, detail="公告优先级仅支持 urgent / notice / reminder")
    return level


def _is_feature_blocked_by_announcement(
    db: Session, tool_id: int, feature_slug: str, now: datetime
) -> bool:
    rows = db.exec(
        select(ToolAnnouncement).where(
            ToolAnnouncement.tool_id == tool_id,
            ToolAnnouncement.is_enabled == True,  # noqa: E712
            ToolAnnouncement.visibility == "tool",
        )
    ).all()
    for row in rows:
        if not _is_announcement_active(row, now):
            continue
        try:
            disabled = json.loads(row.disable_feature_slugs_json or "[]")
        except Exception:
            disabled = []
        if not isinstance(disabled, list):
            continue
        for raw in disabled:
            key = str(raw or "").strip()
            if key and (feature_slug == key or feature_slug.startswith(f"{key}/")):
                return True
    return False


def _ensure_mos_feature_access(
    db: Session,
    current_user: User,
    tool: Tool,
    feature_slug: str,
    *,
    allow_when_tool_inactive: bool = False,
) -> None:
    ensure_tool_access(db, current_user, tool.id)
    if not allow_when_tool_inactive:
        ensure_tool_active_or_superuser(current_user, tool)
    if current_user.is_superuser:
        return
    if _is_feature_blocked_by_announcement(db, tool.id, feature_slug, datetime.utcnow()):
        raise HTTPException(status_code=403, detail="该功能模块维护中，暂不可用")


def _announcement_recipients(db: Session, tool_id: int, now: datetime) -> set[int]:
    rows = db.exec(
        select(UserToolPermission).where(
            UserToolPermission.tool_id == tool_id,
            UserToolPermission.status == PermissionStatus.APPROVED,
        )
    ).all()
    return {
        row.user_id
        for row in rows
        if row.expires_at is None or row.expires_at > now
    }


def _validate_mos_vehicle_rule(rule: dict[str, object]) -> list[str]:
    required_fields = [
        "项目版本号",
        "OCU类型",
        "品牌",
        "车机类型",
        "燃油类型",
        "车机软件版本号",
        "PRNR",
        "发电机号",
        "运营商",
        "产线平台",
        "HU零件号",
        "OCU零件号",
    ]
    errors: list[str] = []
    for key in required_fields:
        if key not in rule:
            errors.append(f"缺少字段: {key}")
    patterns = rule.get("车机软件版本号")
    if not isinstance(patterns, list) or not patterns:
        errors.append("字段“车机软件版本号”必须是非空数组")
    else:
        invalid = [item for item in patterns if not isinstance(item, str) or not item.strip()]
        if invalid:
            errors.append("字段“车机软件版本号”包含空值或非字符串")
    project = str(rule.get("项目版本号") or "").strip()
    if not project:
        errors.append("字段“项目版本号”不能为空")
    return errors

@router.post("/{tool_id}/features/x509-cert", response_model=ToolFeatureResponse)
async def x509_cert_feature(
    tool_id: int,
    body: X509FeatureRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    ensure_mos_integration_toolbox_tool(tool)
    _ensure_mos_feature_access(db, current_user, tool, "x509-cert")

    try:
        if body.action == "check" and not body.iam_sns:
            raise HTTPException(status_code=400, detail="check 动作需要 iam_sns")
        if body.action == "sign" and not body.csrs:
            raise HTTPException(status_code=400, detail="sign 动作需要 csrs")
        if body.action == "parse_csr" and not body.csr:
            raise HTTPException(status_code=400, detail="parse_csr 动作需要 csr")
        if body.action == "parse_cert" and not body.cert:
            raise HTTPException(status_code=400, detail="parse_cert 动作需要 cert")

        result = handle_x509_feature(
            action=body.action,
            env=body.env,
            iam_sns=body.iam_sns,
            csrs=body.csrs,
            csr=body.csr,
            cert=body.cert,
        )
        return ToolFeatureResponse(
            success=bool(result.get("success", False)),
            message="请求完成" if result.get("success") else "请求失败",
            data=result.get("data"),
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise_feature_http_exception("IAM X509 功能执行失败", exc)


@router.post("/{tool_id}/features/token-preload", response_model=ToolFeatureResponse)
async def token_preload_feature(
    tool_id: int,
    body: MosTokenPreloadRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    ensure_mos_integration_toolbox_tool(tool)
    _ensure_mos_feature_access(db, current_user, tool, "token-preload")
    try:
        data = preload_mos_tokens(
            scopes=body.scopes,
            wait=body.wait,
            timeout_seconds=body.timeout_seconds,
            force_refresh=body.force_refresh,
        )
        if data.get("has_errors"):
            return ToolFeatureResponse(success=False, message="Token 预热存在失败项", data=data)
        return ToolFeatureResponse(success=True, message="Token 预热请求已处理", data=data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise_feature_http_exception("Token 预热失败", exc)


@router.get("/{tool_id}/features/token-preload/visibility", response_model=ToolFeatureResponse)
async def token_preload_visibility_feature(
    tool_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    ensure_mos_integration_toolbox_tool(tool)
    _ensure_mos_feature_access(db, current_user, tool, "token-preload/visibility")
    can_manage = can_manage_all_records(db, current_user, tool_id)
    return ToolFeatureResponse(
        success=True,
        message="加载成功",
        data={"can_manage": can_manage},
    )


@router.post("/{tool_id}/features/sim-query", response_model=ToolFeatureResponse)
async def sim_query_feature(
    tool_id: int,
    body: SimQueryRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    ensure_mos_integration_toolbox_tool(tool)
    _ensure_mos_feature_access(db, current_user, tool, "sim-query")

    try:
        if body.provider == "unicom":
            if not body.project or not body.search_value:
                raise HTTPException(status_code=400, detail="联通查询需要 project 与 search_value")
            data = query_unicom_sim(project=body.project, search_value=body.search_value.strip())
            return ToolFeatureResponse(
                success=True,
                message="查询成功（联通首次请求可能较慢，最多约 3 分钟）",
                data=data,
            )

        if not (body.iccid or body.msisdn or body.imsi):
            raise HTTPException(status_code=400, detail="电信查询至少需要 iccid/msisdn/imsi 之一")
        result = query_ctcc_sim(iccid=body.iccid, msisdn=body.msisdn, imsi=body.imsi)
        return ToolFeatureResponse(
            success=bool(result.get("success", False)),
            message="查询成功" if result.get("success") else "查询失败",
            data=result.get("data"),
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise_feature_http_exception("SIM 查询失败", exc)


@router.post("/{tool_id}/features/uat-af-dp-query", response_model=ToolFeatureResponse)
async def uat_af_dp_query_feature(
    tool_id: int,
    body: UatAfDpQueryRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    ensure_mos_integration_toolbox_tool(tool)
    _ensure_mos_feature_access(db, current_user, tool, "uat-af-dp-query")

    if not any([body.vin, body.zxdsn, body.iamsn, body.iccid]):
        raise HTTPException(status_code=400, detail="vin/zxdsn/iamsn/iccid 至少填写一个")

    try:
        result = query_uat_af_dp(vin=body.vin, zxdsn=body.zxdsn, iamsn=body.iamsn, iccid=body.iccid)
        return ToolFeatureResponse(
            success=bool(result.get("success", False)),
            message="查询成功" if result.get("success") else "查询失败",
            data=result.get("data"),
        )
    except Exception as exc:
        raise_feature_http_exception("UAT AF DP 查询失败", exc)


@router.post("/{tool_id}/features/uat-sp-query", response_model=ToolFeatureResponse)
async def uat_sp_query_feature(
    tool_id: int,
    body: UatSpQueryRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    ensure_mos_integration_toolbox_tool(tool)
    _ensure_mos_feature_access(db, current_user, tool, "uat-sp-query")

    try:
        vin = body.vin.strip()
        if body.action == "query_sp_info":
            result = query_uat_sp_vehicle(vin=vin)
        elif body.action == "bind":
            phone = (body.phone or "").strip()
            if not phone:
                raise HTTPException(status_code=400, detail="绑车操作需要手机号")
            result = bind_uat_enrollment(vin=vin, phone=phone)
        else:
            result = unbind_uat_enrollment(vin=vin)
        return ToolFeatureResponse(
            success=bool(result.get("success", False)),
            message="执行成功" if result.get("success") else "执行失败",
            data=result.get("data"),
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise_feature_http_exception("UAT Enrollment 操作失败", exc)


@router.post("/{tool_id}/features/uat-vehicle-import", response_model=ToolFeatureResponse)
async def uat_vehicle_import_feature(
    tool_id: int,
    body: UatVehicleImportRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    ensure_mos_integration_toolbox_tool(tool)
    _ensure_mos_feature_access(db, current_user, tool, "uat-vehicle-import")

    try:
        result = import_uat_vehicle_config(
            target=body.target,
            check_duplicated=body.check_duplicated,
            vehicle_data=body.vehicle_data,
        )
        return ToolFeatureResponse(
            success=bool(result.get("success", False)),
            message="导入成功" if result.get("success") else "导入失败",
            data=result.get("data"),
        )
    except Exception as exc:
        raise_feature_http_exception("UAT 车辆配置导入失败", exc)


@router.post("/{tool_id}/features/uat-vehicle-config-generate", response_model=ToolFeatureResponse)
async def uat_vehicle_config_generate_feature(
    tool_id: int,
    body: UatVehicleConfigGenerateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    ensure_mos_integration_toolbox_tool(tool)
    _ensure_mos_feature_access(db, current_user, tool, "uat-vehicle-config-generate")

    result = generate_uat_vehicle_import_data(
        project=body.project.strip(),
        car_software_version=body.car_software_version.strip(),
        hu_fazit_id=body.hu_fazit_id.strip(),
        ocu_iccid=body.ocu_iccid.strip(),
        msisdn=body.msisdn.strip(),
        ocu_fazit_id=body.ocu_fazit_id.strip(),
        vehicle_vin=body.vehicle_vin.strip().upper(),
        application_department=body.application_department.strip(),
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("data") or "规则匹配失败")
    return ToolFeatureResponse(success=True, message="规则匹配成功", data=result.get("data"))


@router.get("/{tool_id}/features/uat-vehicle-config-rules", response_model=ToolFeatureResponse)
async def uat_vehicle_config_rules_feature(
    tool_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    ensure_mos_integration_toolbox_tool(tool)
    _ensure_mos_feature_access(db, current_user, tool, "uat-vehicle-config-rules")

    data = list_uat_vehicle_config_rules()
    return ToolFeatureResponse(success=True, message="规则加载成功", data=data)


@router.get("/{tool_id}/features/announcement-feed", response_model=PaginatedToolAnnouncements)
async def list_active_announcements_feature(
    tool_id: int,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=200),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    ensure_mos_integration_toolbox_tool(tool)
    _ensure_mos_feature_access(
        db,
        current_user,
        tool,
        "announcement-feed",
        allow_when_tool_inactive=True,
    )
    now = datetime.utcnow()
    rows = db.exec(
        select(ToolAnnouncement)
        .where(
            ToolAnnouncement.tool_id == tool_id,
            ToolAnnouncement.visibility == "tool",
        )
        .order_by(ToolAnnouncement.created_at.desc())
    ).all()
    items = [_build_announcement_schema(row) for row in rows if _is_announcement_active(row, now)]
    return PaginatedToolAnnouncements(total=len(items), items=items[skip : skip + limit])


@router.get("/{tool_id}/features/mos-manage/announcements", response_model=PaginatedToolAnnouncements)
async def list_mos_announcements_manage_feature(
    tool_id: int,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=200),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    ensure_mos_integration_toolbox_tool(tool)
    ensure_manage_permission(db, current_user, tool_id)
    total_raw = db.exec(
        select(func.count(ToolAnnouncement.id)).where(
            ToolAnnouncement.tool_id == tool_id,
            ToolAnnouncement.visibility == "tool",
        )
    ).first()
    total = int(total_raw) if total_raw is not None else 0
    rows = db.exec(
        select(ToolAnnouncement)
        .where(
            ToolAnnouncement.tool_id == tool_id,
            ToolAnnouncement.visibility == "tool",
        )
        .order_by(ToolAnnouncement.created_at.desc())
        .offset(skip)
        .limit(limit)
    ).all()
    return PaginatedToolAnnouncements(
        total=total,
        items=[_build_announcement_schema(row) for row in rows],
    )


@router.post("/{tool_id}/features/mos-manage/announcements", response_model=ToolAnnouncementInDB)
async def create_mos_announcement_manage_feature(
    tool_id: int,
    body: ToolAnnouncementCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    ensure_mos_integration_toolbox_tool(tool)
    ensure_manage_permission(db, current_user, tool_id)
    if body.end_at and body.start_at and body.end_at < body.start_at:
        raise HTTPException(status_code=400, detail="结束时间不能早于开始时间")
    disable_slugs = _normalize_disable_feature_slugs(body.disable_feature_slugs)
    priority = _normalize_priority(body.priority)
    text_color = _normalize_hex_color(body.text_color, "text_color")
    background_color = _normalize_hex_color(body.background_color, "background_color")
    font_family = (body.font_family or "").strip() or None
    now = datetime.utcnow()
    row = ToolAnnouncement(
        tool_id=tool_id,
        visibility="tool",
        priority=priority,
        title=body.title.strip(),
        content=body.content.strip(),
        is_enabled=body.is_enabled,
        start_at=body.start_at,
        end_at=body.end_at,
        scroll_speed_seconds=body.scroll_speed_seconds,
        font_family=font_family,
        font_size_px=body.font_size_px,
        text_color=text_color,
        background_color=background_color,
        disable_feature_slugs_json=json.dumps(disable_slugs, ensure_ascii=False),
        created_by=current_user.id,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    if row.is_enabled:
        notify_message = row.content
        if row.disable_feature_slugs_json and row.disable_feature_slugs_json != "[]":
            try:
                slugs = json.loads(row.disable_feature_slugs_json)
            except Exception:
                slugs = []
            if isinstance(slugs, list) and slugs:
                notify_message += f"\n\n维护模块：{'、'.join([str(item) for item in slugs if str(item).strip()])}"
        if row.start_at or row.end_at:
            start_label = row.start_at.strftime("%Y-%m-%d %H:%M:%S") if row.start_at else "立即生效"
            end_label = row.end_at.strftime("%Y-%m-%d %H:%M:%S") if row.end_at else "长期有效"
            notify_message += f"\n生效时间：{start_label} 至 {end_label}"
        for uid in _announcement_recipients(db, tool_id, now):
            db.add(
                Notification(
                    user_id=uid,
                    title=f"工具「{tool.name}」发布公告：{row.title}",
                    message=notify_message,
                    notification_type="tool",
                    related_id=tool_id,
                )
            )
        db.commit()
    _record_mos_manage_change(
        db,
        tool_id=tool_id,
        current_user=current_user,
        action="create",
        target="announcement",
        summary=f"发布公告：{row.title}",
    )
    return _build_announcement_schema(row)


@router.patch(
    "/{tool_id}/features/mos-manage/announcements/{announcement_id}",
    response_model=ToolAnnouncementInDB,
)
async def update_mos_announcement_manage_feature(
    tool_id: int,
    announcement_id: int,
    body: ToolAnnouncementUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    ensure_mos_integration_toolbox_tool(tool)
    ensure_manage_permission(db, current_user, tool_id)
    row = db.get(ToolAnnouncement, announcement_id)
    if not row or row.tool_id != tool_id or (row.visibility or "tool") != "tool":
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
    if body.priority is not None:
        row.priority = _normalize_priority(body.priority)
    if body.scroll_speed_seconds is not None:
        row.scroll_speed_seconds = body.scroll_speed_seconds
    if body.font_family is not None:
        row.font_family = (body.font_family or "").strip() or None
    if body.font_size_px is not None:
        row.font_size_px = body.font_size_px
    if body.text_color is not None:
        row.text_color = _normalize_hex_color(body.text_color, "text_color")
    if body.background_color is not None:
        row.background_color = _normalize_hex_color(body.background_color, "background_color")
    if row.end_at and row.start_at and row.end_at < row.start_at:
        raise HTTPException(status_code=400, detail="结束时间不能早于开始时间")
    if body.disable_feature_slugs is not None:
        disable_slugs = _normalize_disable_feature_slugs(body.disable_feature_slugs)
        row.disable_feature_slugs_json = json.dumps(disable_slugs, ensure_ascii=False)
    row.updated_at = datetime.utcnow()
    db.add(row)
    db.commit()
    db.refresh(row)
    _record_mos_manage_change(
        db,
        tool_id=tool_id,
        current_user=current_user,
        action="update",
        target="announcement",
        summary=f"更新公告：{row.title}",
    )
    return _build_announcement_schema(row)


@router.get("/{tool_id}/features/mos-manage/vehicle-rules", response_model=ToolFeatureResponse)
async def list_mos_vehicle_rules_manage_feature(
    tool_id: int,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=200),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    ensure_mos_integration_toolbox_tool(tool)
    ensure_manage_permission(db, current_user, tool_id)
    rules = get_vehicle_rules_with_index()
    total = len(rules)
    items = rules[skip : skip + limit]
    return ToolFeatureResponse(success=True, message="加载成功", data={"total": total, "items": items})


@router.post("/{tool_id}/features/mos-manage/vehicle-rules", response_model=ToolFeatureResponse)
async def create_mos_vehicle_rule_manage_feature(
    tool_id: int,
    body: MosVehicleRuleRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    ensure_mos_integration_toolbox_tool(tool)
    ensure_manage_permission(db, current_user, tool_id)
    rules = add_vehicle_rule(body.rule)
    _record_mos_manage_change(
        db,
        tool_id=tool_id,
        current_user=current_user,
        action="create",
        target="vehicle_rule",
        summary=f"新增车辆规则，项目={body.rule.get('项目版本号', '')}",
    )
    return ToolFeatureResponse(success=True, message="新增规则成功", data={"rules": rules})


@router.post("/{tool_id}/features/mos-manage/vehicle-rules/bulk-import", response_model=ToolFeatureResponse)
async def bulk_import_mos_vehicle_rules_manage_feature(
    tool_id: int,
    body: MosVehicleRuleBulkImportRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    ensure_mos_integration_toolbox_tool(tool)
    ensure_manage_permission(db, current_user, tool_id)
    if not body.rules:
        raise HTTPException(status_code=400, detail="rules 不能为空")

    validation_items: list[dict[str, object]] = []
    valid_rules: list[dict[str, object]] = []
    for idx, rule in enumerate(body.rules):
        if not isinstance(rule, dict):
            validation_items.append(
                {"index": idx, "valid": False, "project": "", "errors": ["规则必须是 JSON 对象"]}
            )
            continue
        errors = _validate_mos_vehicle_rule(rule)
        project = str(rule.get("项目版本号") or "")
        validation_items.append(
            {"index": idx, "valid": not errors, "project": project, "errors": errors}
        )
        if not errors:
            valid_rules.append(rule)

    has_errors = any(not item["valid"] for item in validation_items)
    if body.dry_run:
        return ToolFeatureResponse(
            success=True,
            message="预校验完成",
            data={
                "dry_run": True,
                "total": len(body.rules),
                "valid_count": len(valid_rules),
                "invalid_count": len(body.rules) - len(valid_rules),
                "has_errors": has_errors,
                "items": validation_items,
            },
        )

    if has_errors:
        raise HTTPException(status_code=400, detail="存在无效规则，请先修正后再导入")

    rules = bulk_add_vehicle_rules(valid_rules)
    _record_mos_manage_change(
        db,
        tool_id=tool_id,
        current_user=current_user,
        action="bulk_import",
        target="vehicle_rule",
        summary=f"批量导入车辆规则 {len(valid_rules)} 条",
    )
    return ToolFeatureResponse(
        success=True,
        message=f"已导入 {len(valid_rules)} 条规则",
        data={"rules": rules, "imported_count": len(valid_rules)},
    )


@router.put("/{tool_id}/features/mos-manage/vehicle-rules/{rule_index}", response_model=ToolFeatureResponse)
async def update_mos_vehicle_rule_manage_feature(
    tool_id: int,
    rule_index: int,
    body: MosVehicleRuleRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    ensure_mos_integration_toolbox_tool(tool)
    ensure_manage_permission(db, current_user, tool_id)
    try:
        rules = update_vehicle_rule(rule_index, body.rule)
    except IndexError:
        raise HTTPException(status_code=404, detail="规则不存在")
    _record_mos_manage_change(
        db,
        tool_id=tool_id,
        current_user=current_user,
        action="update",
        target="vehicle_rule",
        summary=f"更新车辆规则索引={rule_index}，项目={body.rule.get('项目版本号', '')}",
    )
    return ToolFeatureResponse(success=True, message="更新规则成功", data={"rules": rules})


@router.delete("/{tool_id}/features/mos-manage/vehicle-rules/{rule_index}", response_model=ToolFeatureResponse)
async def delete_mos_vehicle_rule_manage_feature(
    tool_id: int,
    rule_index: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    ensure_mos_integration_toolbox_tool(tool)
    ensure_manage_permission(db, current_user, tool_id)
    try:
        rules = delete_vehicle_rule(rule_index)
    except IndexError:
        raise HTTPException(status_code=404, detail="规则不存在")
    _record_mos_manage_change(
        db,
        tool_id=tool_id,
        current_user=current_user,
        action="delete",
        target="vehicle_rule",
        summary=f"删除车辆规则索引={rule_index}",
    )
    return ToolFeatureResponse(success=True, message="删除规则成功", data={"rules": rules})


@router.get("/{tool_id}/features/mos-manage/runtime-credentials", response_model=ToolFeatureResponse)
async def get_runtime_credentials_manage_feature(
    tool_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    ensure_mos_integration_toolbox_tool(tool)
    ensure_manage_permission(db, current_user, tool_id)
    return ToolFeatureResponse(success=True, message="加载成功", data=get_runtime_credentials_masked())


@router.put("/{tool_id}/features/mos-manage/runtime-credentials", response_model=ToolFeatureResponse)
async def update_runtime_credentials_manage_feature(
    tool_id: int,
    body: MosRuntimeCredentialsUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    ensure_mos_integration_toolbox_tool(tool)
    ensure_manage_permission(db, current_user, tool_id)
    data = update_runtime_credentials(
        uat_mos_portal_account=body.uat_mos_portal_account,
        uat_mos_portal_password=body.uat_mos_portal_password,
        oa_account=body.oa_account,
        oa_password=body.oa_password,
        request_timeout_seconds=body.request_timeout_seconds,
    )
    touched = []
    if body.uat_mos_portal_account is not None:
        touched.append("uat_mos_portal_account")
    if body.uat_mos_portal_password:
        touched.append("uat_mos_portal_password")
    if body.oa_account is not None:
        touched.append("oa_account")
    if body.oa_password:
        touched.append("oa_password")
    if body.request_timeout_seconds is not None:
        touched.append("request_timeout_seconds")
    _record_mos_manage_change(
        db,
        tool_id=tool_id,
        current_user=current_user,
        action="update",
        target="runtime_credentials",
        summary=f"更新后端配置字段: {', '.join(touched) if touched else 'none'}",
    )
    return ToolFeatureResponse(success=True, message="后端配置更新成功", data=data)


@router.get("/{tool_id}/features/mos-manage/change-logs", response_model=ToolFeatureResponse)
async def list_mos_manage_change_logs_feature(
    tool_id: int,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=200),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    ensure_mos_integration_toolbox_tool(tool)
    ensure_manage_permission(db, current_user, tool_id)
    total_raw = db.exec(
        select(func.count(ConfigChangeLog.id))
        .where(ConfigChangeLog.tool_id == tool_id)
    ).first()
    total = int(total_raw) if total_raw is not None else 0
    logs = db.exec(
        select(ConfigChangeLog)
        .where(ConfigChangeLog.tool_id == tool_id)
        .order_by(ConfigChangeLog.created_at.desc())
        .offset(skip)
        .limit(limit)
    ).all()
    users = {}
    for row in logs:
        if row.changed_by not in users:
            user = db.get(User, row.changed_by)
            users[row.changed_by] = user.username if user else str(row.changed_by)
    data = [
        {
            "id": row.id,
            "action": row.action,
            "target": row.target,
            "summary": row.summary,
            "changed_by": row.changed_by,
            "changed_by_name": users.get(row.changed_by, str(row.changed_by)),
            "created_at": row.created_at,
        }
        for row in logs
    ]
    return ToolFeatureResponse(success=True, message="加载成功", data={"total": total, "items": data})


