"""项目空间级联删除（数据安全治理工具）。"""
from __future__ import annotations

from fastapi import HTTPException
from sqlmodel import Session, select

from app.models import (
    DataSecureAssessmentAnswer,
    DataSecureAssessmentSubmission,
    DataSecureBusinessFunctionOptionRequest,
    DataSecureFieldCatalogEntry,
    DataSecureFieldCatalogValue,
    DataSecureFieldClassGrade,
    DataSecureFieldClassificationAuditLog,
    DataSecureFieldClassificationMatrix,
    DataSecureFieldClassificationResult,
    DataSecureFieldClassificationRule,
    DataSecureFieldRequest,
    DataSecureFieldSecurityRequirement,
    DataSecureFieldUsageReport,
    DataSecureFieldUsageReportItem,
    DataSecureGovernanceChangeLog,
    DataSecureLifecycleFieldConfig,
    DataSecureLifecycleFieldDefinition,
    DataSecureProjectSpace,
    DataSecureQuestionnaireQuestion,
    DataSecureRelevanceRule,
    DataSecureTaxonomyNode,
)


def _delete_taxonomy_nodes_for_space(db: Session, tool_id: int, project_space_id: int) -> None:
    nodes = db.exec(
        select(DataSecureTaxonomyNode).where(
            DataSecureTaxonomyNode.tool_id == tool_id,
            DataSecureTaxonomyNode.project_space_id == project_space_id,
        )
    ).all()
    by_id: dict[int, DataSecureTaxonomyNode] = {}
    for n in nodes:
        if n.id is None:
            continue
        by_id[int(n.id)] = n
    remaining: set[int] = set(by_id.keys())
    while remaining:
        nodes_rem = [by_id[i] for i in remaining]
        parent_ids_that_have_children_in_remaining = {
            int(x.parent_id)
            for x in nodes_rem
            if x.parent_id is not None and int(x.parent_id) in remaining
        }
        leaves = remaining - parent_ids_that_have_children_in_remaining
        if not leaves:
            break
        for lid in leaves:
            db.delete(by_id[lid])
        remaining -= leaves
    db.flush()


