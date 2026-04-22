"""service-id-registry tool feature routes."""
import csv
import io
import json
import re
from urllib.parse import quote
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, or_
from sqlmodel import Session, select

from app.database import get_session
from app.models import (
    Tool,
    User,
    ServiceIdRegistryEntry,
    ServiceIdRuleOption,
    ServiceRuleCategory,
    ServiceBaseUrlMode,
)
from app.schemas import (
    SuccessResponse,
    ServiceIdEntryCreate,
    ServiceIdEntryUpdate,
    ServiceIdEntryInDB,
    ServiceIdEntryListResponse,
    ServiceIdRuleOptionCreate,
    ServiceIdRuleOptionUpdate,
    ServiceIdRuleOptionDelete,
    ServiceIdRuleOptionInDB,
    ServiceIdRuleOptionGroupResponse,
    PaginatedServiceIdRuleOptions,
    ServiceBaseUrlJsonRow,
    ServiceIdFieldConfigItem,
    ServiceIdFieldConfigListResponse,
    ServiceIdFieldConfigUpdateRequest,
    ServiceIdFieldConfigCreateRequest,
    ServiceIdFieldConfigDeleteRequest,
)
from app.api.v1.users import get_current_active_user
from app.api.v1.tools_common import (
    ensure_tool_access,
    get_tool_or_404,
    ensure_service_id_registry_tool,
    can_manage_all_records,
    ensure_manage_permission,
)
from app.services import service_id_dynamic_fields as dynamic_fields

router = APIRouter()

_PACKAGE_NAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_.]*$")


def _ensure_tool_feature_access(db: Session, current_user: User, tool: Tool) -> None:
    if not tool.is_active and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="工具暂不可用")
    ensure_tool_access(db, current_user, tool.id)


def _is_ascii_text(value: str) -> bool:
    return all(ord(ch) < 128 for ch in value)


def _validate_base_url_inputs(
    mode: ServiceBaseUrlMode,
    json_key: str | None,
    test_input: str,
    uat_input: str,
    live_input: str,
    json_rows: list[ServiceBaseUrlJsonRow] | None = None,
) -> tuple[str | None, str, str, str]:
    test_value = test_input.strip()
    uat_value = uat_input.strip()
    live_value = live_input.strip()

    if not test_value or not uat_value or not live_value:
        raise HTTPException(status_code=400, detail="Base URL 的测试（Test）/预发（UAT）/生产（Live）均为必填")

    if mode == ServiceBaseUrlMode.STRING:
        for value in (test_value, uat_value, live_value):
            if not _is_ascii_text(value):
                raise HTTPException(status_code=400, detail="Base URL 字符串模式仅支持英文字符")
        return None, test_value, uat_value, live_value

    if json_rows:
        normalized_rows: list[tuple[str, str, str, str]] = []
        seen_keys: set[str] = set()
        for row in json_rows:
            key = row.key.strip()
            test_val = row.test.strip()
            uat_val = row.uat.strip()
            live_val = row.live.strip()
            if not key or not test_val or not uat_val or not live_val:
                raise HTTPException(status_code=400, detail="JSON 行中的键（key）/Test/UAT/Live 均为必填")
            if key in seen_keys:
                raise HTTPException(status_code=400, detail=f"JSON 键（key）重复：{key}")
            if not _is_ascii_text(key):
                raise HTTPException(status_code=400, detail="JSON 模式下键（key）仅支持英文字符")
            for val in (test_val, uat_val, live_val):
                if not _is_ascii_text(val):
                    raise HTTPException(status_code=400, detail="JSON 模式下 Base URL 值仅支持英文字符")
            seen_keys.add(key)
            normalized_rows.append((key, test_val, uat_val, live_val))

        test_map = {key: test_val for key, test_val, _, _ in normalized_rows}
        uat_map = {key: uat_val for key, _, uat_val, _ in normalized_rows}
        live_map = {key: live_val for key, _, _, live_val in normalized_rows}
        primary_key = normalized_rows[0][0]
        return (
            primary_key,
            json.dumps(test_map, separators=(",", ":"), ensure_ascii=True),
            json.dumps(uat_map, separators=(",", ":"), ensure_ascii=True),
            json.dumps(live_map, separators=(",", ":"), ensure_ascii=True),
        )

    key = (json_key or "").strip()
    if not key:
        raise HTTPException(status_code=400, detail="JSON 模式下 base_url_json_key（JSON 键）为必填")
    if not _is_ascii_text(key):
        raise HTTPException(status_code=400, detail="JSON 模式下 base_url_json_key（JSON 键）仅支持英文字符")
    for value in (test_value, uat_value, live_value):
        if not _is_ascii_text(value):
            raise HTTPException(status_code=400, detail="JSON 模式下 Base URL 值仅支持英文字符")

    return (
        key,
        json.dumps({key: test_value}, separators=(",", ":"), ensure_ascii=True),
        json.dumps({key: uat_value}, separators=(",", ":"), ensure_ascii=True),
        json.dumps({key: live_value}, separators=(",", ":"), ensure_ascii=True),
    )


