from __future__ import annotations

from sqlalchemy import text
from sqlalchemy import event
from sqlalchemy.exc import IntegrityError
from sqlmodel import SQLModel, create_engine, Session, select
import os
import json
import time
import contextvars

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
    ToolDisplayConfig,
    ServiceIdRegistryEntry,
    ServiceIdRuleOption,
    ServiceIdFieldConfig,
    ServiceIdFormFieldDefinition,
    ServiceIdEntryCustomFieldValue,
    ServiceIdCsvExportConfig,
    DataSecureProjectSpace,
    DataSecureQuestionnaireQuestion,
    DataSecureRelevanceRule,
    DataSecureAssessmentSubmission,
    DataSecureAssessmentAnswer,
    DataSecureLifecycleFieldDefinition,
    DataSecureLifecycleFieldConfig,
    DataSecureFieldCatalogEntry,
    DataSecureFieldCatalogValue,
    DataSecureTaxonomyNode,
    DataSecureFieldClassGrade,
    DataSecureFieldSecurityRequirement,
    DataSecureFieldRequest,
    DataSecureBusinessFunctionOptionRequest,
    DataSecureGovernanceChangeLog,
    DataSecureFieldUsageReport,
    DataSecureFieldUsageReportItem,
    DataSecureFieldClassificationAuditLog,
    DataSecureFieldClassificationMatrix,
    DataSecureFieldClassificationRule,
    DataSecureFieldClassificationResult,
    MosTokenPoolEntry,
    RsaTokenLivestreamSetting,
)

def _read_int_env(keys: tuple[str, ...], default: int) -> int:
    for key in keys:
        raw = os.getenv(key)
        if raw is None:
            continue
        text = str(raw).strip()
        if not text:
            continue
        try:
            return int(text)
        except ValueError:
            continue
    return default


def _engine_kwargs(database_url: str) -> dict:
    # SQLite（本地开发）不使用连接池参数，避免 create_engine 参数不兼容。
    if database_url.lower().startswith("sqlite"):
        return {"connect_args": {"check_same_thread": False}}
    # PostgreSQL：每 worker 独立连接池；总连接 ≈ workers × (pool_size + max_overflow)
    pool_size = _read_int_env(("SQLALCHEMY_POOL_SIZE",), 4)
    max_overflow = _read_int_env(("SQLALCHEMY_MAX_OVERFLOW",), 2)
    pool_timeout = _read_int_env(("SQLALCHEMY_POOL_TIMEOUT", "SQLALCHEMY_POOL_TIMEOUT_SECONDS"), 30)
    pool_recycle = _read_int_env(("SQLALCHEMY_POOL_RECYCLE", "SQLALCHEMY_POOL_RECYCLE_SECONDS"), 1800)
    statement_timeout_ms = _read_int_env(("SQLALCHEMY_STATEMENT_TIMEOUT_MS",), 15000)
    pool_size = max(1, min(pool_size, 32))
    max_overflow = max(0, min(max_overflow, 32))
    pool_timeout = max(5, min(pool_timeout, 120))
    pool_recycle = max(30, min(pool_recycle, 7200))
    statement_timeout_ms = max(1000, min(statement_timeout_ms, 120000))
    return {
        "pool_pre_ping": True,
        "pool_size": pool_size,
        "max_overflow": max_overflow,
        "pool_timeout": pool_timeout,
        "pool_recycle": pool_recycle,
        "connect_args": {"options": f"-c statement_timeout={statement_timeout_ms}"},
    }


def _should_echo_sql() -> bool:
    return os.getenv("SQL_ECHO", "").strip().lower() in ("1", "true", "yes")


_database_url = DATABASE_URL.strip()

engine = create_engine(
    _database_url,
    echo=_should_echo_sql(),
    **_engine_kwargs(_database_url),
)

_request_sql_timing_ctx: contextvars.ContextVar[dict | None] = contextvars.ContextVar(
    "request_sql_timing",
    default=None,
)


