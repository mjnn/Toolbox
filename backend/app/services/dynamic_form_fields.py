"""Tool-agnostic dynamic form field helpers."""

from __future__ import annotations

import json
import re
from datetime import datetime
from enum import Enum
from typing import Any

from fastapi import HTTPException
from sqlmodel import Session, select


def normalize_allowed_values(values: list[str] | None) -> list[str]:
    if not values:
        return []
    seen: set[str] = set()
    result: list[str] = []
    for raw in values:
        value = str(raw or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def normalize_input_type(value: str | Enum | None, enum_cls: type[Enum], fallback: str | None = None) -> str:
    if isinstance(value, enum_cls):
        return str(value.value)
    text = str(value or "").strip().lower()
    allowed = {str(item.value) for item in enum_cls}
    if text in allowed:
        return text
    return fallback or next(iter(allowed))


def parse_allowed_values_json(raw_json: str | None) -> list[str]:
    if not raw_json:
        return []
    try:
        parsed = json.loads(raw_json)
    except Exception:
        return []
    if not isinstance(parsed, list):
        return []
    return normalize_allowed_values([str(v) for v in parsed])


def validate_one_field(field_key: str, value: str, cfg: dict[str, Any]) -> None:
    label = cfg.get("label") or field_key
    text = value.strip()
    required = bool(cfg.get("required", False))
    if required and not text:
        raise HTTPException(status_code=400, detail=f"{label} 为必填")
    if not text:
        return
    min_length = cfg.get("min_length")
    max_length = cfg.get("max_length")
    if min_length is not None and len(text) < int(min_length):
        raise HTTPException(status_code=400, detail=f"{label} 长度不能少于 {int(min_length)}")
    if max_length is not None and len(text) > int(max_length):
        raise HTTPException(status_code=400, detail=f"{label} 长度不能超过 {int(max_length)}")
    allowed_values = cfg.get("allowed_values") or []
    if allowed_values and text not in allowed_values:
        raise HTTPException(status_code=400, detail=f"{label} 不在允许范围内")
    regex_pattern = cfg.get("regex_pattern")
    if regex_pattern and not re.fullmatch(str(regex_pattern), text):
        msg = str(cfg.get("regex_error_message") or "").strip() or f"{label} 格式不正确"
        raise HTTPException(status_code=400, detail=msg)


def validate_dynamic_field_value(
    field_key: str,
    value: object,
    cfg: dict[str, Any],
    multi_select_input_type: str,
) -> object:
    input_type = str(cfg.get("input_type") or "").strip().lower()
    required = bool(cfg.get("required", False))
    label = cfg.get("label") or field_key
    allowed_values = cfg.get("allowed_values") or []

    if input_type == multi_select_input_type:
        if value is None:
            if required:
                raise HTTPException(status_code=400, detail=f"{label} 为必填")
            return []
        if not isinstance(value, list):
            raise HTTPException(status_code=400, detail=f"{label} 需为多选数组")
        normalized: list[str] = []
        seen: set[str] = set()
        for item in value:
            text = str(item or "").strip()
            if not text or text in seen:
                continue
            seen.add(text)
            normalized.append(text)
        if required and not normalized:
            raise HTTPException(status_code=400, detail=f"{label} 为必填")
        if allowed_values:
            invalid = [item for item in normalized if item not in allowed_values]
            if invalid:
                raise HTTPException(status_code=400, detail=f"{label} 存在不在允许范围内的选项")
        return normalized

    text = str(value or "").strip()
    validate_one_field(field_key, text, cfg)
    if text and allowed_values and text not in allowed_values:
        raise HTTPException(status_code=400, detail=f"{label} 不在允许范围内")
    return text


def normalize_dynamic_extra_fields(
    raw_extra_fields: dict[str, object],
    dynamic_defs: dict[str, dict[str, Any]],
    multi_select_input_type: str,
) -> dict[str, object]:
    unknown_keys = [key for key in raw_extra_fields.keys() if key not in dynamic_defs]
    if unknown_keys:
        raise HTTPException(status_code=400, detail=f"存在未知自定义字段：{', '.join(unknown_keys)}")
    normalized_extra_fields: dict[str, object] = {}
    for key, cfg in dynamic_defs.items():
        normalized = validate_dynamic_field_value(key, raw_extra_fields.get(key), cfg, multi_select_input_type)
        if isinstance(normalized, list):
            if normalized:
                normalized_extra_fields[key] = normalized
        elif isinstance(normalized, str):
            if normalized:
                normalized_extra_fields[key] = normalized
    return normalized_extra_fields


def load_custom_field_values(db: Session, value_model: type, entry_id: int) -> dict[str, object]:
    rows = db.exec(
        select(value_model).where(value_model.entry_id == entry_id)
    ).all()
    result: dict[str, object] = {}
    for row in rows:
        try:
            parsed = json.loads(row.value_json)
        except Exception:
            parsed = ""
        result[row.field_key] = parsed
    return result


def save_custom_field_values(
    db: Session,
    value_model: type,
    entry_id: int,
    updated_by: int,
    values: dict[str, object],
) -> None:
    existing_rows = db.exec(
        select(value_model).where(value_model.entry_id == entry_id)
    ).all()
    existing_by_key = {row.field_key: row for row in existing_rows}
    for field_key, row in existing_by_key.items():
        if field_key not in values:
            db.delete(row)
    now = datetime.utcnow()
    for field_key, value in values.items():
        payload = json.dumps(value, ensure_ascii=False)
        row = existing_by_key.get(field_key)
        if not row:
            row = value_model(
                entry_id=entry_id,
                field_key=field_key,
                value_json=payload,
                updated_by=updated_by,
                updated_at=now,
            )
        else:
            row.value_json = payload
            row.updated_by = updated_by
            row.updated_at = now
        db.add(row)


def delete_custom_field_values_by_entry(db: Session, value_model: type, entry_id: int) -> None:
    rows = db.exec(
        select(value_model).where(value_model.entry_id == entry_id)
    ).all()
    for row in rows:
        db.delete(row)
