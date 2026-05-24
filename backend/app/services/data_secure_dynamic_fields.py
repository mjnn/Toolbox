"""Dynamic field services for data secure lifecycle fields."""

from __future__ import annotations

import json
import re
from datetime import datetime

from fastapi import HTTPException
from sqlmodel import Session, select

from app.services import dynamic_form_fields as form_core
from app.models import (
    DataSecureFieldCatalogEntry,
    DataSecureFieldCatalogValue,
    DataSecureFieldInputType,
    DataSecureLifecycleFieldConfig,
    DataSecureLifecycleFieldDefinition,
)
from app.schemas import (
    DataSecureLifecycleFieldConfigCreateRequest,
    DataSecureLifecycleFieldConfigItem,
    DataSecureLifecycleFieldConfigUpdateItem,
)

FIELD_KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
BUILTIN_FIELD_KEY = "field_name"
BUSINESS_FUNCTION_FIELD_KEY = "business_function"
BUSINESS_FUNCTION_LABEL = "业务功能"
BUILTIN_DEF = {
    BUILTIN_FIELD_KEY: {
        "label": "数据字段",
        "required": True,
        "min_length": 1,
        "max_length": 200,
        "input_type": "text",
        "is_builtin": True,
        "sort_order": 10,
    },
    BUSINESS_FUNCTION_FIELD_KEY: {
        "label": BUSINESS_FUNCTION_LABEL,
        "required": False,
        "min_length": None,
        "max_length": None,
        "input_type": "multi_select",
        "is_builtin": True,
        "sort_order": 20,
    },
}


def _normalize_input_type(value: str | DataSecureFieldInputType | None) -> str:
    return form_core.normalize_input_type(value, DataSecureFieldInputType, DataSecureFieldInputType.TEXT.value)


def _load_custom_defs(db: Session, tool_id: int, project_space_id: int) -> list[DataSecureLifecycleFieldDefinition]:
    return db.exec(
        select(DataSecureLifecycleFieldDefinition).where(
            DataSecureLifecycleFieldDefinition.tool_id == tool_id,
            DataSecureLifecycleFieldDefinition.project_space_id == project_space_id,
            DataSecureLifecycleFieldDefinition.is_active == True,  # noqa: E712
        ).order_by(DataSecureLifecycleFieldDefinition.sort_order, DataSecureLifecycleFieldDefinition.id)
    ).all()


def _cfg_to_dict(row: DataSecureLifecycleFieldConfig) -> dict:
    return {
        "help_text": row.help_text,
        "required": row.required,
        "min_length": row.min_length,
        "max_length": row.max_length,
        "regex_pattern": row.regex_pattern,
        "regex_error_message": row.regex_error_message,
        "allowed_values": form_core.parse_allowed_values_json(row.allowed_values_json),
    }


