"""data-secure-manage tool feature routes."""
from datetime import datetime
import json
import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlmodel import Session, select

from app.api.v1.tools_common import (
    can_manage_all_records,
    ensure_manage_permission,
    ensure_tool_access,
    ensure_tool_operational_for_user,
    get_tool_or_404,
)
from app.api.v1.users import get_current_active_user
from app.database import get_session
from app.models import (
    DataSecureAssessmentAnswer,
    DataSecureAssessmentSubmission,
    DataSecureFieldCatalogEntry,
    DataSecureFieldCatalogValue,
    DataSecureFieldClassGrade,
    DataSecureFieldClassificationAuditLog,
    DataSecureFieldClassificationMatrix,
    DataSecureFieldClassificationResult,
    DataSecureFieldClassificationRule,
    DataSecureFieldSecurityRequirement,
    DataSecureFieldRequest,
    DataSecureFieldRequestStatus,
    DataSecureBusinessFunctionOptionRequest,
    DataSecureGovernanceChangeLog,
    DataSecureFieldUsageReport,
    DataSecureFieldUsageReportItem,
    DataSecureUsageReviewStatus,
    DataSecureLifecycleFieldDefinition,
    DataSecureProjectSpace,
    DataSecureQuestionnaireQuestion,
    DataSecureRelevanceRule,
    DataSecureTaxonomyNode,
    Tool,
    User,
)
from app.schemas import (
    DataSecureAssessmentSubmissionInDB,
    DataSecureAssessmentSubmitRequest,
    DataSecureProjectSpaceCreate,
    DataSecureProjectSpaceDeleteRequest,
    DataSecureProjectSpaceDeleteResult,
    DataSecureProjectSpaceInDB,
    DataSecureSuggestIdentifierKeyRequest,
    DataSecureSuggestIdentifierKeyResponse,
    DataSecureProjectSpaceUpdate,
    DataSecureQuestionCreate,
    DataSecureQuestionDeleteRequest,
    DataSecureQuestionDeleteResult,
    DataSecureQuestionInDB,
    DataSecureQuestionUpdate,
    DataSecureFieldCatalogBatchImport,
    DataSecureFieldCatalogBatchImportResult,
    DataSecureFieldCatalogEntryCreate,
    DataSecureFieldCatalogEntryInDB,
    DataSecureFieldCatalogExtraUpdate,
    DataSecureFieldRequestCreate,
    DataSecureFieldRequestInDB,
    DataSecureFieldRequestReview,
    DataSecureConsolidatedExportResponse,
    DataSecureConsolidatedExportRow,
    DataSecureFieldUsageExportResponse,
    DataSecureFieldUsageExportRow,
    DataSecureFieldUsageLineCreate,
    DataSecureFieldUsageReportCreate,
    DataSecureFieldUsageReportInDB,
    DataSecureFieldUsageReportReviewRequest,
    DataSecureClassificationAuditLogInDB,
    DataSecureClassificationExportResponse,
    DataSecureClassificationExportRow,
    DataSecureClassificationManualOverride,
    DataSecureClassificationMatrixBatchImport,
    DataSecureClassificationMatrixBatchImportResult,
    DataSecureClassificationMatrixCreate,
    DataSecureClassificationMatrixInDB,
    DataSecureClassificationMatrixDeleteResult,
    DataSecureClassificationMatrixUpdate,
    DataSecureClassificationRecomputeResponse,
    DataSecureClassificationResultInDB,
    DataSecureClassificationRuleCreate,
    DataSecureClassificationRuleInDB,
    DataSecureClassificationRuleDeleteResult,
    DataSecureClassificationRuleUpdate,
    PaginatedDataSecureClassificationAuditLogs,
    PaginatedDataSecureClassificationMatrix,
    DataSecureLifecycleFieldConfigCreateRequest,
    DataSecureLifecycleFieldConfigDeleteRequest,
    DataSecureLifecycleFieldConfigListResponse,
    DataSecureLifecycleFieldConfigUpdateItem,
    DataSecureLifecycleFieldConfigUpdateRequest,
    PaginatedDataSecureFieldCatalogEntries,
    DataSecureFieldCatalogValueOptionsResponse,
    PaginatedDataSecureClassificationResults,
    PaginatedDataSecureClassificationRules,
    PaginatedDataSecureFieldRequests,
    DataSecureBusinessFunctionOptionsResponse,
    DataSecureBusinessFunctionOptionRequestCreate,
    DataSecureBusinessFunctionOptionRequestInDB,
    DataSecureBusinessFunctionOptionRequestReview,
    PaginatedDataSecureBusinessFunctionOptionRequests,
    PaginatedDataSecureFieldUsageReports,
    PaginatedDataSecureWorkOrders,
    DataSecureWorkOrderRow,
    DataSecureRelevanceRuleInDB,
    DataSecureRelevanceRuleUpsert,
    PaginatedDataSecureAssessmentSubmissions,
    PaginatedDataSecureProjectSpaces,
    PaginatedDataSecureQuestions,
    DataSecureTaxonomyNodeCreate,
    DataSecureTaxonomyNodeDeleteResult,
    DataSecureTaxonomyNodeInDB,
    DataSecureTaxonomyNodeUpdate,
    PaginatedDataSecureTaxonomyNodes,
    DataSecureFieldClassGradeInDB,
    DataSecureFieldClassGradeUpsert,
    PaginatedDataSecureFieldClassGrades,
    DataSecureFieldSecurityRequirementCreate,
    DataSecureFieldSecurityRequirementEvalRequest,
    DataSecureFieldSecurityRequirementEvalResponse,
    DataSecureFieldSecurityRequirementEvalHit,
    DataSecureFieldSecurityRequirementInDB,
    DataSecureFieldSecurityRequirementDeleteResult,
    DataSecureFieldSecurityRequirementUpdate,
    DataSecureConfigExportRequest,
    DataSecureConfigExportPayload,
    DataSecureConfigExportSelection,
    DataSecureConfigImportRequest,
    DataSecureConfigImportResult,
    DataSecureConfigBatchDeleteRequest,
    DataSecureConfigBatchDeleteResult,
    DataSecureGovernanceChangeLogInDB,
    PaginatedDataSecureGovernanceChangeLogs,
    PaginatedDataSecureFieldSecurityRequirements,
)
from app.services import data_secure_dynamic_fields as ds_dynamic_fields
from app.services import data_secure_structured_governance as ds_struct
from app.services.data_secure_project_space import delete_project_space_cascade
from app.services.identifier_key_slug import suggest_identifier_key

router = APIRouter()
QUESTION_KEY_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_TOOL_KEY = "data-secure-manage"


