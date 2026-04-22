"""Reusable dynamic field services for Service ID forms."""

from __future__ import annotations

import json
import re
from datetime import datetime

from fastapi import HTTPException
from sqlmodel import Session, select

from app.services import dynamic_form_fields as form_core
from app.models import (
    ServiceFieldInputType,
    ServiceIdEntryCustomFieldValue,
    ServiceIdFieldConfig,
    ServiceIdFormFieldDefinition,
    ServiceIdRegistryEntry,
    ServiceBaseUrlMode,
)
from app.schemas import (
    ServiceIdEntryCreate,
    ServiceIdEntryUpdate,
    ServiceIdFieldConfigCreateRequest,
    ServiceIdFieldConfigItem,
    ServiceIdFieldConfigUpdateItem,
)

SERVICE_ID_FIELD_KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,63}$")

SERVICE_ID_BUILTIN_FIELD_DEFS: dict[str, dict] = {
    "business_function": {"label": "业务功能", "required": True, "min_length": 1, "max_length": 20, "input_type": "text", "is_builtin": True, "sort_order": 10},
    "business_description": {"label": "业务功能描述", "required": True, "min_length": 1, "max_length": 50, "input_type": "text", "is_builtin": True, "sort_order": 20},
    "service_id": {"label": "Service ID", "required": True, "min_length": 1, "max_length": 200, "input_type": "text", "is_builtin": True, "sort_order": 30},
    "service_type": {"label": "服务类型", "required": True, "min_length": 1, "max_length": 100, "input_type": "single_select", "is_builtin": True, "sort_order": 40},
    "psga_availability": {"label": "PSGA 可用域", "required": True, "min_length": 1, "max_length": 100, "input_type": "single_select", "is_builtin": True, "sort_order": 50},
    "package_name": {"label": "包名", "required": True, "min_length": 1, "max_length": 200, "input_type": "text", "is_builtin": True, "sort_order": 60},
    "scope_type": {"label": "范围类型", "required": True, "min_length": 1, "max_length": 100, "input_type": "single_select", "is_builtin": True, "sort_order": 70},
    "apn_type": {"label": "网络类型", "required": True, "min_length": 1, "max_length": 100, "input_type": "single_select", "is_builtin": True, "sort_order": 80},
    "access_link_desc": {"label": "访问链路说明", "required": True, "min_length": 1, "max_length": 20, "input_type": "text", "is_builtin": True, "sort_order": 90},
    "base_url_json_key": {"label": "Base URL JSON 键", "required": True, "min_length": 1, "max_length": 100, "input_type": "text", "is_builtin": True, "sort_order": 100},
    "base_url_test_input": {"label": "Base URL 测试", "required": True, "min_length": 1, "input_type": "text", "is_builtin": True, "sort_order": 110},
    "base_url_uat_input": {"label": "Base URL 预发", "required": True, "min_length": 1, "input_type": "text", "is_builtin": True, "sort_order": 120},
    "base_url_live_input": {"label": "Base URL 生产", "required": True, "min_length": 1, "input_type": "text", "is_builtin": True, "sort_order": 130},
}


def normalize_allowed_values(values: list[str] | None) -> list[str]:
    return form_core.normalize_allowed_values(values)


def normalize_input_type(value: str | ServiceFieldInputType | None) -> str:
    return form_core.normalize_input_type(value, ServiceFieldInputType, ServiceFieldInputType.TEXT.value)


def _load_custom_field_definitions(db: Session, tool_id: int) -> list[ServiceIdFormFieldDefinition]:
    return db.exec(
        select(ServiceIdFormFieldDefinition).where(
            ServiceIdFormFieldDefinition.tool_id == tool_id,
            ServiceIdFormFieldDefinition.is_active == True,
        ).order_by(ServiceIdFormFieldDefinition.sort_order, ServiceIdFormFieldDefinition.id)
    ).all()


def _field_config_to_dict(row: ServiceIdFieldConfig) -> dict:
    allowed_values = form_core.parse_allowed_values_json(row.allowed_values_json)
    return {
        "help_text": row.help_text,
        "required": row.required,
        "min_length": row.min_length,
        "max_length": row.max_length,
        "regex_pattern": row.regex_pattern,
        "regex_error_message": row.regex_error_message,
        "allowed_values": allowed_values,
    }