def reset_request_sql_timing() -> None:
    _request_sql_timing_ctx.set({"db_ms": 0.0, "db_count": 0})


def get_request_sql_timing() -> dict:
    data = _request_sql_timing_ctx.get()
    if not data:
        return {"db_ms": 0.0, "db_count": 0}
    return {"db_ms": float(data.get("db_ms", 0.0)), "db_count": int(data.get("db_count", 0))}


@event.listens_for(engine, "before_cursor_execute")
def _before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    conn.info["_query_started_at"] = time.perf_counter()


@event.listens_for(engine, "after_cursor_execute")
def _after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    started = conn.info.pop("_query_started_at", None)
    if started is None:
        return
    timing = _request_sql_timing_ctx.get()
    if timing is None:
        return
    elapsed_ms = (time.perf_counter() - started) * 1000
    timing["db_ms"] = float(timing.get("db_ms", 0.0)) + elapsed_ms
    timing["db_count"] = int(timing.get("db_count", 0)) + 1

SYSTEM_ROLES = {
    "platform_admin": "平台管理员：用户与工具治理（不含系统级配置）",
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

RSA_TOKEN_LIVESTREAM_TOOL = (
    "rsa-token-livestream",
    "RSA Token 直播：统一入口查看直播并可由负责人控制占位提示页。",
)

DATA_SECURE_MANAGE_TOOL = (
    "data-secure-manage",
    "数据安全治理工具：支持数据安全相关流程分阶段治理。",
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
    """幂等创建系统角色；避免 autoflush 与多 worker 并发下的重复 INSERT。"""
    for role_name, description in SYSTEM_ROLES.items():
        with session.no_autoflush:
            if session.exec(select(Role).where(Role.name == role_name)).first():
                continue
        try:
            with session.begin_nested():
                session.add(Role(name=role_name, description=description, is_system=True))
                session.flush()
        except IntegrityError:
            continue


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


def _ensure_rsa_token_livestream_tool(session: Session) -> None:
    tool_name, description = RSA_TOKEN_LIVESTREAM_TOOL
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


def _ensure_data_secure_manage_tool(session: Session) -> None:
    tool_name, description = DATA_SECURE_MANAGE_TOOL
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
            version="0.1.0",
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


def _dedupe_superusers(session: Session) -> None:
    """保证全局仅一名 is_superuser=True；其余原超管降级并赋予 platform_admin 角色。"""
    supers = session.exec(select(User).where(User.is_superuser == True)).all()  # noqa: E712
    if len(supers) <= 1:
        return
    keeper = min(supers, key=lambda u: int(u.id or 0))
    role = session.exec(select(Role).where(Role.name == "platform_admin")).first()
    for u in supers:
        if int(u.id or 0) == int(keeper.id or 0):
            continue
        u.is_superuser = False
        session.add(u)
        if role:
            exists = session.exec(
                select(UserRole).where(UserRole.user_id == u.id, UserRole.role_id == role.id)
            ).first()
            if not exists:
                session.add(UserRole(user_id=int(u.id), role_id=role.id))


def seed_initial_data():
    with Session(engine) as session:
        _ensure_system_roles(session)
        _ensure_first_superuser(session)
        _ensure_service_id_registry_tool(session)
        _ensure_mos_integration_toolbox_tool(session)
        _ensure_rsa_token_livestream_tool(session)
        _ensure_data_secure_manage_tool(session)
        _sync_behavior_catalogs(session)
        session.commit()

        _ensure_user_default_roles(session)
        if os.getenv("TOOLBOX_BOOTSTRAP_USERS", "0") == "1":
            _ensure_bootstrap_users(session)
        _dedupe_superusers(session)
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


def _ensure_tool_runtime_status_column() -> None:
    """为已有库追加 tool.runtime_status（新库由模型创建，此处幂等补列）。"""
    low = str(_database_url).lower()
    with engine.begin() as conn:  # handles commit for both drivers
        if "sqlite" in low:
            rows = conn.execute(text("PRAGMA table_info(tool)")).fetchall()
            names = {str(r[1]) for r in rows} if rows else set()
            if "runtime_status" in names:
                return
            conn.execute(
                text(
                    "ALTER TABLE tool ADD COLUMN runtime_status "
                    "VARCHAR(32) NOT NULL DEFAULT 'active'"
                )
            )
            return
        if "postgres" in low or "postgresql" in low:
            conn.execute(
                text(
                    "ALTER TABLE tool ADD COLUMN IF NOT EXISTS runtime_status "
                    "VARCHAR(32) NOT NULL DEFAULT 'active'"
                )
            )
            return
        # 其他方言：新库 create_all 已建列
        return


def _ensure_data_secure_relevance_rule_columns() -> None:
    """为已有库追加 data secure 判定规则字段（新库由模型创建，此处幂等补列）。"""
    low = str(_database_url).lower()
    with engine.begin() as conn:
        if "sqlite" in low:
            rows = conn.execute(text("PRAGMA table_info(datasecurerelevancerule)")).fetchall()
            names = {str(r[1]) for r in rows} if rows else set()
            if "logic_operator" not in names:
                conn.execute(
                    text(
                        "ALTER TABLE datasecurerelevancerule ADD COLUMN logic_operator "
                        "VARCHAR(10) NOT NULL DEFAULT 'and'"
                    )
                )
            if "question_keys_json" not in names:
                conn.execute(
                    text(
                        "ALTER TABLE datasecurerelevancerule ADD COLUMN question_keys_json "
                        "VARCHAR(4000) NOT NULL DEFAULT '[]'"
                    )
                )
            if "logic_expression" not in names:
                conn.execute(
                    text(
                        "ALTER TABLE datasecurerelevancerule ADD COLUMN logic_expression "
                        "VARCHAR(2000)"
                    )
                )
            return
        if "postgres" in low or "postgresql" in low:
            conn.execute(
                text(
                    "ALTER TABLE datasecurerelevancerule "
                    "ADD COLUMN IF NOT EXISTS logic_operator VARCHAR(10) NOT NULL DEFAULT 'and'"
                )
            )
            conn.execute(
                text(
                    "ALTER TABLE datasecurerelevancerule "
                    "ADD COLUMN IF NOT EXISTS question_keys_json VARCHAR(4000) NOT NULL DEFAULT '[]'"
                )
            )
            conn.execute(
                text(
                    "ALTER TABLE datasecurerelevancerule "
                    "ADD COLUMN IF NOT EXISTS logic_expression VARCHAR(2000)"
                )
            )
            return
        return


def _ensure_data_secure_classification_evolution() -> None:
    """分类分级：规则 priority、结果 auto 快照、审计表（已有库幂等补全）。"""
    low = str(_database_url).lower()
    with engine.begin() as conn:
        if "sqlite" in low:
            rows = conn.execute(text("PRAGMA table_info(datasecurefieldclassificationrule)")).fetchall()
            names = {str(r[1]) for r in rows} if rows else set()
            if names and "priority" not in names:
                conn.execute(
                    text(
                        "ALTER TABLE datasecurefieldclassificationrule ADD COLUMN priority "
                        "INTEGER NOT NULL DEFAULT 100"
                    )
                )
            rows_r = conn.execute(text("PRAGMA table_info(datasecurefieldclassificationresult)")).fetchall()
            names_r = {str(r[1]) for r in rows_r} if rows_r else set()
            result_did_alter = False
            if names_r:
                if "auto_category" not in names_r:
                    result_did_alter = True
                    conn.execute(
                        text(
                            "ALTER TABLE datasecurefieldclassificationresult ADD COLUMN auto_category "
                            "VARCHAR(100) NOT NULL DEFAULT '未分类'"
                        )
                    )
                if "auto_level" not in names_r:
                    result_did_alter = True
                    conn.execute(
                        text(
                            "ALTER TABLE datasecurefieldclassificationresult ADD COLUMN auto_level "
                            "VARCHAR(100) NOT NULL DEFAULT 'L0'"
                        )
                    )
                if "auto_rule_keyword" not in names_r:
                    result_did_alter = True
                    conn.execute(
                        text(
                            "ALTER TABLE datasecurefieldclassificationresult ADD COLUMN auto_rule_keyword "
                            "VARCHAR(100)"
                        )
                    )
                if "auto_rule_id" not in names_r:
                    result_did_alter = True
                    conn.execute(
                        text(
                            "ALTER TABLE datasecurefieldclassificationresult ADD COLUMN auto_rule_id INTEGER"
                        )
                    )
                if "auto_hit_summary" not in names_r:
                    result_did_alter = True
                    conn.execute(
                        text(
                            "ALTER TABLE datasecurefieldclassificationresult ADD COLUMN auto_hit_summary "
                            "VARCHAR(800)"
                        )
                    )
                if "manual_reason" not in names_r:
                    result_did_alter = True
                    conn.execute(
                        text(
                            "ALTER TABLE datasecurefieldclassificationresult ADD COLUMN manual_reason "
                            "VARCHAR(500)"
                        )
                    )
                if result_did_alter:
                    conn.execute(
                        text(
                            "UPDATE datasecurefieldclassificationresult SET "
                            "auto_category = category, auto_level = level, auto_rule_keyword = rule_keyword "
                            "WHERE 1 = 1"
                        )
                    )
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS datasecurefieldclassificationauditlog (
                        id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                        tool_id INTEGER NOT NULL,
                        project_space_id INTEGER NOT NULL,
                        catalog_entry_id INTEGER,
                        result_id INTEGER,
                        user_id INTEGER NOT NULL,
                        action VARCHAR(40) NOT NULL,
                        detail_json VARCHAR(4000) NOT NULL DEFAULT '{}',
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY(tool_id) REFERENCES tool (id),
                        FOREIGN KEY(project_space_id) REFERENCES datasecureprojectspace (id),
                        FOREIGN KEY(catalog_entry_id) REFERENCES datasecurefieldcatalogentry (id),
                        FOREIGN KEY(result_id) REFERENCES datasecurefieldclassificationresult (id),
                        FOREIGN KEY(user_id) REFERENCES user (id)
                    )
                    """
                )
            )
            return
        if "postgres" in low or "postgresql" in low:
            conn.execute(
                text(
                    "ALTER TABLE datasecurefieldclassificationrule "
                    "ADD COLUMN IF NOT EXISTS priority INTEGER NOT NULL DEFAULT 100"
                )
            )
            info = conn.execute(
                text(
                    "SELECT COUNT(*) FROM information_schema.columns "
                    "WHERE table_schema = 'public' AND table_name = 'datasecurefieldclassificationresult' "
                    "AND column_name = 'auto_category'"
                )
            ).scalar()
            auto_col_missing = int(info or 0) == 0
            conn.execute(
                text(
                    "ALTER TABLE datasecurefieldclassificationresult "
                    "ADD COLUMN IF NOT EXISTS auto_category VARCHAR(100) NOT NULL DEFAULT '未分类'"
                )
            )
            conn.execute(
                text(
                    "ALTER TABLE datasecurefieldclassificationresult "
                    "ADD COLUMN IF NOT EXISTS auto_level VARCHAR(100) NOT NULL DEFAULT 'L0'"
                )
            )
            conn.execute(
                text(
                    "ALTER TABLE datasecurefieldclassificationresult "
                    "ADD COLUMN IF NOT EXISTS auto_rule_keyword VARCHAR(100)"
                )
            )
            conn.execute(
                text(
                    "ALTER TABLE datasecurefieldclassificationresult "
                    "ADD COLUMN IF NOT EXISTS auto_rule_id INTEGER"
                )
            )
            conn.execute(
                text(
                    "ALTER TABLE datasecurefieldclassificationresult "
                    "ADD COLUMN IF NOT EXISTS auto_hit_summary VARCHAR(800)"
                )
            )
            conn.execute(
                text(
                    "ALTER TABLE datasecurefieldclassificationresult "
                    "ADD COLUMN IF NOT EXISTS manual_reason VARCHAR(500)"
                )
            )
            if auto_col_missing:
                conn.execute(
                    text(
                        "UPDATE datasecurefieldclassificationresult SET "
                        "auto_category = category, auto_level = level, auto_rule_keyword = rule_keyword "
                        "WHERE 1 = 1"
                    )
                )
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS datasecurefieldclassificationauditlog (
                        id SERIAL PRIMARY KEY,
                        tool_id INTEGER NOT NULL REFERENCES tool(id),
                        project_space_id INTEGER NOT NULL REFERENCES datasecureprojectspace(id),
                        catalog_entry_id INTEGER REFERENCES datasecurefieldcatalogentry(id),
                        result_id INTEGER REFERENCES datasecurefieldclassificationresult(id),
                        user_id INTEGER NOT NULL REFERENCES "user"(id),
                        action VARCHAR(40) NOT NULL,
                        detail_json VARCHAR(4000) NOT NULL DEFAULT '{}',
                        created_at TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc')
                    )
                    """
                )
            )
            return
        return


