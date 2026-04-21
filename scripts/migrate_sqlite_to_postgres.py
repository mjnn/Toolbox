#!/usr/bin/env python3
"""
将 SQLite 备份（如 ref/app.db）中的业务数据导入当前 DATABASE_URL 指向的 PostgreSQL。

用法（在仓库根目录）：
  backend\\.venv\\Scripts\\python.exe scripts/migrate_sqlite_to_postgres.py --sqlite ref/app.db

依赖 backend/.env 中的 DATABASE_URL=postgresql+psycopg2://...

说明：会先 TRUNCATE 目标库中下列表并 RESTART IDENTITY，再按外键顺序从 SQLite 插入；
若仅想试跑连接与行数，可加 --dry-run。
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_BACKEND_ROOT = _REPO_ROOT / "backend"
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

os.chdir(_BACKEND_ROOT)
from dotenv import load_dotenv  # noqa: E402

load_dotenv(_BACKEND_ROOT / ".env")

import pandas as pd  # noqa: E402
from sqlalchemy import create_engine, inspect, text  # noqa: E402
from sqlalchemy.engine import Engine  # noqa: E402
from sqlalchemy.types import Boolean  # noqa: E402

from sqlmodel import SQLModel  # noqa: E402

# 注册元数据
from app import models  # noqa: F401, E402


def _is_sqlite(url: str) -> bool:
    return url.strip().lower().startswith("sqlite")


def _is_postgres(url: str) -> bool:
    u = url.strip().lower()
    return u.startswith("postgresql") or u.startswith("postgres://")


# 与 SQLite 备份中一致的表；按外键依赖顺序插入
_COPY_ORDER = [
    "role",
    "user",
    "tool",
    "userrole",
    "tool_release",
    "usertoolpermission",
    "notification",
    "toolowner",
    "feedback",
    "apiaccesslog",
    "serviceidregistryentry",
    "serviceidruleoption",
    "configchangelog",
    "toolannouncement",
]

# TRUNCATE 时需包含 PG 上可能存在但 SQLite 无数据的表
_TRUNCATE_EXTRA = ["mos_token_pool_entry"]


def _pg_ident(name: str) -> str:
    if name == "user":
        return '"user"'
    return name


def _align_booleans_for_pg(dst: Engine, table: str, df: pd.DataFrame) -> pd.DataFrame:
    """SQLite 用 0/1 存布尔；pandas 读入为 int，写入 PG 的 BOOLEAN 需转换。"""
    insp = inspect(dst)
    try:
        cols = insp.get_columns(table)
    except Exception:
        return df
    for col in cols:
        name = col.get("name")
        if not name or name not in df.columns:
            continue
        ctype = col.get("type")
        if isinstance(ctype, Boolean) or str(ctype).upper().startswith("BOOLEAN"):
            df[name] = df[name].fillna(0).astype(int).astype(bool)
    return df


def _sqlite_tables(sqlite_engine: Engine) -> set[str]:
    with sqlite_engine.connect() as c:
        rows = c.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")).fetchall()
    return {r[0] for r in rows}


def _truncate_postgres(dst: Engine, tables: list[str]) -> None:
    names = ", ".join(_pg_ident(t) for t in tables)
    with dst.connect() as conn:
        conn.execute(text(f"TRUNCATE TABLE {names} RESTART IDENTITY CASCADE"))
        conn.commit()


def _reset_sequences(dst: Engine, tables: list[str]) -> None:
    with dst.connect() as conn:
        for t in tables:
            ident = _pg_ident(t)
            try:
                conn.execute(
                    text(
                        f"SELECT setval("
                        f"pg_get_serial_sequence({repr('public.' + t)}, 'id'), "
                        f"(SELECT COALESCE(MAX(id), 1) FROM {ident}))"
                    )
                )
            except Exception:
                pass
        conn.commit()


def main() -> int:
    p = argparse.ArgumentParser(description="Migrate SQLite app.db data into PostgreSQL")
    p.add_argument(
        "--sqlite",
        type=Path,
        default=_REPO_ROOT / "ref" / "app.db",
        help="Path to SQLite file (default: ref/app.db)",
    )
    p.add_argument("--dry-run", action="store_true", help="Only print counts and exit")
    args = p.parse_args()

    pg_url = os.getenv("DATABASE_URL", "").strip()
    if not _is_postgres(pg_url):
        print("错误: DATABASE_URL 必须是 PostgreSQL（postgresql+psycopg2://...）", file=sys.stderr)
        return 1

    sqlite_path = args.sqlite.resolve()
    if not sqlite_path.is_file():
        print(f"错误: 找不到 SQLite 文件: {sqlite_path}", file=sys.stderr)
        return 1

    sqlite_url = f"sqlite:///{sqlite_path.as_posix()}"
    src = create_engine(sqlite_url, connect_args={"check_same_thread": False})
    dst = create_engine(pg_url, pool_pre_ping=True)

    sqlite_names = _sqlite_tables(src)
    print("SQLite 表:", sorted(sqlite_names))

    for t in _COPY_ORDER:
        if t not in sqlite_names:
            print(f"  (跳过，源库无表) {t}")
            continue
        n = pd.read_sql_query(f"SELECT COUNT(*) AS c FROM {t}", src)["c"].iloc[0]
        print(f"  {t}: {int(n)} 行")

    if args.dry_run:
        print("dry-run: 未写入 PostgreSQL")
        return 0

    SQLModel.metadata.create_all(dst)

    truncate_list = list(
        dict.fromkeys([*_TRUNCATE_EXTRA, *reversed(_COPY_ORDER)])
    )
    print("TRUNCATE:", ", ".join(truncate_list))
    _truncate_postgres(dst, truncate_list)

    for t in _COPY_ORDER:
        if t not in sqlite_names:
            continue
        df = pd.read_sql_query(f"SELECT * FROM {t}", src)
        if df.empty:
            continue
        df = _align_booleans_for_pg(dst, t, df)
        df.to_sql(t, dst, if_exists="append", index=False, method="multi")
        print(f"已导入 {t}: {len(df)} 行")

    _reset_sequences(dst, [t for t in _COPY_ORDER if t in sqlite_names])
    print("完成: 序列已按 MAX(id) 对齐")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