def _get_active_rule_values(db: Session, tool_id: int) -> dict[ServiceRuleCategory, set[str]]:
    rows = db.exec(
        select(ServiceIdRuleOption).where(
            ServiceIdRuleOption.tool_id == tool_id,
            ServiceIdRuleOption.is_active == True,
        )
    ).all()
    values: dict[ServiceRuleCategory, set[str]] = {
        ServiceRuleCategory.SERVICE_TYPE: set(),
        ServiceRuleCategory.PSGA: set(),
        ServiceRuleCategory.SCOPE_TYPE: set(),
        ServiceRuleCategory.APN_TYPE: set(),
    }
    for row in rows:
        normalized = _normalize_rule_category(row.category)
        values[normalized].add(row.value)
    return values


def _normalize_rule_category(value: ServiceRuleCategory | str) -> ServiceRuleCategory:
    if isinstance(value, ServiceRuleCategory):
        return value
    text = str(value or "").strip()
    if not text:
        raise HTTPException(status_code=500, detail="规则类别数据异常")
    if text.startswith("ServiceRuleCategory."):
        text = text.split(".", 1)[1]
    lowered = text.lower()
    mapping = {
        "service_type": ServiceRuleCategory.SERVICE_TYPE,
        "scope_type": ServiceRuleCategory.SCOPE_TYPE,
        "apn_type": ServiceRuleCategory.APN_TYPE,
        "psga": ServiceRuleCategory.PSGA,
    }
    if lowered in mapping:
        return mapping[lowered]
    raise HTTPException(status_code=500, detail=f"未知规则类别：{text}")