def _ensure_data_secure_classification_matrix() -> None:
    """显式分类矩阵表 + 结果表 auto_matrix_id / auto_match_source（已有库幂等）。"""
    low = str(_database_url).lower()
    with engine.begin() as conn:
        if "sqlite" in low:
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS datasecurefieldclassificationmatrix (
                        id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                        tool_id INTEGER NOT NULL,
                        project_space_id INTEGER NOT NULL,
                        field_name VARCHAR(200) NOT NULL,
                        extension_match_json VARCHAR(4000) NOT NULL DEFAULT '{}',
                        category VARCHAR(100) NOT NULL,
                        level VARCHAR(100) NOT NULL,
                        priority INTEGER NOT NULL DEFAULT 200,
                        notes VARCHAR(1000),
                        sort_order INTEGER NOT NULL DEFAULT 0,
                        is_active BOOLEAN NOT NULL DEFAULT 1,
                        created_by INTEGER NOT NULL,
                        updated_by INTEGER NOT NULL,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY(tool_id) REFERENCES tool (id),
                        FOREIGN KEY(project_space_id) REFERENCES datasecureprojectspace (id),
                        FOREIGN KEY(created_by) REFERENCES user (id),
                        FOREIGN KEY(updated_by) REFERENCES user (id)
                    )
                    """
                )
            )
            rows_r = conn.execute(text("PRAGMA table_info(datasecurefieldclassificationresult)")).fetchall()
            names_r = {str(r[1]) for r in rows_r} if rows_r else set()
            if names_r and "auto_matrix_id" not in names_r:
                conn.execute(
                    text(
                        "ALTER TABLE datasecurefieldclassificationresult ADD COLUMN auto_matrix_id INTEGER"
                    )
                )
            if names_r and "auto_match_source" not in names_r:
                conn.execute(
                    text(
                        "ALTER TABLE datasecurefieldclassificationresult ADD COLUMN auto_match_source "
                        "VARCHAR(20) NOT NULL DEFAULT 'keyword'"
                    )
                )
            return
        if "postgres" in low or "postgresql" in low:
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS datasecurefieldclassificationmatrix (
                        id SERIAL PRIMARY KEY,
                        tool_id INTEGER NOT NULL REFERENCES tool(id),
                        project_space_id INTEGER NOT NULL REFERENCES datasecureprojectspace(id),
                        field_name VARCHAR(200) NOT NULL,
                        extension_match_json VARCHAR(4000) NOT NULL DEFAULT '{}',
                        category VARCHAR(100) NOT NULL,
                        level VARCHAR(100) NOT NULL,
                        priority INTEGER NOT NULL DEFAULT 200,
                        notes VARCHAR(1000),
                        sort_order INTEGER NOT NULL DEFAULT 0,
                        is_active BOOLEAN NOT NULL DEFAULT true,
                        created_by INTEGER NOT NULL REFERENCES "user"(id),
                        updated_by INTEGER NOT NULL REFERENCES "user"(id),
                        created_at TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc'),
                        updated_at TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc')
                    )
                    """
                )
            )
            conn.execute(
                text(
                    "ALTER TABLE datasecurefieldclassificationresult "
                    "ADD COLUMN IF NOT EXISTS auto_matrix_id INTEGER"
                )
            )
            conn.execute(
                text(
                    "ALTER TABLE datasecurefieldclassificationresult "
                    "ADD COLUMN IF NOT EXISTS auto_match_source VARCHAR(20) NOT NULL DEFAULT 'keyword'"
                )
            )
            return
        return