def get_field_constraint_map(db: Session, tool_id: int, project_space_id: int) -> dict[str, dict]:
    rows = db.exec(
        select(DataSecureLifecycleFieldConfig).where(
            DataSecureLifecycleFieldConfig.tool_id == tool_id,
            DataSecureLifecycleFieldConfig.project_space_id == project_space_id,
        )
    ).all()
    by_key = {row.field_key: row for row in rows}
    result: dict[str, dict] = {}
    for field_key, default_cfg in BUILTIN_DEF.items():
        merged = dict(default_cfg)
        row = by_key.get(field_key)
        if row:
            custom = _cfg_to_dict(row)
            for key in ("help_text", "required", "min_length", "max_length", "regex_pattern", "regex_error_message"):
                if custom.get(key) is not None:
                    merged[key] = custom[key]
            if custom.get("allowed_values"):
                merged["allowed_values"] = custom["allowed_values"]
        result[field_key] = merged
    custom_defs = _load_custom_defs(db, tool_id, project_space_id)
    for item in custom_defs:
        field_key = item.field_key.strip()
        if not field_key:
            continue
        if field_key in BUILTIN_DEF:
            continue
        merged = {
            "label": item.label,
            "input_type": _normalize_input_type(item.input_type),
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
            custom = _cfg_to_dict(row)
            for key in ("help_text", "required", "min_length", "max_length", "regex_pattern", "regex_error_message"):
                if custom.get(key) is not None:
                    merged[key] = custom[key]
            if custom.get("allowed_values"):
                merged["allowed_values"] = custom["allowed_values"]
        result[field_key] = merged
    return result


def list_field_config_items(db: Session, tool_id: int, project_space_id: int) -> list[DataSecureLifecycleFieldConfigItem]:
    merged = get_field_constraint_map(db, tool_id, project_space_id)
    ordered_items = sorted(
        merged.items(),
        key=lambda item: (0 if bool(item[1].get("is_builtin")) else 1, int(item[1].get("sort_order") or 0), item[0]),
    )
    return [
        DataSecureLifecycleFieldConfigItem(
            field_key=field_key,
            label=str(cfg.get("label") or field_key),
            input_type=_normalize_input_type(cfg.get("input_type")),
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


def ensure_custom_lifecycle_definitions_from_export_items(
    db: Session,
    tool_id: int,
    project_space_id: int,
    export_items: list[DataSecureLifecycleFieldConfigItem],
    updated_by: int,
) -> None:
    """配置导入/复制：为导出载荷中的自定义列补齐定义行（新空间尚无定义时）。"""
    if not export_items:
        return
    now = datetime.utcnow()
    existing_keys = {
        str(r.field_key).strip()
        for r in db.exec(
            select(DataSecureLifecycleFieldDefinition).where(
                DataSecureLifecycleFieldDefinition.tool_id == tool_id,
                DataSecureLifecycleFieldDefinition.project_space_id == project_space_id,
            )
        ).all()
    }
    added = False
    for it in export_items:
        if bool(it.is_builtin):
            continue
        fk = str(it.field_key or "").strip()
        if not fk or fk in BUILTIN_DEF or fk in existing_keys:
            continue
        if not FIELD_KEY_PATTERN.fullmatch(fk):
            continue
        raw_label = (it.label or "").strip() or fk
        field_def = DataSecureLifecycleFieldDefinition(
            tool_id=tool_id,
            project_space_id=project_space_id,
            field_key=fk,
            label=raw_label[:100],
            input_type=DataSecureFieldInputType(_normalize_input_type(it.input_type)),
            is_builtin=False,
            is_active=True,
            sort_order=int(it.sort_order or 0),
            created_by=updated_by,
            updated_by=updated_by,
            created_at=now,
            updated_at=now,
        )
        db.add(field_def)
        existing_keys.add(fk)
        added = True
    if added:
        db.flush()


def ensure_default_custom_fields_for_catalog_import(
    db: Session,
    tool_id: int,
    project_space_id: int,
    *,
    field_keys: set[str],
    labels: dict[str, str],
    updated_by: int,
) -> list[str]:
    """主表 CSV 导入：为 extra 中出现的、尚未定义的自定义 field_key 自动创建填报表单字段（单行文本、无必填/长度/正则/选项限制）。返回本次新建的 field_key 列表。不 commit。"""
    if not field_keys:
        return []
    existing_defs = {
        row.field_key
        for row in db.exec(
            select(DataSecureLifecycleFieldDefinition).where(
                DataSecureLifecycleFieldDefinition.tool_id == tool_id,
                DataSecureLifecycleFieldDefinition.project_space_id == project_space_id,
            )
        ).all()
    }
    created: list[str] = []
    now = datetime.utcnow()
    for field_key in sorted(field_keys):
        fk = field_key.strip()
        if fk in BUILTIN_DEF:
            continue
        if not FIELD_KEY_PATTERN.fullmatch(fk):
            continue
        if fk in existing_defs:
            continue
        raw_lbl = (labels.get(fk) or fk).strip() or fk
        lbl = raw_lbl[:100]
        field_def = DataSecureLifecycleFieldDefinition(
            tool_id=tool_id,
            project_space_id=project_space_id,
            field_key=fk,
            label=lbl,
            input_type=DataSecureFieldInputType.TEXT,
            is_builtin=False,
            is_active=True,
            sort_order=9999,
            created_by=updated_by,
            updated_by=updated_by,
            created_at=now,
            updated_at=now,
        )
        db.add(field_def)
        cfg = DataSecureLifecycleFieldConfig(
            tool_id=tool_id,
            project_space_id=project_space_id,
            field_key=fk,
            help_text=None,
            required=False,
            min_length=None,
            max_length=None,
            regex_pattern=None,
            regex_error_message=None,
            allowed_values_json=None,
            updated_by=updated_by,
            updated_at=now,
        )
        db.add(cfg)
        created.append(fk)
        existing_defs.add(fk)
    if created:
        db.flush()
    return created


def create_field_config(
    db: Session,
    tool_id: int,
    project_space_id: int,
    body: DataSecureLifecycleFieldConfigCreateRequest,
    updated_by: int,
) -> DataSecureLifecycleFieldConfigItem:
    field_key = body.field_key.strip()
    if not FIELD_KEY_PATTERN.fullmatch(field_key):
        raise HTTPException(status_code=400, detail="字段 key 仅支持小写字母、数字、下划线，且必须字母开头")
    if field_key in BUILTIN_DEF:
        raise HTTPException(status_code=400, detail="该字段 key 属于内置字段，不可重复新增")
    exists = db.exec(
        select(DataSecureLifecycleFieldDefinition).where(
            DataSecureLifecycleFieldDefinition.tool_id == tool_id,
            DataSecureLifecycleFieldDefinition.project_space_id == project_space_id,
            DataSecureLifecycleFieldDefinition.field_key == field_key,
        )
    ).first()
    if exists:
        raise HTTPException(status_code=400, detail="字段 key 已存在")
    if body.min_length is not None and body.max_length is not None and body.min_length > body.max_length:
        raise HTTPException(status_code=400, detail="最小长度不能大于最大长度")
    allowed_values = form_core.normalize_allowed_values(body.allowed_values)
    regex_pattern = body.regex_pattern.strip() if body.regex_pattern else None
    if regex_pattern:
        try:
            re.compile(regex_pattern)
        except re.error:
            raise HTTPException(status_code=400, detail="正则表达式不合法")
    now = datetime.utcnow()
    field_def = DataSecureLifecycleFieldDefinition(
        tool_id=tool_id,
        project_space_id=project_space_id,
        field_key=field_key,
        label=body.label.strip(),
        input_type=DataSecureFieldInputType(_normalize_input_type(body.input_type)),
        is_builtin=False,
        is_active=True,
        sort_order=9999,
        created_by=updated_by,
        updated_by=updated_by,
        created_at=now,
        updated_at=now,
    )
    db.add(field_def)
    cfg = DataSecureLifecycleFieldConfig(
        tool_id=tool_id,
        project_space_id=project_space_id,
        field_key=field_key,
        help_text=(body.help_text or "").strip() or None,
        required=body.required,
        min_length=body.min_length,
        max_length=body.max_length,
        regex_pattern=regex_pattern,
        regex_error_message=(body.regex_error_message or "").strip() or None,
        allowed_values_json=json.dumps(allowed_values, ensure_ascii=False) if allowed_values else None,
        updated_by=updated_by,
        updated_at=now,
    )
    db.add(cfg)
    db.commit()
    return DataSecureLifecycleFieldConfigItem(
        field_key=field_key,
        label=field_def.label,
        input_type=_normalize_input_type(field_def.input_type),
        is_builtin=False,
        sort_order=field_def.sort_order,
        help_text=cfg.help_text,
        required=bool(cfg.required or False),
        min_length=cfg.min_length,
        max_length=cfg.max_length,
        regex_pattern=cfg.regex_pattern,
        regex_error_message=cfg.regex_error_message,
        allowed_values=allowed_values,
    )


def delete_field_config(db: Session, tool_id: int, project_space_id: int, field_key: str) -> None:
    normalized_key = field_key.strip()
    if normalized_key in BUILTIN_DEF:
        raise HTTPException(status_code=400, detail="内置字段不支持删除")
    field_def = db.exec(
        select(DataSecureLifecycleFieldDefinition).where(
            DataSecureLifecycleFieldDefinition.tool_id == tool_id,
            DataSecureLifecycleFieldDefinition.project_space_id == project_space_id,
            DataSecureLifecycleFieldDefinition.field_key == normalized_key,
        )
    ).first()
    if not field_def:
        raise HTTPException(status_code=404, detail="字段不存在")
    cfg = db.exec(
        select(DataSecureLifecycleFieldConfig).where(
            DataSecureLifecycleFieldConfig.tool_id == tool_id,
            DataSecureLifecycleFieldConfig.project_space_id == project_space_id,
            DataSecureLifecycleFieldConfig.field_key == normalized_key,
        )
    ).first()
    if cfg:
        db.delete(cfg)
    values = db.exec(select(DataSecureFieldCatalogValue).where(DataSecureFieldCatalogValue.field_key == normalized_key)).all()
    for value in values:
        db.delete(value)
    db.delete(field_def)
    db.commit()


def update_field_configs(
    db: Session,
    tool_id: int,
    project_space_id: int,
    items: list[DataSecureLifecycleFieldConfigUpdateItem],
    updated_by: int,
) -> None:
    now = datetime.utcnow()
    field_map = get_field_constraint_map(db, tool_id, project_space_id)
    custom_defs = {
        row.field_key: row
        for row in db.exec(
            select(DataSecureLifecycleFieldDefinition).where(
                DataSecureLifecycleFieldDefinition.tool_id == tool_id,
                DataSecureLifecycleFieldDefinition.project_space_id == project_space_id,
            )
        ).all()
    }
    for item in items:
        field_key = item.field_key.strip()
        cfg = field_map.get(field_key)
        if not cfg:
            raise HTTPException(status_code=400, detail=f"不支持的字段：{field_key}")
        is_builtin = bool(cfg.get("is_builtin"))
        if item.min_length is not None and item.max_length is not None and item.min_length > item.max_length:
            raise HTTPException(status_code=400, detail=f"{field_key} 的最小长度不能大于最大长度")
        allowed_values = form_core.normalize_allowed_values(item.allowed_values)
        regex_pattern = item.regex_pattern.strip() if item.regex_pattern is not None else None
        if regex_pattern:
            try:
                re.compile(regex_pattern)
            except re.error:
                raise HTTPException(status_code=400, detail=f"{field_key} 的正则表达式不合法")
        if not is_builtin:
            definition = custom_defs.get(field_key)
            if not definition:
                raise HTTPException(status_code=400, detail=f"字段定义不存在：{field_key}")
            if item.label is not None:
                definition.label = item.label.strip()
            if item.input_type is not None:
                definition.input_type = DataSecureFieldInputType(_normalize_input_type(item.input_type))
            if item.sort_order is not None:
                definition.sort_order = int(item.sort_order)
            if item.is_active is not None:
                definition.is_active = bool(item.is_active)
            definition.updated_by = updated_by
            definition.updated_at = now
            db.add(definition)
        row = db.exec(
            select(DataSecureLifecycleFieldConfig).where(
                DataSecureLifecycleFieldConfig.tool_id == tool_id,
                DataSecureLifecycleFieldConfig.project_space_id == project_space_id,
                DataSecureLifecycleFieldConfig.field_key == field_key,
            )
        ).first()
        should_reset = (
            (item.help_text is None or str(item.help_text).strip() == "")
            and item.required is None
            and item.min_length is None
            and item.max_length is None
            and (regex_pattern is None or regex_pattern == "")
            and (item.regex_error_message is None or str(item.regex_error_message).strip() == "")
            and not allowed_values
        )
        if should_reset:
            if row:
                db.delete(row)
            continue
        if not row:
            row = DataSecureLifecycleFieldConfig(
                tool_id=tool_id,
                project_space_id=project_space_id,
                field_key=field_key,
                updated_by=updated_by,
                updated_at=now,
            )
        row.help_text = (item.help_text or "").strip() or None
        row.required = item.required
        row.min_length = item.min_length
        row.max_length = item.max_length
        row.regex_pattern = regex_pattern or None
        row.regex_error_message = (item.regex_error_message or "").strip() or None
        row.allowed_values_json = json.dumps(allowed_values, ensure_ascii=False) if allowed_values else None
        row.updated_by = updated_by
        row.updated_at = now
        db.add(row)
    db.commit()


def validate_extra_fields(
    db: Session,
    tool_id: int,
    project_space_id: int,
    raw_extra_fields: dict[str, object],
) -> dict[str, object]:
    field_map = get_field_constraint_map(db, tool_id, project_space_id)
    dynamic_defs = {
        k: v
        for k, v in field_map.items()
        if (not bool(v.get("is_builtin"))) or k == BUSINESS_FUNCTION_FIELD_KEY
    }
    return form_core.normalize_dynamic_extra_fields(
        raw_extra_fields or {},
        dynamic_defs,
        DataSecureFieldInputType.MULTI_SELECT.value,
    )


def validate_extra_fields_subset(
    db: Session,
    tool_id: int,
    project_space_id: int,
    raw_extra_fields: dict[str, object],
) -> dict[str, object]:
    """仅校验请求体中出现的自定义列；不要求补全全部生命周期列（申请阶段使用）。"""
    field_map = get_field_constraint_map(db, tool_id, project_space_id)
    dynamic_defs = {
        k: v
        for k, v in field_map.items()
        if (not bool(v.get("is_builtin"))) or k == BUSINESS_FUNCTION_FIELD_KEY
    }
    return form_core.normalize_dynamic_extra_fields_subset(
        raw_extra_fields or {},
        dynamic_defs,
        DataSecureFieldInputType.MULTI_SELECT.value,
    )


def load_catalog_extra_fields(db: Session, entry_id: int) -> dict[str, object]:
    return form_core.load_custom_field_values(db, DataSecureFieldCatalogValue, entry_id)


def save_catalog_extra_fields(db: Session, entry_id: int, updated_by: int, values: dict[str, object]) -> None:
    form_core.save_custom_field_values(db, DataSecureFieldCatalogValue, entry_id, updated_by, values)


def resolve_business_function_field_key(_db: Session, _tool_id: int, _project_space_id: int) -> str | None:
    """与填报表单内置列一致，固定为 business_function（主表其他信息 JSON 中读写该 key）。"""
    return BUSINESS_FUNCTION_FIELD_KEY


def list_business_function_option_strings(
    db: Session, tool_id: int, project_space_id: int
) -> tuple[str | None, bool, list[str]]:
    """返回 (field_key, 是否已配置该列, 可选功能名称列表)。列表 = 字段允许值 ∪ 主表该列已填过的去重值。"""
    fk = resolve_business_function_field_key(db, tool_id, project_space_id)
    if not fk:
        return None, False, []
    field_map = get_field_constraint_map(db, tool_id, project_space_id)
    cfg = field_map.get(fk) or {}
    allowed = [str(x).strip() for x in (cfg.get("allowed_values") or []) if str(x).strip()]
    catalog_vals: set[str] = set()
    entries = db.exec(
        select(DataSecureFieldCatalogEntry).where(
            DataSecureFieldCatalogEntry.tool_id == tool_id,
            DataSecureFieldCatalogEntry.project_space_id == project_space_id,
        )
    ).all()
    for ent in entries:
        extra = load_catalog_extra_fields(db, int(ent.id))
        raw = extra.get(fk)
        if raw is None:
            continue
        if isinstance(raw, list):
            for x in raw:
                s = str(x).strip()
                if s:
                    catalog_vals.add(s)
        else:
            s = str(raw).strip()
            if s:
                catalog_vals.add(s)
    merged = sorted({*allowed, *catalog_vals})
    # 仅当确有可选项时，前端才应强制下拉选择；否则允许自由输入并可发起新增申请。
    return fk, bool(merged), merged


def validate_assessment_function_name_against_business_options(
    db: Session, tool_id: int, project_space_id: int, function_name: str
) -> None:
    """若已配置「业务功能」列且已有可选清单，则功能名称必须命中清单之一。"""
    fk, _, opts = list_business_function_option_strings(db, tool_id, project_space_id)
    if not fk:
        return
    fn = (function_name or "").strip()
    if not fn:
        raise HTTPException(status_code=400, detail="请填写功能名称")
    if opts and fn not in opts:
        raise HTTPException(
            status_code=400,
            detail="功能名称须从「业务功能」可选列表中选择；若无合适项请使用「申请新增业务功能选项」提交给工具负责人审核",
        )


def append_allowed_value_to_lifecycle_field(
    db: Session, tool_id: int, project_space_id: int, field_key: str, value: str, updated_by: int
) -> None:
    """在指定列的允许值列表末尾追加一项（去重）。自定义列需有定义；内置 business_function 仅写配置行。"""
    fk = field_key.strip()
    val = (value or "").strip()
    if not val:
        raise HTTPException(status_code=400, detail="选项文本不能为空")
    if fk == BUSINESS_FUNCTION_FIELD_KEY:
        cfg_bf = db.exec(
            select(DataSecureLifecycleFieldConfig).where(
                DataSecureLifecycleFieldConfig.tool_id == tool_id,
                DataSecureLifecycleFieldConfig.project_space_id == project_space_id,
                DataSecureLifecycleFieldConfig.field_key == fk,
            )
        ).first()
        vals_bf: list[str] = []
        if cfg_bf and cfg_bf.allowed_values_json:
            vals_bf = form_core.parse_allowed_values_json(cfg_bf.allowed_values_json)
        if val in vals_bf:
            return
        vals_bf.append(val)
        now_bf = datetime.utcnow()
        if not cfg_bf:
            cfg_bf = DataSecureLifecycleFieldConfig(
                tool_id=tool_id,
                project_space_id=project_space_id,
                field_key=fk,
                updated_by=updated_by,
                updated_at=now_bf,
            )
        cfg_bf.allowed_values_json = json.dumps(vals_bf, ensure_ascii=False)
        cfg_bf.updated_by = updated_by
        cfg_bf.updated_at = now_bf
        db.add(cfg_bf)
        db.flush()
        return
    field_def = db.exec(
        select(DataSecureLifecycleFieldDefinition).where(
            DataSecureLifecycleFieldDefinition.tool_id == tool_id,
            DataSecureLifecycleFieldDefinition.project_space_id == project_space_id,
            DataSecureLifecycleFieldDefinition.field_key == fk,
        )
    ).first()
    if not field_def or field_def.is_builtin:
        raise HTTPException(status_code=400, detail="目标填报字段不存在或为内置字段")
    cfg = db.exec(
        select(DataSecureLifecycleFieldConfig).where(
            DataSecureLifecycleFieldConfig.tool_id == tool_id,
            DataSecureLifecycleFieldConfig.project_space_id == project_space_id,
            DataSecureLifecycleFieldConfig.field_key == fk,
        )
    ).first()
    vals: list[str] = []
    if cfg and cfg.allowed_values_json:
        vals = form_core.parse_allowed_values_json(cfg.allowed_values_json)
    if val in vals:
        return
    vals.append(val)
    now = datetime.utcnow()
    if not cfg:
        cfg = DataSecureLifecycleFieldConfig(
            tool_id=tool_id,
            project_space_id=project_space_id,
            field_key=fk,
            updated_by=updated_by,
            updated_at=now,
        )
    cfg.allowed_values_json = json.dumps(vals, ensure_ascii=False)
    cfg.updated_by = updated_by
    cfg.updated_at = now
    db.add(cfg)
    db.flush()
