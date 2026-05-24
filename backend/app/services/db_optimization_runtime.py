"""Shared helpers for DB pool tuning overrides (used by host admin + tools)."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from urllib.parse import urlparse

from fastapi import HTTPException
from sqlmodel import Session, select

from app.core.config_simple import BACKEND_ROOT, DATABASE_URL
from app.schemas import MosDbOptimizationUpdateRequest


_DB_OPTIMIZATION_FILE = Path(BACKEND_ROOT) / "runtime" / "db_optimization.json"


def db_optimization_overrides_path() -> Path:
    return _DB_OPTIMIZATION_FILE


def mask_database_url(raw: str) -> str:
    text = (raw or "").strip()
    if not text:
        return ""
    parsed = urlparse(text)
    if parsed.password:
        return text.replace(f":{parsed.password}@", ":***@")
    return text


def is_remote_database_url(raw: str) -> bool:
    parsed = urlparse((raw or "").strip())
    host = (parsed.hostname or "").lower()
    return bool(host and host not in {"localhost", "127.0.0.1", "::1"})


def load_db_optimization_overrides() -> dict[str, int]:
    if not _DB_OPTIMIZATION_FILE.exists():
        return {}
    try:
        raw = json.loads(_DB_OPTIMIZATION_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(raw, dict):
        return {}
    result: dict[str, int] = {}
    for key in (
        "pool_size",
        "max_overflow",
        "pool_timeout_seconds",
        "pool_recycle_seconds",
        "workers",
        "statement_timeout_ms",
    ):
        value = raw.get(key)
        if isinstance(value, int):
            result[key] = value
    return result


def save_db_optimization_overrides(data: dict[str, int]) -> None:
    _DB_OPTIMIZATION_FILE.parent.mkdir(parents=True, exist_ok=True)
    _DB_OPTIMIZATION_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def upsert_env_lines(env_path: Path, updates: dict[str, int]) -> None:
    rows: list[str] = []
    if env_path.exists():
        rows = env_path.read_text(encoding="utf-8").splitlines()
    for key, value in updates.items():
        line = f"{key}={value}"
        found = False
        for idx, existing in enumerate(rows):
            if existing.strip().startswith(f"{key}="):
                rows[idx] = line
                found = True
                break
        if not found:
            rows.append(line)
    payload = "\n".join(rows).strip()
    env_path.write_text(payload + "\n", encoding="utf-8")


def current_pool_env_snapshot() -> dict[str, int]:
    return {
        "SQLALCHEMY_POOL_SIZE": int(os.getenv("SQLALCHEMY_POOL_SIZE", "4")),
        "SQLALCHEMY_MAX_OVERFLOW": int(os.getenv("SQLALCHEMY_MAX_OVERFLOW", "2")),
        "SQLALCHEMY_POOL_TIMEOUT": int(os.getenv("SQLALCHEMY_POOL_TIMEOUT", "30")),
        "SQLALCHEMY_POOL_RECYCLE": int(os.getenv("SQLALCHEMY_POOL_RECYCLE", "1800")),
        "TOOLBOX_WORKERS": int(os.getenv("TOOLBOX_WORKERS", "2")),
        "SQLALCHEMY_STATEMENT_TIMEOUT_MS": int(os.getenv("SQLALCHEMY_STATEMENT_TIMEOUT_MS", "15000")),
    }


def recommendation_from_env(env_current: dict[str, int]) -> dict[str, int]:
    return {
        "pool_size": max(4, env_current["SQLALCHEMY_POOL_SIZE"]),
        "max_overflow": max(2, env_current["SQLALCHEMY_MAX_OVERFLOW"]),
        "pool_timeout_seconds": max(30, env_current["SQLALCHEMY_POOL_TIMEOUT"]),
        "pool_recycle_seconds": max(1800, env_current["SQLALCHEMY_POOL_RECYCLE"]),
        "workers": max(2, env_current["TOOLBOX_WORKERS"]),
        "statement_timeout_ms": max(15000, env_current["SQLALCHEMY_STATEMENT_TIMEOUT_MS"]),
    }


def build_db_optimization_read_payload(
    *,
    database_url: str | None = None,
    note: str,
) -> dict:
    url = (database_url or DATABASE_URL or "").strip()
    overrides = load_db_optimization_overrides()
    env_current = current_pool_env_snapshot()
    return {
        "database_url_masked": mask_database_url(url),
        "is_remote_database": is_remote_database_url(url),
        "current_env": env_current,
        "saved_overrides": overrides,
        "recommendation": recommendation_from_env(env_current),
        "requires_restart": True,
        "note": note,
    }


def apply_db_optimization_update(
    body: MosDbOptimizationUpdateRequest,
    *,
    env_file: Path | None = None,
) -> dict:
    updates: dict[str, int] = {}
    if body.pool_size is not None:
        updates["pool_size"] = body.pool_size
    if body.max_overflow is not None:
        updates["max_overflow"] = body.max_overflow
    if body.pool_timeout_seconds is not None:
        updates["pool_timeout_seconds"] = body.pool_timeout_seconds
    if body.pool_recycle_seconds is not None:
        updates["pool_recycle_seconds"] = body.pool_recycle_seconds
    if body.workers is not None:
        updates["workers"] = body.workers
    if body.statement_timeout_ms is not None:
        updates["statement_timeout_ms"] = body.statement_timeout_ms
    if not updates:
        raise HTTPException(status_code=400, detail="至少提交一项数据库优化参数")

    saved = load_db_optimization_overrides()
    saved.update(updates)
    save_db_optimization_overrides(saved)

    if body.apply_to_env:
        effective = {
            "pool_size": int(saved.get("pool_size", os.getenv("SQLALCHEMY_POOL_SIZE", "4"))),
            "max_overflow": int(saved.get("max_overflow", os.getenv("SQLALCHEMY_MAX_OVERFLOW", "2"))),
            "pool_timeout_seconds": int(saved.get("pool_timeout_seconds", os.getenv("SQLALCHEMY_POOL_TIMEOUT", "30"))),
            "pool_recycle_seconds": int(saved.get("pool_recycle_seconds", os.getenv("SQLALCHEMY_POOL_RECYCLE", "1800"))),
            "workers": int(saved.get("workers", os.getenv("TOOLBOX_WORKERS", "2"))),
            "statement_timeout_ms": int(saved.get("statement_timeout_ms", os.getenv("SQLALCHEMY_STATEMENT_TIMEOUT_MS", "15000"))),
        }
        env_updates = {
            "SQLALCHEMY_POOL_SIZE": effective["pool_size"],
            "SQLALCHEMY_MAX_OVERFLOW": effective["max_overflow"],
            "SQLALCHEMY_POOL_TIMEOUT": effective["pool_timeout_seconds"],
            "SQLALCHEMY_POOL_RECYCLE": effective["pool_recycle_seconds"],
            "TOOLBOX_WORKERS": effective["workers"],
            "SQLALCHEMY_STATEMENT_TIMEOUT_MS": effective["statement_timeout_ms"],
        }
        upsert_env_lines(env_file or (Path(BACKEND_ROOT) / ".env"), env_updates)

    return {
        "saved_overrides": saved,
        "applied_to_env": body.apply_to_env,
        "requires_restart": True,
    }


def ping_database_ms(db: Session) -> int:
    started = time.perf_counter()
    db.exec(select(1)).first()
    return int((time.perf_counter() - started) * 1000)