def _ensure_data_secure_function_name_varchar_500() -> None:
    """相关性判定 / 字段填报摘要：function_name 由 200 扩至 500（已有库幂等）。"""
    low = str(_database_url).lower()
    with engine.begin() as conn:
        if "sqlite" in low:
            # SQLite 对 VARCHAR 长度不强制，以 ORM 与请求体验证为准
            return
        if "postgres" in low or "postgresql" in low:
            for table in ("datasecureassessmentsubmission", "datasecurefieldusagereport"):
                row = conn.execute(
                    text(
                        "SELECT character_maximum_length FROM information_schema.columns "
                        "WHERE table_schema = current_schema() AND table_name = :t AND column_name = 'function_name'"
                    ),
                    {"t": table},
                ).fetchone()
                cur = int(row[0]) if row and row[0] is not None else None
                if cur is not None and cur >= 500:
                    continue
                conn.execute(text(f"ALTER TABLE {table} ALTER COLUMN function_name TYPE VARCHAR(500)"))
            return
        return


def _ensure_data_secure_question_help_text_varchar_8000() -> None:
    """问卷问题说明：help_text 从 1000 扩至 8000，支持 Markdown 富内容。"""
    low = str(_database_url).lower()
    with engine.begin() as conn:
        if "sqlite" in low:
            # SQLite 对 VARCHAR 长度不强制
            return
        if "postgres" in low or "postgresql" in low:
            row = conn.execute(
                text(
                    "SELECT character_maximum_length FROM information_schema.columns "
                    "WHERE table_schema = current_schema() "
                    "AND table_name = 'datasecurequestionnairequestion' "
                    "AND column_name = 'help_text'"
                )
            ).fetchone()
            cur = int(row[0]) if row and row[0] is not None else None
            if cur is not None and cur >= 8000:
                return
            conn.execute(
                text("ALTER TABLE datasecurequestionnairequestion ALTER COLUMN help_text TYPE VARCHAR(8000)")
            )
            return
        return


