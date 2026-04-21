from datetime import datetime
from typing import Optional
from enum import Enum
from sqlmodel import SQLModel, Field
from sqlalchemy import UniqueConstraint

class PermissionStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True, max_length=50)
    email: str = Field(unique=True, index=True, max_length=100)
    hashed_password: str
    full_name: Optional[str] = Field(default=None, max_length=100)
    department: Optional[str] = Field(default=None, max_length=100)
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)
    """新注册用户默认 False，需管理员审核通过后方可登录。"""
    is_approved: bool = Field(default=True, index=True)
    avatar_url: Optional[str] = Field(default=None, max_length=512)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class Role(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True, max_length=50)
    description: Optional[str] = None
    is_system: bool = Field(default=False)  # 系统角色不能删除

class UserRole(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("user_id", "role_id", name="uq_user_role"),)
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    role_id: int = Field(foreign_key="role.id")
    assigned_at: datetime = Field(default_factory=datetime.utcnow)

class Tool(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True, max_length=100)
    description: Optional[str] = None
    version: str = Field(default="1.0.0", max_length=20)
    """对外发版号（semver 语义由团队约定）。"""
    spec_revision: Optional[str] = Field(default=None, max_length=32)
    """需求/模板修订版本（如 NEW_TOOL 模板中的 v0.2），展示在工具卡片上与发版记录中。"""
    behavior_catalog_json: Optional[str] = Field(
        default=None,
        description="JSON array of {key, label} for user-visible behavior names in usage logs",
    )
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ToolRelease(SQLModel, table=True):
    """工具发版记录：每次发版一条，用于详情页展示与发版通知。"""

    __tablename__ = "tool_release"

    id: Optional[int] = Field(default=None, primary_key=True)
    tool_id: int = Field(foreign_key="tool.id", index=True)
    version: str = Field(max_length=32)
    spec_revision: Optional[str] = Field(default=None, max_length=32)
    title: str = Field(default="版本更新", max_length=200)
    changelog: str = Field(max_length=8000)
    published_at: datetime = Field(default_factory=datetime.utcnow)
    published_by: int = Field(foreign_key="user.id")

class UserToolPermission(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("user_id", "tool_id", name="uq_user_tool_permission"),)
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    tool_id: int = Field(foreign_key="tool.id")
    status: PermissionStatus = Field(default=PermissionStatus.PENDING)
    applied_at: datetime = Field(default_factory=datetime.utcnow)
    applied_reason: str
    reviewed_by: Optional[int] = Field(default=None, foreign_key="user.id")
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None
    expires_at: Optional[datetime] = None