def get_field_constraint_map(db: Session, tool_id: int) -> dict[str, dict]:
    rows = db.exec(
        select(ServiceIdFieldConfig).where(ServiceIdFieldConfig.tool_id == tool_id)
    ).all()
    by_key = {row.field_key: row for row in rows}
    result: dict[str, dict] = {}
    for field_key, default_cfg in SERVICE_ID_BUILTIN_FIELD_DEFS.items():
        merged = dict(default_cfg)
        row = by_key.get(field_key)
        if row:
            custom = _field_config_to_dict(row)
            if custom["help_text"] is not None:
                merged["help_text"] = custom["help_text"]
            if custom["required"] is not None:
                merged["required"] = custom["required"]
            if custom["min_length"] is not None:
                merged["min_length"] = custom["min_length"]
            if custom["max_length"] is not None:
                merged["max_length"] = custom["max_length"]
            if custom["regex_pattern"] is not None:
                merged["regex_pattern"] = custom["regex_pattern"]
            if custom["regex_error_message"] is not None:
                merged["regex_error_message"] = custom["regex_error_message"]
            if custom["allowed_values"]:
                merged["allowed_values"] = custom["allowed_values"]
        result[field_key] = merged
    custom_defs = _load_custom_field_definitions(db, tool_id)
    for item in custom_defs:
        field_key = item.field_key.strip()
        if not field_key:
            continue
        merged = {
            "label": item.label,
            "input_type": normalize_input_type(item.input_type),
            "is_builtin": False,
            "sort_order": int(item.sort_order or 0),
            "required": False,
            "min_length": None,
            "max_length": None,
            "regex_pattern": None,
            "regex_error_message": None,
            "allowed_values": [],
        }
        row = by_key.get(field_key)
        if row:
            custom = _field_config_to_dict(row)
            if custom["help_text"] is not None:
                merged["help_text"] = custom["help_text"]
            if custom["required"] is not None:
                merged["required"] = custom["required"]
            if custom["min_length"] is not None:
                merged["min_length"] = custom["min_length"]
            if custom["max_length"] is not None:
                merged["max_length"] = custom["max_length"]
            if custom["regex_pattern"] is not None:
                merged["regex_pattern"] = custom["regex_pattern"]
            if custom["regex_error_message"] is not None:
                merged["regex_error_message"] = custom["regex_error_message"]
            if custom["allowed_values"]:
                merged["allowed_values"] = custom["allowed_values"]
        result[field_key] = merged
    return result


def list_field_config_items(db: Session, tool_id: int) -> list[ServiceIdFieldConfigItem]:
    merged = get_field_constraint_map(db, tool_id)
    ordered_items = sorted(
        merged.items(),
        key=lambda item: (
            0 if bool(item[1].get("is_builtin")) else 1,
            int(item[1].get("sort_order") or 0),
            item[0],
        ),
    )
    return [
        ServiceIdFieldConfigItem(
            field_key=field_key,
            label=str(cfg.get("label") or field_key),
            input_type=normalize_input_type(cfg.get("input_type")),
            is_builtin=bool(cfg.get("is_builtin")),
            sort_order=int(cfg.get("sort_order") or 0),
            help_text=cfg.get("help_text"),
            required=bool(cfg.get("required", False)),
            min_length=cfg.get("min_length"),
            max_length=cfg.get("max_length"),
            regex_pattern=cfg.get("regex_pattern"),
            regex_error_message=cfg.get("regex_error_message"),
            allowed_values=cfg.get("allowed_values") or [],
        )
        for field_key, cfg in ordered_items
    ]


def _validate_one_field(field_key: str, value: str, cfg: dict) -> None:
    form_core.validate_one_field(field_key, value, cfg)


def _validate_dynamic_field_value(field_key: str, value: object, cfg: dict) -> object:
    return form_core.validate_dynamic_field_value(
        field_key,
        value,
        cfg,
        ServiceFieldInputType.MULTI_SELECT.value,
    )


def validate_custom_field_constraints(
    db: Session,
    tool_id: int,
    payload: ServiceIdEntryCreate | ServiceIdEntryUpdate,
) -> dict[str, object]:
    field_map = get_field_constraint_map(db, tool_id)
    _validate_one_field("business_function", payload.business_function, field_map["business_function"])
    _validate_one_field("business_description", payload.business_description, field_map["business_description"])
    _validate_one_field("service_id", payload.service_id, field_map["service_id"])
    _validate_one_field("service_type", payload.service_type, field_map["service_type"])
    _validate_one_field("psga_availability", payload.psga_availability, field_map["psga_availability"])
    _validate_one_field("package_name", payload.package_name, field_map["package_name"])
    _validate_one_field("scope_type", payload.scope_type, field_map["scope_type"])
    _validate_one_field("apn_type", payload.apn_type, field_map["apn_type"])
    _validate_one_field("access_link_desc", payload.access_link_desc, field_map["access_link_desc"])
    _validate_one_field("base_url_test_input", payload.base_url_test_input, field_map["base_url_test_input"])
    _validate_one_field("base_url_uat_input", payload.base_url_uat_input, field_map["base_url_uat_input"])
    _validate_one_field("base_url_live_input", payload.base_url_live_input, field_map["base_url_live_input"])

    if payload.base_url_mode == ServiceBaseUrlMode.JSON:
        if payload.base_url_json_rows:
            for row in payload.base_url_json_rows:
                _validate_one_field("base_url_json_key", row.key, field_map["base_url_json_key"])
                _validate_one_field("base_url_test_input", row.test, field_map["base_url_test_input"])
                _validate_one_field("base_url_uat_input", row.uat, field_map["base_url_uat_input"])
                _validate_one_field("base_url_live_input", row.live, field_map["base_url_live_input"])
        else:
            _validate_one_field("base_url_json_key", payload.base_url_json_key or "", field_map["base_url_json_key"])

    dynamic_defs = {
        key: cfg for key, cfg in field_map.items() if not bool(cfg.get("is_builtin"))
    }
    return form_core.normalize_dynamic_extra_fields(
        payload.extra_fields or {},
        dynamic_defs,
        ServiceFieldInputType.MULTI_SELECT.value,
    )


