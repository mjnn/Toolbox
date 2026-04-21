# config_simple.py — 从 backend/.env 加载配置（DATABASE_URL、JWT、首个超管等）

from __future__ import annotations

import json
import os
from pathlib import Path

_backend_root = Path(__file__).resolve().parent.parent.parent
_env_path = _backend_root / ".env"
if _env_path.is_file():
    from dotenv import load_dotenv

    load_dotenv(_env_path)

# API 配置
API_V1_STR = "/api/v1"
PROJECT_NAME = "Tools Platform"

# CORS — 支持 JSON 数组字符串，与 backend/.env 示例一致
_cors_raw = os.getenv("BACKEND_CORS_ORIGINS")
if _cors_raw:
    try:
        BACKEND_CORS_ORIGINS = json.loads(_cors_raw)
    except json.JSONDecodeError:
        BACKEND_CORS_ORIGINS = ["http://localhost:5173", "http://localhost:3000"]
else:
    BACKEND_CORS_ORIGINS = ["http://localhost:5173", "http://localhost:3000"]

def _allow_dev_sqlite() -> bool:
    return os.getenv("TOOLBOX_ALLOW_SQLITE_DEV", "").strip().lower() in ("1", "true", "yes")


def _normalize_database_url(raw: str) -> str:
    u = (raw or "").strip()
    if not u:
        if _allow_dev_sqlite():
            # 开发便捷模式：允许在 start-dev 场景下免配置直连本地 SQLite。
            return "sqlite:///./app.db"
        raise RuntimeError(
            "DATABASE_URL 未设置。请在 backend/.env 中配置 PostgreSQL，例如：\n"
            "  DATABASE_URL=postgresql+psycopg2://user:pass@host:5432/dbname"
        )
    low = u.lower()
    if low.startswith("sqlite"):
        if _allow_dev_sqlite():
            return u
        raise RuntimeError(
            "SQLite 仅允许本地开发快捷启动（设置 TOOLBOX_ALLOW_SQLITE_DEV=1）。"
            " 部署与发布请改用 PostgreSQL（postgresql+psycopg2://...）。"
        )
    if not (low.startswith("postgresql") or low.startswith("postgres://")):
        raise RuntimeError(
            "DATABASE_URL 须为 PostgreSQL 连接串（postgresql+psycopg2://...）。"
        )
    return u


# 默认支持 PostgreSQL；仅在 TOOLBOX_ALLOW_SQLITE_DEV=1 时允许 SQLite（用于本地开发快捷启动）。
DATABASE_URL = _normalize_database_url(os.getenv("DATABASE_URL", ""))
# 以下由 run_server.py / database.py 读取（不在本文件赋值）：
# TOOLBOX_WORKERS — Uvicorn 进程数；未设置时默认 2
# SQLALCHEMY_POOL_SIZE / SQLALCHEMY_MAX_OVERFLOW — 连接池（默认 4 / 2）

# JWT
SECRET_KEY = os.getenv("SECRET_KEY", "your-strong-secret-key-change-in-production")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# 首个超级管理员（库中尚无任何 is_superuser 时自动创建；需同时配置邮箱与密码）
FIRST_SUPERUSER = os.getenv("FIRST_SUPERUSER", "admin@example.com").strip()
FIRST_SUPERUSER_PASSWORD = os.getenv("FIRST_SUPERUSER_PASSWORD", "admin123")
# 默认可留空，将使用邮箱 @ 前的本地部分作为用户名
FIRST_SUPERUSER_USERNAME = os.getenv("FIRST_SUPERUSER_USERNAME", "").strip()

BACKEND_ROOT = _backend_root