def delete_project_space_cascade(db: Session, tool_id: int, project_space_id: int) -> None:
    """删除项目空间及其下全部业务数据与治理配置（不可逆）。"""
    space = db.get(DataSecureProjectSpace, project_space_id)
    if not space or int(space.tool_id) != int(tool_id):
        raise HTTPException(status_code=404, detail="项目空间不存在")

    sub_rows = db.exec(
        select(DataSecureAssessmentSubmission).where(
            DataSecureAssessmentSubmission.tool_id == tool_id,
            DataSecureAssessmentSubmission.project_space_id == project_space_id,
        )
    ).all()
    sub_ids = [int(s.id) for s in sub_rows if s.id is not None]
    if sub_ids:
        ans = db.exec(
            select(DataSecureAssessmentAnswer).where(DataSecureAssessmentAnswer.submission_id.in_(sub_ids))
        ).all()
        for a in ans:
            db.delete(a)
        db.flush()
    for s in sub_rows:
        db.delete(s)
    db.flush()

    rep_rows = db.exec(
        select(DataSecureFieldUsageReport).where(
            DataSecureFieldUsageReport.tool_id == tool_id,
            DataSecureFieldUsageReport.project_space_id == project_space_id,
        )
    ).all()
    rep_ids = [int(r.id) for r in rep_rows if r.id is not None]
    if rep_ids:
        items = db.exec(
            select(DataSecureFieldUsageReportItem).where(DataSecureFieldUsageReportItem.report_id.in_(rep_ids))
        ).all()
        for it in items:
            db.delete(it)
        db.flush()
    for r in rep_rows:
        db.delete(r)
    db.flush()

    audit_logs = db.exec(
        select(DataSecureFieldClassificationAuditLog).where(
            DataSecureFieldClassificationAuditLog.tool_id == tool_id,
            DataSecureFieldClassificationAuditLog.project_space_id == project_space_id,
        )
    ).all()
    for row in audit_logs:
        db.delete(row)
    db.flush()

    cls_results = db.exec(
        select(DataSecureFieldClassificationResult).where(
            DataSecureFieldClassificationResult.tool_id == tool_id,
            DataSecureFieldClassificationResult.project_space_id == project_space_id,
        )
    ).all()
    for row in cls_results:
        db.delete(row)
    db.flush()

    cg_rows = db.exec(
        select(DataSecureFieldClassGrade).where(
            DataSecureFieldClassGrade.tool_id == tool_id,
            DataSecureFieldClassGrade.project_space_id == project_space_id,
        )
    ).all()
    for row in cg_rows:
        db.delete(row)
    db.flush()

    sec_rows = db.exec(
        select(DataSecureFieldSecurityRequirement).where(
            DataSecureFieldSecurityRequirement.tool_id == tool_id,
            DataSecureFieldSecurityRequirement.project_space_id == project_space_id,
        )
    ).all()
    for row in sec_rows:
        db.delete(row)
    db.flush()

    entries = db.exec(
        select(DataSecureFieldCatalogEntry).where(
            DataSecureFieldCatalogEntry.tool_id == tool_id,
            DataSecureFieldCatalogEntry.project_space_id == project_space_id,
        )
    ).all()
    entry_ids = [int(e.id) for e in entries if e.id is not None]
    if entry_ids:
        vals = db.exec(
            select(DataSecureFieldCatalogValue).where(DataSecureFieldCatalogValue.entry_id.in_(entry_ids))
        ).all()
        for v in vals:
            db.delete(v)
        db.flush()
    for e in entries:
        db.delete(e)
    db.flush()

    rule_rows = db.exec(
        select(DataSecureFieldClassificationRule).where(
            DataSecureFieldClassificationRule.tool_id == tool_id,
            DataSecureFieldClassificationRule.project_space_id == project_space_id,
        )
    ).all()
    for row in rule_rows:
        db.delete(row)
    db.flush()

    matrix_rows = db.exec(
        select(DataSecureFieldClassificationMatrix).where(
            DataSecureFieldClassificationMatrix.tool_id == tool_id,
            DataSecureFieldClassificationMatrix.project_space_id == project_space_id,
        )
    ).all()
    for row in matrix_rows:
        db.delete(row)
    db.flush()

    q_rows = db.exec(
        select(DataSecureQuestionnaireQuestion).where(
            DataSecureQuestionnaireQuestion.tool_id == tool_id,
            DataSecureQuestionnaireQuestion.project_space_id == project_space_id,
        )
    ).all()
    for q in q_rows:
        db.delete(q)
    db.flush()

    rr = db.exec(
        select(DataSecureRelevanceRule).where(
            DataSecureRelevanceRule.tool_id == tool_id,
            DataSecureRelevanceRule.project_space_id == project_space_id,
        )
    ).all()
    for row in rr:
        db.delete(row)
    db.flush()

    _delete_taxonomy_nodes_for_space(db, tool_id, project_space_id)

    lfc_rows = db.exec(
        select(DataSecureLifecycleFieldConfig).where(
            DataSecureLifecycleFieldConfig.tool_id == tool_id,
            DataSecureLifecycleFieldConfig.project_space_id == project_space_id,
        )
    ).all()
    for row in lfc_rows:
        db.delete(row)
    db.flush()

    lfd_rows = db.exec(
        select(DataSecureLifecycleFieldDefinition).where(
            DataSecureLifecycleFieldDefinition.tool_id == tool_id,
            DataSecureLifecycleFieldDefinition.project_space_id == project_space_id,
        )
    ).all()
    for row in lfd_rows:
        db.delete(row)
    db.flush()

    fr_rows = db.exec(
        select(DataSecureFieldRequest).where(
            DataSecureFieldRequest.tool_id == tool_id,
            DataSecureFieldRequest.project_space_id == project_space_id,
        )
    ).all()
    for row in fr_rows:
        db.delete(row)
    db.flush()

    bfo_rows = db.exec(
        select(DataSecureBusinessFunctionOptionRequest).where(
            DataSecureBusinessFunctionOptionRequest.tool_id == tool_id,
            DataSecureBusinessFunctionOptionRequest.project_space_id == project_space_id,
        )
    ).all()
    for row in bfo_rows:
        db.delete(row)
    db.flush()

    gov_rows = db.exec(
        select(DataSecureGovernanceChangeLog).where(
            DataSecureGovernanceChangeLog.tool_id == tool_id,
            DataSecureGovernanceChangeLog.project_space_id == project_space_id,
        )
    ).all()
    for row in gov_rows:
        db.delete(row)
    db.flush()

    db.delete(space)
    db.commit()
