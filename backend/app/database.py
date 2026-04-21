from __future__ import annotations

from sqlalchemy import text
from sqlmodel import SQLModel, create_engine, Session, select
import os
import json

from app.core.config_simple import (
    DATABASE_URL,
    FIRST_SUPERUSER,
    FIRST_SUPERUSER_PASSWORD,
    FIRST_SUPERUSER_USERNAME,
)
from app.models import (  # noqa: F401 — imported for SQLModel metadata registration
    Tool,
    ToolRelease,
    ToolAnnouncement,
    APIAccessLog,
    Role,
    User,
    UserRole,
    Feedback,
    ToolOwner,
    ServiceIdRegistryEntry,
    ServiceIdRuleOption,
    MosTokenPoolEntry,
)

def _engine_kwargs() -> dict:
    # 每 worker 独立连接池；总连接 ≈ workers × (pool_size + max_overflow)，需与 RDS 规格匹配
    pool_size = int(os.getenv("SQLALCHEMY_POOL_SIZE", "4"))
    max_overflow = int(os.getenv("SQLALCHEMY_MAX_OVERFLOW", "2"))
    pool_size = max(1, min(pool_size, 32))
    max_overflow = max(0, min(max_overflow, 32))
    return {
        "pool_pre_ping": True,
        "pool_size": pool_size,
        "max_overflow": max_overflow,
    }


def _should_echo_sql() -> bool:
    return os.getenv("SQL_ECHO", "").strip().lower() in ("1", "true", "yes")


_database_url = DATABASE_URL.strip()

engine = create_engine(
    _database_url,
    echo=_should_echo_sql(),
    **_engine_kwargs(),
)

SYSTEM_ROLES = {
    "tool_owner": "Can review and approve tool access requests",
    "tool_user": "Can apply for tool access",
}

SERVICE_ID_REGISTRY_TOOL = (
    "service-id-registry",
    "Service ID 统一管理：普通用户提交申请，负责人定义规则并全量治理。",
)

MOS_INTEGRATION_TOOLBOX_TOOL = (
    "mos-integration-toolbox",
    "MOS综合工具箱：IAM X509、SIM、UAT AF DP、UAT SP、UAT车辆配置导入。",
)

BOOTSTRAP_USERS = [
    {
        "username": "admin",
        "email": "admin@example.com",
        "full_name": "System Admin",
        "department": "Platform",
        "password": "admin123",
        "is_superuser": True,
        "is_approved": True,
    },
    {
        "username": "owner",
        "email": "owner@example.com",
        "full_name": "Feature Owner",
        "department": "Product",
        "password": "owner123",
        "is_superuser": False,
        "is_approved": True,
    },
    {
        "username": "user",
        "email": "user@example.com",
        "full_name": "Normal User",
        "department": "Business",
        "password": "user12345",
        "is_superuser": False,
        "is_approved": True,
    },
]


def _ensure_system_roles(session: Session):
    for role_name, description in SYSTEM_ROLES.items():
        role = session.exec(select(Role).where(Role.name == role_name)).first()
        if not role:
            session.add(Role(name=role_name, description=description, is_system=True))


def _ensure_first_superuser(session: Session) -> None:
    """空库且无超管时，根据 FIRST_SUPERUSER / FIRST_SUPERUSER_PASSWORD 创建首个管理员。"""
    from app.api.v1.auth import get_password_hash

    existing_super = session.exec(select(User).where(User.is_superuser == True)).first()  # noqa: E712
    if existing_super:
        return
    email = (FIRST_SUPERUSER or "").strip()
    password = (FIRST_SUPERUSER_PASSWORD or "").strip()
    if not email or not password:
        return
    username = (FIRST_SUPERUSER_USERNAME or "").strip() or email.split("@", 1)[0]
    if not username:
        return
    if session.exec(select(User).where(User.username == username)).first():
        return
    if session.exec(select(User).where(User.email == email)).first():
        return

    user = User(
        username=username,
        email=email,
        hashed_password=get_password_hash(password),
        full_name="系统管理员",
        department="Platform",
        is_superuser=True,
        is_approved=True,
        is_active=True,
    )
    session.add(user)
    session.flush()

    tool_user_role = session.exec(select(Role).where(Role.name == "tool_user")).first()
    tool_owner_role = session.exec(select(Role).where(Role.name == "tool_owner")).first()
    if tool_user_role:
        session.add(UserRole(user_id=user.id, role_id=tool_user_role.id))
    if tool_owner_role:
        session.add(UserRole(user_id=user.id, role_id=tool_owner_role.id))


def _ensure_service_id_registry_tool(session: Session) -> None:
    tool_name, description = SERVICE_ID_REGISTRY_TOOL
    exists = session.exec(select(Tool).where(Tool.name == tool_name)).first()
    if exists:
        if not exists.description:
            exists.description = description
            session.add(exists)
        return
    session.add(
        Tool(
            name=tool_name,
            description=description,
            version="1.0.0",
            is_active=True,
        )
    )


def _ensure_mos_integration_toolbox_tool(session: Session) -> None:
    tool_name, description = MOS_INTEGRATION_TOOLBOX_TOOL
    exists = session.exec(select(Tool).where(Tool.name == tool_name)).first()
    if exists:
        if not exists.description:
            exists.description = description
            session.add(exists)
        elif exists.description and "重构版" in exists.description:
            exists.description = description
            session.add(exists)
        return
    session.add(
        Tool(
            name=tool_name,
            description=description,
            version="1.0.0",
            is_active=True,
        )
    )


