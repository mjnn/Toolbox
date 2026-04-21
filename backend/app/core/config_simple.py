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

# 数据库：默认本地 SQLite；生产可用
# postgresql+psycopg2://user:pass@host:5432/dbname?sslmode=require
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db").strip()

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

# 供路径解析等使用（如 SQLite 相对路径锚定到 backend 目录）
BACKEND_ROOT = _backend_root