def load_entry_custom_fields(db: Session, entry_id: int) -> dict[str, object]:
    return form_core.load_custom_field_values(db, ServiceIdEntryCustomFieldValue, entry_id)


def save_entry_custom_fields(
    db: Session,
    entry_id: int,
    updated_by: int,
    values: dict[str, object],
) -> None:
    form_core.save_custom_field_values(db, ServiceIdEntryCustomFieldValue, entry_id, updated_by, values)


def delete_entry_custom_fields_by_entry(db: Session, entry_id: int) -> None:
    form_core.delete_custom_field_values_by_entry(db, ServiceIdEntryCustomFieldValue, entry_id)


def create_field_config(
    db: Session,
    tool_id: int,
    body: ServiceIdFieldConfigCreateRequest,
    updated_by: int,
) -> ServiceIdFieldConfigItem:
    field_key = body.field_key.strip()
    if not SERVICE_ID_FIELD_KEY_PATTERN.fullmatch(field_key):
        raise HTTPException(status_code=400, detail="字段 key 仅支持小写字母、数字、下划线，且必须字母开头")
    if field_key in SERVICE_ID_BUILTIN_FIELD_DEFS:
        raise HTTPException(status_code=400, detail="该字段 key 属于内置字段，不可重复新增")
    exists_def = db.exec(
        select(ServiceIdFormFieldDefinition).where(
            ServiceIdFormFieldDefinition.tool_id == tool_id,
            ServiceIdFormFieldDefinition.field_key == field_key,
        )
    ).first()
    if exists_def:
        raise HTTPException(status_code=400, detail="字段 key 已存在")
    if body.min_length is not None and body.max_length is not None and body.min_length > body.max_length:
        raise HTTPException(status_code=400, detail="最小长度不能大于最大长度")
    allowed_values = normalize_allowed_values(body.allowed_values)
    if len(allowed_values) > 200:
        raise HTTPException(status_code=400, detail="可选值数量过多")
    regex_pattern = body.regex_pattern.strip() if body.regex_pattern else None
    regex_error_message = body.regex_error_message.strip() if body.regex_error_message else None
    if regex_pattern:
        try:
            re.compile(regex_pattern)
        except re.error:
            raise HTTPException(status_code=400, detail="正则表达式不合法")
    now = datetime.utcnow()
    field_def = ServiceIdFormFieldDefinition(
        tool_id=tool_id,
        field_key=field_key,
        label=body.label.strip(),
        input_type=ServiceFieldInputType(normalize_input_type(body.input_type)),
        is_builtin=False,
        is_active=True,
        sort_order=9999,
        created_by=updated_by,
        updated_by=updated_by,
        created_at=now,
        updated_at=now,
    )
    db.add(field_def)
    field_cfg = ServiceIdFieldConfig(
        tool_id=tool_id,
        field_key=field_key,
        help_text=(body.help_text or "").strip() or None,
        required=body.required,
        min_length=body.min_length,
        max_length=body.max_length,
        regex_pattern=regex_pattern,
        regex_error_message=regex_error_message,
        allowed_values_json=json.dumps(allowed_values, ensure_ascii=False) if allowed_values else None,
        updated_by=updated_by,
        updated_at=now,
    )
    db.add(field_cfg)
    db.commit()
    return ServiceIdFieldConfigItem(
        field_key=field_key,
        label=field_def.label,
        input_type=normalize_input_type(field_def.input_type),
        is_builtin=False,
        sort_order=field_def.sort_order,
        help_text=field_cfg.help_text,
        required=bool(field_cfg.required or False),
        min_length=field_cfg.min_length,
        max_length=field_cfg.max_length,
        regex_pattern=field_cfg.regex_pattern,
        regex_error_message=field_cfg.regex_error_message,
        allowed_values=allowed_values,
    )