def _build_rule_option_response(
    row: ServiceIdRuleOption,
    normalized_category: ServiceRuleCategory | None = None,
) -> ServiceIdRuleOptionInDB:
    category = normalized_category or _normalize_rule_category(row.category)
    return ServiceIdRuleOptionInDB(
        id=row.id,
        tool_id=row.tool_id,
        category=category,
        value=row.value,
        is_active=row.is_active,
        created_by=row.created_by,
        updated_by=row.updated_by,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _validate_custom_field_constraints(
    db: Session,
    tool_id: int,
    payload: ServiceIdEntryCreate | ServiceIdEntryUpdate,
) -> dict[str, object]:
    return dynamic_fields.validate_custom_field_constraints(db, tool_id, payload)


def _validate_entry_payload(
    db: Session,
    tool_id: int,
    payload: ServiceIdEntryCreate | ServiceIdEntryUpdate,
    existing_id: int | None = None,
) -> tuple[str | None, str, str, str, dict[str, object]]:
    normalized_extra_fields = _validate_custom_field_constraints(db, tool_id, payload)
    if not _PACKAGE_NAME_PATTERN.match(payload.package_name.strip()):
        raise HTTPException(
            status_code=400,
            detail="包名（package_name）仅支持英文字母、数字、下划线和点号",
        )

    rule_values = _get_active_rule_values(db, tool_id)
    if payload.service_type not in rule_values[ServiceRuleCategory.SERVICE_TYPE]:
        raise HTTPException(status_code=400, detail="服务类型不在可选规则内")
    if payload.scope_type not in rule_values[ServiceRuleCategory.SCOPE_TYPE]:
        raise HTTPException(status_code=400, detail="范围类型不在可选规则内")
    if payload.apn_type not in rule_values[ServiceRuleCategory.APN_TYPE]:
        raise HTTPException(status_code=400, detail="网络类型不在可选规则内")
    psga_value = payload.psga_availability.strip()
    if not psga_value:
        raise HTTPException(status_code=400, detail="PSGA 可用域为必填")
    if psga_value not in rule_values[ServiceRuleCategory.PSGA]:
        raise HTTPException(status_code=400, detail="PSGA 可用域存在非法选项")

    service_id_value = payload.service_id.strip()
    exists = db.exec(
        select(ServiceIdRegistryEntry).where(ServiceIdRegistryEntry.service_id == service_id_value)
    ).first()
    if exists and exists.id != existing_id:
        raise HTTPException(status_code=400, detail="服务 ID 已存在")

    json_key, base_test, base_uat, base_live = _validate_base_url_inputs(
        payload.base_url_mode,
        payload.base_url_json_key,
        payload.base_url_test_input,
        payload.base_url_uat_input,
        payload.base_url_live_input,
        payload.base_url_json_rows,
    )
    return json_key, base_test, base_uat, base_live, normalized_extra_fields

def _build_entry_response(db: Session, entry: ServiceIdRegistryEntry) -> ServiceIdEntryInDB:
    created_user = db.get(User, entry.created_by)
    updated_user = db.get(User, entry.updated_by)
    raw_psga_values = [s.strip() for s in entry.psga_availability.split(",") if s.strip()]
    psga_value = raw_psga_values[0] if raw_psga_values else ""
    extra_fields = dynamic_fields.load_entry_custom_fields(db, entry.id)
    return ServiceIdEntryInDB(
        id=entry.id,
        tool_id=entry.tool_id,
        business_function=entry.business_function,
        business_description=entry.business_description,
        service_id=entry.service_id,
        service_type=entry.service_type,
        psga_availability=psga_value,
        package_name=entry.package_name,
        scope_type=entry.scope_type,
        apn_type=entry.apn_type,
        access_link_desc=entry.access_link_desc,
        base_url_mode=entry.base_url_mode,
        base_url_json_key=entry.base_url_json_key,
        base_url_test=entry.base_url_test,
        base_url_uat=entry.base_url_uat,
        base_url_live=entry.base_url_live,
        extra_fields=extra_fields,
        created_by=entry.created_by,
        updated_by=entry.updated_by,
        created_by_name=created_user.username if created_user else None,
        updated_by_name=updated_user.username if updated_user else None,
        created_at=entry.created_at,
        updated_at=entry.updated_at,
    )
@router.get("/{tool_id}/features/service-id-entries", response_model=ServiceIdEntryListResponse)
async def list_service_id_entries(
    tool_id: int,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=200),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    ensure_service_id_registry_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)

    can_manage_all = can_manage_all_records(db, current_user, tool_id)
    where_conditions = [ServiceIdRegistryEntry.tool_id == tool_id]
    if not can_manage_all:
        where_conditions.append(ServiceIdRegistryEntry.created_by == current_user.id)
    total = db.exec(
        select(func.count())
        .select_from(ServiceIdRegistryEntry)
        .where(*where_conditions)
    ).one()
    statement = (
        select(ServiceIdRegistryEntry)
        .where(*where_conditions)
        .order_by(ServiceIdRegistryEntry.updated_at.desc())
        .offset(skip)
        .limit(limit)
    )
    rows = db.exec(statement).all()
    return ServiceIdEntryListResponse(
        can_manage_all=can_manage_all,
        total=int(total or 0),
        items=[_build_entry_response(db, row) for row in rows],
    )