class Notification(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    title: str
    message: str
    is_read: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    notification_type: str = Field(default="system")  # system, permission, alert
    related_id: Optional[int] = None  # 关联的权限申请ID等


class ToolOwner(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("tool_id", "user_id", name="uq_tool_owner"),)
    id: Optional[int] = Field(default=None, primary_key=True)
    tool_id: int = Field(foreign_key="tool.id", index=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    assigned_at: datetime = Field(default_factory=datetime.utcnow)


class FeedbackCategory(str, Enum):
    """用户反馈类型"""

    TOOL_USAGE = "tool_usage"  # 工具使用与问题反馈（绑定 tool_id）
    NEW_TOOL_SUGGESTION = "new_tool_suggestion"  # 新增工具建议（全局）
    SYSTEM_FEEDBACK = "system_feedback"  # 系统使用与问题反馈（全局）


class Feedback(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    tool_id: Optional[int] = Field(default=None, foreign_key="tool.id", index=True)
    category: str = Field(index=True, max_length=50)
    title: Optional[str] = Field(default=None, max_length=200)
    content: str = Field(max_length=8000)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class APIAccessLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    username: Optional[str] = Field(default=None, index=True, max_length=50)
    method: str = Field(index=True, max_length=10)
    path: str = Field(index=True, max_length=255)
    query_string: Optional[str] = None
    status_code: int = Field(index=True)
    latency_ms: int = 0
    client_ip: Optional[str] = Field(default=None, max_length=64)
    user_agent: Optional[str] = None
    tool_id: Optional[int] = Field(default=None, foreign_key="tool.id", index=True)
    feature_name: Optional[str] = Field(
        default=None,
        index=True,
        max_length=200,
        description="Path segment after /features/, may include subpaths",
    )
    behavior_label: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Resolved Chinese label for feature_name",
    )
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class ServiceBaseUrlMode(str, Enum):
    STRING = "string"
    JSON = "json"


class ServiceRuleCategory(str, Enum):
    SERVICE_TYPE = "service_type"
    PSGA = "psga"
    SCOPE_TYPE = "scope_type"
    APN_TYPE = "apn_type"


class ServiceIdRegistryEntry(SQLModel, table=True):
    __table_args__ = (
        UniqueConstraint("service_id", name="uq_service_id_registry_service_id"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    tool_id: int = Field(foreign_key="tool.id", index=True)
    created_by: int = Field(foreign_key="user.id", index=True)
    updated_by: int = Field(foreign_key="user.id", index=True)

    business_function: str = Field(max_length=20)
    business_description: str = Field(max_length=50)
    service_id: str = Field(index=True, max_length=200)
    service_type: str = Field(max_length=100)
    psga_availability: str = Field(max_length=200)
    package_name: str = Field(max_length=200)
    scope_type: str = Field(max_length=100)
    apn_type: str = Field(max_length=100)
    access_link_desc: str = Field(max_length=20)

    base_url_mode: ServiceBaseUrlMode = Field(default=ServiceBaseUrlMode.STRING)
    base_url_json_key: Optional[str] = Field(default=None, max_length=100)
    base_url_test: str
    base_url_uat: str
    base_url_live: str

    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class ServiceIdRuleOption(SQLModel, table=True):
    __table_args__ = (
        UniqueConstraint("tool_id", "category", "value", name="uq_service_id_rule_option"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    tool_id: int = Field(foreign_key="tool.id", index=True)
    category: ServiceRuleCategory = Field(index=True)
    value: str = Field(max_length=100)
    is_active: bool = Field(default=True, index=True)
    created_by: int = Field(foreign_key="user.id", index=True)
    updated_by: int = Field(foreign_key="user.id", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class MosTokenPoolEntry(SQLModel, table=True):
    """MOS 集成工具箱 token 池（SP/Zone/VMP 等缓存）持久化，供多进程/多 worker 共享。"""

    __tablename__ = "mos_token_pool_entry"

    id: Optional[int] = Field(default=None, primary_key=True)
    cache_key: str = Field(unique=True, index=True, max_length=128)
    payload_enc: str = Field(description="Fernet 加密的 JSON 载荷")
    expires_at: datetime = Field(index=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ConfigChangeLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tool_id: int = Field(foreign_key="tool.id", index=True)
    changed_by: int = Field(foreign_key="user.id", index=True)
    action: str = Field(max_length=50, index=True)
    target: str = Field(max_length=100, index=True)
    summary: Optional[str] = Field(default=None, max_length=1000)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class ToolAnnouncement(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tool_id: Optional[int] = Field(default=None, foreign_key="tool.id", index=True)
    visibility: str = Field(default="global", index=True, max_length=20)
    priority: str = Field(default="notice", index=True, max_length=20)
    title: str = Field(max_length=200)
    content: str = Field(max_length=4000)
    is_enabled: bool = Field(default=True, index=True)
    start_at: Optional[datetime] = Field(default=None, index=True)
    end_at: Optional[datetime] = Field(default=None, index=True)
    scroll_speed_seconds: int = Field(default=45)
    font_family: Optional[str] = Field(default=None, max_length=100)
    font_size_px: int = Field(default=14)
    text_color: Optional[str] = Field(default=None, max_length=20)
    background_color: Optional[str] = Field(default=None, max_length=20)
    disable_feature_slugs_json: str = Field(default="[]", max_length=4000)
    created_by: int = Field(foreign_key="user.id", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow, index=True)