def delete_field_config(db: Session, tool_id: int, field_key: str) -> None:
    normalized_key = field_key.strip()
    if normalized_key in SERVICE_ID_BUILTIN_FIELD_DEFS:
        raise HTTPException(status_code=400, detail="内置字段不支持删除")
    field_def = db.exec(
        select(ServiceIdFormFieldDefinition).where(
            ServiceIdFormFieldDefinition.tool_id == tool_id,
            ServiceIdFormFieldDefinition.field_key == normalized_key,
        )
    ).first()
    if not field_def:
        raise HTTPException(status_code=404, detail="字段不存在")
    cfg = db.exec(
        select(ServiceIdFieldConfig).where(
            ServiceIdFieldConfig.tool_id == tool_id,
            ServiceIdFieldConfig.field_key == normalized_key,
        )
    ).first()
    if cfg:
        db.delete(cfg)
    values = db.exec(
        select(ServiceIdEntryCustomFieldValue).where(ServiceIdEntryCustomFieldValue.field_key == normalized_key)
    ).all()
    for value in values:
        entry = db.get(ServiceIdRegistryEntry, value.entry_id)
        if entry and entry.tool_id == tool_id:
            db.delete(value)
    db.delete(field_def)
    db.commit()


def update_field_configs(
    db: Session,
    tool_id: int,
    items: list[ServiceIdFieldConfigUpdateItem],
    updated_by: int,
) -> None:
    now = datetime.utcnow()
    field_map = get_field_constraint_map(db, tool_id)
    custom_def_by_key = {
        row.field_key: row for row in _load_custom_field_definitions(db, tool_id)
    }
    for item in items:
        field_key = item.field_key.strip()
        cfg = field_map.get(field_key)
        if not cfg:
            raise HTTPException(status_code=400, detail=f"不支持的字段：{field_key}")
        is_builtin = bool(cfg.get("is_builtin"))

        if item.min_length is not None and item.max_length is not None and item.min_length > item.max_length:
            raise HTTPException(status_code=400, detail=f"{field_key} 的最小长度不能大于最大长度")
        allowed_values = normalize_allowed_values(item.allowed_values)
        if len(allowed_values) > 200:
            raise HTTPException(status_code=400, detail=f"{field_key} 的可选值数量过多")
        help_text = item.help_text.strip() if item.help_text is not None else None
        regex_pattern = item.regex_pattern.strip() if item.regex_pattern is not None else None
        regex_error_message = item.regex_error_message.strip() if item.regex_error_message is not None else None
        if regex_pattern:
            try:
                re.compile(regex_pattern)
            except re.error:
                raise HTTPException(status_code=400, detail=f"{field_key} 的正则表达式不合法")

        if not is_builtin:
            definition = custom_def_by_key.get(field_key)
            if not definition:
                raise HTTPException(status_code=400, detail=f"字段定义不存在：{field_key}")
            if item.label is not None:
                definition.label = item.label.strip()
            if item.input_type is not None:
                definition.input_type = ServiceFieldInputType(normalize_input_type(item.input_type))
            if item.sort_order is not None:
                definition.sort_order = int(item.sort_order)
            if item.is_active is not None:
                definition.is_active = bool(item.is_active)
            definition.updated_by = updated_by
            definition.updated_at = now
            db.add(definition)

        row = db.exec(
            select(ServiceIdFieldConfig).where(
                ServiceIdFieldConfig.tool_id == tool_id,
                ServiceIdFieldConfig.field_key == field_key,
            )
        ).first()
        should_reset = (
            (help_text is None or help_text == "")
            and item.required is None
            and item.min_length is None
            and item.max_length is None
            and (regex_pattern is None or regex_pattern == "")
            and (regex_error_message is None or regex_error_message == "")
            and not allowed_values
        )
        if should_reset:
            if row:
                db.delete(row)
            continue
        if not row:
            row = ServiceIdFieldConfig(
                tool_id=tool_id,
                field_key=field_key,
                updated_by=updated_by,
                updated_at=now,
            )
        row.help_text = help_text if help_text else None
        row.required = item.required
        row.min_length = item.min_length
        row.max_length = item.max_length
        row.regex_pattern = regex_pattern if regex_pattern else None
        row.regex_error_message = regex_error_message if regex_error_message else None
        row.allowed_values_json = json.dumps(allowed_values, ensure_ascii=False) if allowed_values else None
        row.updated_by = updated_by
        row.updated_at = now
        db.add(row)
    db.commit()
