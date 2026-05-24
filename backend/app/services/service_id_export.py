"""Service ID registry CSV export: column metadata, saved layout, and row rendering."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from typing import Iterable

from fastapi import HTTPException
from sqlmodel import Session, select

from app.models import (
    ServiceIdCsvExportConfig,
    ServiceIdEntryCustomFieldValue,
    ServiceIdFormFieldDefinition,
    ServiceIdRegistryEntry,
    User,
)

_BUILTIN_EXPORT_DEFAULTS: list[tuple[str, str]] = [
    ("service_id", "服务ID (service_id)"),
    ("business_function", "业务功能 (business_function)"),
    ("business_description", "业务功能描述 (business_description)"),
    ("service_type", "服务类型 (service_type)"),
    ("psga_availability", "PSGA可用性 (psga_availability)"),
    ("package_name", "包名 (package_name)"),
    ("scope_type", "范围类型 (scope_type)"),
    ("apn_type", "APN类型 (apn_type)"),
    ("access_link_desc", "访问链路说明 (access_link_desc)"),
    ("base_url_mode", "Base URL模式 (base_url_mode)"),
    ("base_url_json_key", "JSON键 (base_url_json_key)"),
    ("base_url_test", "测试环境Base URL (base_url_test)"),
    ("base_url_uat", "预发环境Base URL (base_url_uat)"),
    ("base_url_live", "生产环境Base URL (base_url_live)"),
    ("created_by_username", "创建人 (created_by)"),
    ("updated_by_username", "最后更新人 (updated_by)"),
    ("created_at", "创建时间 (created_at)"),
    ("updated_at", "最后更新时间 (updated_at)"),
]

_BUILTIN_KEYS: set[str] = {k for k, _ in _BUILTIN_EXPORT_DEFAULTS}


def _extra_prefix(field_key: str) -> str:
    return f"extra__{field_key}"


def _load_active_custom_definitions(db: Session, tool_id: int) -> list[ServiceIdFormFieldDefinition]:
    return db.exec(
        select(ServiceIdFormFieldDefinition).where(
            ServiceIdFormFieldDefinition.tool_id == tool_id,
            ServiceIdFormFieldDefinition.is_active == True,  # noqa: E712
        ).order_by(ServiceIdFormFieldDefinition.sort_order, ServiceIdFormFieldDefinition.id)
    ).all()


def allowed_export_keys(db: Session, tool_id: int) -> set[str]:
    keys = set(_BUILTIN_KEYS)
    for item in _load_active_custom_definitions(db, tool_id):
        fk = (item.field_key or "").strip()
        if fk:
            keys.add(_extra_prefix(fk))
    return keys


def list_export_column_options(db: Session, tool_id: int) -> list[dict[str, str]]:
    options: list[dict[str, str]] = [
        {"key": key, "default_header": header, "group": "builtin"} for key, header in _BUILTIN_EXPORT_DEFAULTS
    ]
    for item in _load_active_custom_definitions(db, tool_id):
        fk = (item.field_key or "").strip()
        if not fk:
            continue
        key = _extra_prefix(fk)
        options.append(
            {
                "key": key,
                "default_header": f"{item.label} ({fk})",
                "group": "custom",
            }
        )
    return options


def default_export_columns(db: Session, tool_id: int) -> list[dict[str, str]]:
    """Default CSV layout: built-ins (legacy order) only; custom fields are opt-in via saved config."""
    _ = tool_id
    return [{"key": k, "header": h} for k, h in _BUILTIN_EXPORT_DEFAULTS]


def _parse_saved_columns(raw: str | None) -> list[dict[str, str]]:
    if not raw or not str(raw).strip():
        return []
    try:
        data = json.loads(raw)
    except Exception:
        return []
    cols = data.get("columns") if isinstance(data, dict) else None
    if not isinstance(cols, list):
        return []
    out: list[dict[str, str]] = []
    for item in cols:
        if not isinstance(item, dict):
            continue
        key = str(item.get("key", "")).strip()
        header = str(item.get("header", "")).strip()
        if key and header:
            out.append({"key": key, "header": header})
    return out


def get_saved_export_columns_row(db: Session, tool_id: int) -> ServiceIdCsvExportConfig | None:
    return db.exec(select(ServiceIdCsvExportConfig).where(ServiceIdCsvExportConfig.tool_id == tool_id)).first()


def resolve_effective_export_columns(db: Session, tool_id: int) -> list[tuple[str, str]]:
    allowed = allowed_export_keys(db, tool_id)
    row = get_saved_export_columns_row(db, tool_id)
    parsed = _parse_saved_columns(row.columns_json if row else None)
    filtered = [(c["key"], c["header"]) for c in parsed if c["key"] in allowed]
    if filtered:
        return filtered
    return [(c["key"], c["header"]) for c in default_export_columns(db, tool_id) if c["key"] in allowed]


def validate_and_normalize_columns(
    db: Session, tool_id: int, columns: list[dict[str, str]]
) -> list[dict[str, str]]:
    allowed = allowed_export_keys(db, tool_id)
    if not columns:
        raise HTTPException(status_code=400, detail="至少选择一列导出")
    if len(columns) > 64:
        raise HTTPException(status_code=400, detail="导出列数量不能超过 64")
    seen: set[str] = set()
    normalized: list[dict[str, str]] = []
    for item in columns:
        key = str(item.get("key", "")).strip()
        header = str(item.get("header", "")).strip()
        if not key or not header:
            raise HTTPException(status_code=400, detail="每列需提供字段 key 与 CSV 表头")
        if len(header) > 200:
            raise HTTPException(status_code=400, detail="CSV 表头长度不能超过 200")
        if key not in allowed:
            raise HTTPException(status_code=400, detail=f"未知或已下线的导出字段：{key}")
        if key in seen:
            raise HTTPException(status_code=400, detail=f"导出字段重复：{key}")
        seen.add(key)
        normalized.append({"key": key, "header": header})
    return normalized


def build_export_config_response(db: Session, tool_id: int) -> dict[str, object]:
    options = list_export_column_options(db, tool_id)
    row = get_saved_export_columns_row(db, tool_id)
    parsed = _parse_saved_columns(row.columns_json if row else None)
    allowed = allowed_export_keys(db, tool_id)
    filtered = [{"key": c["key"], "header": c["header"]} for c in parsed if c["key"] in allowed]
    if not filtered:
        filtered = default_export_columns(db, tool_id)
    return {"options": options, "columns": filtered}


def upsert_export_columns(
    db: Session, tool_id: int, columns: list[dict[str, str]], user_id: int
) -> ServiceIdCsvExportConfig:
    normalized = validate_and_normalize_columns(db, tool_id, columns)
    payload = json.dumps({"columns": normalized}, ensure_ascii=False)
    now = datetime.utcnow()
    row = get_saved_export_columns_row(db, tool_id)
    if row:
        row.columns_json = payload
        row.updated_by = user_id
        row.updated_at = now
        db.add(row)
    else:
        row = ServiceIdCsvExportConfig(
            tool_id=tool_id,
            columns_json=payload,
            updated_by=user_id,
            updated_at=now,
        )
        db.add(row)
    db.commit()
    db.refresh(row)
    return row


def load_custom_field_values_bulk(db: Session, entry_ids: Iterable[int]) -> dict[int, dict[str, object]]:
    ids = [int(i) for i in entry_ids if i is not None]
    if not ids:
        return {}
    rows = db.exec(select(ServiceIdEntryCustomFieldValue).where(ServiceIdEntryCustomFieldValue.entry_id.in_(ids))).all()
    out: dict[int, dict[str, object]] = defaultdict(dict)
    for row in rows:
        try:
            parsed = json.loads(row.value_json)
        except Exception:
            parsed = ""
        out[int(row.entry_id)][row.field_key] = parsed
    return {int(k): dict(v) for k, v in out.items()}


def _format_cell_scalar(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return ";".join(str(x) for x in value)
    return str(value)


def cell_value_for_export_key(
    key: str,
    entry: ServiceIdRegistryEntry,
    extras: dict[str, object],
    created_user: User | None,
    updated_user: User | None,
) -> str:
    if key.startswith("extra__"):
        fk = key[8:]
        return _format_cell_scalar(extras.get(fk))
    if key == "created_by_username":
        return created_user.username if created_user else str(entry.created_by)
    if key == "updated_by_username":
        return updated_user.username if updated_user else str(entry.updated_by)
    if key == "base_url_mode":
        return entry.base_url_mode.value if hasattr(entry.base_url_mode, "value") else str(entry.base_url_mode)
    if key in ("created_at", "updated_at"):
        dt = getattr(entry, key, None)
        return dt.isoformat() if isinstance(dt, datetime) else ""
    if hasattr(entry, key):
        val = getattr(entry, key)
        if val is None:
            return ""
        return str(val)
    return ""