def _ensure_data_secure_usage_report_workflow_columns() -> None:
    """字段填报工单：关联问卷提交、审批状态（历史行 assessment 为空视为已批准）。"""
    low = str(_database_url).lower()
    with engine.begin() as conn:
        if "sqlite" in low:
            rows = conn.execute(text("PRAGMA table_info(datasecurefieldusagereport)")).fetchall()
            names = {str(r[1]) for r in rows} if rows else set()
            if not names:
                return
            if "assessment_submission_id" not in names:
                conn.execute(text("ALTER TABLE datasecurefieldusagereport ADD COLUMN assessment_submission_id INTEGER"))
            if "review_status" not in names:
                conn.execute(
                    text(
                        "ALTER TABLE datasecurefieldusagereport ADD COLUMN review_status "
                        "VARCHAR(20) NOT NULL DEFAULT 'pending'"
                    )
                )
            if "review_notes" not in names:
                conn.execute(text("ALTER TABLE datasecurefieldusagereport ADD COLUMN review_notes VARCHAR(1000)"))
            if "reviewed_by" not in names:
                conn.execute(text("ALTER TABLE datasecurefieldusagereport ADD COLUMN reviewed_by INTEGER"))
            if "reviewed_at" not in names:
                conn.execute(text("ALTER TABLE datasecurefieldusagereport ADD COLUMN reviewed_at TIMESTAMP"))
            return
        if "postgres" in low or "postgresql" in low:
            conn.execute(
                text(
                    "ALTER TABLE datasecurefieldusagereport "
                    "ADD COLUMN IF NOT EXISTS assessment_submission_id INTEGER "
                    "REFERENCES datasecureassessmentsubmission(id)"
                )
            )
            conn.execute(
                text(
                    "ALTER TABLE datasecurefieldusagereport "
                    "ADD COLUMN IF NOT EXISTS review_status VARCHAR(20) NOT NULL DEFAULT 'pending'"
                )
            )
            conn.execute(
                text(
                    "ALTER TABLE datasecurefieldusagereport "
                    "ADD COLUMN IF NOT EXISTS review_notes VARCHAR(1000)"
                )
            )
            conn.execute(
                text(
                    "ALTER TABLE datasecurefieldusagereport "
                    "ADD COLUMN IF NOT EXISTS reviewed_by INTEGER REFERENCES \"user\"(id)"
                )
            )
            conn.execute(
                text(
                    "ALTER TABLE datasecurefieldusagereport "
                    "ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMP WITH TIME ZONE"
                )
            )
            return
        return


