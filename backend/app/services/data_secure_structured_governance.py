"""结构化数据治理：分类树（多层级）、数据字段分级（C0–C3）、安全要求逻辑表达式。"""

from __future__ import annotations

import json
from typing import Any

from fastapi import HTTPException
from sqlmodel import Session

from app.models import DataSecureFieldClassGrade, DataSecureTaxonomyNode

MAX_TAXONOMY_CHAIN_LEN = 32


def taxonomy_depth_from_root(db: Session, node: DataSecureTaxonomyNode) -> int:
    """根为 0，每向下一层 +1。"""
    d = 0
    cur: DataSecureTaxonomyNode | None = node
    seen: set[int] = set()
    while cur is not None and cur.parent_id is not None:
        nid = int(cur.id) if cur.id is not None else 0
        if nid in seen:
            raise HTTPException(status_code=400, detail="分类节点父链存在环")
        seen.add(nid)
        d += 1
        if d >= MAX_TAXONOMY_CHAIN_LEN:
            raise HTTPException(status_code=400, detail="分类树层级过深")
        cur = db.get(DataSecureTaxonomyNode, int(cur.parent_id))
    return d

CONFIDENTIALITY_GRADES: tuple[str, ...] = (
    "C0-Public",
    "C1-Internal",
    "C2-Confidential",
    "C3-Secret",
)


def normalize_confidentiality_grade(raw: str) -> str:
    text = (raw or "").strip()
    if text not in CONFIDENTIALITY_GRADES:
        raise HTTPException(
            status_code=400,
            detail=f"数据分级须为以下之一：{', '.join(CONFIDENTIALITY_GRADES)}",
        )
    return text


def parse_predicate_map(raw: str | None) -> dict[str, Any]:
    try:
        data = json.loads(raw or "{}")
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(k).strip(): v for k, v in data.items() if str(k).strip()}


def predicate_map_to_json(pred: dict[str, Any]) -> str:
    return json.dumps(pred or {}, ensure_ascii=False)


