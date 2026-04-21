import os
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from jose import jwt, JWTError
from sqlmodel import Session, select
from datetime import datetime
import logging
import re
import time

from app.api.v1.api import api_router
from app.core.config_simple import (
    PROJECT_NAME,
    BACKEND_CORS_ORIGINS,
    API_V1_STR,
    SECRET_KEY,
    ALGORITHM,
)
from app.database import create_db_and_tables, engine
from app.services.tool_behavior_catalog import resolve_behavior_label_from_tool
from app.core.logging_config import setup_logging
from app.models import APIAccessLog, Tool, User

setup_logging()
logger = logging.getLogger("app.main")
backend_access_logger = logging.getLogger("access.backend")
frontend_access_logger = logging.getLogger("access.frontend")

TOOL_FEATURE_REGEX = re.compile(
    r"^/api/v1/tools/(?P<tool_id>\d+)/features/(?P<feature>[a-zA-Z0-9_/-]+)$"
)


def parse_actor(authorization_header: str | None) -> tuple[int | None, str | None]:
    if not authorization_header or not authorization_header.startswith("Bearer "):
        return None, None
    token = authorization_header.replace("Bearer ", "", 1).strip()
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None, None
    username = payload.get("sub")
    if not username:
        return None, None
    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == username)).first()
        if not user:
            return None, username
        return user.id, user.username


def parse_tool_feature(path: str) -> tuple[int | None, str | None]:
    match = TOOL_FEATURE_REGEX.match(path)
    if not match:
        return None, None
    return int(match.group("tool_id")), match.group("feature")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时创建数据库表
    create_db_and_tables()
    yield
    # 关闭时清理资源
    pass

app = FastAPI(
    title=PROJECT_NAME,
    lifespan=lifespan,
)

# 设置CORS
if BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# 包含API路由
app.include_router(api_router, prefix=API_V1_STR)

if getattr(sys, "frozen", False):
    BASE_RUNTIME_DIR = Path(sys.executable).resolve().parent
    bundle_dir = Path(getattr(sys, "_MEIPASS", BASE_RUNTIME_DIR))
    configured_frontend_dist = os.getenv("TOOLBOX_FRONTEND_DIST")
    frontend_candidates = []
    if configured_frontend_dist:
        frontend_candidates.append(Path(configured_frontend_dist))
    frontend_candidates.extend(
        [
            BASE_RUNTIME_DIR / "frontend" / "dist",
            BASE_RUNTIME_DIR / "_internal" / "frontend" / "dist",
            bundle_dir / "frontend" / "dist",
        ]
    )
    FRONTEND_DIST_DIR = next(
        (p for p in frontend_candidates if (p / "index.html").exists()),
        frontend_candidates[0],
    )
else:
    BASE_RUNTIME_DIR = Path(__file__).resolve().parent
    FRONTEND_DIST_DIR = Path(
        os.getenv("TOOLBOX_FRONTEND_DIST", str(BASE_RUNTIME_DIR.parent / "frontend" / "dist"))
    )

STATIC_DIR = Path(os.getenv("TOOLBOX_STATIC_DIR", str(BASE_RUNTIME_DIR / "static")))
os.makedirs(STATIC_DIR / "avatars", exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
if (FRONTEND_DIST_DIR / "assets").exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST_DIR / "assets"), name="frontend-assets")


@app.middleware("http")
async def audit_log_middleware(request, call_next):
    started = time.perf_counter()
    response = await call_next(request)
    latency_ms = int((time.perf_counter() - started) * 1000)

    user_id, username = parse_actor(request.headers.get("Authorization"))
    tool_id, feature_name = parse_tool_feature(request.url.path)
    query_string = request.url.query if request.url.query else None
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")

    try:
        with Session(engine) as session:
            behavior_label = None
            if tool_id and feature_name:
                tool_row = session.get(Tool, tool_id)
                behavior_label = resolve_behavior_label_from_tool(tool_row, feature_name)
            session.add(
                APIAccessLog(
                    user_id=user_id,
                    username=username,
                    method=request.method,
                    path=request.url.path,
                    query_string=query_string,
                    status_code=response.status_code,
                    latency_ms=latency_ms,
                    client_ip=client_ip,
                    user_agent=user_agent,
                    tool_id=tool_id,
                    feature_name=feature_name,
                    behavior_label=behavior_label,
                    created_at=datetime.utcnow(),
                )
            )
            session.commit()
    except Exception as exc:
        logger.exception("Failed to persist api access log: %s", exc)

    access_logger = backend_access_logger if request.url.path.startswith("/api/") else frontend_access_logger
    access_logger.info(
        "request method=%s path=%s status=%s user=%s ip=%s latency_ms=%s",
        request.method,
        request.url.path,
        response.status_code,
        username or "anonymous",
        client_ip or "-",
        latency_ms,
    )
    logger.info(
        "request method=%s path=%s status=%s user=%s latency_ms=%s",
        request.method,
        request.url.path,
        response.status_code,
        username or "anonymous",
        latency_ms,
    )
    return response

@app.get("/")
async def root():
    index_file = FRONTEND_DIST_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "Tools Platform API", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/{full_path:path}")
async def spa_fallback(full_path: str):
    if full_path.startswith("api/") or full_path.startswith("static/"):
        raise HTTPException(status_code=404, detail="Not found")
    requested_file = FRONTEND_DIST_DIR / full_path
    if requested_file.exists() and requested_file.is_file():
        return FileResponse(requested_file)
    index_file = FRONTEND_DIST_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    raise HTTPException(
        status_code=404,
        detail="Frontend dist not found. Build frontend before running packaged app.",
    )