def _ensure_data_secure_usage_report_item_extra_snapshot() -> None:
    """填报明细：追加其他信息快照列（已有库幂等补列）。"""
    low = str(_database_url).lower()
    with engine.begin() as conn:
        if "sqlite" in low:
            rows = conn.execute(text("PRAGMA table_info(datasecurefieldusagereportitem)")).fetchall()
            names = {str(r[1]) for r in rows} if rows else set()
            if names and "extra_snapshot_json" not in names:
                conn.execute(
                    text(
                        "ALTER TABLE datasecurefieldusagereportitem ADD COLUMN extra_snapshot_json "
                        "VARCHAR(8000) NOT NULL DEFAULT '{}'"
                    )
                )
            return
        if "postgres" in low or "postgresql" in low:
            conn.execute(
                text(
                    "ALTER TABLE datasecurefieldusagereportitem "
                    "ADD COLUMN IF NOT EXISTS extra_snapshot_json VARCHAR(8000) NOT NULL DEFAULT '{}'"
                )
            )
            return
        return


def _ensure_data_secure_field_request_request_type() -> None:
    """字段新增申请：补 request_type 列，区分数据字段/业务功能申请。"""
    low = str(_database_url).lower()
    with engine.begin() as conn:
        if "sqlite" in low:
            rows = conn.execute(text("PRAGMA table_info(datasecurefieldrequest)")).fetchall()
            names = {str(r[1]) for r in rows} if rows else set()
            if names and "request_type" not in names:
                conn.execute(
                    text(
                        "ALTER TABLE datasecurefieldrequest ADD COLUMN request_type "
                        "VARCHAR(32) NOT NULL DEFAULT 'data_field'"
                    )
                )
            return
        if "postgres" in low or "postgresql" in low:
            conn.execute(
                text(
                    "ALTER TABLE datasecurefieldrequest "
                    "ADD COLUMN IF NOT EXISTS request_type VARCHAR(32) NOT NULL DEFAULT 'data_field'"
                )
            )
            return
        return


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    _ensure_tool_runtime_status_column()
    _ensure_data_secure_relevance_rule_columns()
    _ensure_data_secure_classification_evolution()
    _ensure_data_secure_classification_matrix()
    _ensure_data_secure_usage_report_item_extra_snapshot()
    _ensure_data_secure_field_request_request_type()
    _ensure_data_secure_usage_report_workflow_columns()
    _ensure_data_secure_function_name_varchar_500()
    _ensure_data_secure_question_help_text_varchar_8000()
    seed_initial_data()
    with Session(engine) as session:
        _backfill_apiaccesslog_behavior_labels(session)

def get_session():
    with Session(engine) as session:
        yield session