def _ensure_user_default_roles(session: Session):
    users = session.exec(select(User)).all()
    tool_user_role = session.exec(select(Role).where(Role.name == "tool_user")).first()
    tool_owner_role = session.exec(select(Role).where(Role.name == "tool_owner")).first()
    if not tool_user_role or not tool_owner_role:
        return

    for user in users:
        has_tool_user = session.exec(
            select(UserRole).where(
                UserRole.user_id == user.id,
                UserRole.role_id == tool_user_role.id,
            )
        ).first()
        if not has_tool_user:
            session.add(UserRole(user_id=user.id, role_id=tool_user_role.id))

        if user.is_superuser:
            has_tool_owner = session.exec(
                select(UserRole).where(
                    UserRole.user_id == user.id,
                    UserRole.role_id == tool_owner_role.id,
                )
            ).first()
            if not has_tool_owner:
                session.add(UserRole(user_id=user.id, role_id=tool_owner_role.id))


def _ensure_bootstrap_users(session: Session):
    from app.api.v1.auth import get_password_hash

    tool_user_role = session.exec(select(Role).where(Role.name == "tool_user")).first()
    tool_owner_role = session.exec(select(Role).where(Role.name == "tool_owner")).first()
    service_tool = session.exec(
        select(Tool).where(Tool.name == SERVICE_ID_REGISTRY_TOOL[0])
    ).first()

    for spec in BOOTSTRAP_USERS:
        user = session.exec(select(User).where(User.username == spec["username"])).first()
        if not user:
            user = User(
                username=spec["username"],
                email=spec["email"],
                hashed_password=get_password_hash(spec["password"]),
                full_name=spec["full_name"],
                department=spec["department"],
                is_superuser=spec["is_superuser"],
                is_approved=spec["is_approved"],
                is_active=True,
            )
            session.add(user)
            session.flush()
        else:
            changed = False
            if not user.is_approved:
                user.is_approved = True
                changed = True
            if spec["is_superuser"] and not user.is_superuser:
                user.is_superuser = True
                changed = True
            if changed:
                session.add(user)

        if tool_user_role:
            has_user_role = session.exec(
                select(UserRole).where(
                    UserRole.user_id == user.id,
                    UserRole.role_id == tool_user_role.id,
                )
            ).first()
            if not has_user_role:
                session.add(UserRole(user_id=user.id, role_id=tool_user_role.id))

        if spec["username"] in {"admin", "owner"} and tool_owner_role:
            has_owner_role = session.exec(
                select(UserRole).where(
                    UserRole.user_id == user.id,
                    UserRole.role_id == tool_owner_role.id,
                )
            ).first()
            if not has_owner_role:
                session.add(UserRole(user_id=user.id, role_id=tool_owner_role.id))

        if spec["username"] == "owner" and service_tool:
            owner_binding = session.exec(
                select(ToolOwner).where(
                    ToolOwner.tool_id == service_tool.id,
                    ToolOwner.user_id == user.id,
                )
            ).first()
            if not owner_binding:
                session.add(ToolOwner(tool_id=service_tool.id, user_id=user.id))


def _sync_behavior_catalogs(session: Session) -> None:
    from app.services.tool_behavior_catalog import default_behavior_catalogs

    defaults = default_behavior_catalogs()
    for name, js in defaults.items():
        t = session.exec(select(Tool).where(Tool.name == name)).first()
        if not t:
            continue
        if t.behavior_catalog_json is None or str(t.behavior_catalog_json).strip() == "":
            t.behavior_catalog_json = js
            session.add(t)
            continue
        try:
            existing_raw = json.loads(t.behavior_catalog_json)
        except Exception:
            existing_raw = []
        try:
            default_raw = json.loads(js)
        except Exception:
            default_raw = []
        if not isinstance(existing_raw, list) or not isinstance(default_raw, list):
            continue
        existing_by_key = {
            str(item.get("key", "")).strip(): item
            for item in existing_raw
            if isinstance(item, dict) and str(item.get("key", "")).strip()
        }
        changed = False
        for item in default_raw:
            if not isinstance(item, dict):
                continue
            key = str(item.get("key", "")).strip()
            label = str(item.get("label", "")).strip()
            if not key or not label:
                continue
            if key not in existing_by_key:
                existing_raw.append({"key": key, "label": label})
                changed = True
        if changed:
            t.behavior_catalog_json = json.dumps(existing_raw, ensure_ascii=False)
            session.add(t)


def seed_initial_data():
    with Session(engine) as session:
        _ensure_system_roles(session)
        _ensure_first_superuser(session)
        _ensure_service_id_registry_tool(session)
        _ensure_mos_integration_toolbox_tool(session)
        _sync_behavior_catalogs(session)
        session.commit()

        _ensure_user_default_roles(session)
        if os.getenv("TOOLBOX_BOOTSTRAP_USERS", "0") == "1":
            _ensure_bootstrap_users(session)
        session.commit()

def _backfill_apiaccesslog_behavior_labels(session: Session) -> None:
    from app.services.tool_behavior_catalog import resolve_behavior_label_from_tool

    need = session.exec(
        select(APIAccessLog).where(
            APIAccessLog.tool_id != None,  # noqa: E711
            APIAccessLog.feature_name != None,  # noqa: E711
            APIAccessLog.behavior_label == None,  # noqa: E711
        )
    ).all()
    if not need:
        return
    for row in need:
        tool = session.get(Tool, row.tool_id) if row.tool_id else None
        row.behavior_label = resolve_behavior_label_from_tool(tool, row.feature_name)
        session.add(row)
    session.commit()


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    seed_initial_data()
    with Session(engine) as session:
        _backfill_apiaccesslog_behavior_labels(session)

def get_session():
    with Session(engine) as session:
        yield session