@router.post("/{tool_id}/features/service-id-entries", response_model=ServiceIdEntryInDB)
async def create_service_id_entry(
    tool_id: int,
    body: ServiceIdEntryCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    ensure_service_id_registry_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)

    json_key, base_test, base_uat, base_live, normalized_extra_fields = _validate_entry_payload(db, tool_id, body)
    now = datetime.utcnow()
    row = ServiceIdRegistryEntry(
        tool_id=tool_id,
        created_by=current_user.id,
        updated_by=current_user.id,
        business_function=body.business_function.strip(),
        business_description=body.business_description.strip(),
        service_id=body.service_id.strip(),
        service_type=body.service_type.strip(),
        psga_availability=body.psga_availability.strip(),
        package_name=body.package_name.strip(),
        scope_type=body.scope_type.strip(),
        apn_type=body.apn_type.strip(),
        access_link_desc=body.access_link_desc.strip(),
        base_url_mode=body.base_url_mode,
        base_url_json_key=json_key,
        base_url_test=base_test,
        base_url_uat=base_uat,
        base_url_live=base_live,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    dynamic_fields.save_entry_custom_fields(db, row.id, current_user.id, normalized_extra_fields)
    db.commit()
    return _build_entry_response(db, row)


@router.put("/{tool_id}/features/service-id-entries", response_model=ServiceIdEntryInDB)
async def update_service_id_entry(
    tool_id: int,
    body: ServiceIdEntryUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    ensure_service_id_registry_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)

    row = db.get(ServiceIdRegistryEntry, body.id)
    if not row or row.tool_id != tool_id:
        raise HTTPException(status_code=404, detail="记录不存在")

    can_manage_all = can_manage_all_records(db, current_user, tool_id)
    if not can_manage_all and row.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="仅可编辑自己提交的记录")

    json_key, base_test, base_uat, base_live, normalized_extra_fields = _validate_entry_payload(
        db, tool_id, body, existing_id=row.id
    )
    row.business_function = body.business_function.strip()
    row.business_description = body.business_description.strip()
    row.service_id = body.service_id.strip()
    row.service_type = body.service_type.strip()
    row.psga_availability = body.psga_availability.strip()
    row.package_name = body.package_name.strip()
    row.scope_type = body.scope_type.strip()
    row.apn_type = body.apn_type.strip()
    row.access_link_desc = body.access_link_desc.strip()
    row.base_url_mode = body.base_url_mode
    row.base_url_json_key = json_key
    row.base_url_test = base_test
    row.base_url_uat = base_uat
    row.base_url_live = base_live
    row.updated_by = current_user.id
    row.updated_at = datetime.utcnow()
    db.add(row)
    db.commit()
    db.refresh(row)
    dynamic_fields.save_entry_custom_fields(db, row.id, current_user.id, normalized_extra_fields)
    db.commit()
    return _build_entry_response(db, row)


@router.delete("/{tool_id}/features/service-id-entries", response_model=SuccessResponse)
async def delete_service_id_entry(
    tool_id: int,
    entry_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    ensure_service_id_registry_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)

    row = db.get(ServiceIdRegistryEntry, entry_id)
    if not row or row.tool_id != tool_id:
        raise HTTPException(status_code=404, detail="记录不存在")

    can_manage_all = can_manage_all_records(db, current_user, tool_id)
    if not can_manage_all and row.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="仅可删除自己提交的记录")

    dynamic_fields.delete_entry_custom_fields_by_entry(db, row.id)
    db.delete(row)
    db.commit()
    return SuccessResponse(message="已删除记录")


@router.get("/{tool_id}/features/service-id-rule-options", response_model=ServiceIdRuleOptionGroupResponse)
async def list_service_id_rule_options(
    tool_id: int,
    include_inactive: bool = False,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    ensure_service_id_registry_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)

    can_manage_all = can_manage_all_records(db, current_user, tool_id)
    statement = select(ServiceIdRuleOption).where(ServiceIdRuleOption.tool_id == tool_id)
    if not (can_manage_all and include_inactive):
        statement = statement.where(ServiceIdRuleOption.is_active == True)
    rows = db.exec(
        statement.order_by(ServiceIdRuleOption.category, ServiceIdRuleOption.created_at)
    ).all()

    result = ServiceIdRuleOptionGroupResponse()
    for row in rows:
        normalized = _normalize_rule_category(row.category)
        item = _build_rule_option_response(row, normalized)
        if normalized == ServiceRuleCategory.SERVICE_TYPE:
            result.service_type.append(item)
        elif normalized == ServiceRuleCategory.PSGA:
            result.psga.append(item)
        elif normalized == ServiceRuleCategory.SCOPE_TYPE:
            result.scope_type.append(item)
        elif normalized == ServiceRuleCategory.APN_TYPE:
            result.apn_type.append(item)
    return result


