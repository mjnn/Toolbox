#!/usr/bin/env python3
"""Validate TOOLBOX_TOOL_UPSTREAMS coverage and upstream health."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple
from urllib import error, request

from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config_simple import DATABASE_URL  # noqa: E402


def parse_tool_upstreams(raw: str) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    for seg in (raw or "").split(","):
        item = seg.strip()
        if not item or "=" not in item:
            continue
        key, val = item.split("=", 1)
        tool_name = key.strip()
        base = val.strip().rstrip("/")
        if not tool_name or not base:
            continue
        if not (base.startswith("http://") or base.startswith("https://")):
            continue
        mapping[tool_name] = base
    return mapping


def load_tool_names() -> List[str]:
    engine = create_engine(DATABASE_URL, future=True)
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT name FROM tool ORDER BY id ASC")).all()
    return [str(r[0]) for r in rows if r and r[0]]


def probe_upstream(base_url: str, timeout_s: float = 4.0) -> Tuple[bool, str]:
    candidates = ["/health", "/api/v1/meta/version"]
    last_error = ""
    for path in candidates:
        url = f"{base_url}{path}"
        try:
            req = request.Request(url=url, method="GET")
            with request.urlopen(req, timeout=timeout_s) as resp:
                code = int(resp.getcode() or 0)
        except error.URLError as exc:
            last_error = f"{path}: {exc}"
            continue
        if code < 500:
            return True, f"{path} -> HTTP {code}"
        last_error = f"{path} -> HTTP {code}"
    return False, last_error or "no endpoint reachable"


def main() -> int:
    raw = (os.getenv("TOOLBOX_TOOL_UPSTREAMS") or "").strip()
    mapping = parse_tool_upstreams(raw)
    if not mapping:
        print("ERROR: TOOLBOX_TOOL_UPSTREAMS 未配置或格式无效", file=sys.stderr)
        return 2

    tool_names = load_tool_names()
    if not tool_names:
        print("WARN: 数据库中未找到 tool 记录")
        return 0

    missing = [name for name in tool_names if name not in mapping]
    extra = [name for name in sorted(mapping.keys()) if name not in set(tool_names)]

    unhealthy: List[Tuple[str, str, str]] = []
    for name in tool_names:
        upstream = mapping.get(name)
        if not upstream:
            continue
        ok, detail = probe_upstream(upstream)
        if not ok:
            unhealthy.append((name, upstream, detail))

    print("=== TOOLBOX_TOOL_UPSTREAMS 覆盖检查 ===")
    print(f"DB tool count: {len(tool_names)}")
    print(f"Upstream mapping count: {len(mapping)}")

    if missing:
        print("\n[缺失映射]")
        for name in missing:
            print(f"- {name}")
    else:
        print("\n[缺失映射] 无")

    if extra:
        print("\n[多余映射（DB 不存在）]")
        for name in extra:
            print(f"- {name} -> {mapping[name]}")
    else:
        print("\n[多余映射] 无")

    if unhealthy:
        print("\n[上游健康检查失败]")
        for name, upstream, detail in unhealthy:
            print(f"- {name} -> {upstream} ({detail})")
    else:
        print("\n[上游健康检查] 全部通过")

    if missing or unhealthy:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
