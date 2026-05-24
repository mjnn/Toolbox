# config_simple.py — 从 .env 加载配置（DATABASE_URL、JWT、首个超管等）

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def _resolve_backend_root() -> Path:
    """源码 / Docker：backend 目录；PyInstaller：与 toolbox-backend.exe 同目录（便携包根）。"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent.parent


def _load_dotenv_first_match() -> None:
    """按优先级加载第一个存在的 .env（override=False，不覆盖已在进程/编排里注入的变量）。"""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return

    backend_root = _resolve_backend_root()
    candidates: list[Path] = []
    explicit = (os.getenv("TOOLBOX_BACKEND_ENV_FILE") or "").strip()
    if explicit:
        candidates.append(Path(explicit))
    candidates.append(Path.cwd() / ".env")
    candidates.append(backend_root / ".env")

    seen: set[str] = set()
    for raw in candidates:
        try:
            p = raw.resolve()
        except OSError:
            p = raw
        key = str(p)
        if key in seen:
            continue
        seen.add(key)
        if p.is_file():
            load_dotenv(p, override=False)
            break


_load_dotenv_first_match()

_backend_root = _resolve_backend_root()

# API 配置
API_V1_STR = "/api/v1"
PROJECT_NAME = "Tools Platform"


def _parse_cors_origins(raw: str | None) -> list[str]:
    default = ["http://localhost:5173", "http://localhost:3000"]
    text = (raw or "").strip()
    if not text:
        return default
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            values = [str(v).strip() for v in parsed if str(v).strip()]
            if values:
                return values
    except json.JSONDecodeError:
        pass

    # 兼容非严格 JSON 输入（例如 [http://a,https://b] 或带转义字符）。
    normalized = text.replace("\\", "").strip()
    if normalized.startswith("[") and normalized.endswith("]"):
        normalized = normalized[1:-1]
    values = [
        item.strip().strip('"').strip("'")
        for item in normalized.split(",")
        if item.strip().strip('"').strip("'")
    ]
    return values or default


# CORS — 支持 JSON 数组字符串，兼容非严格数组格式输入
BACKEND_CORS_ORIGINS = _parse_cors_origins(os.getenv("BACKEND_CORS_ORIGINS"))


def _allow_dev_sqlite() -> bool:
    return os.getenv("TOOLBOX_ALLOW_SQLITE_DEV", "").strip().lower() in ("1", "true", "yes")


def _normalize_database_url(raw: str) -> str:
    u = (raw or "").strip()
    if not u:
        if _allow_dev_sqlite():
            # 开发便捷模式：允许在 start-dev 场景下免配置直连本地 SQLite。
            return "sqlite:///./app.db"
        raise RuntimeError(
            "DATABASE_URL 未设置。请在以下任一位置配置 PostgreSQL，例如：\n"
            "  DATABASE_URL=postgresql+psycopg2://user:pass@host:5432/dbname\n"
            "  - 进程环境变量（Docker Compose / systemd）\n"
            "  - 当前工作目录下的 .env\n"
            "  - 与可执行文件同目录的 .env（便携包）\n"
            "  - backend/.env（源码开发）\n"
            "  - 或设置 TOOLBOX_BACKEND_ENV_FILE 指向 .env 绝对路径"
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