@router.post("/{tool_id}/features/service-id-rule-options", response_model=ServiceIdRuleOptionInDB)
async def create_service_id_rule_option(
    tool_id: int,
    body: ServiceIdRuleOptionCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    ensure_service_id_registry_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    ensure_manage_permission(db, current_user, tool_id)

    value = body.value.strip()
    exists = db.exec(
        select(ServiceIdRuleOption).where(
            ServiceIdRuleOption.tool_id == tool_id,
            ServiceIdRuleOption.category == body.category,
            ServiceIdRuleOption.value == value,
        )
    ).first()
    if exists:
        raise HTTPException(status_code=400, detail="规则值已存在")

    now = datetime.utcnow()
    row = ServiceIdRuleOption(
        tool_id=tool_id,
        category=body.category,
        value=value,
        is_active=True,
        created_by=current_user.id,
        updated_by=current_user.id,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _build_rule_option_response(row)


@router.get("/{tool_id}/features/service-id-rule-options/list", response_model=PaginatedServiceIdRuleOptions)
async def list_service_id_rule_options_page(
    tool_id: int,
    category: ServiceRuleCategory,
    include_inactive: bool = False,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=200),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    ensure_service_id_registry_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)

    can_manage_all = can_manage_all_records(db, current_user, tool_id)
    where_conditions = [
        ServiceIdRuleOption.tool_id == tool_id,
        ServiceIdRuleOption.category == category,
    ]
    if not (can_manage_all and include_inactive):
        where_conditions.append(ServiceIdRuleOption.is_active == True)

    total = db.exec(
        select(func.count())
        .select_from(ServiceIdRuleOption)
        .where(*where_conditions)
    ).one()
    rows = db.exec(
        select(ServiceIdRuleOption)
        .where(*where_conditions)
        .order_by(ServiceIdRuleOption.created_at.desc())
        .offset(skip)
        .limit(limit)
    ).all()
    return PaginatedServiceIdRuleOptions(
        total=int(total or 0),
        items=[_build_rule_option_response(row) for row in rows],
    )


@router.put("/{tool_id}/features/service-id-rule-options", response_model=ServiceIdRuleOptionInDB)
async def update_service_id_rule_option(
    tool_id: int,
    body: ServiceIdRuleOptionUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    ensure_service_id_registry_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    ensure_manage_permission(db, current_user, tool_id)

    row = db.get(ServiceIdRuleOption, body.id)
    if not row or row.tool_id != tool_id:
        raise HTTPException(status_code=404, detail="规则值不存在")

    if body.value is not None:
        new_value = body.value.strip()
        exists = db.exec(
            select(ServiceIdRuleOption).where(
                ServiceIdRuleOption.tool_id == tool_id,
                ServiceIdRuleOption.category == row.category,
                ServiceIdRuleOption.value == new_value,
            )
        ).first()
        if exists and exists.id != row.id:
            raise HTTPException(status_code=400, detail="规则值已存在")
        row.value = new_value
    if body.is_active is not None:
        row.is_active = body.is_active
    row.updated_by = current_user.id
    row.updated_at = datetime.utcnow()
    db.add(row)
    db.commit()
    db.refresh(row)
    return _build_rule_option_response(row)


@router.delete("/{tool_id}/features/service-id-rule-options", response_model=SuccessResponse)
async def delete_service_id_rule_option(
    tool_id: int,
    body: ServiceIdRuleOptionDelete,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    ensure_service_id_registry_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    ensure_manage_permission(db, current_user, tool_id)

    row = db.get(ServiceIdRuleOption, body.id)
    if not row or row.tool_id != tool_id:
        raise HTTPException(status_code=404, detail="规则值不存在")
    db.delete(row)
    db.commit()
    return SuccessResponse(message="已删除规则值")


@router.get("/{tool_id}/features/service-id-field-config", response_model=ServiceIdFieldConfigListResponse)
async def list_service_id_field_configs(
    tool_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    ensure_service_id_registry_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    items = dynamic_fields.list_field_config_items(db, tool_id)
    return ServiceIdFieldConfigListResponse(items=items)


@router.post("/{tool_id}/features/service-id-field-config", response_model=ServiceIdFieldConfigItem)
async def create_service_id_field_config(
    tool_id: int,
    body: ServiceIdFieldConfigCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    ensure_service_id_registry_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    ensure_manage_permission(db, current_user, tool_id)

    return dynamic_fields.create_field_config(db, tool_id, body, current_user.id)


@router.delete("/{tool_id}/features/service-id-field-config", response_model=SuccessResponse)
async def delete_service_id_field_config(
    tool_id: int,
    body: ServiceIdFieldConfigDeleteRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    ensure_service_id_registry_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    ensure_manage_permission(db, current_user, tool_id)

    dynamic_fields.delete_field_config(db, tool_id, body.field_key)
    return SuccessResponse(message="字段已删除")


@router.put("/{tool_id}/features/service-id-field-config", response_model=ServiceIdFieldConfigListResponse)
async def update_service_id_field_configs(
    tool_id: int,
    body: ServiceIdFieldConfigUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    ensure_service_id_registry_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    ensure_manage_permission(db, current_user, tool_id)

    dynamic_fields.update_field_configs(db, tool_id, body.items, current_user.id)
    return await list_service_id_field_configs(tool_id=tool_id, current_user=current_user, db=db)


@router.get("/{tool_id}/features/service-id-export")
async def export_service_id_entries(
    tool_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    ensure_service_id_registry_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    ensure_manage_permission(db, current_user, tool_id)

    rows = db.exec(
        select(ServiceIdRegistryEntry)
        .where(ServiceIdRegistryEntry.tool_id == tool_id)
        .order_by(ServiceIdRegistryEntry.updated_at.desc())
    ).all()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "服务ID (service_id)",
            "业务功能 (business_function)",
            "业务功能描述 (business_description)",
            "服务类型 (service_type)",
            "PSGA可用性 (psga_availability)",
            "包名 (package_name)",
            "范围类型 (scope_type)",
            "APN类型 (apn_type)",
            "访问链路说明 (access_link_desc)",
            "Base URL模式 (base_url_mode)",
            "JSON键 (base_url_json_key)",
            "测试环境Base URL (base_url_test)",
            "预发环境Base URL (base_url_uat)",
            "生产环境Base URL (base_url_live)",
            "创建人 (created_by)",
            "最后更新人 (updated_by)",
            "创建时间 (created_at)",
            "最后更新时间 (updated_at)",
        ]
    )
    for row in rows:
        created_user = db.get(User, row.created_by)
        updated_user = db.get(User, row.updated_by)
        writer.writerow(
            [
                row.service_id,
                row.business_function,
                row.business_description,
                row.service_type,
                row.psga_availability,
                row.package_name,
                row.scope_type,
                row.apn_type,
                row.access_link_desc,
                row.base_url_mode.value,
                row.base_url_json_key or "",
                row.base_url_test,
                row.base_url_uat,
                row.base_url_live,
                created_user.username if created_user else row.created_by,
                updated_user.username if updated_user else row.updated_by,
                row.created_at.isoformat() if row.created_at else "",
                row.updated_at.isoformat() if row.updated_at else "",
            ]
        )
    payload = "\ufeff" + buf.getvalue()
    encoded_filename = quote("service-id-registry-导出.csv")
    return StreamingResponse(
        iter([payload.encode("utf-8")]),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": (
                f"attachment; filename=\"service-id-registry-export.csv\"; "
                f"filename*=UTF-8''{encoded_filename}"
            )
        },
    )

