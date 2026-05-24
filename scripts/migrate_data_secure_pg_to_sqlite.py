#!/usr/bin/env python3
"""
Copy PostgreSQL (RDS) tables for the data-secure governance feature into a local SQLite file.

This script is intended to run on a machine that can reach the RDS instance (VPN / allowlist).
It does not ship credentials; pass --pg-url or set DSMS_PG_SOURCE_URL / DATABASE_URL.

Copies:
  - All public tables whose name starts with 'datasecure' (case-insensitive).
  - The subset of `tool` rows referenced by those tables (via tool_id), so FK-like
    references remain consistent for offline inspection.

Does NOT copy `user` by default (many FK columns point at user.id). Add --include-users
to also copy every `user` row referenced by collected user id columns on DataSecure tables.

Dependencies (same as backend): sqlalchemy, pandas, psycopg2-binary.
  Example: backend\\.venv\\Scripts\\pip install -r backend\\requirements.txt

Usage:
  python scripts/migrate_data_secure_pg_to_sqlite.py ^
    --pg-url "postgresql+psycopg2://user:pass@host:5432/dbname" ^
    --out ref/Data_Secure_Management_System(DSMS)/data/data_secure_from_rds.sqlite ^
    --tool-name data-secure-manage
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    env_path = REPO_ROOT / "backend" / ".env"
    if env_path.is_file():
        load_dotenv(env_path)


def _discover_datasecure_tables(src_engine) -> list[str]:
    from sqlalchemy import inspect

    insp = inspect(src_engine)
    names = [t for t in insp.get_table_names(schema="public") if t.lower().startswith("datasecure")]
    return sorted(names)


def _table_has_column(src_engine, table: str, col: str) -> bool:
    from sqlalchemy import inspect

    insp = inspect(src_engine)
    try:
        cols = {c["name"].lower() for c in insp.get_columns(table, schema="public")}
    except Exception:
        return False
    return col.lower() in cols


def _collect_tool_ids(src_engine, tables: list[str], tool_name: str | None) -> list[int]:
    from sqlalchemy import text

    if tool_name:
        with src_engine.connect() as conn:
            rows = conn.execute(
                text("SELECT id FROM tool WHERE name = :n"), {"n": tool_name}
            ).fetchall()
            return [int(r[0]) for r in rows]

    parts: list[str] = []
    for t in tables:
        if not _table_has_column(src_engine, t, "tool_id"):
            continue
        parts.append(f'SELECT tool_id FROM "{t}" WHERE tool_id IS NOT NULL')
    if not parts:
        return []
    sql = "SELECT DISTINCT tool_id FROM (" + " UNION ALL ".join(parts) + ") u WHERE tool_id IS NOT NULL"
    with src_engine.connect() as conn:
        rows = conn.execute(text(sql)).fetchall()
    return sorted({int(r[0]) for r in rows})


def _copy_tool_rows(src_engine, dst_engine, tool_ids: list[int]) -> int:
    import pandas as pd
    from sqlalchemy import text

    if not tool_ids:
        return 0
    ids_csv = ",".join(str(i) for i in tool_ids)
    df = pd.read_sql_query(text(f"SELECT * FROM tool WHERE id IN ({ids_csv})"), src_engine)
    df.to_sql("tool", dst_engine, if_exists="replace", index=False)
    return len(df)


def _collect_user_ids(src_engine, tables: list[str]) -> set[int]:
    """Best-effort: distinct integers in columns that typically reference user.id."""
    from sqlalchemy import inspect, text

    candidate_suffixes = ("_by",)
    exact = {"submitted_by", "requested_by", "reviewed_by", "changed_by", "user_id"}
    ids: set[int] = set()
    insp = inspect(src_engine)
    for t in tables:
        try:
            cols = [c["name"] for c in insp.get_columns(t, schema="public")]
        except Exception:
            continue
        for col in cols:
            if col in exact or col.endswith(candidate_suffixes):
                q = text(f'SELECT DISTINCT "{col}" AS uid FROM "{t}" WHERE "{col}" IS NOT NULL')
                try:
                    with src_engine.connect() as conn:
                        for row in conn.execute(q):
                            if row[0] is not None:
                                ids.add(int(row[0]))
                except Exception:
                    # Quoted identifiers differ on some PG configs; try unquoted lowercase
                    q2 = text(f"SELECT DISTINCT {col} AS uid FROM {t} WHERE {col} IS NOT NULL")
                    try:
                        with src_engine.connect() as conn:
                            for row in conn.execute(q2):
                                if row[0] is not None:
                                    ids.add(int(row[0]))
                    except Exception:
                        continue
    return ids


def _copy_user_rows(src_engine, dst_engine, user_ids: set[int]) -> int:
    import pandas as pd
    from sqlalchemy import text

    if not user_ids:
        return 0
    ids_csv = ",".join(str(i) for i in sorted(user_ids))
    df = pd.read_sql_query(text(f"SELECT * FROM \"user\" WHERE id IN ({ids_csv})"), src_engine)
    if df.empty:
        df = pd.read_sql_query(text(f"SELECT * FROM user WHERE id IN ({ids_csv})"), src_engine)
    # SQLite reserved name: quote as "user" when writing
    df.to_sql("user", dst_engine, if_exists="replace", index=False)
    return len(df)


def _copy_table(src_engine, dst_engine, table: str, where_sql: str | None) -> int:
    import pandas as pd
    from sqlalchemy import text

    q = f'SELECT * FROM "{table}"' if where_sql is None else f'SELECT * FROM "{table}" WHERE {where_sql}'
    try:
        df = pd.read_sql_query(text(q), src_engine)
    except Exception:
        q = f"SELECT * FROM {table}" if where_sql is None else f"SELECT * FROM {table} WHERE {where_sql}"
        df = pd.read_sql_query(text(q), src_engine)
    if df.empty:
        df.to_sql(table, dst_engine, if_exists="replace", index=False)
        return 0
    chunksize = 5000
    if len(df) <= chunksize:
        df.to_sql(table, dst_engine, if_exists="replace", index=False)
        return len(df)
    first = True
    total = 0
    for start in range(0, len(df), chunksize):
        part = df.iloc[start : start + chunksize]
        part.to_sql(table, dst_engine, if_exists="replace" if first else "append", index=False)
        first = False
        total += len(part)
    return total


def main() -> int:
    _load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pg-url",
        default=os.environ.get("DSMS_PG_SOURCE_URL") or os.environ.get("DATABASE_URL"),
        help="PostgreSQL URL, e.g. postgresql+psycopg2://user:pass@host:5432/dbname",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=REPO_ROOT
        / "ref"
        / "Data_Secure_Management_System(DSMS)"
        / "data"
        / "data_secure_from_rds.sqlite",
        help="Output SQLite file path",
    )
    parser.add_argument(
        "--tool-name",
        default=None,
        help="If set, only copy DataSecure rows where tool_id belongs to tool.name = this value",
    )
    parser.add_argument(
        "--include-users",
        action="store_true",
        help="Also copy `user` rows referenced by DataSecure tables (best-effort column scan)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only print discovered tables and tool id count; do not write SQLite",
    )
    args = parser.parse_args()
    if not args.pg_url or not str(args.pg_url).strip().startswith("postgres"):
        print(
            "ERROR: Provide a PostgreSQL URL via --pg-url or env DSMS_PG_SOURCE_URL / DATABASE_URL.",
            file=sys.stderr,
        )
        return 2

    try:
        from sqlalchemy import create_engine
    except ImportError as e:
        print("ERROR: sqlalchemy required.", e, file=sys.stderr)
        return 2

    src_url = str(args.pg_url).strip()
    if src_url.startswith("postgres://"):
        src_url = "postgresql+psycopg2://" + src_url[len("postgres://") :]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    if args.out.exists():
        args.out.unlink()

    src_engine = create_engine(src_url, pool_pre_ping=True)
    dst_engine = create_engine(f"sqlite:///{args.out.as_posix()}", future=True)

    tables = _discover_datasecure_tables(src_engine)
    if not tables:
        print("No tables found matching datasecure* in public schema.", file=sys.stderr)
        return 1

    tool_ids = _collect_tool_ids(src_engine, tables, args.tool_name)
    if args.tool_name and not tool_ids:
        print(f"No tool.id found for name={args.tool_name!r}", file=sys.stderr)
        return 1

    where_tool = None
    if args.tool_name:
        ids_csv = ",".join(str(i) for i in tool_ids)
        where_tool = f"tool_id IN ({ids_csv})"

    print(f"Discovered {len(tables)} DataSecure tables.")
    print("Tables:", ", ".join(tables))
    print(f"Tool rows to copy: {len(tool_ids)} (filter name={args.tool_name!r})")

    if args.dry_run:
        return 0

    n_tool = _copy_tool_rows(src_engine, dst_engine, tool_ids)
    print(f"Copied tool rows: {n_tool}")

    if args.include_users:
        uids = _collect_user_ids(src_engine, tables)
        nu = _copy_user_rows(src_engine, dst_engine, uids)
        print(f"Copied user rows (referenced): {nu} (distinct ids={len(uids)})")

    total_rows = 0
    for t in tables:
        where = where_tool if (where_tool and _table_has_column(src_engine, t, "tool_id")) else None
        n = _copy_table(src_engine, dst_engine, t, where)
        total_rows += n
        print(f"  {t}: {n} rows")

    src_engine.dispose()
    dst_engine.dispose()
    print(f"Done. SQLite file: {args.out} (approx {total_rows} DataSecure rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