def validate_predicate_map(pred: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for token, spec in pred.items():
        if not isinstance(spec, dict):
            raise HTTPException(status_code=400, detail=f"谓词「{token}」配置须为对象")
        kind = str(spec.get("kind") or "").strip()
        if kind not in (
            "grade_equals",
            "l1_node_key",
            "l2_node_key",
            "taxonomy_path_node_key",
            "lifecycle_field_contains",
        ):
            raise HTTPException(
                status_code=400,
                detail="谓词「"
                + token
                + "」的 kind 须为 grade_equals / l1_node_key / l2_node_key / taxonomy_path_node_key（路径上任一层 node_key）/ lifecycle_field_contains",
            )
        val = spec.get("value")
        if kind == "grade_equals":
            normalize_confidentiality_grade(str(val or ""))
            out[token] = {"kind": kind, "value": str(val or "").strip()}
            continue
        if kind == "lifecycle_field_contains":
            field_key = str(spec.get("field_key") or "").strip()
            if not field_key:
                raise HTTPException(status_code=400, detail=f"谓词「{token}」须填写 field_key（数据生命周期字段）")
            if val is None or str(val).strip() == "":
                raise HTTPException(status_code=400, detail=f"谓词「{token}」须填写 value（字段值模糊匹配）")
            out[token] = {"kind": kind, "field_key": field_key, "value": str(val).strip()}
            continue
        elif val is None or str(val).strip() == "":
            raise HTTPException(status_code=400, detail=f"谓词「{token}」须填写 value（node_key 或分级值）")
        out[token] = {"kind": kind, "value": str(val).strip() if val is not None else ""}
    return out


def taxonomy_path_node_keys_for_grade(db: Session, class_grade: DataSecureFieldClassGrade | None) -> set[str]:
    """当前密级绑定分类路径上（根→最细）所有节点的 node_key，用于 taxonomy_path_node_key 谓词。"""
    if not class_grade:
        return set()
    try:
        chain = taxonomy_chain_for_grade(db, class_grade)
    except HTTPException:
        return set()
    out: set[str] = set()
    for n in chain:
        k = (n.node_key or "").strip()
        if k:
            out.add(k)
    return out


def build_predicate_truth(
    *,
    class_grade: DataSecureFieldClassGrade | None,
    l1: DataSecureTaxonomyNode | None,
    l2: DataSecureTaxonomyNode | None,
    predicate_map: dict[str, Any],
    lifecycle_fields: dict[str, Any] | None = None,
    taxonomy_path_node_keys: set[str] | None = None,
) -> dict[str, bool]:
    grade = (class_grade.confidentiality_grade if class_grade else "") or ""
    l1_key = (l1.node_key if l1 else "") or ""
    l2_key = (l2.node_key if l2 else "") or ""
    lifecycle_map = lifecycle_fields or {}
    path_keys = taxonomy_path_node_keys or set()
    truth: dict[str, bool] = {}
    for token, spec in predicate_map.items():
        if not isinstance(spec, dict):
            truth[token] = False
            continue
        kind = str(spec.get("kind") or "")
        val = str(spec.get("value") or "").strip()
        if kind == "grade_equals":
            truth[token] = grade == val
        elif kind == "l1_node_key":
            truth[token] = bool(l1_key and l1_key == val)
        elif kind == "l2_node_key":
            truth[token] = bool(l2_key and l2_key == val)
        elif kind == "taxonomy_path_node_key":
            truth[token] = bool(val and path_keys and val.strip() in path_keys)
        elif kind == "lifecycle_field_contains":
            field_key = str(spec.get("field_key") or "").strip()
            raw = lifecycle_map.get(field_key)
            if raw is None:
                truth[token] = False
            elif isinstance(raw, list):
                truth[token] = any(val and val in str(x) for x in raw)
            else:
                truth[token] = bool(val and val in str(raw))
        else:
            truth[token] = False
    return truth


def taxonomy_chain_from_leaf(
    db: Session, tool_id: int, project_space_id: int, leaf_id: int
) -> list[DataSecureTaxonomyNode]:
    """自叶节点沿 parent 回溯至根，返回 [根, …, 叶]。"""
    rev: list[DataSecureTaxonomyNode] = []
    cur_id: int | None = int(leaf_id)
    seen: set[int] = set()
    for _ in range(MAX_TAXONOMY_CHAIN_LEN + 1):
        if cur_id is None:
            break
        if cur_id in seen:
            raise HTTPException(status_code=400, detail="分类节点父链存在环")
        seen.add(cur_id)
        cur = db.get(DataSecureTaxonomyNode, cur_id)
        if not cur or int(cur.tool_id) != int(tool_id) or int(cur.project_space_id) != int(project_space_id):
            raise HTTPException(status_code=404, detail="分类节点不存在")
        rev.append(cur)
        cur_id = int(cur.parent_id) if cur.parent_id is not None else None
    if not rev:
        return []
    rev.reverse()
    return rev


def taxonomy_chain_for_grade(db: Session, row: DataSecureFieldClassGrade) -> list[DataSecureTaxonomyNode]:
    if row.taxonomy_l2_id:
        chain = taxonomy_chain_from_leaf(db, int(row.tool_id), int(row.project_space_id), int(row.taxonomy_l2_id))
        if row.taxonomy_l1_id and chain and int(chain[0].id) != int(row.taxonomy_l1_id):
            raise HTTPException(status_code=400, detail="密级绑定中的根分类与细粒度分类不在同一路径上")
        return chain
    if row.taxonomy_l1_id:
        n = db.get(DataSecureTaxonomyNode, int(row.taxonomy_l1_id))
        if not n:
            return []
        if int(n.tool_id) != int(row.tool_id) or int(n.project_space_id) != int(row.project_space_id):
            return []
        return [n]
    return []


def load_taxonomy_nodes_for_grade(db: Session, row: DataSecureFieldClassGrade) -> tuple[DataSecureTaxonomyNode | None, DataSecureTaxonomyNode | None]:
    """返回 (根节点, 最细分类节点)；仅绑定根时最细为 None。用于谓词 l1_node_key / l2_node_key。"""
    chain = taxonomy_chain_for_grade(db, row)
    if not chain:
        return None, None
    root = chain[0]
    if len(chain) == 1:
        return root, None
    return root, chain[-1]


def display_category_path_for_grade(db: Session, row: DataSecureFieldClassGrade, field_name: str) -> str:
    chain = taxonomy_chain_for_grade(db, row)
    parts = [n.name.strip() for n in chain if n and (n.name or "").strip()]
    parts.append((field_name or "").strip())
    return " / ".join(parts) if parts else (field_name or "").strip()