def _parse_question_keys_json(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        arr = json.loads(raw)
    except Exception:
        return []
    if not isinstance(arr, list):
        return []
    out: list[str] = []
    for item in arr:
        key = str(item or "").strip()
        if key:
            out.append(key)
    return out


def _tokenize_logic_expression(expression: str) -> list[str]:
    src = expression.strip()
    tokens: list[str] = []
    i = 0
    while i < len(src):
        ch = src[i]
        if ch.isspace():
            i += 1
            continue
        if ch in ("(", ")"):
            tokens.append(ch)
            i += 1
            continue
        j = i
        while j < len(src) and (src[j].isalnum() or src[j] in ("_", "-")):
            j += 1
        if j == i:
            raise HTTPException(status_code=400, detail=f"表达式包含非法字符：{ch}")
        tokens.append(src[i:j])
        i = j
    return tokens


def _to_rpn(tokens: list[str], valid_keys: set[str]) -> list[str]:
    output: list[str] = []
    ops: list[str] = []
    precedence = {"or": 1, "and": 2}
    for token in tokens:
        low = token.lower()
        if token == "(":
            ops.append(token)
            continue
        if token == ")":
            while ops and ops[-1] != "(":
                output.append(ops.pop())
            if not ops or ops[-1] != "(":
                raise HTTPException(status_code=400, detail="表达式括号不匹配")
            ops.pop()
            continue
        if low in ("and", "or"):
            while ops and ops[-1].lower() in ("and", "or") and precedence[ops[-1].lower()] >= precedence[low]:
                output.append(ops.pop())
            ops.append(low)
            continue
        if token not in valid_keys:
            raise HTTPException(status_code=400, detail=f"表达式引用了无效题目标识：{token}")
        output.append(token)
    while ops:
        op = ops.pop()
        if op == "(":
            raise HTTPException(status_code=400, detail="表达式括号不匹配")
        output.append(op.lower())
    return output


def _validate_logic_expression(expression: str, valid_keys: set[str]) -> list[str]:
    tokens = _tokenize_logic_expression(expression)
    if not tokens:
        raise HTTPException(status_code=400, detail="逻辑表达式不能为空")
    rpn = _to_rpn(tokens, valid_keys)
    depth = 0
    for token in rpn:
        if token in ("and", "or"):
            if depth < 2:
                raise HTTPException(status_code=400, detail="逻辑表达式格式无效")
            depth -= 1
        else:
            depth += 1
    if depth != 1:
        raise HTTPException(status_code=400, detail="逻辑表达式格式无效")
    return rpn


def _eval_logic_expression(expression: str, valid_keys: set[str], answer_by_key: dict[str, bool]) -> bool:
    rpn = _validate_logic_expression(expression, valid_keys)
    stack: list[bool] = []
    for token in rpn:
        if token in ("and", "or"):
            b = stack.pop()
            a = stack.pop()
            stack.append((a and b) if token == "and" else (a or b))
        else:
            stack.append(bool(answer_by_key.get(token, False)))
    return bool(stack[0]) if stack else False


def _validate_taxonomy_node_key(node_key: str) -> str:
    nk = (node_key or "").strip()
    if not nk or len(nk) > 64:
        raise HTTPException(status_code=400, detail="分类 node_key 长度须为 1–64")
    for ch in nk:
        if not (ch.isalnum() or ch in "_-"):
            raise HTTPException(status_code=400, detail="node_key 仅允许字母、数字、下划线、连字符")
    return nk


def _get_taxonomy_node_in_space(
    db: Session, tool_id: int, project_space_id: int, node_id: int
) -> DataSecureTaxonomyNode:
    row = db.get(DataSecureTaxonomyNode, node_id)
    if not row or row.tool_id != tool_id or row.project_space_id != project_space_id:
        raise HTTPException(status_code=404, detail="分类节点不存在")
    return row


def _taxonomy_parent_for_create(
    db: Session, tool_id: int, project_space_id: int, parent_id: int | None
) -> DataSecureTaxonomyNode | None:
    if parent_id is None:
        return None
    parent = _get_taxonomy_node_in_space(db, tool_id, project_space_id, int(parent_id))
    depth = ds_struct.taxonomy_depth_from_root(db, parent)
    if depth + 1 >= ds_struct.MAX_TAXONOMY_CHAIN_LEN:
        raise HTTPException(
            status_code=400,
            detail=f"分类树单链最多 {ds_struct.MAX_TAXONOMY_CHAIN_LEN} 级（含根），无法在更深层级下继续新增",
        )
    return parent


def _resolve_class_grade_taxonomy_ids(
    db: Session,
    tool_id: int,
    project_space_id: int,
    taxonomy_l1_id: int | None,
    taxonomy_l2_id: int | None,
) -> tuple[int | None, int | None]:
    """taxonomy_l2_id 表示最细粒度分类节点（任意深度）；taxonomy_l1_id 须与其根一致或留空由服务端推导。"""
    if taxonomy_l2_id is not None:
        leaf = _get_taxonomy_node_in_space(db, tool_id, project_space_id, int(taxonomy_l2_id))
        chain = ds_struct.taxonomy_chain_from_leaf(db, tool_id, project_space_id, int(leaf.id))
        if not chain:
            raise HTTPException(status_code=400, detail="分类节点链无效")
        root_id = int(chain[0].id)
        if taxonomy_l1_id is not None and int(taxonomy_l1_id) != root_id:
            raise HTTPException(status_code=400, detail="taxonomy_l1_id 须为最细分类节点所在路径的根节点")
        if int(leaf.id) == root_id:
            return root_id, None
        return root_id, int(leaf.id)
    if taxonomy_l1_id is not None:
        l1 = _get_taxonomy_node_in_space(db, tool_id, project_space_id, int(taxonomy_l1_id))
        if l1.parent_id is not None:
            raise HTTPException(
                status_code=400,
                detail="仅绑定根分类时 taxonomy_l1_id 须为根节点；若绑定子级，请填写 taxonomy_l2_id（最细分类节点）",
            )
        return int(l1.id), None
    return None, None


def _build_taxonomy_node_row(row: DataSecureTaxonomyNode) -> DataSecureTaxonomyNodeInDB:
    return DataSecureTaxonomyNodeInDB(
        id=int(row.id),
        tool_id=row.tool_id,
        project_space_id=row.project_space_id,
        parent_id=row.parent_id,
        name=row.name,
        node_key=row.node_key,
        sort_order=row.sort_order,
        is_active=row.is_active,
        created_by=row.created_by,
        updated_by=row.updated_by,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _build_class_grade_row(
    db: Session, row: DataSecureFieldClassGrade, entry: DataSecureFieldCatalogEntry | None = None
) -> DataSecureFieldClassGradeInDB:
    ent = entry if entry is not None else db.get(DataSecureFieldCatalogEntry, row.catalog_entry_id)
    try:
        chain = ds_struct.taxonomy_chain_for_grade(db, row)
    except HTTPException:
        chain = []
    path_names = " / ".join(n.name.strip() for n in chain if n and (n.name or "").strip()) or None
    path_ids = [int(n.id) for n in chain if n.id is not None] or None
    root = chain[0] if chain else None
    leaf = chain[-1] if len(chain) > 1 else None
    return DataSecureFieldClassGradeInDB(
        id=int(row.id),
        tool_id=row.tool_id,
        project_space_id=row.project_space_id,
        catalog_entry_id=int(row.catalog_entry_id),
        field_name=(ent.field_name if ent else "") or "",
        taxonomy_l1_id=row.taxonomy_l1_id,
        taxonomy_l2_id=row.taxonomy_l2_id,
        taxonomy_l1_name=root.name if root else None,
        taxonomy_l2_name=leaf.name if leaf else None,
        taxonomy_path=path_names,
        taxonomy_path_ids=path_ids,
        confidentiality_grade=row.confidentiality_grade,
        notes=row.notes,
        created_by=row.created_by,
        updated_by=row.updated_by,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _build_security_requirement_row(
    db: Session, row: DataSecureFieldSecurityRequirement, entry: DataSecureFieldCatalogEntry | None = None
) -> DataSecureFieldSecurityRequirementInDB:
    ent = entry if entry is not None else db.get(DataSecureFieldCatalogEntry, row.catalog_entry_id)
    pred: dict[str, Any] = {}
    try:
        pred = json.loads(row.predicate_map_json or "{}")
    except Exception:
        pred = {}
    if not isinstance(pred, dict):
        pred = {}
    return DataSecureFieldSecurityRequirementInDB(
        id=int(row.id),
        tool_id=row.tool_id,
        project_space_id=row.project_space_id,
        catalog_entry_id=int(row.catalog_entry_id),
        field_name=(ent.field_name if ent else "") or "",
        requirement_text=row.requirement_text,
        logic_expression=row.logic_expression,
        predicate_map=pred,
        priority=row.priority,
        sort_order=row.sort_order,
        is_active=row.is_active,
        created_by=row.created_by,
        updated_by=row.updated_by,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _sync_structured_to_classification_result(
    db: Session,
    tool_id: int,
    project_space_id: int,
    entry: DataSecureFieldCatalogEntry,
    class_grade: DataSecureFieldClassGrade,
    updated_by: int,
) -> None:
    cat_path = ds_struct.display_category_path_for_grade(db, class_grade, entry.field_name)
    grade = class_grade.confidentiality_grade
    hit = f"已按分类分级和要求治理绑定：展示路径「{cat_path}」，密级「{grade}」。"
    row = db.exec(
        select(DataSecureFieldClassificationResult).where(
            DataSecureFieldClassificationResult.catalog_entry_id == int(entry.id)
        )
    ).first()
    now = datetime.utcnow()
    if not row:
        row = DataSecureFieldClassificationResult(
            tool_id=tool_id,
            project_space_id=project_space_id,
            catalog_entry_id=int(entry.id),
            field_name_snapshot=entry.field_name,
            category=cat_path,
            level=grade,
            rule_keyword=None,
            auto_category=cat_path,
            auto_level=grade,
            auto_rule_keyword=None,
            auto_rule_id=None,
            auto_matrix_id=None,
            auto_match_source="structured",
            auto_hit_summary=hit,
            manual_reason=None,
            source="auto",
            updated_by=updated_by,
            updated_at=now,
        )
    else:
        row.field_name_snapshot = entry.field_name
        row.auto_category = cat_path
        row.auto_level = grade
        row.auto_rule_keyword = None
        row.auto_rule_id = None
        row.auto_matrix_id = None
        row.auto_match_source = "structured"
        row.auto_hit_summary = hit
        if row.source != "manual":
            row.category = cat_path
            row.level = grade
            row.rule_keyword = None
        row.updated_by = updated_by
        row.updated_at = now
    db.add(row)


def _ensure_data_secure_manage_tool(tool: Tool) -> None:
    if tool.name != _TOOL_KEY:
        raise HTTPException(status_code=400, detail="当前功能仅支持 data-secure-manage 工具")


def _ensure_tool_feature_access(db: Session, current_user: User, tool: Tool) -> None:
    ensure_tool_operational_for_user(current_user, tool)
    ensure_tool_access(db, current_user, tool.id)


def _normalize_change_reason(reason: str) -> str:
    text = (reason or "").strip()
    if len(text) < 5:
        raise HTTPException(status_code=400, detail="请填写变更原因，至少 5 个字")
    return text


def _append_governance_change_log(
    db: Session,
    *,
    tool_id: int,
    project_space_id: int,
    domain: str,
    action: str,
    target_type: str,
    target_id: str,
    change_reason: str,
    changed_by: int,
    detail: dict[str, Any] | None = None,
) -> None:
    db.add(
        DataSecureGovernanceChangeLog(
            tool_id=tool_id,
            project_space_id=project_space_id,
            domain=domain,
            action=action,
            target_type=target_type,
            target_id=target_id,
            change_reason=change_reason,
            detail_json=json.dumps(detail or {}, ensure_ascii=False),
            changed_by=changed_by,
            created_at=datetime.utcnow(),
        )
    )


def _build_governance_change_log_row(db: Session, row: DataSecureGovernanceChangeLog) -> DataSecureGovernanceChangeLogInDB:
    who = db.get(User, row.changed_by)
    try:
        detail = json.loads(row.detail_json or "{}")
    except Exception:
        detail = {}
    if not isinstance(detail, dict):
        detail = {}
    return DataSecureGovernanceChangeLogInDB(
        id=int(row.id),
        tool_id=row.tool_id,
        project_space_id=row.project_space_id,
        domain=row.domain,
        action=row.action,
        target_type=row.target_type,
        target_id=row.target_id,
        change_reason=row.change_reason,
        detail=detail,
        changed_by=row.changed_by,
        changed_by_name=who.username if who else None,
        created_at=row.created_at,
    )


def _build_space_row(row: DataSecureProjectSpace) -> DataSecureProjectSpaceInDB:
    return DataSecureProjectSpaceInDB(
        id=int(row.id),
        tool_id=row.tool_id,
        space_key=row.space_key,
        name=row.name,
        description=row.description,
        is_active=row.is_active,
        created_by=row.created_by,
        updated_by=row.updated_by,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _build_question_row(row: DataSecureQuestionnaireQuestion) -> DataSecureQuestionInDB:
    return DataSecureQuestionInDB(
        id=int(row.id),
        tool_id=row.tool_id,
        project_space_id=row.project_space_id,
        question_key=row.question_key,
        title=row.title,
        help_text=row.help_text,
        question_type=row.question_type.value,
        is_required=row.is_required,
        sort_order=row.sort_order,
        is_active=row.is_active,
        created_by=row.created_by,
        updated_by=row.updated_by,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _build_catalog_entry_row(db: Session, row: DataSecureFieldCatalogEntry) -> DataSecureFieldCatalogEntryInDB:
    return DataSecureFieldCatalogEntryInDB(
        id=int(row.id),
        tool_id=row.tool_id,
        project_space_id=row.project_space_id,
        field_name=row.field_name,
        extra_fields=ds_dynamic_fields.load_catalog_extra_fields(db, int(row.id)),
        created_by=row.created_by,
        updated_by=row.updated_by,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _try_insert_field_catalog_entry(
    db: Session,
    *,
    tool_id: int,
    project_space_id: int,
    field_name: str,
    extra_fields: dict,
    created_by_user_id: int,
    updated_by_user_id: int,
) -> tuple[DataSecureFieldCatalogEntry | None, str | None]:
    """在主表插入一条记录（含扩展列子集校验与分类初始化）。重复或校验失败返回 (None, 说明)。"""
    fn = (field_name or "").strip()
    if not fn:
        return None, "数据字段名称不能为空"
    exists = db.exec(
        select(DataSecureFieldCatalogEntry).where(
            DataSecureFieldCatalogEntry.tool_id == tool_id,
            DataSecureFieldCatalogEntry.project_space_id == project_space_id,
            DataSecureFieldCatalogEntry.field_name == fn,
        )
    ).first()
    if exists:
        return None, "主表中已存在同名数据字段"
    try:
        normalized = ds_dynamic_fields.validate_extra_fields_subset(
            db,
            tool_id,
            project_space_id,
            extra_fields or {},
        )
    except HTTPException as exc:
        return None, str(exc.detail)
    now = datetime.utcnow()
    entry = DataSecureFieldCatalogEntry(
        tool_id=tool_id,
        project_space_id=project_space_id,
        field_name=fn,
        created_by=created_by_user_id,
        updated_by=updated_by_user_id,
        created_at=now,
        updated_at=now,
    )
    db.add(entry)
    db.flush()
    ds_dynamic_fields.save_catalog_extra_fields(db, int(entry.id), updated_by_user_id, normalized)
    _upsert_classification_for_entry(db, tool_id, project_space_id, entry, updated_by_user_id)
    return entry, None


def _build_field_request_row(db: Session, row: DataSecureFieldRequest) -> DataSecureFieldRequestInDB:
    requester = db.get(User, row.requested_by)
    reviewer = db.get(User, row.reviewed_by) if row.reviewed_by else None
    space = db.get(DataSecureProjectSpace, row.project_space_id)
    payload: dict = {}
    try:
        payload = json.loads(row.payload_json or "{}")
    except Exception:
        payload = {}
    return DataSecureFieldRequestInDB(
        id=int(row.id),
        tool_id=row.tool_id,
        project_space_id=row.project_space_id,
        project_space_name=space.name if space else f"空间#{row.project_space_id}",
        requested_by=row.requested_by,
        requested_by_name=requester.username if requester else None,
        request_type=(row.request_type or "data_field"),
        field_name=row.field_name,
        reason=row.reason,
        payload=payload,
        status=row.status.value,
        review_notes=row.review_notes,
        reviewed_by=row.reviewed_by,
        reviewed_by_name=reviewer.username if reviewer else None,
        reviewed_at=row.reviewed_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _build_usage_report_row(db: Session, row: DataSecureFieldUsageReport) -> DataSecureFieldUsageReportInDB:
    submitter = db.get(User, row.submitted_by)
    reviewer = db.get(User, row.reviewed_by) if getattr(row, "reviewed_by", None) else None
    space = db.get(DataSecureProjectSpace, row.project_space_id)
    items = db.exec(
        select(DataSecureFieldUsageReportItem).where(
            DataSecureFieldUsageReportItem.report_id == int(row.id)
        )
    ).all()
    entry_ids = [int(item.catalog_entry_id) for item in items]
    field_names = [item.field_name_snapshot for item in items]
    rs = getattr(row, "review_status", None)
    rs_val = rs.value if hasattr(rs, "value") else (rs or "pending")
    return DataSecureFieldUsageReportInDB(
        id=int(row.id),
        tool_id=row.tool_id,
        project_space_id=row.project_space_id,
        project_space_name=space.name if space else f"空间#{row.project_space_id}",
        submitted_by=row.submitted_by,
        submitted_by_name=submitter.username if submitter else None,
        assessment_submission_id=getattr(row, "assessment_submission_id", None),
        function_name=row.function_name,
        function_description=row.function_description,
        field_entry_ids=entry_ids,
        field_names=field_names,
        notes=row.notes,
        review_status=str(rs_val),
        review_notes=getattr(row, "review_notes", None),
        reviewed_by=getattr(row, "reviewed_by", None),
        reviewed_by_name=reviewer.username if reviewer else None,
        reviewed_at=getattr(row, "reviewed_at", None),
        submitted_at=row.submitted_at,
    )


def _security_requirements_join_text(db: Session, tool_id: int, project_space_id: int, catalog_entry_id: int) -> str:
    rows = db.exec(
        select(DataSecureFieldSecurityRequirement)
        .where(
            DataSecureFieldSecurityRequirement.tool_id == tool_id,
            DataSecureFieldSecurityRequirement.project_space_id == project_space_id,
            DataSecureFieldSecurityRequirement.catalog_entry_id == catalog_entry_id,
            DataSecureFieldSecurityRequirement.is_active == True,  # noqa: E712
        )
        .order_by(
            DataSecureFieldSecurityRequirement.priority.desc(),
            DataSecureFieldSecurityRequirement.sort_order,
            DataSecureFieldSecurityRequirement.id,
        )
    ).all()
    parts = [str(r.requirement_text or "").strip() for r in rows if str(r.requirement_text or "").strip()]
    return "；".join(parts[:80])


def _build_classification_rule_row(row: DataSecureFieldClassificationRule) -> DataSecureClassificationRuleInDB:
    return DataSecureClassificationRuleInDB(
        id=int(row.id),
        tool_id=row.tool_id,
        project_space_id=row.project_space_id,
        keyword=row.keyword,
        category=row.category,
        level=row.level,
        priority=int(getattr(row, "priority", 100) or 100),
        notes=row.notes,
        sort_order=row.sort_order,
        is_active=row.is_active,
        created_by=row.created_by,
        updated_by=row.updated_by,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _parse_matrix_criteria_json(raw: str | None) -> dict[str, Any]:
    try:
        data = json.loads(raw or "{}")
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(k).strip(): v for k, v in data.items() if str(k).strip()}


def _matrix_criteria_to_json(criteria: dict[str, Any]) -> str:
    return json.dumps(criteria or {}, ensure_ascii=False)


def _validate_matrix_extension_match(
    db: Session, tool_id: int, project_space_id: int, criteria: dict[str, Any]
) -> dict[str, Any]:
    field_map = ds_dynamic_fields.get_field_constraint_map(db, tool_id, project_space_id)
    custom_keys = {k for k, v in field_map.items() if not bool(v.get("is_builtin"))}
    out: dict[str, Any] = {}
    for k, v in (criteria or {}).items():
        key = str(k).strip()
        if not key:
            continue
        if key not in custom_keys:
            raise HTTPException(status_code=400, detail=f"扩展列条件含未知字段：{key}")
        out[key] = v
    return out


def _normalize_matrix_match_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        parts = sorted(str(x).strip() for x in value if str(x).strip())
        return "|".join(parts)
    return str(value).strip()


def _catalog_extra_matches_matrix_criteria(catalog_extra: dict[str, Any], criteria: dict[str, Any]) -> bool:
    for key, expected in criteria.items():
        if key not in catalog_extra:
            return False
        if _normalize_matrix_match_value(expected) != _normalize_matrix_match_value(catalog_extra.get(key)):
            return False
    return True


def _format_matrix_hit_summary(spec: DataSecureFieldClassificationMatrix, field_name: str) -> str:
    crit = _parse_matrix_criteria_json(spec.extension_match_json)
    crit_txt = json.dumps(crit, ensure_ascii=False) if crit else "（无扩展列条件，仅数据字段名称精确匹配）"
    return (
        f"已按「显式分类矩阵」命中：矩阵编号 {spec.id}，优先级 {spec.priority}，排序号 {spec.sort_order}；"
        f"数据字段「{field_name.strip()}」且扩展列同时精确匹配 {crit_txt}；"
        f"分类为「{spec.category}」，分级为「{spec.level}」。"
    )


def _match_classification_matrix(
    field_name: str,
    catalog_extra: dict[str, Any],
    specs: list[DataSecureFieldClassificationMatrix],
) -> tuple[str, str, int | None, DataSecureFieldClassificationMatrix | None]:
    fn = (field_name or "").strip()
    for spec in specs:
        if not spec.is_active:
            continue
        if (spec.field_name or "").strip() != fn:
            continue
        crit = _parse_matrix_criteria_json(spec.extension_match_json)
        if not _catalog_extra_matches_matrix_criteria(catalog_extra, crit):
            continue
        return spec.category, spec.level, int(spec.id), spec
    return "未分类", "L0", None, None


def _build_classification_matrix_row(row: DataSecureFieldClassificationMatrix) -> DataSecureClassificationMatrixInDB:
    return DataSecureClassificationMatrixInDB(
        id=int(row.id),
        tool_id=row.tool_id,
        project_space_id=row.project_space_id,
        field_name=row.field_name,
        extension_match=_parse_matrix_criteria_json(row.extension_match_json),
        category=row.category,
        level=row.level,
        priority=int(getattr(row, "priority", 200) or 200),
        notes=row.notes,
        sort_order=row.sort_order,
        is_active=row.is_active,
        created_by=row.created_by,
        updated_by=row.updated_by,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _build_classification_result_row(db: Session, row: DataSecureFieldClassificationResult) -> DataSecureClassificationResultInDB:
    updater = db.get(User, row.updated_by)
    return DataSecureClassificationResultInDB(
        id=int(row.id),
        tool_id=row.tool_id,
        project_space_id=row.project_space_id,
        catalog_entry_id=row.catalog_entry_id,
        field_name_snapshot=row.field_name_snapshot,
        category=row.category,
        level=row.level,
        rule_keyword=row.rule_keyword,
        auto_category=str(getattr(row, "auto_category", None) or row.category),
        auto_level=str(getattr(row, "auto_level", None) or row.level),
        auto_rule_keyword=getattr(row, "auto_rule_keyword", None),
        auto_rule_id=getattr(row, "auto_rule_id", None),
        auto_matrix_id=getattr(row, "auto_matrix_id", None),
        auto_match_source=str(getattr(row, "auto_match_source", None) or "keyword"),
        auto_hit_summary=getattr(row, "auto_hit_summary", None),
        manual_reason=getattr(row, "manual_reason", None),
        source=row.source,
        updated_by=row.updated_by,
        updated_by_name=updater.username if updater else None,
        updated_at=row.updated_at,
    )


def _append_classification_audit(
    db: Session,
    tool_id: int,
    project_space_id: int,
    user_id: int,
    action: str,
    detail: dict,
    catalog_entry_id: int | None = None,
    result_id: int | None = None,
) -> None:
    log = DataSecureFieldClassificationAuditLog(
        tool_id=tool_id,
        project_space_id=project_space_id,
        catalog_entry_id=catalog_entry_id,
        result_id=result_id,
        user_id=user_id,
        action=action,
        detail_json=json.dumps(detail, ensure_ascii=False),
        created_at=datetime.utcnow(),
    )
    db.add(log)


def _build_classification_audit_row(db: Session, row: DataSecureFieldClassificationAuditLog) -> DataSecureClassificationAuditLogInDB:
    actor = db.get(User, row.user_id)
    detail: dict = {}
    try:
        detail = json.loads(row.detail_json or "{}")
    except Exception:
        detail = {}
    return DataSecureClassificationAuditLogInDB(
        id=int(row.id),
        tool_id=row.tool_id,
        project_space_id=row.project_space_id,
        catalog_entry_id=row.catalog_entry_id,
        result_id=row.result_id,
        user_id=row.user_id,
        user_name=actor.username if actor else None,
        action=row.action,
        detail=detail,
        created_at=row.created_at,
    )


def _format_auto_hit_summary(
    field_name: str,
    matched: DataSecureFieldClassificationRule | None,
    auto_cat: str,
    auto_level: str,
) -> str:
    if matched:
        return (
            f"已按「优先级数值优先，其次排序号，再按规则编号」匹配：当前命中规则编号 {matched.id}，"
            f"优先级 {matched.priority}，排序号 {matched.sort_order}，关键词「{matched.keyword}」；"
            f"自动分类为「{auto_cat}」，分级为「{auto_level}」。数据字段名：{field_name}。"
        )
    return f"未命中任何启用规则，已使用默认分类「{auto_cat}」、分级「{auto_level}」。数据字段名：{field_name}。"


def _match_classification_rule(
    field_name: str, rules: list[DataSecureFieldClassificationRule]
) -> tuple[str, str, str | None, int | None, DataSecureFieldClassificationRule | None]:
    text = (field_name or "").strip().lower()
    for rule in rules:
        if not rule.is_active:
            continue
        keyword = (rule.keyword or "").strip().lower()
        if keyword and keyword in text:
            return rule.category, rule.level, rule.keyword, int(rule.id), rule
    return "未分类", "L0", None, None, None


def _upsert_classification_for_entry(
    db: Session,
    tool_id: int,
    project_space_id: int,
    entry: DataSecureFieldCatalogEntry,
    updated_by: int,
) -> None:
    specs = db.exec(
        select(DataSecureFieldClassificationMatrix)
        .where(
            DataSecureFieldClassificationMatrix.tool_id == tool_id,
            DataSecureFieldClassificationMatrix.project_space_id == project_space_id,
            DataSecureFieldClassificationMatrix.is_active == True,  # noqa: E712
        )
        .order_by(
            DataSecureFieldClassificationMatrix.priority.desc(),
            DataSecureFieldClassificationMatrix.sort_order,
            DataSecureFieldClassificationMatrix.id,
        )
    ).all()
    catalog_extra_raw = ds_dynamic_fields.load_catalog_extra_fields(db, int(entry.id))
    catalog_extra: dict[str, Any] = {str(k): v for k, v in (catalog_extra_raw or {}).items()}
    auto_cat, auto_level, matrix_id, matched_matrix = _match_classification_matrix(
        entry.field_name, catalog_extra, specs
    )
    matched_rule = None
    auto_kw: str | None = None
    auto_rid: int | None = None
    match_source = "default"
    hit = ""
    if matched_matrix is not None:
        match_source = "matrix"
        hit = _format_matrix_hit_summary(matched_matrix, entry.field_name)
    else:
        rules = db.exec(
            select(DataSecureFieldClassificationRule)
            .where(
                DataSecureFieldClassificationRule.tool_id == tool_id,
                DataSecureFieldClassificationRule.project_space_id == project_space_id,
                DataSecureFieldClassificationRule.is_active == True,  # noqa: E712
            )
            .order_by(
                DataSecureFieldClassificationRule.priority.desc(),
                DataSecureFieldClassificationRule.sort_order,
                DataSecureFieldClassificationRule.id,
            )
        ).all()
        auto_cat, auto_level, auto_kw, auto_rid, matched_rule = _match_classification_rule(entry.field_name, rules)
        hit = _format_auto_hit_summary(entry.field_name, matched_rule, auto_cat, auto_level)
        match_source = "keyword" if matched_rule is not None else "default"
    row = db.exec(
        select(DataSecureFieldClassificationResult).where(
            DataSecureFieldClassificationResult.catalog_entry_id == int(entry.id)
        )
    ).first()
    now = datetime.utcnow()
    if not row:
        row = DataSecureFieldClassificationResult(
            tool_id=tool_id,
            project_space_id=project_space_id,
            catalog_entry_id=int(entry.id),
            field_name_snapshot=entry.field_name,
            category=auto_cat,
            level=auto_level,
            rule_keyword=auto_kw,
            auto_category=auto_cat,
            auto_level=auto_level,
            auto_rule_keyword=auto_kw,
            auto_rule_id=auto_rid,
            auto_matrix_id=matrix_id,
            auto_match_source=match_source,
            auto_hit_summary=hit,
            manual_reason=None,
            source="auto",
            updated_by=updated_by,
            updated_at=now,
        )
    else:
        row.field_name_snapshot = entry.field_name
        row.auto_category = auto_cat
        row.auto_level = auto_level
        row.auto_rule_keyword = auto_kw
        row.auto_rule_id = auto_rid
        row.auto_matrix_id = matrix_id
        row.auto_match_source = match_source
        row.auto_hit_summary = hit
        if row.source != "manual":
            row.category = auto_cat
            row.level = auto_level
            row.rule_keyword = auto_kw
        row.updated_by = updated_by
        row.updated_at = now
    db.add(row)


@router.get("/{tool_id}/features/project-spaces", response_model=PaginatedDataSecureProjectSpaces)
async def list_project_spaces(
    tool_id: int,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=200),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    _ensure_data_secure_manage_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    where = [DataSecureProjectSpace.tool_id == tool_id]
    if not can_manage_all_records(db, current_user, tool_id):
        where.append(DataSecureProjectSpace.is_active == True)  # noqa: E712
    total = db.exec(select(func.count()).select_from(DataSecureProjectSpace).where(*where)).one()
    rows = db.exec(
        select(DataSecureProjectSpace)
        .where(*where)
        .order_by(DataSecureProjectSpace.updated_at.desc())
        .offset(skip)
        .limit(limit)
    ).all()
    return PaginatedDataSecureProjectSpaces(total=int(total or 0), items=[_build_space_row(r) for r in rows])


@router.post("/{tool_id}/features/suggest-identifier-key", response_model=DataSecureSuggestIdentifierKeyResponse)
async def suggest_identifier_key_route(
    tool_id: int,
    body: DataSecureSuggestIdentifierKeyRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    _ensure_data_secure_manage_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    ensure_manage_permission(db, current_user, tool_id)
    key = suggest_identifier_key(body.source_text, body.target)
    return DataSecureSuggestIdentifierKeyResponse(key=key)


@router.post("/{tool_id}/features/project-spaces", response_model=DataSecureProjectSpaceInDB)
async def create_project_space(
    tool_id: int,
    body: DataSecureProjectSpaceCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    _ensure_data_secure_manage_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    ensure_manage_permission(db, current_user, tool_id)
    if body.copy_from_project_space_id is not None:
        _normalize_change_reason(body.change_reason or "")
        src_space = db.get(DataSecureProjectSpace, int(body.copy_from_project_space_id))
        if not src_space or int(src_space.tool_id) != int(tool_id):
            raise HTTPException(status_code=404, detail="复制源项目空间不存在")
    exists = db.exec(
        select(DataSecureProjectSpace).where(
            DataSecureProjectSpace.tool_id == tool_id,
            DataSecureProjectSpace.space_key == body.space_key.strip(),
        )
    ).first()
    if exists:
        raise HTTPException(status_code=400, detail="项目空间标识已存在")
    now = datetime.utcnow()
    row = DataSecureProjectSpace(
        tool_id=tool_id,
        space_key=body.space_key.strip(),
        name=body.name.strip(),
        description=(body.description or "").strip() or None,
        is_active=body.is_active,
        created_by=current_user.id,
        updated_by=current_user.id,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    new_id = int(row.id)
    if body.copy_from_project_space_id is not None:
        src_id = int(body.copy_from_project_space_id)
        reason = _normalize_change_reason(body.change_reason or "")
        sel = DataSecureConfigExportSelection(
            include_spaces=False,
            include_questions=True,
            include_relevance_rule=True,
            include_lifecycle_fields=True,
            include_taxonomy_nodes=True,
            include_field_class_grades=True,
            include_security_requirements=True,
            include_classification_rules=True,
            include_classification_matrix=True,
        )
        export_payload = _build_config_export_payload(db, tool_id, src_id, sel)
        import_body = DataSecureConfigImportRequest(
            target_project_space_id=new_id,
            payload=export_payload,
            change_reason=reason,
        )
        _apply_data_secure_config_import(db, tool_id, import_body, current_user)
    return _build_space_row(row)


@router.put("/{tool_id}/features/project-spaces", response_model=DataSecureProjectSpaceInDB)
async def update_project_space(
    tool_id: int,
    body: DataSecureProjectSpaceUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    _ensure_data_secure_manage_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    ensure_manage_permission(db, current_user, tool_id)
    row = db.get(DataSecureProjectSpace, body.id)
    if not row or row.tool_id != tool_id:
        raise HTTPException(status_code=404, detail="项目空间不存在")
    if body.space_key is not None:
        key = body.space_key.strip()
        exists = db.exec(
            select(DataSecureProjectSpace).where(
                DataSecureProjectSpace.tool_id == tool_id,
                DataSecureProjectSpace.space_key == key,
            )
        ).first()
        if exists and exists.id != row.id:
            raise HTTPException(status_code=400, detail="项目空间标识已存在")
        row.space_key = key
    if body.name is not None:
        row.name = body.name.strip()
    if body.description is not None:
        row.description = body.description.strip() or None
    if body.is_active is not None:
        row.is_active = body.is_active
    row.updated_by = current_user.id
    row.updated_at = datetime.utcnow()
    db.add(row)
    db.commit()
    db.refresh(row)
    return _build_space_row(row)


@router.post("/{tool_id}/features/project-spaces/delete", response_model=DataSecureProjectSpaceDeleteResult)
async def delete_project_space_endpoint(
    tool_id: int,
    body: DataSecureProjectSpaceDeleteRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    _ensure_data_secure_manage_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    ensure_manage_permission(db, current_user, tool_id)
    _normalize_change_reason(body.change_reason)
    delete_project_space_cascade(db, tool_id, int(body.id))
    return DataSecureProjectSpaceDeleteResult()


@router.get("/{tool_id}/features/questionnaire/questions", response_model=PaginatedDataSecureQuestions)
async def list_questions(
    tool_id: int,
    project_space_id: int,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    _ensure_data_secure_manage_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    where = [
        DataSecureQuestionnaireQuestion.tool_id == tool_id,
        DataSecureQuestionnaireQuestion.project_space_id == project_space_id,
    ]
    if not can_manage_all_records(db, current_user, tool_id):
        where.append(DataSecureQuestionnaireQuestion.is_active == True)  # noqa: E712
    total = db.exec(select(func.count()).select_from(DataSecureQuestionnaireQuestion).where(*where)).one()
    rows = db.exec(
        select(DataSecureQuestionnaireQuestion)
        .where(*where)
        .order_by(DataSecureQuestionnaireQuestion.sort_order.asc(), DataSecureQuestionnaireQuestion.id.asc())
        .offset(skip)
        .limit(limit)
    ).all()
    return PaginatedDataSecureQuestions(total=int(total or 0), items=[_build_question_row(r) for r in rows])


@router.post("/{tool_id}/features/questionnaire/questions", response_model=DataSecureQuestionInDB)
async def create_question(
    tool_id: int,
    body: DataSecureQuestionCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    _ensure_data_secure_manage_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    ensure_manage_permission(db, current_user, tool_id)
    space = db.get(DataSecureProjectSpace, body.project_space_id)
    if not space or space.tool_id != tool_id:
        raise HTTPException(status_code=404, detail="项目空间不存在")
    question_key = body.question_key.strip()
    if not QUESTION_KEY_PATTERN.fullmatch(question_key):
        raise HTTPException(status_code=400, detail="题目标识仅支持字母、数字、下划线、连字符，长度 1-64")
    exists = db.exec(
        select(DataSecureQuestionnaireQuestion).where(
            DataSecureQuestionnaireQuestion.tool_id == tool_id,
            DataSecureQuestionnaireQuestion.project_space_id == body.project_space_id,
            DataSecureQuestionnaireQuestion.question_key == question_key,
        )
    ).first()
    if exists:
        raise HTTPException(status_code=400, detail="问卷题目标识已存在")
    now = datetime.utcnow()
    row = DataSecureQuestionnaireQuestion(
        tool_id=tool_id,
        project_space_id=body.project_space_id,
        question_key=question_key,
        title=body.title.strip(),
        help_text=(body.help_text or "").strip() or None,
        question_type=body.question_type,
        is_required=body.is_required,
        sort_order=body.sort_order,
        is_active=body.is_active,
        created_by=current_user.id,
        updated_by=current_user.id,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _build_question_row(row)


@router.put("/{tool_id}/features/questionnaire/questions", response_model=DataSecureQuestionInDB)
async def update_question(
    tool_id: int,
    body: DataSecureQuestionUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    _ensure_data_secure_manage_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    ensure_manage_permission(db, current_user, tool_id)
    row = db.get(DataSecureQuestionnaireQuestion, body.id)
    if not row or row.tool_id != tool_id:
        raise HTTPException(status_code=404, detail="问卷题目不存在")
    if body.title is not None:
        row.title = body.title.strip()
    if body.help_text is not None:
        row.help_text = body.help_text.strip() or None
    if body.is_required is not None:
        row.is_required = body.is_required
    if body.sort_order is not None:
        row.sort_order = body.sort_order
    if body.is_active is not None:
        row.is_active = body.is_active
    row.updated_by = current_user.id
    row.updated_at = datetime.utcnow()
    db.add(row)
    db.commit()
    db.refresh(row)
    return _build_question_row(row)


@router.post("/{tool_id}/features/questionnaire/questions/delete", response_model=DataSecureQuestionDeleteResult)
async def delete_question(
    tool_id: int,
    body: DataSecureQuestionDeleteRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    _ensure_data_secure_manage_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    ensure_manage_permission(db, current_user, tool_id)
    row = db.get(DataSecureQuestionnaireQuestion, body.id)
    if not row or row.tool_id != tool_id:
        raise HTTPException(status_code=404, detail="问卷题目不存在")
    reason = _normalize_change_reason(body.change_reason)
    rule = db.exec(
        select(DataSecureRelevanceRule).where(
            DataSecureRelevanceRule.tool_id == tool_id,
            DataSecureRelevanceRule.project_space_id == row.project_space_id,
        )
    ).first()
    if rule:
        key = str(row.question_key).strip()
        key_refs = set(_parse_question_keys_json(rule.question_keys_json))
        if key in key_refs:
            raise HTTPException(status_code=400, detail=f"题目「{key}」已被相关性规则引用，请先更新规则后再删除")
        logic_expression = (rule.logic_expression or "").strip()
        if logic_expression:
            tokens = _tokenize_logic_expression(logic_expression)
            if key in {t for t in tokens if t not in ('(', ')', 'and', 'or')}:
                raise HTTPException(status_code=400, detail=f"题目「{key}」已在逻辑表达式中使用，请先更新规则后再删除")
    question_id = int(row.id)
    project_space_id = int(row.project_space_id)
    question_key = str(row.question_key)
    db.delete(row)
    _append_governance_change_log(
        db,
        tool_id=tool_id,
        project_space_id=project_space_id,
        domain="questionnaire",
        action="delete",
        target_type="question",
        target_id=question_key,
        change_reason=reason,
        changed_by=current_user.id,
        detail={"question_id": question_id, "question_key": question_key},
    )
    db.commit()
    return DataSecureQuestionDeleteResult()


@router.get("/{tool_id}/features/relevance-rule", response_model=DataSecureRelevanceRuleInDB | None)
async def get_relevance_rule(
    tool_id: int,
    project_space_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    _ensure_data_secure_manage_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    row = db.exec(
        select(DataSecureRelevanceRule).where(
            DataSecureRelevanceRule.tool_id == tool_id,
            DataSecureRelevanceRule.project_space_id == project_space_id,
        )
    ).first()
    if not row:
        return None
    return DataSecureRelevanceRuleInDB(
        id=int(row.id),
        tool_id=row.tool_id,
        project_space_id=row.project_space_id,
        min_yes_count=row.min_yes_count,
        logic_operator="or" if str(row.logic_operator).lower() == "or" else "and",
        question_keys=_parse_question_keys_json(row.question_keys_json),
        logic_expression=(row.logic_expression or "").strip() or None,
        notes=row.notes,
        updated_by=row.updated_by,
        updated_at=row.updated_at,
    )


@router.put("/{tool_id}/features/relevance-rule", response_model=DataSecureRelevanceRuleInDB)
async def upsert_relevance_rule(
    tool_id: int,
    body: DataSecureRelevanceRuleUpsert,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    _ensure_data_secure_manage_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    ensure_manage_permission(db, current_user, tool_id)
    space = db.get(DataSecureProjectSpace, body.project_space_id)
    if not space or space.tool_id != tool_id:
        raise HTTPException(status_code=404, detail="项目空间不存在")
    valid_question_keys = {
        str(q.question_key)
        for q in db.exec(
            select(DataSecureQuestionnaireQuestion).where(
                DataSecureQuestionnaireQuestion.tool_id == tool_id,
                DataSecureQuestionnaireQuestion.project_space_id == body.project_space_id,
            )
        ).all()
    }
    normalized_keys = [str(k).strip() for k in body.question_keys if str(k).strip()]
    if normalized_keys:
        invalid_keys = [k for k in normalized_keys if k not in valid_question_keys]
        if invalid_keys:
            raise HTTPException(status_code=400, detail=f"规则题目无效：{', '.join(invalid_keys)}")
    normalized_expression = (body.logic_expression or "").strip()
    if normalized_expression:
        _validate_logic_expression(normalized_expression, valid_question_keys)
    row = db.exec(
        select(DataSecureRelevanceRule).where(
            DataSecureRelevanceRule.tool_id == tool_id,
            DataSecureRelevanceRule.project_space_id == body.project_space_id,
        )
    ).first()
    reason = _normalize_change_reason(body.change_reason)
    if not row:
        row = DataSecureRelevanceRule(
            tool_id=tool_id,
            project_space_id=body.project_space_id,
            min_yes_count=body.min_yes_count,
            logic_operator=body.logic_operator,
            question_keys_json=json.dumps(
                normalized_keys,
                ensure_ascii=False,
            ),
            logic_expression=normalized_expression or None,
            notes=(body.notes or "").strip() or None,
            updated_by=current_user.id,
            updated_at=datetime.utcnow(),
        )
    else:
        row.min_yes_count = body.min_yes_count
        row.logic_operator = body.logic_operator
        row.question_keys_json = json.dumps(
            normalized_keys,
            ensure_ascii=False,
        )
        row.logic_expression = normalized_expression or None
        row.notes = (body.notes or "").strip() or None
        row.updated_by = current_user.id
        row.updated_at = datetime.utcnow()
    db.add(row)
    _append_governance_change_log(
        db,
        tool_id=tool_id,
        project_space_id=body.project_space_id,
        domain="relevance_rule",
        action="upsert",
        target_type="rule",
        target_id=f"project_space:{body.project_space_id}",
        change_reason=reason,
        changed_by=current_user.id,
        detail={
            "min_yes_count": body.min_yes_count,
            "logic_operator": body.logic_operator,
            "question_keys": normalized_keys,
            "logic_expression": normalized_expression or None,
        },
    )
    db.commit()
    db.refresh(row)
    return DataSecureRelevanceRuleInDB(
        id=int(row.id),
        tool_id=row.tool_id,
        project_space_id=row.project_space_id,
        min_yes_count=row.min_yes_count,
        logic_operator="or" if str(row.logic_operator).lower() == "or" else "and",
        question_keys=_parse_question_keys_json(row.question_keys_json),
        logic_expression=(row.logic_expression or "").strip() or None,
        notes=row.notes,
        updated_by=row.updated_by,
        updated_at=row.updated_at,
    )


@router.post("/{tool_id}/features/relevance-assessments", response_model=DataSecureAssessmentSubmissionInDB)
async def submit_relevance_assessment(
    tool_id: int,
    body: DataSecureAssessmentSubmitRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    _ensure_data_secure_manage_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    space = db.get(DataSecureProjectSpace, body.project_space_id)
    if not space or space.tool_id != tool_id or not space.is_active:
        raise HTTPException(status_code=404, detail="项目空间不存在或不可用")
    ds_dynamic_fields.validate_assessment_function_name_against_business_options(
        db, tool_id, body.project_space_id, body.function_name
    )
    questions = db.exec(
        select(DataSecureQuestionnaireQuestion).where(
            DataSecureQuestionnaireQuestion.tool_id == tool_id,
            DataSecureQuestionnaireQuestion.project_space_id == body.project_space_id,
            DataSecureQuestionnaireQuestion.is_active == True,  # noqa: E712
        )
    ).all()
    if not questions:
        raise HTTPException(status_code=400, detail="当前项目空间尚未配置问卷题目")
    question_by_id = {int(q.id): q for q in questions}
    received_ids = {int(a.question_id) for a in body.answers}
    missing_required = [q.title for q in questions if q.is_required and int(q.id) not in received_ids]
    if missing_required:
        raise HTTPException(status_code=400, detail=f"存在必填题未回答：{'；'.join(missing_required)}")
    invalid_ids = [str(qid) for qid in received_ids if qid not in question_by_id]
    if invalid_ids:
        raise HTTPException(status_code=400, detail=f"存在无效题目：{', '.join(invalid_ids)}")
    yes_count = len([a for a in body.answers if a.answer_bool])
    total_count = len(body.answers)
    rule = db.exec(
        select(DataSecureRelevanceRule).where(
            DataSecureRelevanceRule.tool_id == tool_id,
            DataSecureRelevanceRule.project_space_id == body.project_space_id,
        )
    ).first()
    min_yes_count = rule.min_yes_count if rule else 1
    answer_by_question_key = {
        question_by_id[int(a.question_id)].question_key: bool(a.answer_bool)
        for a in body.answers
        if int(a.question_id) in question_by_id
    }
    configured_keys = _parse_question_keys_json(rule.question_keys_json if rule else "[]")
    configured_keys = [k for k in configured_keys if k in answer_by_question_key]
    logic_operator = "or" if rule and str(rule.logic_operator).lower() == "or" else "and"
    logic_expression = (rule.logic_expression or "").strip() if rule else ""
    if logic_expression:
        valid_keys = {q.question_key for q in questions}
        is_related = _eval_logic_expression(logic_expression, valid_keys, answer_by_question_key)
        result_summary = (
            f"判定为相关（表达式：{logic_expression}）"
            if is_related
            else f"判定为不相关（表达式：{logic_expression}）"
        )
    elif configured_keys:
        flags = [bool(answer_by_question_key.get(k, False)) for k in configured_keys]
        is_related = any(flags) if logic_operator == "or" else all(flags)
        join_text = "或" if logic_operator == "or" else "与"
        result_summary = (
            f"判定为相关（规则：{' {} '.format(join_text).join(configured_keys)}）"
            if is_related
            else f"判定为不相关（规则：{' {} '.format(join_text).join(configured_keys)}）"
        )
    else:
        is_related = yes_count >= min_yes_count
        result_summary = (
            f"判定为相关（是={yes_count}/{total_count}，阈值={min_yes_count}）"
            if is_related
            else f"判定为不相关（是={yes_count}/{total_count}，阈值={min_yes_count}）"
        )
    submission = DataSecureAssessmentSubmission(
        tool_id=tool_id,
        project_space_id=body.project_space_id,
        submitted_by=current_user.id,
        function_name=body.function_name.strip(),
        function_description=(body.function_description or "").strip() or None,
        yes_count=yes_count,
        total_count=total_count,
        is_related=is_related,
        result_summary=result_summary,
        submitted_at=datetime.utcnow(),
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)
    for item in body.answers:
        q = question_by_id[int(item.question_id)]
        db.add(
            DataSecureAssessmentAnswer(
                submission_id=int(submission.id),
                question_id=int(q.id),
                answer_bool=item.answer_bool,
                answer_text=(item.answer_text or "").strip() or None,
            )
        )
    db.commit()
    return await get_assessment_submission(tool_id, int(submission.id), current_user, db)


@router.get("/{tool_id}/features/relevance-assessments/{submission_id}", response_model=DataSecureAssessmentSubmissionInDB)
async def get_assessment_submission(
    tool_id: int,
    submission_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    _ensure_data_secure_manage_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    row = db.get(DataSecureAssessmentSubmission, submission_id)
    if not row or row.tool_id != tool_id:
        raise HTTPException(status_code=404, detail="填报记录不存在")
    can_manage = can_manage_all_records(db, current_user, tool_id)
    if not can_manage and row.submitted_by != current_user.id:
        raise HTTPException(status_code=403, detail="仅可查看自己提交的记录")
    answers_raw = db.exec(
        select(DataSecureAssessmentAnswer).where(DataSecureAssessmentAnswer.submission_id == submission_id)
    ).all()
    question_map = {
        int(q.id): q
        for q in db.exec(
            select(DataSecureQuestionnaireQuestion).where(
                DataSecureQuestionnaireQuestion.project_space_id == row.project_space_id
            )
        ).all()
    }
    submitter = db.get(User, row.submitted_by)
    space = db.get(DataSecureProjectSpace, row.project_space_id)
    return DataSecureAssessmentSubmissionInDB(
        id=int(row.id),
        tool_id=row.tool_id,
        project_space_id=row.project_space_id,
        project_space_name=space.name if space else f"空间#{row.project_space_id}",
        submitted_by=row.submitted_by,
        submitted_by_name=submitter.username if submitter else None,
        function_name=row.function_name,
        function_description=row.function_description,
        yes_count=row.yes_count,
        total_count=row.total_count,
        is_related=row.is_related,
        result_summary=row.result_summary,
        submitted_at=row.submitted_at,
        answers=[
            {
                "question_id": a.question_id,
                "question_key": question_map.get(a.question_id).question_key if question_map.get(a.question_id) else str(a.question_id),
                "question_title": question_map.get(a.question_id).title if question_map.get(a.question_id) else str(a.question_id),
                "answer_bool": a.answer_bool,
                "answer_text": a.answer_text,
            }
            for a in answers_raw
        ],
    )


@router.get("/{tool_id}/features/relevance-assessments", response_model=PaginatedDataSecureAssessmentSubmissions)
async def list_assessment_submissions(
    tool_id: int,
    project_space_id: int | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=500),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    _ensure_data_secure_manage_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    can_manage = can_manage_all_records(db, current_user, tool_id)
    where = [DataSecureAssessmentSubmission.tool_id == tool_id]
    if project_space_id is not None:
        where.append(DataSecureAssessmentSubmission.project_space_id == project_space_id)
    if not can_manage:
        where.append(DataSecureAssessmentSubmission.submitted_by == current_user.id)
    total = db.exec(select(func.count()).select_from(DataSecureAssessmentSubmission).where(*where)).one()
    rows = db.exec(
        select(DataSecureAssessmentSubmission)
        .where(*where)
        .order_by(DataSecureAssessmentSubmission.submitted_at.desc())
        .offset(skip)
        .limit(limit)
    ).all()
    items = [await get_assessment_submission(tool_id, int(r.id), current_user, db) for r in rows]
    return PaginatedDataSecureAssessmentSubmissions(total=int(total or 0), items=items)


@router.get("/{tool_id}/features/lifecycle-field-config", response_model=DataSecureLifecycleFieldConfigListResponse)
async def list_lifecycle_field_configs(
    tool_id: int,
    project_space_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    _ensure_data_secure_manage_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    return DataSecureLifecycleFieldConfigListResponse(
        items=ds_dynamic_fields.list_field_config_items(db, tool_id, project_space_id)
    )


@router.post("/{tool_id}/features/lifecycle-field-config", response_model=DataSecureLifecycleFieldConfigListResponse)
async def create_lifecycle_field_config(
    tool_id: int,
    body: DataSecureLifecycleFieldConfigCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    _ensure_data_secure_manage_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    ensure_manage_permission(db, current_user, tool_id)
    reason = _normalize_change_reason(body.change_reason)
    ds_dynamic_fields.create_field_config(db, tool_id, body.project_space_id, body, current_user.id)
    _append_governance_change_log(
        db,
        tool_id=tool_id,
        project_space_id=body.project_space_id,
        domain="lifecycle_fields",
        action="create",
        target_type="field",
        target_id=body.field_key.strip(),
        change_reason=reason,
        changed_by=current_user.id,
        detail={"field_key": body.field_key.strip(), "label": body.label.strip(), "input_type": body.input_type},
    )
    db.commit()
    return await list_lifecycle_field_configs(tool_id, body.project_space_id, current_user, db)


@router.put("/{tool_id}/features/lifecycle-field-config", response_model=DataSecureLifecycleFieldConfigListResponse)
async def update_lifecycle_field_configs(
    tool_id: int,
    body: DataSecureLifecycleFieldConfigUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    _ensure_data_secure_manage_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    ensure_manage_permission(db, current_user, tool_id)
    reason = _normalize_change_reason(body.change_reason)
    ds_dynamic_fields.update_field_configs(db, tool_id, body.project_space_id, body.items, current_user.id)
    _append_governance_change_log(
        db,
        tool_id=tool_id,
        project_space_id=body.project_space_id,
        domain="lifecycle_fields",
        action="update",
        target_type="field_batch",
        target_id=f"count:{len(body.items)}",
        change_reason=reason,
        changed_by=current_user.id,
        detail={"field_keys": [str(i.field_key).strip() for i in body.items]},
    )
    db.commit()
    return await list_lifecycle_field_configs(tool_id, body.project_space_id, current_user, db)


@router.delete("/{tool_id}/features/lifecycle-field-config", response_model=DataSecureLifecycleFieldConfigListResponse)
async def delete_lifecycle_field_config(
    tool_id: int,
    body: DataSecureLifecycleFieldConfigDeleteRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    _ensure_data_secure_manage_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    ensure_manage_permission(db, current_user, tool_id)
    ds_dynamic_fields.delete_field_config(db, tool_id, body.project_space_id, body.field_key)
    _append_governance_change_log(
        db,
        tool_id=tool_id,
        project_space_id=body.project_space_id,
        domain="lifecycle_fields",
        action="delete",
        target_type="field",
        target_id=body.field_key.strip(),
        change_reason=_normalize_change_reason(body.change_reason),
        changed_by=current_user.id,
        detail={"field_key": body.field_key.strip()},
    )
    db.commit()
    return await list_lifecycle_field_configs(tool_id, body.project_space_id, current_user, db)


@router.get("/{tool_id}/features/governance-change-logs", response_model=PaginatedDataSecureGovernanceChangeLogs)
async def list_governance_change_logs(
    tool_id: int,
    project_space_id: int,
    domain: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=200),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    _ensure_data_secure_manage_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    ensure_manage_permission(db, current_user, tool_id)
    where = [
        DataSecureGovernanceChangeLog.tool_id == tool_id,
        DataSecureGovernanceChangeLog.project_space_id == project_space_id,
    ]
    if domain and domain.strip():
        where.append(DataSecureGovernanceChangeLog.domain == domain.strip())
    total = db.exec(select(func.count()).select_from(DataSecureGovernanceChangeLog).where(*where)).one()
    rows = db.exec(
        select(DataSecureGovernanceChangeLog)
        .where(*where)
        .order_by(DataSecureGovernanceChangeLog.created_at.desc(), DataSecureGovernanceChangeLog.id.desc())
        .offset(skip)
        .limit(limit)
    ).all()
    return PaginatedDataSecureGovernanceChangeLogs(
        total=int(total or 0),
        items=[_build_governance_change_log_row(db, r) for r in rows],
    )


def _build_config_export_payload(
    db: Session, tool_id: int, project_space_id: int, sel: DataSecureConfigExportSelection
) -> DataSecureConfigExportPayload:
    sid = int(project_space_id)
    payload = DataSecureConfigExportPayload(
        tool_key=_TOOL_KEY,
        project_space_id=sid,
        exported_at=datetime.utcnow(),
        selection=sel,
    )

    if sel.include_spaces:
        rows = db.exec(
            select(DataSecureProjectSpace).where(
                DataSecureProjectSpace.tool_id == tool_id,
                DataSecureProjectSpace.id == sid,
            )
        ).all()
        payload.spaces = [_build_space_row(r) for r in rows]
    if sel.include_questions:
        rows = db.exec(
            select(DataSecureQuestionnaireQuestion)
            .where(
                DataSecureQuestionnaireQuestion.tool_id == tool_id,
                DataSecureQuestionnaireQuestion.project_space_id == sid,
            )
            .order_by(DataSecureQuestionnaireQuestion.sort_order, DataSecureQuestionnaireQuestion.id)
        ).all()
        payload.questions = [_build_question_row(r) for r in rows]
    if sel.include_relevance_rule:
        rule = db.exec(
            select(DataSecureRelevanceRule).where(
                DataSecureRelevanceRule.tool_id == tool_id,
                DataSecureRelevanceRule.project_space_id == sid,
            )
        ).first()
        payload.relevance_rule = _build_relevance_rule_row(rule) if rule else None
    if sel.include_lifecycle_fields:
        payload.lifecycle_fields = ds_dynamic_fields.list_field_config_items(db, tool_id, sid)
    if sel.include_taxonomy_nodes:
        rows = db.exec(
            select(DataSecureTaxonomyNode)
            .where(
                DataSecureTaxonomyNode.tool_id == tool_id,
                DataSecureTaxonomyNode.project_space_id == sid,
            )
            .order_by(DataSecureTaxonomyNode.sort_order, DataSecureTaxonomyNode.id)
        ).all()
        payload.taxonomy_nodes = [_build_taxonomy_node_row(r) for r in rows]
    if sel.include_field_class_grades:
        rows = db.exec(
            select(DataSecureFieldClassGrade)
            .where(
                DataSecureFieldClassGrade.tool_id == tool_id,
                DataSecureFieldClassGrade.project_space_id == sid,
            )
            .order_by(DataSecureFieldClassGrade.updated_at.desc())
        ).all()
        entry_ids = list({int(r.catalog_entry_id) for r in rows})
        entries: dict[int, DataSecureFieldCatalogEntry] = {}
        if entry_ids:
            erows = db.exec(select(DataSecureFieldCatalogEntry).where(DataSecureFieldCatalogEntry.id.in_(entry_ids))).all()
            entries = {int(e.id): e for e in erows}
        payload.field_class_grades = [_build_class_grade_row(db, r, entries.get(int(r.catalog_entry_id))) for r in rows]
    if sel.include_security_requirements:
        rows = db.exec(
            select(DataSecureFieldSecurityRequirement)
            .where(
                DataSecureFieldSecurityRequirement.tool_id == tool_id,
                DataSecureFieldSecurityRequirement.project_space_id == sid,
            )
            .order_by(DataSecureFieldSecurityRequirement.priority.desc(), DataSecureFieldSecurityRequirement.sort_order)
        ).all()
        entry_ids = list({int(r.catalog_entry_id) for r in rows})
        entries: dict[int, DataSecureFieldCatalogEntry] = {}
        if entry_ids:
            erows = db.exec(select(DataSecureFieldCatalogEntry).where(DataSecureFieldCatalogEntry.id.in_(entry_ids))).all()
            entries = {int(e.id): e for e in erows}
        payload.security_requirements = [_build_security_requirement_row(db, r, entries.get(int(r.catalog_entry_id))) for r in rows]
    if sel.include_classification_rules:
        rows = db.exec(
            select(DataSecureFieldClassificationRule)
            .where(
                DataSecureFieldClassificationRule.tool_id == tool_id,
                DataSecureFieldClassificationRule.project_space_id == sid,
            )
            .order_by(DataSecureFieldClassificationRule.priority.desc(), DataSecureFieldClassificationRule.sort_order)
        ).all()
        payload.classification_rules = [_build_classification_rule_row(r) for r in rows]
    if sel.include_classification_matrix:
        rows = db.exec(
            select(DataSecureFieldClassificationMatrix)
            .where(
                DataSecureFieldClassificationMatrix.tool_id == tool_id,
                DataSecureFieldClassificationMatrix.project_space_id == sid,
            )
            .order_by(DataSecureFieldClassificationMatrix.priority.desc(), DataSecureFieldClassificationMatrix.sort_order)
        ).all()
        payload.classification_matrix = [_build_classification_matrix_row(r) for r in rows]
    return payload


@router.post("/{tool_id}/features/config-export", response_model=DataSecureConfigExportPayload)
async def export_config_payload(
    tool_id: int,
    body: DataSecureConfigExportRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    _ensure_data_secure_manage_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    ensure_manage_permission(db, current_user, tool_id)
    return _build_config_export_payload(db, tool_id, int(body.project_space_id), body.selection)


def _apply_data_secure_config_import(
    db: Session, tool_id: int, body: DataSecureConfigImportRequest, user: User
) -> DataSecureConfigImportResult:
    reason = _normalize_change_reason(body.change_reason)
    sid = int(body.target_project_space_id)
    payload = body.payload
    counts: dict[str, int] = {}

    space = db.get(DataSecureProjectSpace, sid)
    if not space or int(space.tool_id) != int(tool_id):
        raise HTTPException(status_code=404, detail="目标项目空间不存在")

    if payload.selection.include_questions:
        for q in payload.questions:
            row = db.exec(
                select(DataSecureQuestionnaireQuestion).where(
                    DataSecureQuestionnaireQuestion.tool_id == tool_id,
                    DataSecureQuestionnaireQuestion.project_space_id == sid,
                    DataSecureQuestionnaireQuestion.question_key == q.question_key.strip(),
                )
            ).first()
            if row:
                row.title = q.title
                row.help_text = q.help_text
                row.sort_order = q.sort_order
                row.is_required = q.is_required
                row.is_active = q.is_active
                row.updated_by = user.id
                row.updated_at = datetime.utcnow()
                db.add(row)
            else:
                db.add(
                    DataSecureQuestionnaireQuestion(
                        tool_id=tool_id,
                        project_space_id=sid,
                        question_key=q.question_key.strip(),
                        title=q.title,
                        help_text=q.help_text,
                        question_type=q.question_type,
                        is_required=q.is_required,
                        sort_order=q.sort_order,
                        is_active=q.is_active,
                        created_by=user.id,
                        updated_by=user.id,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                    )
                )
            counts["questions"] = counts.get("questions", 0) + 1

    if payload.selection.include_relevance_rule and payload.relevance_rule:
        rr = payload.relevance_rule
        row = db.exec(
            select(DataSecureRelevanceRule).where(
                DataSecureRelevanceRule.tool_id == tool_id,
                DataSecureRelevanceRule.project_space_id == sid,
            )
        ).first()
        if not row:
            row = DataSecureRelevanceRule(
                tool_id=tool_id,
                project_space_id=sid,
                min_yes_count=max(0, int(rr.min_yes_count)),
                logic_operator=rr.logic_operator,
                question_keys_json=json.dumps(rr.question_keys or [], ensure_ascii=False),
                logic_expression=(rr.logic_expression or "").strip() or None,
                notes=rr.notes,
                updated_by=user.id,
                updated_at=datetime.utcnow(),
            )
        else:
            row.min_yes_count = max(0, int(rr.min_yes_count))
            row.logic_operator = rr.logic_operator
            row.question_keys_json = json.dumps(rr.question_keys or [], ensure_ascii=False)
            row.logic_expression = (rr.logic_expression or "").strip() or None
            row.notes = rr.notes
            row.updated_by = user.id
            row.updated_at = datetime.utcnow()
        db.add(row)
        counts["relevance_rule"] = 1

    if payload.selection.include_lifecycle_fields and payload.lifecycle_fields:
        ds_dynamic_fields.ensure_custom_lifecycle_definitions_from_export_items(
            db, tool_id, sid, payload.lifecycle_fields, user.id
        )
        items = [
            DataSecureLifecycleFieldConfigUpdateItem(
                field_key=f.field_key,
                label=f.label,
                input_type=f.input_type,
                sort_order=f.sort_order,
                help_text=f.help_text,
                required=f.required,
                min_length=f.min_length,
                max_length=f.max_length,
                regex_pattern=f.regex_pattern,
                regex_error_message=f.regex_error_message,
                allowed_values=f.allowed_values or [],
            )
            for f in payload.lifecycle_fields
        ]
        if items:
            ds_dynamic_fields.update_field_configs(db, tool_id, sid, items, user.id)
            counts["lifecycle_fields"] = len(items)

    if payload.selection.include_classification_rules:
        for x in db.exec(
            select(DataSecureFieldClassificationRule).where(
                DataSecureFieldClassificationRule.tool_id == tool_id,
                DataSecureFieldClassificationRule.project_space_id == sid,
            )
        ).all():
            db.delete(x)
        db.flush()
        now_cls = datetime.utcnow()
        for r in payload.classification_rules:
            db.add(
                DataSecureFieldClassificationRule(
                    tool_id=tool_id,
                    project_space_id=sid,
                    keyword=(r.keyword or "").strip(),
                    category=(r.category or "").strip(),
                    level=(r.level or "").strip(),
                    priority=int(getattr(r, "priority", 100) or 100),
                    notes=r.notes,
                    sort_order=int(r.sort_order or 0),
                    is_active=bool(r.is_active),
                    created_by=user.id,
                    updated_by=user.id,
                    created_at=now_cls,
                    updated_at=now_cls,
                )
            )
            counts["classification_rules"] = counts.get("classification_rules", 0) + 1

    if payload.selection.include_classification_matrix:
        for x in db.exec(
            select(DataSecureFieldClassificationMatrix).where(
                DataSecureFieldClassificationMatrix.tool_id == tool_id,
                DataSecureFieldClassificationMatrix.project_space_id == sid,
            )
        ).all():
            db.delete(x)
        db.flush()
        now_mx = datetime.utcnow()
        for m in payload.classification_matrix:
            crit = _validate_matrix_extension_match(db, tool_id, sid, m.extension_match or {})
            db.add(
                DataSecureFieldClassificationMatrix(
                    tool_id=tool_id,
                    project_space_id=sid,
                    field_name=(m.field_name or "").strip(),
                    extension_match_json=_matrix_criteria_to_json(crit),
                    category=(m.category or "").strip(),
                    level=(m.level or "").strip(),
                    priority=int(getattr(m, "priority", 200) or 200),
                    notes=m.notes,
                    sort_order=int(m.sort_order or 0),
                    is_active=bool(m.is_active),
                    created_by=user.id,
                    updated_by=user.id,
                    created_at=now_mx,
                    updated_at=now_mx,
                )
            )
            counts["classification_matrix"] = counts.get("classification_matrix", 0) + 1

    node_key_to_id: dict[str, int] = {}
    if payload.selection.include_taxonomy_nodes and payload.taxonomy_nodes:
        existing_nodes = db.exec(
            select(DataSecureTaxonomyNode).where(
                DataSecureTaxonomyNode.tool_id == tool_id,
                DataSecureTaxonomyNode.project_space_id == sid,
            )
        ).all()
        node_key_to_id = {str(n.node_key).strip(): int(n.id) for n in existing_nodes if (n.node_key or "").strip()}
        pending = list(payload.taxonomy_nodes)
        guard = 0
        while pending and guard < 5000:
            guard += 1
            progressed = False
            for i in range(len(pending) - 1, -1, -1):
                src = pending[i]
                parent_id = None
                if src.parent_id is not None:
                    parent = next((x for x in payload.taxonomy_nodes if int(x.id) == int(src.parent_id)), None)
                    if parent is None:
                        pending.pop(i)
                        continue
                    parent_key = (parent.node_key or "").strip()
                    parent_id = node_key_to_id.get(parent_key)
                    if parent_id is None:
                        continue
                nk = (src.node_key or "").strip()
                if not nk:
                    pending.pop(i)
                    continue
                row = db.exec(
                    select(DataSecureTaxonomyNode).where(
                        DataSecureTaxonomyNode.tool_id == tool_id,
                        DataSecureTaxonomyNode.project_space_id == sid,
                        DataSecureTaxonomyNode.node_key == nk,
                    )
                ).first()
                if row:
                    row.parent_id = parent_id
                    row.name = src.name
                    row.sort_order = src.sort_order
                    row.is_active = src.is_active
                    row.updated_by = user.id
                    row.updated_at = datetime.utcnow()
                    db.add(row)
                    node_key_to_id[nk] = int(row.id)
                else:
                    row = DataSecureTaxonomyNode(
                        tool_id=tool_id,
                        project_space_id=sid,
                        parent_id=parent_id,
                        name=src.name,
                        node_key=nk,
                        sort_order=src.sort_order,
                        is_active=src.is_active,
                        created_by=user.id,
                        updated_by=user.id,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                    )
                    db.add(row)
                    db.flush()
                    node_key_to_id[nk] = int(row.id)
                counts["taxonomy_nodes"] = counts.get("taxonomy_nodes", 0) + 1
                pending.pop(i)
                progressed = True
            if not progressed:
                break

    entry_name_to_id: dict[str, int] = {}
    entry_rows = db.exec(
        select(DataSecureFieldCatalogEntry).where(
            DataSecureFieldCatalogEntry.tool_id == tool_id,
            DataSecureFieldCatalogEntry.project_space_id == sid,
        )
    ).all()
    for e in entry_rows:
        entry_name_to_id[(e.field_name or "").strip()] = int(e.id)

    if payload.selection.include_field_class_grades:
        for cg in payload.field_class_grades:
            cid = entry_name_to_id.get((cg.field_name or "").strip())
            if not cid:
                continue
            l1 = None
            l2 = None
            if cg.taxonomy_l1_id is not None:
                source = next((x for x in payload.taxonomy_nodes if int(x.id) == int(cg.taxonomy_l1_id)), None)
                if source:
                    l1 = node_key_to_id.get((source.node_key or "").strip())
            if cg.taxonomy_l2_id is not None:
                source = next((x for x in payload.taxonomy_nodes if int(x.id) == int(cg.taxonomy_l2_id)), None)
                if source:
                    l2 = node_key_to_id.get((source.node_key or "").strip())
            row = db.exec(select(DataSecureFieldClassGrade).where(DataSecureFieldClassGrade.catalog_entry_id == cid)).first()
            if row:
                row.taxonomy_l1_id = l1
                row.taxonomy_l2_id = l2
                row.confidentiality_grade = cg.confidentiality_grade
                row.notes = cg.notes
                row.updated_by = user.id
                row.updated_at = datetime.utcnow()
                db.add(row)
            else:
                db.add(
                    DataSecureFieldClassGrade(
                        tool_id=tool_id,
                        project_space_id=sid,
                        catalog_entry_id=cid,
                        taxonomy_l1_id=l1,
                        taxonomy_l2_id=l2,
                        confidentiality_grade=cg.confidentiality_grade,
                        notes=cg.notes,
                        created_by=user.id,
                        updated_by=user.id,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                    )
                )
            counts["field_class_grades"] = counts.get("field_class_grades", 0) + 1

    if payload.selection.include_security_requirements:
        for sr in payload.security_requirements:
            cid = entry_name_to_id.get((sr.field_name or "").strip())
            if not cid:
                continue
            existing = db.exec(
                select(DataSecureFieldSecurityRequirement).where(
                    DataSecureFieldSecurityRequirement.tool_id == tool_id,
                    DataSecureFieldSecurityRequirement.project_space_id == sid,
                    DataSecureFieldSecurityRequirement.catalog_entry_id == cid,
                    DataSecureFieldSecurityRequirement.requirement_text == sr.requirement_text,
                    DataSecureFieldSecurityRequirement.logic_expression == sr.logic_expression,
                )
            ).first()
            pred = ds_struct.validate_predicate_map(sr.predicate_map or {})
            if existing:
                existing.predicate_map_json = ds_struct.predicate_map_to_json(pred)
                existing.priority = sr.priority
                existing.sort_order = sr.sort_order
                existing.is_active = sr.is_active
                existing.updated_by = user.id
                existing.updated_at = datetime.utcnow()
                db.add(existing)
            else:
                db.add(
                    DataSecureFieldSecurityRequirement(
                        tool_id=tool_id,
                        project_space_id=sid,
                        catalog_entry_id=cid,
                        requirement_text=sr.requirement_text,
                        logic_expression=sr.logic_expression,
                        predicate_map_json=ds_struct.predicate_map_to_json(pred),
                        priority=sr.priority,
                        sort_order=sr.sort_order,
                        is_active=sr.is_active,
                        created_by=user.id,
                        updated_by=user.id,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                    )
                )
            counts["security_requirements"] = counts.get("security_requirements", 0) + 1

    _append_governance_change_log(
        db,
        tool_id=tool_id,
        project_space_id=sid,
        domain="config_import_export",
        action="import",
        target_type="config_payload",
        target_id=f"space:{sid}",
        change_reason=reason,
        changed_by=user.id,
        detail={"imported_counts": counts},
    )
    db.commit()
    return DataSecureConfigImportResult(target_project_space_id=sid, imported_counts=counts)


@router.post("/{tool_id}/features/config-import", response_model=DataSecureConfigImportResult)
async def import_config_payload(
    tool_id: int,
    body: DataSecureConfigImportRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    _ensure_data_secure_manage_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    ensure_manage_permission(db, current_user, tool_id)
    return _apply_data_secure_config_import(db, tool_id, body, current_user)


@router.post("/{tool_id}/features/config-batch-delete", response_model=DataSecureConfigBatchDeleteResult)
async def batch_delete_config_items(
    tool_id: int,
    body: DataSecureConfigBatchDeleteRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    _ensure_data_secure_manage_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    ensure_manage_permission(db, current_user, tool_id)
    reason = _normalize_change_reason(body.change_reason)
    sid = int(body.project_space_id)
    deleted_items: list[dict[str, str]] = []
    failed_items: list[dict[str, str]] = []

    for item in body.items:
        domain = item.domain
        tid = (item.target_id or "").strip()
        try:
            if domain == "question":
                row = db.get(DataSecureQuestionnaireQuestion, int(tid))
                if not row or int(row.tool_id) != int(tool_id) or int(row.project_space_id) != sid:
                    raise HTTPException(status_code=404, detail="题目不存在")
                db.delete(row)
            elif domain == "lifecycle_field":
                ds_dynamic_fields.delete_field_config(db, tool_id, sid, tid)
            elif domain == "taxonomy_node":
                row = db.get(DataSecureTaxonomyNode, int(tid))
                if not row or int(row.tool_id) != int(tool_id) or int(row.project_space_id) != sid:
                    raise HTTPException(status_code=404, detail="分类节点不存在")
                db.delete(row)
            elif domain == "field_class_grade":
                row = db.get(DataSecureFieldClassGrade, int(tid))
                if not row or int(row.tool_id) != int(tool_id) or int(row.project_space_id) != sid:
                    raise HTTPException(status_code=404, detail="密级绑定不存在")
                db.delete(row)
            elif domain == "security_requirement":
                row = db.get(DataSecureFieldSecurityRequirement, int(tid))
                if not row or int(row.tool_id) != int(tool_id) or int(row.project_space_id) != sid:
                    raise HTTPException(status_code=404, detail="安全要求不存在")
                db.delete(row)
            _append_governance_change_log(
                db,
                tool_id=tool_id,
                project_space_id=sid,
                domain=domain,
                action="delete",
                target_type=domain,
                target_id=tid,
                change_reason=reason,
                changed_by=current_user.id,
                detail={"batch": True},
            )
            deleted_items.append({"domain": domain, "target_id": tid})
        except Exception as exc:
            msg = str(getattr(exc, "detail", None) or str(exc) or "删除失败")
            failed_items.append({"domain": domain, "target_id": tid, "reason": msg})
    db.commit()
    return DataSecureConfigBatchDeleteResult(
        deleted_count=len(deleted_items),
        deleted_items=deleted_items,
        failed_items=failed_items,
    )


@router.get("/{tool_id}/features/field-catalog", response_model=PaginatedDataSecureFieldCatalogEntries)
async def list_field_catalog(
    tool_id: int,
    project_space_id: int,
    q: str | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=200),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    _ensure_data_secure_manage_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    where = [
        DataSecureFieldCatalogEntry.tool_id == tool_id,
        DataSecureFieldCatalogEntry.project_space_id == project_space_id,
    ]
    if q and q.strip():
        where.append(DataSecureFieldCatalogEntry.field_name.ilike(f"%{q.strip()}%"))
    total = db.exec(select(func.count()).select_from(DataSecureFieldCatalogEntry).where(*where)).one()
    rows = db.exec(
        select(DataSecureFieldCatalogEntry)
        .where(*where)
        .order_by(DataSecureFieldCatalogEntry.updated_at.desc())
        .offset(skip)
        .limit(limit)
    ).all()
    return PaginatedDataSecureFieldCatalogEntries(
        total=int(total or 0),
        items=[_build_catalog_entry_row(db, r) for r in rows],
    )


@router.get("/{tool_id}/features/field-catalog-value-options", response_model=DataSecureFieldCatalogValueOptionsResponse)
async def list_field_catalog_value_options(
    tool_id: int,
    project_space_id: int,
    field_key: str = Query(..., min_length=1, max_length=64),
    q: str = Query(default=""),
    limit: int = Query(default=30, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    _ensure_data_secure_manage_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    fk = field_key.strip()
    if not fk:
        return DataSecureFieldCatalogValueOptionsResponse(field_key="", q=q or "", options=[])

    where = [
        DataSecureFieldCatalogEntry.tool_id == tool_id,
        DataSecureFieldCatalogEntry.project_space_id == project_space_id,
        DataSecureFieldCatalogValue.field_key == fk,
        DataSecureFieldCatalogValue.entry_id == DataSecureFieldCatalogEntry.id,
    ]
    rows = db.exec(
        select(DataSecureFieldCatalogValue.value_json)
        .join(DataSecureFieldCatalogEntry, DataSecureFieldCatalogValue.entry_id == DataSecureFieldCatalogEntry.id)
        .where(*where)
        .order_by(DataSecureFieldCatalogValue.updated_at.desc())
        .limit(2000)
    ).all()

    kw = (q or "").strip().lower()
    options: list[str] = []
    seen: set[str] = set()
    for raw_json in rows:
        try:
            parsed = json.loads(raw_json or "null")
        except Exception:
            parsed = None
        values = parsed if isinstance(parsed, list) else [parsed]
        for item in values:
            text = str(item or "").strip()
            if not text:
                continue
            if kw and kw not in text.lower():
                continue
            if text in seen:
                continue
            seen.add(text)
            options.append(text)
            if len(options) >= limit:
                return DataSecureFieldCatalogValueOptionsResponse(field_key=fk, q=q or "", options=options)
    return DataSecureFieldCatalogValueOptionsResponse(field_key=fk, q=q or "", options=options)


@router.post("/{tool_id}/features/field-catalog/batch-import", response_model=DataSecureFieldCatalogBatchImportResult)
async def batch_import_field_catalog(
    tool_id: int,
    body: DataSecureFieldCatalogBatchImport,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    _ensure_data_secure_manage_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    ensure_manage_permission(db, current_user, tool_id)
    space = db.get(DataSecureProjectSpace, body.project_space_id)
    if not space or space.tool_id != tool_id:
        raise HTTPException(status_code=404, detail="项目空间不存在")
    created = 0
    skipped_dup = 0
    failed_val = 0
    errors: list[str] = []
    max_err = 80
    all_extra_keys: set[str] = set()
    for item in body.items:
        all_extra_keys.update((item.extra_fields or {}).keys())
    auto_created_field_keys = ds_dynamic_fields.ensure_default_custom_fields_for_catalog_import(
        db,
        tool_id,
        body.project_space_id,
        field_keys=all_extra_keys,
        labels=dict(body.auto_field_labels or {}),
        updated_by=current_user.id,
    )
    for i, item in enumerate(body.items):
        entry, err = _try_insert_field_catalog_entry(
            db,
            tool_id=tool_id,
            project_space_id=body.project_space_id,
            field_name=item.field_name,
            extra_fields=item.extra_fields or {},
            created_by_user_id=current_user.id,
            updated_by_user_id=current_user.id,
        )
        if entry:
            created += 1
        elif err and "已存在" in err:
            skipped_dup += 1
        else:
            failed_val += 1
            if len(errors) < max_err:
                errors.append(f"第 {i + 1} 条「{item.field_name.strip()}」：{err or '导入失败'}")
    db.commit()
    return DataSecureFieldCatalogBatchImportResult(
        created_count=created,
        skipped_duplicate=skipped_dup,
        failed_validation=failed_val,
        errors=errors,
        auto_created_field_keys=auto_created_field_keys,
    )


@router.post("/{tool_id}/features/field-catalog", response_model=DataSecureFieldCatalogEntryInDB)
async def create_field_catalog_entry(
    tool_id: int,
    body: DataSecureFieldCatalogEntryCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    _ensure_data_secure_manage_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    ensure_manage_permission(db, current_user, tool_id)
    space = db.get(DataSecureProjectSpace, body.project_space_id)
    if not space or space.tool_id != tool_id:
        raise HTTPException(status_code=404, detail="项目空间不存在")
    entry, err = _try_insert_field_catalog_entry(
        db,
        tool_id=tool_id,
        project_space_id=body.project_space_id,
        field_name=body.field_name,
        extra_fields=body.extra_fields or {},
        created_by_user_id=current_user.id,
        updated_by_user_id=current_user.id,
    )
    if not entry:
        raise HTTPException(status_code=400, detail=err or "无法新增主表记录")
    db.commit()
    db.refresh(entry)
    return _build_catalog_entry_row(db, entry)


@router.put("/{tool_id}/features/field-catalog/{entry_id}", response_model=DataSecureFieldCatalogEntryInDB)
async def update_field_catalog_extra_fields(
    tool_id: int,
    entry_id: int,
    body: DataSecureFieldCatalogExtraUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    _ensure_data_secure_manage_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    ensure_manage_permission(db, current_user, tool_id)
    entry = db.get(DataSecureFieldCatalogEntry, entry_id)
    if not entry or entry.tool_id != tool_id:
        raise HTTPException(status_code=404, detail="数据字段主表记录不存在")
    normalized = ds_dynamic_fields.validate_extra_fields(
        db,
        tool_id,
        int(entry.project_space_id),
        body.extra_fields or {},
    )
    now = datetime.utcnow()
    entry.updated_by = current_user.id
    entry.updated_at = now
    db.add(entry)
    db.flush()
    ds_dynamic_fields.save_catalog_extra_fields(db, int(entry.id), current_user.id, normalized)
    _upsert_classification_for_entry(db, tool_id, int(entry.project_space_id), entry, current_user.id)
    db.commit()
    db.refresh(entry)
    return _build_catalog_entry_row(db, entry)


@router.post("/{tool_id}/features/field-requests", response_model=DataSecureFieldRequestInDB)
async def create_field_request(
    tool_id: int,
    body: DataSecureFieldRequestCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    _ensure_data_secure_manage_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    space = db.get(DataSecureProjectSpace, body.project_space_id)
    if not space or space.tool_id != tool_id:
        raise HTTPException(status_code=404, detail="项目空间不存在")
    exists = db.exec(
        select(DataSecureFieldCatalogEntry).where(
            DataSecureFieldCatalogEntry.tool_id == tool_id,
            DataSecureFieldCatalogEntry.project_space_id == body.project_space_id,
            DataSecureFieldCatalogEntry.field_name == body.field_name.strip(),
        )
    ).first()
    if exists:
        raise HTTPException(status_code=400, detail="该数据字段已存在，无需申请")
    normalized_extra_fields = ds_dynamic_fields.validate_extra_fields_subset(
        db,
        tool_id,
        body.project_space_id,
        body.extra_fields or {},
    )
    now = datetime.utcnow()
    row = DataSecureFieldRequest(
        tool_id=tool_id,
        project_space_id=body.project_space_id,
        requested_by=current_user.id,
        request_type=(body.request_type or "data_field"),
        field_name=body.field_name.strip(),
        payload_json=json.dumps(normalized_extra_fields, ensure_ascii=False),
        reason=(body.reason or "").strip() or None,
        status=DataSecureFieldRequestStatus.PENDING,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _build_field_request_row(db, row)


@router.get("/{tool_id}/features/field-requests", response_model=PaginatedDataSecureFieldRequests)
async def list_field_requests(
    tool_id: int,
    project_space_id: int | None = None,
    status: str | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=200),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    _ensure_data_secure_manage_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    can_manage = can_manage_all_records(db, current_user, tool_id)
    where = [DataSecureFieldRequest.tool_id == tool_id]
    if project_space_id is not None:
        where.append(DataSecureFieldRequest.project_space_id == project_space_id)
    if status and status in ("pending", "approved", "rejected"):
        where.append(DataSecureFieldRequest.status == status)
    if not can_manage:
        where.append(DataSecureFieldRequest.requested_by == current_user.id)
    total = db.exec(select(func.count()).select_from(DataSecureFieldRequest).where(*where)).one()
    rows = db.exec(
        select(DataSecureFieldRequest)
        .where(*where)
        .order_by(DataSecureFieldRequest.created_at.desc())
        .offset(skip)
        .limit(limit)
    ).all()
    return PaginatedDataSecureFieldRequests(
        total=int(total or 0),
        items=[_build_field_request_row(db, r) for r in rows],
    )


@router.put("/{tool_id}/features/field-requests/{request_id}/review", response_model=DataSecureFieldRequestInDB)
async def review_field_request(
    tool_id: int,
    request_id: int,
    body: DataSecureFieldRequestReview,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    _ensure_data_secure_manage_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    ensure_manage_permission(db, current_user, tool_id)
    row = db.get(DataSecureFieldRequest, request_id)
    if not row or row.tool_id != tool_id:
        raise HTTPException(status_code=404, detail="申请记录不存在")
    if row.status != DataSecureFieldRequestStatus.PENDING:
        raise HTTPException(status_code=400, detail="该申请已处理，不可重复审核")
    now = datetime.utcnow()
    row.status = DataSecureFieldRequestStatus.APPROVED if body.status == "approved" else DataSecureFieldRequestStatus.REJECTED
    row.review_notes = (body.review_notes or "").strip() or None
    row.reviewed_by = current_user.id
    row.reviewed_at = now
    row.updated_at = now
    db.add(row)
    if row.status == DataSecureFieldRequestStatus.APPROVED:
        payload: dict = {}
        try:
            payload = json.loads(row.payload_json or "{}")
        except Exception:
            payload = {}
        entry, err = _try_insert_field_catalog_entry(
            db,
            tool_id=tool_id,
            project_space_id=row.project_space_id,
            field_name=row.field_name,
            extra_fields=payload,
            created_by_user_id=row.requested_by,
            updated_by_user_id=current_user.id,
        )
        if not entry and err and "已存在" not in err:
            raise HTTPException(status_code=400, detail=f"审核通过但无法写入主表：{err}")
    db.commit()
    db.refresh(row)
    return _build_field_request_row(db, row)


def _build_business_function_option_request_row(
    db: Session, row: DataSecureBusinessFunctionOptionRequest
) -> DataSecureBusinessFunctionOptionRequestInDB:
    requester = db.get(User, row.requested_by)
    reviewer = db.get(User, row.reviewed_by) if row.reviewed_by else None
    space = db.get(DataSecureProjectSpace, row.project_space_id)
    return DataSecureBusinessFunctionOptionRequestInDB(
        id=int(row.id),
        tool_id=row.tool_id,
        project_space_id=row.project_space_id,
        project_space_name=space.name if space else f"空间#{row.project_space_id}",
        requested_by=row.requested_by,
        requested_by_name=requester.username if requester else None,
        proposed_option=row.proposed_option,
        reason=row.reason,
        status=row.status.value,
        review_notes=row.review_notes,
        reviewed_by=row.reviewed_by,
        reviewed_by_name=reviewer.username if reviewer else None,
        reviewed_at=row.reviewed_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.get("/{tool_id}/features/business-function-options", response_model=DataSecureBusinessFunctionOptionsResponse)
async def get_business_function_options(
    tool_id: int,
    project_space_id: int = Query(..., description="项目空间 id"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    _ensure_data_secure_manage_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    space = db.get(DataSecureProjectSpace, project_space_id)
    if not space or space.tool_id != tool_id:
        raise HTTPException(status_code=404, detail="项目空间不存在")
    fk, _cfg_ok, opts = ds_dynamic_fields.list_business_function_option_strings(db, tool_id, project_space_id)
    return DataSecureBusinessFunctionOptionsResponse(
        field_key=fk,
        business_function_configured=fk is not None,
        options=opts,
    )


@router.post(
    "/{tool_id}/features/business-function-option-requests",
    response_model=DataSecureBusinessFunctionOptionRequestInDB,
)
async def create_business_function_option_request(
    tool_id: int,
    body: DataSecureBusinessFunctionOptionRequestCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    _ensure_data_secure_manage_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    space = db.get(DataSecureProjectSpace, body.project_space_id)
    if not space or space.tool_id != tool_id:
        raise HTTPException(status_code=404, detail="项目空间不存在")
    prop = body.proposed_option.strip()
    fk, _, opts = ds_dynamic_fields.list_business_function_option_strings(db, tool_id, body.project_space_id)
    if fk and prop in opts:
        raise HTTPException(status_code=400, detail="该业务功能选项已存在，无需申请")
    dup = db.exec(
        select(DataSecureBusinessFunctionOptionRequest).where(
            DataSecureBusinessFunctionOptionRequest.tool_id == tool_id,
            DataSecureBusinessFunctionOptionRequest.project_space_id == body.project_space_id,
            DataSecureBusinessFunctionOptionRequest.status == DataSecureFieldRequestStatus.PENDING,
            func.lower(DataSecureBusinessFunctionOptionRequest.proposed_option) == prop.lower(),
        )
    ).first()
    if dup:
        raise HTTPException(status_code=400, detail="已存在内容相同的待审核申请，请勿重复提交")
    now = datetime.utcnow()
    row = DataSecureBusinessFunctionOptionRequest(
        tool_id=tool_id,
        project_space_id=body.project_space_id,
        requested_by=current_user.id,
        proposed_option=prop,
        reason=(body.reason or "").strip() or None,
        status=DataSecureFieldRequestStatus.PENDING,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _build_business_function_option_request_row(db, row)


@router.get(
    "/{tool_id}/features/business-function-option-requests",
    response_model=PaginatedDataSecureBusinessFunctionOptionRequests,
)
async def list_business_function_option_requests(
    tool_id: int,
    project_space_id: int | None = None,
    status: str | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=200),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    _ensure_data_secure_manage_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    can_manage = can_manage_all_records(db, current_user, tool_id)
    where = [DataSecureBusinessFunctionOptionRequest.tool_id == tool_id]
    if project_space_id is not None:
        where.append(DataSecureBusinessFunctionOptionRequest.project_space_id == project_space_id)
    if status and status in ("pending", "approved", "rejected"):
        where.append(DataSecureBusinessFunctionOptionRequest.status == status)
    if not can_manage:
        where.append(DataSecureBusinessFunctionOptionRequest.requested_by == current_user.id)
    total = db.exec(select(func.count()).select_from(DataSecureBusinessFunctionOptionRequest).where(*where)).one()
    rows = db.exec(
        select(DataSecureBusinessFunctionOptionRequest)
        .where(*where)
        .order_by(DataSecureBusinessFunctionOptionRequest.created_at.desc())
        .offset(skip)
        .limit(limit)
    ).all()
    return PaginatedDataSecureBusinessFunctionOptionRequests(
        total=int(total or 0),
        items=[_build_business_function_option_request_row(db, r) for r in rows],
    )


@router.put(
    "/{tool_id}/features/business-function-option-requests/{request_id}/review",
    response_model=DataSecureBusinessFunctionOptionRequestInDB,
)
async def review_business_function_option_request(
    tool_id: int,
    request_id: int,
    body: DataSecureBusinessFunctionOptionRequestReview,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    _ensure_data_secure_manage_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    ensure_manage_permission(db, current_user, tool_id)
    row = db.get(DataSecureBusinessFunctionOptionRequest, request_id)
    if not row or row.tool_id != tool_id:
        raise HTTPException(status_code=404, detail="申请记录不存在")
    if row.status != DataSecureFieldRequestStatus.PENDING:
        raise HTTPException(status_code=400, detail="该申请已处理，不可重复审核")
    now = datetime.utcnow()
    row.status = DataSecureFieldRequestStatus.APPROVED if body.status == "approved" else DataSecureFieldRequestStatus.REJECTED
    row.review_notes = (body.review_notes or "").strip() or None
    row.reviewed_by = current_user.id
    row.reviewed_at = now
    row.updated_at = now
    db.add(row)
    if row.status == DataSecureFieldRequestStatus.APPROVED:
        target_fk = ds_dynamic_fields.resolve_business_function_field_key(db, tool_id, row.project_space_id)
        if not target_fk:
            raise HTTPException(
                status_code=400,
                detail="当前空间尚未配置「业务功能」填报列（field_key 建议 business_function），无法写入新选项",
            )
        ds_dynamic_fields.append_allowed_value_to_lifecycle_field(
            db, tool_id, row.project_space_id, target_fk, row.proposed_option, current_user.id
        )
    db.commit()
    db.refresh(row)
    return _build_business_function_option_request_row(db, row)


@router.post("/{tool_id}/features/field-usage-reports", response_model=DataSecureFieldUsageReportInDB)
async def create_field_usage_report(
    tool_id: int,
    body: DataSecureFieldUsageReportCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    _ensure_data_secure_manage_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    space = db.get(DataSecureProjectSpace, body.project_space_id)
    if not space or space.tool_id != tool_id:
        raise HTTPException(status_code=404, detail="项目空间不存在")
    lines_in: list[DataSecureFieldUsageLineCreate] = []
    if body.lines and len(body.lines) > 0:
        lines_in = list(body.lines)
    elif body.field_entry_ids and len(body.field_entry_ids) > 0:
        lines_in = [DataSecureFieldUsageLineCreate(catalog_entry_id=int(eid), extra_fields={}) for eid in body.field_entry_ids]
    if not lines_in:
        raise HTTPException(status_code=400, detail="请至少提交一条数据字段填报（含 catalog_entry_id）")
    seen_ids: set[int] = set()
    deduped: list[DataSecureFieldUsageLineCreate] = []
    for ln in lines_in:
        cid = int(ln.catalog_entry_id)
        if cid in seen_ids:
            continue
        seen_ids.add(cid)
        deduped.append(ln)
    if not deduped:
        raise HTTPException(status_code=400, detail="请至少选择一条数据字段")
    entry_ids = [int(l.catalog_entry_id) for l in deduped]
    catalog_rows = db.exec(
        select(DataSecureFieldCatalogEntry).where(
            DataSecureFieldCatalogEntry.tool_id == tool_id,
            DataSecureFieldCatalogEntry.project_space_id == body.project_space_id,
            DataSecureFieldCatalogEntry.id.in_(entry_ids),
        )
    ).all()
    if len(catalog_rows) != len(set(entry_ids)):
        raise HTTPException(status_code=400, detail="存在无效的数据字段，请先在主表中确认")
    aid = int(body.assessment_submission_id)
    asm = db.get(DataSecureAssessmentSubmission, aid)
    if not asm or asm.tool_id != tool_id or int(asm.project_space_id) != int(body.project_space_id):
        raise HTTPException(status_code=400, detail="问卷提交记录不存在或与当前项目空间不一致")
    if int(asm.submitted_by) != int(current_user.id):
        raise HTTPException(status_code=403, detail="只能基于本人提交的问卷继续填报字段")
    if not bool(asm.is_related):
        raise HTTPException(status_code=400, detail="仅当问卷判定为「相关」后可提交字段填报工单")
    dup = db.exec(
        select(DataSecureFieldUsageReport).where(
            DataSecureFieldUsageReport.tool_id == tool_id,
            DataSecureFieldUsageReport.assessment_submission_id == aid,
        )
    ).first()
    if dup:
        raise HTTPException(status_code=400, detail="该问卷已关联字段填报，请勿重复提交")
    catalog_by_id = {int(r.id): r for r in catalog_rows}
    fn = ((body.function_name or "").strip() or asm.function_name or "数据字段填报")[:500]
    now = datetime.utcnow()
    report = DataSecureFieldUsageReport(
        tool_id=tool_id,
        project_space_id=body.project_space_id,
        submitted_by=current_user.id,
        assessment_submission_id=aid,
        function_name=fn,
        function_description=(body.function_description or "").strip() or asm.function_description,
        notes=(body.notes or "").strip() or None,
        review_status=DataSecureUsageReviewStatus.PENDING,
        submitted_at=now,
    )
    db.add(report)
    db.flush()
    for ln in deduped:
        entry = catalog_by_id[int(ln.catalog_entry_id)]
        normalized = ds_dynamic_fields.validate_extra_fields_subset(
            db,
            tool_id,
            body.project_space_id,
            ln.extra_fields or {},
        )
        snap = json.dumps(normalized, ensure_ascii=False)
        db.add(
            DataSecureFieldUsageReportItem(
                report_id=int(report.id),
                catalog_entry_id=int(entry.id),
                field_name_snapshot=entry.field_name,
                extra_snapshot_json=snap,
                created_at=now,
            )
        )
    db.commit()
    db.refresh(report)
    return _build_usage_report_row(db, report)


@router.get("/{tool_id}/features/field-usage-reports", response_model=PaginatedDataSecureFieldUsageReports)
async def list_field_usage_reports(
    tool_id: int,
    project_space_id: int | None = None,
    review_status: str | None = Query(default=None, description="pending/approved/rejected，负责人筛选用"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=200),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    _ensure_data_secure_manage_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    can_manage = can_manage_all_records(db, current_user, tool_id)
    where = [DataSecureFieldUsageReport.tool_id == tool_id]
    if project_space_id is not None:
        where.append(DataSecureFieldUsageReport.project_space_id == project_space_id)
    if review_status and str(review_status).strip():
        rs = str(review_status).strip().lower()
        st_map = {
            "pending": DataSecureUsageReviewStatus.PENDING,
            "approved": DataSecureUsageReviewStatus.APPROVED,
            "rejected": DataSecureUsageReviewStatus.REJECTED,
        }
        if rs in st_map:
            where.append(DataSecureFieldUsageReport.review_status == st_map[rs])
    if not can_manage:
        where.append(DataSecureFieldUsageReport.submitted_by == current_user.id)
    total = db.exec(select(func.count()).select_from(DataSecureFieldUsageReport).where(*where)).one()
    rows = db.exec(
        select(DataSecureFieldUsageReport)
        .where(*where)
        .order_by(DataSecureFieldUsageReport.submitted_at.desc())
        .offset(skip)
        .limit(limit)
    ).all()
    return PaginatedDataSecureFieldUsageReports(
        total=int(total or 0),
        items=[_build_usage_report_row(db, row) for row in rows],
    )


@router.get("/{tool_id}/features/field-usage-reports/export", response_model=DataSecureFieldUsageExportResponse)
async def export_field_usage_reports(
    tool_id: int,
    project_space_id: int | None = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    _ensure_data_secure_manage_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    ensure_manage_permission(db, current_user, tool_id)
    where = [DataSecureFieldUsageReport.tool_id == tool_id]
    if project_space_id is not None:
        where.append(DataSecureFieldUsageReport.project_space_id == project_space_id)
    reports = db.exec(
        select(DataSecureFieldUsageReport)
        .where(*where)
        .order_by(DataSecureFieldUsageReport.submitted_at.desc())
    ).all()
    rows: list[DataSecureFieldUsageExportRow] = []
    for report in reports:
        report_row = _build_usage_report_row(db, report)
        items = db.exec(
            select(DataSecureFieldUsageReportItem).where(DataSecureFieldUsageReportItem.report_id == int(report.id))
        ).all()
        for it in items:
            rows.append(
                DataSecureFieldUsageExportRow(
                    project_space_name=report_row.project_space_name,
                    function_name=report_row.function_name,
                    function_description=report_row.function_description,
                    data_field_name=it.field_name_snapshot,
                    other_info_json=getattr(it, "extra_snapshot_json", None) or "{}",
                    submitted_by_name=report_row.submitted_by_name,
                    submitted_at=report_row.submitted_at,
                )
            )
    return DataSecureFieldUsageExportResponse(items=rows)


@router.post("/{tool_id}/features/field-usage-reports/{report_id}/review", response_model=DataSecureFieldUsageReportInDB)
async def review_field_usage_report(
    tool_id: int,
    report_id: int,
    body: DataSecureFieldUsageReportReviewRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    _ensure_data_secure_manage_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    ensure_manage_permission(db, current_user, tool_id)
    row = db.get(DataSecureFieldUsageReport, report_id)
    if not row or row.tool_id != tool_id:
        raise HTTPException(status_code=404, detail="填报工单不存在")
    if row.review_status != DataSecureUsageReviewStatus.PENDING:
        raise HTTPException(status_code=400, detail="该工单已审批，无法重复操作")
    if body.status == "approved":
        row.review_status = DataSecureUsageReviewStatus.APPROVED
    else:
        row.review_status = DataSecureUsageReviewStatus.REJECTED
    row.review_notes = (body.review_notes or "").strip() or None
    row.reviewed_by = current_user.id
    row.reviewed_at = datetime.utcnow()
    db.add(row)
    db.commit()
    db.refresh(row)
    return _build_usage_report_row(db, row)


@router.get("/{tool_id}/features/work-orders", response_model=PaginatedDataSecureWorkOrders)
async def list_work_orders(
    tool_id: int,
    project_space_id: int | None = None,
    mine: bool = Query(default=False, description="为真时仅返回当前用户本人提交的问卷工单（工具负责人查看「我的」时用）"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=200),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    """问卷 + 字段填报工单合并列表（按问卷提交时间倒序）。"""
    tool = get_tool_or_404(db, tool_id)
    _ensure_data_secure_manage_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    can_manage = can_manage_all_records(db, current_user, tool_id)
    where = [DataSecureAssessmentSubmission.tool_id == tool_id]
    if project_space_id is not None:
        where.append(DataSecureAssessmentSubmission.project_space_id == project_space_id)
    if not can_manage:
        where.append(DataSecureAssessmentSubmission.submitted_by == current_user.id)
    elif mine:
        where.append(DataSecureAssessmentSubmission.submitted_by == current_user.id)
    total = db.exec(select(func.count()).select_from(DataSecureAssessmentSubmission).where(*where)).one()
    rows = db.exec(
        select(DataSecureAssessmentSubmission)
        .where(*where)
        .order_by(DataSecureAssessmentSubmission.submitted_at.desc())
        .offset(skip)
        .limit(limit)
    ).all()
    items: list[DataSecureWorkOrderRow] = []
    for a in rows:
        ur = db.exec(
            select(DataSecureFieldUsageReport).where(
                DataSecureFieldUsageReport.tool_id == tool_id,
                DataSecureFieldUsageReport.assessment_submission_id == int(a.id),
            )
        ).first()
        rs = getattr(ur, "review_status", None) if ur else None
        rs_out = rs.value if hasattr(rs, "value") else (str(rs) if rs else None)
        items.append(
            DataSecureWorkOrderRow(
                assessment_submission_id=int(a.id),
                questionnaire_submitted_at=a.submitted_at,
                function_name=a.function_name,
                is_related=bool(a.is_related),
                result_summary=a.result_summary,
                field_usage_report_id=int(ur.id) if ur else None,
                usage_submitted_at=ur.submitted_at if ur else None,
                review_status=rs_out,  # type: ignore[arg-type]
                review_notes=getattr(ur, "review_notes", None) if ur else None,
            )
        )
    return PaginatedDataSecureWorkOrders(total=int(total or 0), items=items)


@router.get("/{tool_id}/features/approved-consolidated-export", response_model=DataSecureConsolidatedExportResponse)
async def export_approved_consolidated(
    tool_id: int,
    project_space_id: int,
    mine: bool = Query(default=False, description="仅导出当前用户本人过审工单"),
    filter_field_key: list[str] | None = Query(
        default=None,
        description="可重复传参：按填报快照中的列 key 筛选（多选为 OR：任一列命中即参与后续值判断）",
    ),
    filter_value_contains: list[str] | None = Query(
        default=None,
        description="可重复传参：列值需包含其中任一子串（OR）；未传则仅按列存在性筛选",
    ),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    """过审字段填报工单 + 问卷摘要 + 分类分级 + 安全要求（配置级）合并导出。"""
    tool = get_tool_or_404(db, tool_id)
    _ensure_data_secure_manage_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    can_manage = can_manage_all_records(db, current_user, tool_id)
    if not can_manage and not mine:
        raise HTTPException(status_code=403, detail="仅工具负责人可导出全量；普通用户请使用「仅本人」导出")
    space = db.get(DataSecureProjectSpace, project_space_id)
    if not space or space.tool_id != tool_id:
        raise HTTPException(status_code=404, detail="项目空间不存在")
    where = [
        DataSecureFieldUsageReport.tool_id == tool_id,
        DataSecureFieldUsageReport.project_space_id == project_space_id,
        DataSecureFieldUsageReport.review_status == DataSecureUsageReviewStatus.APPROVED,
    ]
    if mine or not can_manage:
        where.append(DataSecureFieldUsageReport.submitted_by == current_user.id)
    reports = db.exec(
        select(DataSecureFieldUsageReport).where(*where).order_by(DataSecureFieldUsageReport.submitted_at.desc())
    ).all()
    out_rows: list[DataSecureConsolidatedExportRow] = []
    fkeys = [str(x).strip() for x in (filter_field_key or []) if str(x).strip()]
    fvals = [str(x).strip() for x in (filter_value_contains or []) if str(x).strip()]
    for report in reports:
        asm_id = getattr(report, "assessment_submission_id", None)
        asm = db.get(DataSecureAssessmentSubmission, asm_id) if asm_id else None
        if not asm:
            continue
        space_name = space.name
        items = db.exec(
            select(DataSecureFieldUsageReportItem).where(DataSecureFieldUsageReportItem.report_id == int(report.id))
        ).all()
        submitter = db.get(User, report.submitted_by)
        for it in items:
            snap_raw = getattr(it, "extra_snapshot_json", None) or "{}"
            if fkeys:
                try:
                    snap = json.loads(snap_raw)
                except Exception:
                    snap = {}
                if not isinstance(snap, dict):
                    snap = {}
                snap_ok = False
                for fk in fkeys:
                    if fk not in snap:
                        continue
                    cell = snap.get(fk)
                    s = str(cell)
                    if not fvals:
                        snap_ok = True
                        break
                    if any(v in s for v in fvals):
                        snap_ok = True
                        break
                if not snap_ok:
                    continue
            cls_row = db.exec(
                select(DataSecureFieldClassificationResult).where(
                    DataSecureFieldClassificationResult.tool_id == tool_id,
                    DataSecureFieldClassificationResult.project_space_id == project_space_id,
                    DataSecureFieldClassificationResult.catalog_entry_id == int(it.catalog_entry_id),
                )
            ).first()
            sec_txt = _security_requirements_join_text(db, tool_id, project_space_id, int(it.catalog_entry_id))
            out_rows.append(
                DataSecureConsolidatedExportRow(
                    project_space_name=space_name,
                    assessment_submission_id=int(asm.id),
                    questionnaire_submitted_at=asm.submitted_at,
                    is_related=bool(asm.is_related),
                    result_summary=asm.result_summary,
                    field_usage_report_id=int(report.id),
                    usage_submitted_at=report.submitted_at,
                    submitted_by_name=submitter.username if submitter else None,
                    data_field_name=it.field_name_snapshot,
                    other_info_json=snap_raw,
                    category=cls_row.category if cls_row else "",
                    level=cls_row.level if cls_row else "",
                    auto_category=cls_row.auto_category if cls_row else "",
                    auto_level=cls_row.auto_level if cls_row else "",
                    auto_hit_summary=cls_row.auto_hit_summary if cls_row else None,
                    security_requirements_text=sec_txt,
                )
            )
    return DataSecureConsolidatedExportResponse(items=out_rows)


@router.get("/{tool_id}/features/classification-matrix", response_model=PaginatedDataSecureClassificationMatrix)
async def list_classification_matrix(
    tool_id: int,
    project_space_id: int,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=500),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    _ensure_data_secure_manage_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    where = [
        DataSecureFieldClassificationMatrix.tool_id == tool_id,
        DataSecureFieldClassificationMatrix.project_space_id == project_space_id,
    ]
    total = db.exec(select(func.count()).select_from(DataSecureFieldClassificationMatrix).where(*where)).one()
    rows = db.exec(
        select(DataSecureFieldClassificationMatrix)
        .where(*where)
        .order_by(
            DataSecureFieldClassificationMatrix.priority.desc(),
            DataSecureFieldClassificationMatrix.sort_order,
            DataSecureFieldClassificationMatrix.id,
        )
        .offset(skip)
        .limit(limit)
    ).all()
    return PaginatedDataSecureClassificationMatrix(
        total=int(total or 0),
        items=[_build_classification_matrix_row(r) for r in rows],
    )


@router.post("/{tool_id}/features/classification-matrix/batch-import", response_model=DataSecureClassificationMatrixBatchImportResult)
async def batch_import_classification_matrix(
    tool_id: int,
    body: DataSecureClassificationMatrixBatchImport,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    _ensure_data_secure_manage_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    ensure_manage_permission(db, current_user, tool_id)
    space = db.get(DataSecureProjectSpace, body.project_space_id)
    if not space or space.tool_id != tool_id:
        raise HTTPException(status_code=404, detail="项目空间不存在")
    created = 0
    failed = 0
    errors: list[str] = []
    max_err = 80
    now = datetime.utcnow()
    for i, item in enumerate(body.items):
        try:
            crit = _validate_matrix_extension_match(
                db, tool_id, body.project_space_id, item.extension_match or {}
            )
            row = DataSecureFieldClassificationMatrix(
                tool_id=tool_id,
                project_space_id=body.project_space_id,
                field_name=item.field_name.strip(),
                extension_match_json=_matrix_criteria_to_json(crit),
                category=item.category.strip(),
                level=item.level.strip(),
                priority=item.priority,
                notes=(item.notes or "").strip() or None,
                sort_order=item.sort_order,
                is_active=True,
                created_by=current_user.id,
                updated_by=current_user.id,
                created_at=now,
                updated_at=now,
            )
            db.add(row)
            created += 1
        except HTTPException as exc:
            failed += 1
            if len(errors) < max_err:
                errors.append(f"第 {i + 1} 条「{item.field_name.strip()}」：{str(exc.detail)}")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            if len(errors) < max_err:
                errors.append(f"第 {i + 1} 条「{item.field_name.strip()}」：{exc}")
    db.commit()
    return DataSecureClassificationMatrixBatchImportResult(
        created_count=created,
        failed_validation=failed,
        errors=errors,
    )


@router.post("/{tool_id}/features/classification-matrix", response_model=DataSecureClassificationMatrixInDB)
async def create_classification_matrix(
    tool_id: int,
    body: DataSecureClassificationMatrixCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    _ensure_data_secure_manage_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    ensure_manage_permission(db, current_user, tool_id)
    space = db.get(DataSecureProjectSpace, body.project_space_id)
    if not space or space.tool_id != tool_id:
        raise HTTPException(status_code=404, detail="项目空间不存在")
    crit = _validate_matrix_extension_match(db, tool_id, body.project_space_id, body.extension_match or {})
    now = datetime.utcnow()
    row = DataSecureFieldClassificationMatrix(
        tool_id=tool_id,
        project_space_id=body.project_space_id,
        field_name=body.field_name.strip(),
        extension_match_json=_matrix_criteria_to_json(crit),
        category=body.category.strip(),
        level=body.level.strip(),
        priority=body.priority,
        notes=(body.notes or "").strip() or None,
        sort_order=body.sort_order,
        is_active=True,
        created_by=current_user.id,
        updated_by=current_user.id,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _build_classification_matrix_row(row)


@router.put("/{tool_id}/features/classification-matrix", response_model=DataSecureClassificationMatrixInDB)
async def update_classification_matrix(
    tool_id: int,
    body: DataSecureClassificationMatrixUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    _ensure_data_secure_manage_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    ensure_manage_permission(db, current_user, tool_id)
    reason = _normalize_change_reason(body.change_reason)
    row = db.get(DataSecureFieldClassificationMatrix, body.id)
    if not row or row.tool_id != tool_id:
        raise HTTPException(status_code=404, detail="显式分类矩阵记录不存在")
    if body.field_name is not None:
        row.field_name = body.field_name.strip()
    if body.extension_match is not None:
        crit = _validate_matrix_extension_match(db, tool_id, row.project_space_id, body.extension_match)
        row.extension_match_json = _matrix_criteria_to_json(crit)
    if body.category is not None:
        row.category = body.category.strip()
    if body.level is not None:
        row.level = body.level.strip()
    if body.priority is not None:
        row.priority = body.priority
    if body.notes is not None:
        row.notes = body.notes.strip() or None
    if body.sort_order is not None:
        row.sort_order = body.sort_order
    if body.is_active is not None:
        row.is_active = body.is_active
    row.updated_by = current_user.id
    row.updated_at = datetime.utcnow()
    db.add(row)
    _append_governance_change_log(
        db,
        tool_id=tool_id,
        project_space_id=int(row.project_space_id),
        domain="classification_matrix",
        action="update",
        target_type="matrix",
        target_id=str(int(row.id)),
        change_reason=reason,
        changed_by=current_user.id,
        detail={"field_name": row.field_name, "is_active": bool(row.is_active), "priority": int(row.priority)},
    )
    db.commit()
    db.refresh(row)
    return _build_classification_matrix_row(row)


@router.delete("/{tool_id}/features/classification-matrix/{matrix_id}", response_model=DataSecureClassificationMatrixDeleteResult)
async def delete_classification_matrix(
    tool_id: int,
    matrix_id: int,
    change_reason: str = Query(..., min_length=5, max_length=1000),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    _ensure_data_secure_manage_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    ensure_manage_permission(db, current_user, tool_id)
    reason = _normalize_change_reason(change_reason)
    row = db.get(DataSecureFieldClassificationMatrix, matrix_id)
    if not row or row.tool_id != tool_id:
        raise HTTPException(status_code=404, detail="显式分类矩阵记录不存在")
    project_space_id = int(row.project_space_id)
    db.delete(row)
    _append_governance_change_log(
        db,
        tool_id=tool_id,
        project_space_id=project_space_id,
        domain="classification_matrix",
        action="delete",
        target_type="matrix",
        target_id=str(matrix_id),
        change_reason=reason,
        changed_by=current_user.id,
        detail={"field_name": row.field_name},
    )
    db.commit()
    return DataSecureClassificationMatrixDeleteResult()


@router.get("/{tool_id}/features/classification-rules", response_model=PaginatedDataSecureClassificationRules)
async def list_classification_rules(
    tool_id: int,
    project_space_id: int,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=200),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    _ensure_data_secure_manage_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    where = [
        DataSecureFieldClassificationRule.tool_id == tool_id,
        DataSecureFieldClassificationRule.project_space_id == project_space_id,
    ]
    total = db.exec(select(func.count()).select_from(DataSecureFieldClassificationRule).where(*where)).one()
    rows = db.exec(
        select(DataSecureFieldClassificationRule)
        .where(*where)
        .order_by(
            DataSecureFieldClassificationRule.priority.desc(),
            DataSecureFieldClassificationRule.sort_order,
            DataSecureFieldClassificationRule.id,
        )
        .offset(skip)
        .limit(limit)
    ).all()
    return PaginatedDataSecureClassificationRules(total=int(total or 0), items=[_build_classification_rule_row(r) for r in rows])


@router.post("/{tool_id}/features/classification-rules", response_model=DataSecureClassificationRuleInDB)
async def create_classification_rule(
    tool_id: int,
    body: DataSecureClassificationRuleCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    _ensure_data_secure_manage_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    ensure_manage_permission(db, current_user, tool_id)
    now = datetime.utcnow()
    row = DataSecureFieldClassificationRule(
        tool_id=tool_id,
        project_space_id=body.project_space_id,
        keyword=body.keyword.strip(),
        category=body.category.strip(),
        level=body.level.strip(),
        priority=body.priority,
        notes=(body.notes or "").strip() or None,
        sort_order=body.sort_order,
        is_active=True,
        created_by=current_user.id,
        updated_by=current_user.id,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _build_classification_rule_row(row)


@router.put("/{tool_id}/features/classification-rules", response_model=DataSecureClassificationRuleInDB)
async def update_classification_rule(
    tool_id: int,
    body: DataSecureClassificationRuleUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    _ensure_data_secure_manage_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    ensure_manage_permission(db, current_user, tool_id)
    reason = _normalize_change_reason(body.change_reason)
    row = db.get(DataSecureFieldClassificationRule, body.id)
    if not row or row.tool_id != tool_id:
        raise HTTPException(status_code=404, detail="分类分级规则不存在")
    if body.keyword is not None:
        row.keyword = body.keyword.strip()
    if body.category is not None:
        row.category = body.category.strip()
    if body.level is not None:
        row.level = body.level.strip()
    if body.priority is not None:
        row.priority = body.priority
    if body.notes is not None:
        row.notes = body.notes.strip() or None
    if body.sort_order is not None:
        row.sort_order = body.sort_order
    if body.is_active is not None:
        row.is_active = body.is_active
    row.updated_by = current_user.id
    row.updated_at = datetime.utcnow()
    db.add(row)
    _append_governance_change_log(
        db,
        tool_id=tool_id,
        project_space_id=int(row.project_space_id),
        domain="classification_rule",
        action="update",
        target_type="rule",
        target_id=str(int(row.id)),
        change_reason=reason,
        changed_by=current_user.id,
        detail={"keyword": row.keyword, "is_active": bool(row.is_active), "priority": int(row.priority)},
    )
    db.commit()
    db.refresh(row)
    return _build_classification_rule_row(row)


@router.delete("/{tool_id}/features/classification-rules/{rule_id}", response_model=DataSecureClassificationRuleDeleteResult)
async def delete_classification_rule(
    tool_id: int,
    rule_id: int,
    change_reason: str = Query(..., min_length=5, max_length=1000),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    _ensure_data_secure_manage_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    ensure_manage_permission(db, current_user, tool_id)
    reason = _normalize_change_reason(change_reason)
    row = db.get(DataSecureFieldClassificationRule, rule_id)
    if not row or row.tool_id != tool_id:
        raise HTTPException(status_code=404, detail="分类分级规则不存在")
    project_space_id = int(row.project_space_id)
    db.delete(row)
    _append_governance_change_log(
        db,
        tool_id=tool_id,
        project_space_id=project_space_id,
        domain="classification_rule",
        action="delete",
        target_type="rule",
        target_id=str(rule_id),
        change_reason=reason,
        changed_by=current_user.id,
        detail={"keyword": row.keyword},
    )
    db.commit()
    return DataSecureClassificationRuleDeleteResult()


@router.post("/{tool_id}/features/classification-recompute", response_model=DataSecureClassificationRecomputeResponse)
async def recompute_classification(
    tool_id: int,
    project_space_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    _ensure_data_secure_manage_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    ensure_manage_permission(db, current_user, tool_id)
    entries = db.exec(
        select(DataSecureFieldCatalogEntry).where(
            DataSecureFieldCatalogEntry.tool_id == tool_id,
            DataSecureFieldCatalogEntry.project_space_id == project_space_id,
        )
    ).all()
    for entry in entries:
        _upsert_classification_for_entry(db, tool_id, project_space_id, entry, current_user.id)
    _append_classification_audit(
        db,
        tool_id,
        project_space_id,
        current_user.id,
        "batch_auto_recompute",
        {"处理条数": len(entries), "说明": "已对主表字段重算自动分类快照；人工覆写条目的展示分类未改动"},
    )
    db.commit()
    return DataSecureClassificationRecomputeResponse(updated_count=len(entries))


@router.get("/{tool_id}/features/classification-results", response_model=PaginatedDataSecureClassificationResults)
async def list_classification_results(
    tool_id: int,
    project_space_id: int,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=200),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    _ensure_data_secure_manage_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    where = [
        DataSecureFieldClassificationResult.tool_id == tool_id,
        DataSecureFieldClassificationResult.project_space_id == project_space_id,
    ]
    total = db.exec(select(func.count()).select_from(DataSecureFieldClassificationResult).where(*where)).one()
    rows = db.exec(
        select(DataSecureFieldClassificationResult)
        .where(*where)
        .order_by(DataSecureFieldClassificationResult.updated_at.desc())
        .offset(skip)
        .limit(limit)
    ).all()
    return PaginatedDataSecureClassificationResults(
        total=int(total or 0),
        items=[_build_classification_result_row(db, row) for row in rows],
    )


@router.put("/{tool_id}/features/classification-results/{result_id}/manual", response_model=DataSecureClassificationResultInDB)
async def manual_override_classification_result(
    tool_id: int,
    result_id: int,
    body: DataSecureClassificationManualOverride,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    _ensure_data_secure_manage_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    ensure_manage_permission(db, current_user, tool_id)
    row = db.get(DataSecureFieldClassificationResult, result_id)
    if not row or row.tool_id != tool_id:
        raise HTTPException(status_code=404, detail="分类分级结果不存在")
    before = {
        "category": row.category,
        "level": row.level,
        "source": row.source,
        "manual_reason": row.manual_reason,
    }
    row.category = body.category.strip()
    row.level = body.level.strip()
    row.rule_keyword = None
    row.manual_reason = body.reason.strip()
    row.source = "manual"
    row.updated_by = current_user.id
    row.updated_at = datetime.utcnow()
    db.add(row)
    _append_classification_audit(
        db,
        tool_id,
        row.project_space_id,
        current_user.id,
        "manual_override",
        {"变更前": before, "变更后": {"category": row.category, "level": row.level, "原因": row.manual_reason}},
        catalog_entry_id=int(row.catalog_entry_id),
        result_id=int(row.id),
    )
    db.commit()
    db.refresh(row)
    return _build_classification_result_row(db, row)


@router.post("/{tool_id}/features/classification-results/{result_id}/revert-auto", response_model=DataSecureClassificationResultInDB)
async def revert_classification_result_to_auto(
    tool_id: int,
    result_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    _ensure_data_secure_manage_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    ensure_manage_permission(db, current_user, tool_id)
    row = db.get(DataSecureFieldClassificationResult, result_id)
    if not row or row.tool_id != tool_id:
        raise HTTPException(status_code=404, detail="分类分级结果不存在")
    if row.source != "manual":
        raise HTTPException(status_code=400, detail="当前记录并非人工覆写，无需恢复自动分类")
    before = {"category": row.category, "level": row.level, "manual_reason": row.manual_reason}
    row.category = row.auto_category
    row.level = row.auto_level
    row.rule_keyword = row.auto_rule_keyword
    row.manual_reason = None
    row.source = "auto"
    row.updated_by = current_user.id
    row.updated_at = datetime.utcnow()
    db.add(row)
    _append_classification_audit(
        db,
        tool_id,
        row.project_space_id,
        current_user.id,
        "revert_to_auto",
        {"变更前": before, "变更后": {"category": row.category, "level": row.level}},
        catalog_entry_id=int(row.catalog_entry_id),
        result_id=int(row.id),
    )
    db.commit()
    db.refresh(row)
    return _build_classification_result_row(db, row)


@router.get("/{tool_id}/features/classification-audit", response_model=PaginatedDataSecureClassificationAuditLogs)
async def list_classification_audit_logs(
    tool_id: int,
    project_space_id: int,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=200),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    _ensure_data_secure_manage_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    ensure_manage_permission(db, current_user, tool_id)
    where = [
        DataSecureFieldClassificationAuditLog.tool_id == tool_id,
        DataSecureFieldClassificationAuditLog.project_space_id == project_space_id,
    ]
    total = db.exec(select(func.count()).select_from(DataSecureFieldClassificationAuditLog).where(*where)).one()
    rows = db.exec(
        select(DataSecureFieldClassificationAuditLog)
        .where(*where)
        .order_by(DataSecureFieldClassificationAuditLog.created_at.desc())
        .offset(skip)
        .limit(limit)
    ).all()
    return PaginatedDataSecureClassificationAuditLogs(
        total=int(total or 0),
        items=[_build_classification_audit_row(db, r) for r in rows],
    )


@router.get("/{tool_id}/features/classification-export", response_model=DataSecureClassificationExportResponse)
async def export_classification_results(
    tool_id: int,
    project_space_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    _ensure_data_secure_manage_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    ensure_manage_permission(db, current_user, tool_id)
    rows = db.exec(
        select(DataSecureFieldClassificationResult)
        .where(
            DataSecureFieldClassificationResult.tool_id == tool_id,
            DataSecureFieldClassificationResult.project_space_id == project_space_id,
        )
        .order_by(DataSecureFieldClassificationResult.field_name_snapshot)
        .limit(5000)
    ).all()
    out: list[DataSecureClassificationExportRow] = []
    for r in rows:
        updater = db.get(User, r.updated_by)
        out.append(
            DataSecureClassificationExportRow(
                project_space_id=r.project_space_id,
                catalog_entry_id=int(r.catalog_entry_id),
                field_name=r.field_name_snapshot,
                effective_category=r.category,
                effective_level=r.level,
                effective_rule_keyword=r.rule_keyword,
                source=r.source,
                auto_category=str(getattr(r, "auto_category", None) or r.category),
                auto_level=str(getattr(r, "auto_level", None) or r.level),
                auto_rule_keyword=getattr(r, "auto_rule_keyword", None),
                auto_rule_id=getattr(r, "auto_rule_id", None),
                auto_matrix_id=getattr(r, "auto_matrix_id", None),
                auto_match_source=str(getattr(r, "auto_match_source", None) or "keyword"),
                auto_hit_summary=getattr(r, "auto_hit_summary", None),
                manual_reason=getattr(r, "manual_reason", None),
                updated_by_name=updater.username if updater else None,
                updated_at=r.updated_at,
            )
        )
    return DataSecureClassificationExportResponse(items=out)


# --- 结构化治理：多级分类树、字段分级（C0–C3）、安全要求逻辑表达式 ---


@router.get("/{tool_id}/features/taxonomy-nodes", response_model=PaginatedDataSecureTaxonomyNodes)
async def list_taxonomy_nodes(
    tool_id: int,
    project_space_id: int,
    parent_is_root: bool = Query(default=False),
    parent_id: int | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    _ensure_data_secure_manage_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    where = [
        DataSecureTaxonomyNode.tool_id == tool_id,
        DataSecureTaxonomyNode.project_space_id == project_space_id,
    ]
    if parent_is_root:
        where.append(DataSecureTaxonomyNode.parent_id.is_(None))  # type: ignore[union-attr]
    elif parent_id is not None:
        where.append(DataSecureTaxonomyNode.parent_id == int(parent_id))
    total = db.exec(select(func.count()).select_from(DataSecureTaxonomyNode).where(*where)).one()
    rows = db.exec(
        select(DataSecureTaxonomyNode)
        .where(*where)
        .order_by(DataSecureTaxonomyNode.sort_order, DataSecureTaxonomyNode.id)
        .offset(skip)
        .limit(limit)
    ).all()
    return PaginatedDataSecureTaxonomyNodes(
        total=int(total or 0),
        items=[_build_taxonomy_node_row(r) for r in rows],
    )


@router.post("/{tool_id}/features/taxonomy-nodes", response_model=DataSecureTaxonomyNodeInDB)
async def create_taxonomy_node(
    tool_id: int,
    body: DataSecureTaxonomyNodeCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    _ensure_data_secure_manage_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    ensure_manage_permission(db, current_user, tool_id)
    reason = _normalize_change_reason(body.change_reason)
    space = db.get(DataSecureProjectSpace, body.project_space_id)
    if not space or space.tool_id != tool_id:
        raise HTTPException(status_code=404, detail="项目空间不存在")
    nk = _validate_taxonomy_node_key(body.node_key)
    dup = db.exec(
        select(DataSecureTaxonomyNode).where(
            DataSecureTaxonomyNode.project_space_id == body.project_space_id,
            DataSecureTaxonomyNode.node_key == nk,
        )
    ).first()
    if dup:
        raise HTTPException(status_code=400, detail="同一空间下 node_key 已存在")
    _taxonomy_parent_for_create(db, tool_id, body.project_space_id, body.parent_id)
    now = datetime.utcnow()
    row = DataSecureTaxonomyNode(
        tool_id=tool_id,
        project_space_id=body.project_space_id,
        parent_id=body.parent_id,
        name=body.name.strip(),
        node_key=nk,
        sort_order=body.sort_order,
        is_active=True,
        created_by=current_user.id,
        updated_by=current_user.id,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    _append_governance_change_log(
        db,
        tool_id=tool_id,
        project_space_id=body.project_space_id,
        domain="taxonomy",
        action="create",
        target_type="taxonomy_node",
        target_id=nk,
        change_reason=reason,
        changed_by=current_user.id,
        detail={"name": body.name.strip(), "parent_id": body.parent_id, "sort_order": body.sort_order},
    )
    db.commit()
    db.refresh(row)
    return _build_taxonomy_node_row(row)


@router.put("/{tool_id}/features/taxonomy-nodes/{node_id}", response_model=DataSecureTaxonomyNodeInDB)
async def update_taxonomy_node(
    tool_id: int,
    node_id: int,
    body: DataSecureTaxonomyNodeUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    _ensure_data_secure_manage_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    ensure_manage_permission(db, current_user, tool_id)
    reason = _normalize_change_reason(body.change_reason)
    row = db.get(DataSecureTaxonomyNode, node_id)
    if not row or row.tool_id != tool_id:
        raise HTTPException(status_code=404, detail="分类节点不存在")
    if body.name is not None:
        row.name = body.name.strip()
    if body.sort_order is not None:
        row.sort_order = body.sort_order
    if body.is_active is not None:
        row.is_active = body.is_active
        if not body.is_active:
            frontier = [int(row.id)]
            seen: set[int] = set()
            while frontier:
                nid = frontier.pop()
                if nid in seen:
                    continue
                seen.add(nid)
                kids = db.exec(
                    select(DataSecureTaxonomyNode).where(DataSecureTaxonomyNode.parent_id == nid)
                ).all()
                for ch in kids:
                    cid = int(ch.id) if ch.id is not None else 0
                    if cid and cid not in seen:
                        frontier.append(cid)
                    if ch.is_active:
                        ch.is_active = False
                        ch.updated_by = current_user.id
                        ch.updated_at = datetime.utcnow()
                        db.add(ch)
    row.updated_by = current_user.id
    row.updated_at = datetime.utcnow()
    db.add(row)
    _append_governance_change_log(
        db,
        tool_id=tool_id,
        project_space_id=row.project_space_id,
        domain="taxonomy",
        action="update",
        target_type="taxonomy_node",
        target_id=row.node_key,
        change_reason=reason,
        changed_by=current_user.id,
        detail={"node_id": int(row.id), "name": row.name, "is_active": row.is_active, "sort_order": row.sort_order},
    )
    db.commit()
    db.refresh(row)
    return _build_taxonomy_node_row(row)


@router.delete("/{tool_id}/features/taxonomy-nodes/{node_id}", response_model=DataSecureTaxonomyNodeDeleteResult)
async def delete_taxonomy_node(
    tool_id: int,
    node_id: int,
    change_reason: str = Query(..., min_length=5, max_length=1000),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    _ensure_data_secure_manage_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    ensure_manage_permission(db, current_user, tool_id)
    reason = _normalize_change_reason(change_reason)
    row = db.get(DataSecureTaxonomyNode, node_id)
    if not row or row.tool_id != tool_id:
        raise HTTPException(status_code=404, detail="分类节点不存在")
    child_exists = db.exec(
        select(DataSecureTaxonomyNode.id).where(DataSecureTaxonomyNode.parent_id == node_id).limit(1)
    ).first()
    if child_exists is not None:
        raise HTTPException(status_code=400, detail="当前节点存在子节点，请先处理子节点后再删除")
    bind_count = db.exec(
        select(func.count())
        .select_from(DataSecureFieldClassGrade)
        .where(
            DataSecureFieldClassGrade.tool_id == tool_id,
            DataSecureFieldClassGrade.project_space_id == int(row.project_space_id),
            or_(
                DataSecureFieldClassGrade.taxonomy_l1_id == node_id,
                DataSecureFieldClassGrade.taxonomy_l2_id == node_id,
            ),
        )
    ).one()
    if int(bind_count or 0) > 0:
        raise HTTPException(status_code=400, detail="当前节点已被密级绑定引用，请先解除绑定后再删除")
    target_id = row.node_key
    project_space_id = int(row.project_space_id)
    name = row.name
    db.delete(row)
    _append_governance_change_log(
        db,
        tool_id=tool_id,
        project_space_id=project_space_id,
        domain="taxonomy",
        action="delete",
        target_type="taxonomy_node",
        target_id=target_id,
        change_reason=reason,
        changed_by=current_user.id,
        detail={"node_id": node_id, "name": name},
    )
    db.commit()
    return DataSecureTaxonomyNodeDeleteResult()


@router.get("/{tool_id}/features/field-class-grade", response_model=PaginatedDataSecureFieldClassGrades)
async def list_field_class_grades(
    tool_id: int,
    project_space_id: int,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    _ensure_data_secure_manage_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    where = [
        DataSecureFieldClassGrade.tool_id == tool_id,
        DataSecureFieldClassGrade.project_space_id == project_space_id,
    ]
    total = db.exec(select(func.count()).select_from(DataSecureFieldClassGrade).where(*where)).one()
    rows = db.exec(
        select(DataSecureFieldClassGrade)
        .where(*where)
        .order_by(DataSecureFieldClassGrade.updated_at.desc())
        .offset(skip)
        .limit(limit)
    ).all()
    entry_ids = [int(r.catalog_entry_id) for r in rows]
    entries: dict[int, DataSecureFieldCatalogEntry] = {}
    if entry_ids:
        erows = db.exec(
            select(DataSecureFieldCatalogEntry).where(DataSecureFieldCatalogEntry.id.in_(entry_ids))
        ).all()
        entries = {int(e.id): e for e in erows}
    items = [_build_class_grade_row(db, r, entries.get(int(r.catalog_entry_id))) for r in rows]
    return PaginatedDataSecureFieldClassGrades(total=int(total or 0), items=items)


@router.put("/{tool_id}/features/field-class-grade", response_model=DataSecureFieldClassGradeInDB)
async def upsert_field_class_grade(
    tool_id: int,
    body: DataSecureFieldClassGradeUpsert,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    _ensure_data_secure_manage_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    ensure_manage_permission(db, current_user, tool_id)
    reason = _normalize_change_reason(body.change_reason)
    space = db.get(DataSecureProjectSpace, body.project_space_id)
    if not space or space.tool_id != tool_id:
        raise HTTPException(status_code=404, detail="项目空间不存在")
    entry = db.get(DataSecureFieldCatalogEntry, body.catalog_entry_id)
    if not entry or entry.tool_id != tool_id or entry.project_space_id != body.project_space_id:
        raise HTTPException(status_code=404, detail="数据字段主表记录不存在")
    grade = ds_struct.normalize_confidentiality_grade(body.confidentiality_grade)
    l1_id, l2_id = _resolve_class_grade_taxonomy_ids(
        db, tool_id, body.project_space_id, body.taxonomy_l1_id, body.taxonomy_l2_id
    )
    now = datetime.utcnow()
    existing = db.exec(
        select(DataSecureFieldClassGrade).where(DataSecureFieldClassGrade.catalog_entry_id == int(entry.id))
    ).first()
    if existing:
        existing.taxonomy_l1_id = l1_id
        existing.taxonomy_l2_id = l2_id
        existing.confidentiality_grade = grade
        existing.notes = body.notes
        existing.updated_by = current_user.id
        existing.updated_at = now
        db.add(existing)
        _sync_structured_to_classification_result(
            db, tool_id, body.project_space_id, entry, existing, current_user.id
        )
        _append_governance_change_log(
            db,
            tool_id=tool_id,
            project_space_id=body.project_space_id,
            domain="field_class_grade",
            action="update",
            target_type="catalog_entry",
            target_id=str(entry.id),
            change_reason=reason,
            changed_by=current_user.id,
            detail={"field_name": entry.field_name, "grade": grade, "taxonomy_l1_id": l1_id, "taxonomy_l2_id": l2_id},
        )
        db.commit()
        db.refresh(existing)
        return _build_class_grade_row(db, existing, entry)
    row = DataSecureFieldClassGrade(
        tool_id=tool_id,
        project_space_id=body.project_space_id,
        catalog_entry_id=int(entry.id),
        taxonomy_l1_id=l1_id,
        taxonomy_l2_id=l2_id,
        confidentiality_grade=grade,
        notes=body.notes,
        created_by=current_user.id,
        updated_by=current_user.id,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.flush()
    _sync_structured_to_classification_result(db, tool_id, body.project_space_id, entry, row, current_user.id)
    _append_governance_change_log(
        db,
        tool_id=tool_id,
        project_space_id=body.project_space_id,
        domain="field_class_grade",
        action="create",
        target_type="catalog_entry",
        target_id=str(entry.id),
        change_reason=reason,
        changed_by=current_user.id,
        detail={"field_name": entry.field_name, "grade": grade, "taxonomy_l1_id": l1_id, "taxonomy_l2_id": l2_id},
    )
    db.commit()
    db.refresh(row)
    return _build_class_grade_row(db, row, entry)


@router.delete("/{tool_id}/features/field-class-grade/{catalog_entry_id}")
async def delete_field_class_grade(
    tool_id: int,
    catalog_entry_id: int,
    change_reason: str = Query(..., min_length=5, max_length=1000),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    _ensure_data_secure_manage_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    ensure_manage_permission(db, current_user, tool_id)
    reason = _normalize_change_reason(change_reason)
    row = db.exec(
        select(DataSecureFieldClassGrade).where(DataSecureFieldClassGrade.catalog_entry_id == catalog_entry_id)
    ).first()
    if not row or row.tool_id != tool_id:
        raise HTTPException(status_code=404, detail="分类分级和要求治理中未找到该字段的分级记录")
    entry = db.get(DataSecureFieldCatalogEntry, catalog_entry_id)
    row_space_id = int(row.project_space_id)
    db.delete(row)
    _append_governance_change_log(
        db,
        tool_id=tool_id,
        project_space_id=row_space_id,
        domain="field_class_grade",
        action="delete",
        target_type="catalog_entry",
        target_id=str(catalog_entry_id),
        change_reason=reason,
        changed_by=current_user.id,
        detail={"field_name": entry.field_name if entry else None},
    )
    db.commit()
    if entry and entry.tool_id == tool_id:
        _upsert_classification_for_entry(db, tool_id, row_space_id, entry, current_user.id)
        db.commit()
    return {"ok": True}


@router.get("/{tool_id}/features/field-security-requirements", response_model=PaginatedDataSecureFieldSecurityRequirements)
async def list_field_security_requirements(
    tool_id: int,
    project_space_id: int,
    catalog_entry_id: int | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    _ensure_data_secure_manage_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    where = [
        DataSecureFieldSecurityRequirement.tool_id == tool_id,
        DataSecureFieldSecurityRequirement.project_space_id == project_space_id,
    ]
    if catalog_entry_id is not None:
        where.append(DataSecureFieldSecurityRequirement.catalog_entry_id == int(catalog_entry_id))
    total = db.exec(select(func.count()).select_from(DataSecureFieldSecurityRequirement).where(*where)).one()
    rows = db.exec(
        select(DataSecureFieldSecurityRequirement)
        .where(*where)
        .order_by(DataSecureFieldSecurityRequirement.priority.desc(), DataSecureFieldSecurityRequirement.sort_order, DataSecureFieldSecurityRequirement.id)
        .offset(skip)
        .limit(limit)
    ).all()
    entry_ids = list({int(r.catalog_entry_id) for r in rows})
    entries: dict[int, DataSecureFieldCatalogEntry] = {}
    if entry_ids:
        erows = db.exec(
            select(DataSecureFieldCatalogEntry).where(DataSecureFieldCatalogEntry.id.in_(entry_ids))
        ).all()
        entries = {int(e.id): e for e in erows}
    items = [_build_security_requirement_row(db, r, entries.get(int(r.catalog_entry_id))) for r in rows]
    return PaginatedDataSecureFieldSecurityRequirements(total=int(total or 0), items=items)


@router.post("/{tool_id}/features/field-security-requirements", response_model=DataSecureFieldSecurityRequirementInDB)
async def create_field_security_requirement(
    tool_id: int,
    body: DataSecureFieldSecurityRequirementCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    _ensure_data_secure_manage_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    ensure_manage_permission(db, current_user, tool_id)
    reason = _normalize_change_reason(body.change_reason)
    space = db.get(DataSecureProjectSpace, body.project_space_id)
    if not space or space.tool_id != tool_id:
        raise HTTPException(status_code=404, detail="项目空间不存在")
    entry = db.get(DataSecureFieldCatalogEntry, body.catalog_entry_id)
    if not entry or entry.tool_id != tool_id or entry.project_space_id != body.project_space_id:
        raise HTTPException(status_code=404, detail="数据字段主表记录不存在")
    pred = ds_struct.validate_predicate_map(body.predicate_map or {})
    keys = set(pred.keys())
    _validate_logic_expression(body.logic_expression.strip(), keys)
    now = datetime.utcnow()
    row = DataSecureFieldSecurityRequirement(
        tool_id=tool_id,
        project_space_id=body.project_space_id,
        catalog_entry_id=int(entry.id),
        requirement_text=body.requirement_text.strip(),
        logic_expression=body.logic_expression.strip(),
        predicate_map_json=ds_struct.predicate_map_to_json(pred),
        priority=body.priority,
        sort_order=body.sort_order,
        is_active=True,
        created_by=current_user.id,
        updated_by=current_user.id,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    _append_governance_change_log(
        db,
        tool_id=tool_id,
        project_space_id=body.project_space_id,
        domain="security_requirement",
        action="create",
        target_type="requirement",
        target_id=f"catalog:{entry.id}",
        change_reason=reason,
        changed_by=current_user.id,
        detail={"catalog_entry_id": int(entry.id), "logic_expression": body.logic_expression.strip()},
    )
    db.commit()
    db.refresh(row)
    return _build_security_requirement_row(db, row, entry)


@router.put("/{tool_id}/features/field-security-requirements/{requirement_id}", response_model=DataSecureFieldSecurityRequirementInDB)
async def update_field_security_requirement(
    tool_id: int,
    requirement_id: int,
    body: DataSecureFieldSecurityRequirementUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    _ensure_data_secure_manage_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    ensure_manage_permission(db, current_user, tool_id)
    reason = _normalize_change_reason(body.change_reason)
    row = db.get(DataSecureFieldSecurityRequirement, requirement_id)
    if not row or row.tool_id != tool_id:
        raise HTTPException(status_code=404, detail="安全要求记录不存在")
    entry = db.get(DataSecureFieldCatalogEntry, row.catalog_entry_id)
    pred_existing = ds_struct.parse_predicate_map(row.predicate_map_json)
    if body.predicate_map is not None:
        pred_existing = ds_struct.validate_predicate_map(body.predicate_map)
        row.predicate_map_json = ds_struct.predicate_map_to_json(pred_existing)
    if body.logic_expression is not None:
        row.logic_expression = body.logic_expression.strip()
    keys = set(ds_struct.parse_predicate_map(row.predicate_map_json).keys())
    _validate_logic_expression((row.logic_expression or "").strip(), keys)
    if body.requirement_text is not None:
        row.requirement_text = body.requirement_text.strip()
    if body.priority is not None:
        row.priority = body.priority
    if body.sort_order is not None:
        row.sort_order = body.sort_order
    if body.is_active is not None:
        row.is_active = body.is_active
    row.updated_by = current_user.id
    row.updated_at = datetime.utcnow()
    db.add(row)
    _append_governance_change_log(
        db,
        tool_id=tool_id,
        project_space_id=row.project_space_id,
        domain="security_requirement",
        action="update",
        target_type="requirement",
        target_id=str(requirement_id),
        change_reason=reason,
        changed_by=current_user.id,
        detail={"catalog_entry_id": int(row.catalog_entry_id), "is_active": row.is_active, "priority": row.priority},
    )
    db.commit()
    db.refresh(row)
    return _build_security_requirement_row(db, row, entry)


@router.delete("/{tool_id}/features/field-security-requirements/{requirement_id}", response_model=DataSecureFieldSecurityRequirementDeleteResult)
async def delete_field_security_requirement(
    tool_id: int,
    requirement_id: int,
    change_reason: str = Query(..., min_length=5, max_length=1000),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    _ensure_data_secure_manage_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    ensure_manage_permission(db, current_user, tool_id)
    reason = _normalize_change_reason(change_reason)
    row = db.get(DataSecureFieldSecurityRequirement, requirement_id)
    if not row or row.tool_id != tool_id:
        raise HTTPException(status_code=404, detail="安全要求记录不存在")
    project_space_id = int(row.project_space_id)
    catalog_entry_id = int(row.catalog_entry_id)
    db.delete(row)
    _append_governance_change_log(
        db,
        tool_id=tool_id,
        project_space_id=project_space_id,
        domain="security_requirement",
        action="delete",
        target_type="requirement",
        target_id=str(requirement_id),
        change_reason=reason,
        changed_by=current_user.id,
        detail={"catalog_entry_id": catalog_entry_id},
    )
    db.commit()
    return DataSecureFieldSecurityRequirementDeleteResult()


@router.post("/{tool_id}/features/field-security-requirements-eval", response_model=DataSecureFieldSecurityRequirementEvalResponse)
async def eval_field_security_requirements(
    tool_id: int,
    body: DataSecureFieldSecurityRequirementEvalRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    tool = get_tool_or_404(db, tool_id)
    _ensure_data_secure_manage_tool(tool)
    _ensure_tool_feature_access(db, current_user, tool)
    entry = db.get(DataSecureFieldCatalogEntry, body.catalog_entry_id)
    if not entry or entry.tool_id != tool_id or entry.project_space_id != body.project_space_id:
        raise HTTPException(status_code=404, detail="数据字段主表记录不存在")
    cg = db.exec(
        select(DataSecureFieldClassGrade).where(DataSecureFieldClassGrade.catalog_entry_id == int(entry.id))
    ).first()
    l1, l2 = (None, None)
    grade_label = ""
    path_keys: set[str] = set()
    if cg:
        l1, l2 = ds_struct.load_taxonomy_nodes_for_grade(db, cg)
        grade_label = cg.confidentiality_grade or ""
        path_keys = ds_struct.taxonomy_path_node_keys_for_grade(db, cg)
    lifecycle_map = ds_dynamic_fields.load_catalog_extra_fields(db, int(entry.id))
    lifecycle_map["field_name"] = entry.field_name
    cat_path = ds_struct.display_category_path_for_grade(db, cg, entry.field_name) if cg else entry.field_name
    reqs = db.exec(
        select(DataSecureFieldSecurityRequirement)
        .where(
            DataSecureFieldSecurityRequirement.tool_id == tool_id,
            DataSecureFieldSecurityRequirement.project_space_id == body.project_space_id,
            DataSecureFieldSecurityRequirement.catalog_entry_id == int(entry.id),
            DataSecureFieldSecurityRequirement.is_active == True,  # noqa: E712
        )
        .order_by(DataSecureFieldSecurityRequirement.priority.desc(), DataSecureFieldSecurityRequirement.sort_order)
    ).all()
    hits: list[DataSecureFieldSecurityRequirementEvalHit] = []
    for req in reqs:
        pmap = ds_struct.parse_predicate_map(req.predicate_map_json)
        pmap = ds_struct.validate_predicate_map(pmap)
        truth = ds_struct.build_predicate_truth(
            class_grade=cg,
            l1=l1,
            l2=l2,
            predicate_map=pmap,
            lifecycle_fields=lifecycle_map,
            taxonomy_path_node_keys=path_keys,
        )
        keys = set(truth.keys())
        _validate_logic_expression(req.logic_expression.strip(), keys)
        matched = _eval_logic_expression(req.logic_expression.strip(), keys, truth)
        hits.append(
            DataSecureFieldSecurityRequirementEvalHit(
                requirement_id=int(req.id),
                requirement_text=req.requirement_text,
                logic_expression=req.logic_expression,
                matched=matched,
            )
        )
    return DataSecureFieldSecurityRequirementEvalResponse(
        catalog_entry_id=int(entry.id),
        field_name=entry.field_name,
        confidentiality_grade=grade_label,
        category_path=cat_path,
        hits=hits,
    )
