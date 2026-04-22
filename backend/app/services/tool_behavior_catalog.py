"""Resolve human-readable behavior labels from tool behavior catalogs (JSON on Tool)."""
from __future__ import annotations

import json
from typing import Optional

from app.models import Tool


def _humanize_feature_slug(feature_slug: str) -> str:
    """Fallback when no catalog entry matches."""
    return feature_slug.replace("-", " ").replace("/", " › ")


def resolve_behavior_label_from_catalog_json(catalog_json: str | None, feature_slug: str | None) -> str:
    if not feature_slug:
        return "—"
    if catalog_json:
        try:
            raw = json.loads(catalog_json)
        except (json.JSONDecodeError, TypeError):
            raw = []
        pairs: list[tuple[str, str]] = []
        if isinstance(raw, list):
            for item in raw:
                if not isinstance(item, dict):
                    continue
                key = str(item.get("key", "")).strip()
                label = str(item.get("label", "")).strip()
                if key and label:
                    pairs.append((key, label))
        pairs.sort(key=lambda p: len(p[0]), reverse=True)
        for key, label in pairs:
            if feature_slug == key or feature_slug.startswith(key + "/"):
                return label
    return _humanize_feature_slug(feature_slug)


def resolve_behavior_label_from_tool(tool: Optional[Tool], feature_slug: str | None) -> str:
    if not feature_slug:
        return "—"
    catalog = getattr(tool, "behavior_catalog_json", None) if tool else None
    return resolve_behavior_label_from_catalog_json(catalog, feature_slug)


def default_behavior_catalogs() -> dict[str, str]:
    """tool.name -> JSON string for built-in tools."""
    service_id = [
        {"key": "service-id-entries", "label": "服务 ID 条目（查询与维护）"},
        {"key": "service-id-rule-options", "label": "服务 ID 规则选项"},
        {"key": "service-id-export", "label": "导出服务 ID 全量"},
    ]
    mos = [
        {"key": "x509-cert", "label": "IAM X509（查询 / 签发 / CSR与证书解析）"},
        {"key": "sim-query", "label": "SIM 卡信息查询"},
        {"key": "uat-af-dp-query", "label": "UAT AF DP 数据查询"},
        {"key": "uat-sp-query", "label": "UAT SP 后台信息查询"},
        {"key": "uat-vehicle-import", "label": "UAT 车辆配置导入"},
        {"key": "uat-vehicle-config-generate", "label": "UAT 车辆配置规则生成"},
        {"key": "uat-vehicle-config-rules", "label": "UAT 车辆配置规则列表"},
        {"key": "announcement-feed", "label": "系统公告查看"},
        {"key": "mos-manage/announcements", "label": "MOS 管理：公告发布与维护"},
        {"key": "mos-manage/vehicle-rules/bulk-import", "label": "MOS 管理：车辆规则批量导入"},
        {"key": "mos-manage/vehicle-rules", "label": "MOS 管理：车辆规则"},
        {"key": "mos-manage/runtime-credentials", "label": "MOS 管理：运行环境凭据"},
        {"key": "mos-manage/db-optimization", "label": "MOS 管理：数据库优化配置"},
        {"key": "mos-manage/db-optimization/ping", "label": "MOS 管理：数据库连通性检测"},
        {"key": "mos-manage/change-logs", "label": "MOS 管理：配置变更记录"},
    ]
    rsa_livestream = [
        {"key": "livestream/config", "label": "RSA Token 直播配置查看"},
        {"key": "livestream/manage-config", "label": "RSA Token 直播配置管理"},
        {"key": "livestream/flv-proxy", "label": "RSA Token 直播内网转发播放"},
    ]
    return {
        "service-id-registry": json.dumps(service_id, ensure_ascii=False),
        "mos-integration-toolbox": json.dumps(mos, ensure_ascii=False),
        "rsa-token-livestream": json.dumps(rsa_livestream, ensure_ascii=False),
    }
