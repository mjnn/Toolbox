from datetime import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, EmailStr, Field, model_validator
from typing import Literal
from app.models import ServiceBaseUrlMode, ServiceRuleCategory, ToolRuntimeStatus

# Token schemas
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class RefreshTokenRequest(BaseModel):
    refresh_token: str

# User schemas
class UserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    department: Optional[str] = None


class UserCreate(UserBase):
    password: str
    full_name: str = Field(..., min_length=1, max_length=100)
    department: str = Field(..., min_length=1, max_length=100)
    requested_tool_id: Optional[int] = None
    requested_tool_reason: Optional[str] = Field(default=None, max_length=500)
    registration_entry: Optional[Literal["direct_register", "apply_tool"]] = None


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = None
    department: Optional[str] = Field(None, max_length=100)


class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str


class AccountDeleteConfirm(BaseModel):
    """注销本账号时校验登录密码"""

    password: str


class RegisterResponse(BaseModel):
    message: str
    username: str


class PublicNewToolSuggestionCreate(BaseModel):
    nickname: str = Field(..., min_length=1, max_length=50)
    contact: Optional[str] = Field(default=None, max_length=100)
    content: str = Field(..., min_length=5, max_length=2000)


class UserInDB(UserBase):
    id: int
    is_active: bool
    is_superuser: bool
    """唯一超级管理员；系统级配置仅该账号可操作。"""
    is_platform_admin: bool = False
    """是否持有 platform_admin 角色（与 is_superuser 独立）。"""
    is_approved: bool
    avatar_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PaginatedUsers(BaseModel):
    total: int
    items: List[UserInDB]


class UserLogin(BaseModel):
    username: str
    password: str

# Role schemas
class RoleBase(BaseModel):
    name: str
    description: Optional[str] = None

class RoleCreate(RoleBase):
    pass

class RoleInDB(RoleBase):
    id: int
    is_system: bool

    class Config:
        from_attributes = True


class RoleAssignmentRequest(BaseModel):
    role_name: Literal["tool_owner", "tool_user", "platform_admin"]


class UserRolesResponse(BaseModel):
    user_id: int
    roles: List[str]


class AdminUserImportIssue(BaseModel):
    row: int
    email: Optional[str] = None
    username: Optional[str] = None
    reason: str


class AdminUserImportResponse(BaseModel):
    total_rows: int
    created_count: int
    skipped_count: int
    created_users: List[UserInDB]
    skipped_items: List[AdminUserImportIssue]


class AdminResetPasswordRequest(BaseModel):
    new_password: str = Field(..., min_length=8, max_length=128)


class AdminToolAssignmentOption(BaseModel):
    """管理员为用户勾选可用工具时的候选项。"""

    id: int
    name: str
    display_name: Optional[str] = None
    is_active: bool
    runtime_status: ToolRuntimeStatus = ToolRuntimeStatus.ACTIVE


class AdminUserAllowedToolsUpdate(BaseModel):
    """将用户可用工具同步为指定集合（已批准权限）；未列出的既有权限记录将被移除。"""

    tool_ids: List[int] = Field(default_factory=list)


class AdminUserAllowedToolsResponse(BaseModel):
    tool_ids: List[int]


class ToolTrafficRow(BaseModel):
    tool_id: int
    tool_name: str
    request_count: int


class ToolTrafficDashboardResponse(BaseModel):
    period: Literal["day", "week", "month"]
    range_start: datetime
    range_end: datetime
    rows: List[ToolTrafficRow]


class EnvFilePayload(BaseModel):
    """后端进程工作区根目录下的 .env 全文（UTF-8）。"""

    content: str = Field(default="", max_length=524288)


class BackendRestartRequest(BaseModel):
    """须与前端二次确认后提交的固定确认码一致。"""

    confirmation: str = Field(..., min_length=1, max_length=128)


# Tool schemas
class ToolBase(BaseModel):
    name: str
    description: Optional[str] = None
    display_name: Optional[str] = None
    display_description: Optional[str] = None
    version: str = "1.0.0"
    spec_revision: Optional[str] = None
    behavior_catalog_json: Optional[str] = None

class ToolCreate(ToolBase):
    pass

class ToolUpdate(BaseModel):
    description: Optional[str] = None
    is_active: Optional[bool] = None


class ToolStatusUpdate(BaseModel):
    """工具管理页：停启用与运行时状态（发版中可设「更新中」以阻止业务使用）。"""

    is_active: Optional[bool] = None
    runtime_status: Optional[ToolRuntimeStatus] = None

    @model_validator(mode="after")
    def at_least_one(self):
        if self.is_active is None and self.runtime_status is None:
            raise ValueError("is_active 与 runtime_status 须至少提供其一")
        return self


class ToolDisplayConfigUpdate(BaseModel):
    display_name: Optional[str] = Field(default=None, max_length=100)
    display_description: Optional[str] = Field(default=None, max_length=1000)


class ToolInDB(ToolBase):
    id: int
    is_active: bool
    runtime_status: ToolRuntimeStatus = ToolRuntimeStatus.ACTIVE
    created_at: datetime

    class Config:
        from_attributes = True


class ToolReleaseInDB(BaseModel):
    id: int
    tool_id: int
    version: str
    spec_revision: Optional[str] = None
    title: str
    changelog: str
    published_at: datetime
    published_by: int

    class Config:
        from_attributes = True


class ToolVersionSyncRequest(BaseModel):
    """宿主从工具接口拉取版本信息并记录到版本历史。"""

    notify_users: bool = True


class ToolVersionSyncResult(BaseModel):
    status: Literal["recorded", "no_change"]
    message: str
    release: ToolReleaseInDB


class PaginatedToolReleases(BaseModel):
    total: int
    items: List[ToolReleaseInDB]


AnnouncementVisibilityLiteral = Literal["global", "tool"]
AnnouncementPriorityLiteral = Literal["urgent", "notice", "reminder"]


class ToolAnnouncementBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=4000)
    is_enabled: bool = True
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    visibility: AnnouncementVisibilityLiteral = "global"
    priority: AnnouncementPriorityLiteral = "notice"
    scroll_speed_seconds: int = Field(default=45, ge=10, le=300)
    font_family: Optional[str] = Field(default=None, max_length=100)
    font_size_px: int = Field(default=14, ge=12, le=32)
    text_color: Optional[str] = Field(default=None, max_length=20)
    background_color: Optional[str] = Field(default=None, max_length=20)
    disable_feature_slugs: List[str] = Field(default_factory=list)


class ToolAnnouncementCreate(ToolAnnouncementBase):
    pass


class ToolAnnouncementUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    content: Optional[str] = Field(default=None, min_length=1, max_length=4000)
    is_enabled: Optional[bool] = None
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    visibility: Optional[AnnouncementVisibilityLiteral] = None
    priority: Optional[AnnouncementPriorityLiteral] = None
    scroll_speed_seconds: Optional[int] = Field(default=None, ge=10, le=300)
    font_family: Optional[str] = Field(default=None, max_length=100)
    font_size_px: Optional[int] = Field(default=None, ge=12, le=32)
    text_color: Optional[str] = Field(default=None, max_length=20)
    background_color: Optional[str] = Field(default=None, max_length=20)
    disable_feature_slugs: Optional[List[str]] = None


class ToolAnnouncementInDB(ToolAnnouncementBase):
    id: int
    tool_id: Optional[int] = None
    created_by: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PaginatedToolAnnouncements(BaseModel):
    total: int
    items: List[ToolAnnouncementInDB]


# Permission schemas
class PermissionBase(BaseModel):
    tool_id: int
    applied_reason: str

class PermissionCreate(PermissionBase):
    pass

class PermissionUpdate(BaseModel):
    status: Optional[str] = None
    review_notes: Optional[str] = None
    expires_at: Optional[datetime] = None

class PermissionInDB(PermissionBase):
    id: int
    user_id: int
    status: str
    applied_at: datetime
    reviewed_by: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None
    expires_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class PermissionWithDetails(PermissionInDB):
    user: UserInDB
    tool: ToolInDB
    reviewer: Optional[UserInDB] = None


class ToolOwnerInDB(BaseModel):
    id: int
    tool_id: int
    user_id: int
    assigned_at: datetime

    class Config:
        from_attributes = True


class ToolOwnerWithUser(ToolOwnerInDB):
    user: UserInDB


class ToolLicenseUserRow(BaseModel):
    """已获批使用某工具的用户及开通/最近使用时间（管理员或工具负责人可见）"""

    user: UserInDB
    granted_at: datetime
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PaginatedToolLicenseUsers(BaseModel):
    total: int
    items: List[ToolLicenseUserRow]


class ToolLicenseCandidateRow(BaseModel):
    """可批量授权/取消授权的候选用户（已排除管理员与当前操作人）。"""

    user: UserInDB
    currently_authorized: bool


class PaginatedToolLicenseCandidates(BaseModel):
    total: int
    items: List[ToolLicenseCandidateRow]


class ToolLicenseBatchUpdateRequest(BaseModel):
    action: Literal["grant", "revoke"]
    user_ids: List[int] = Field(default_factory=list)


class ToolLicenseBatchUpdateResult(BaseModel):
    action: Literal["grant", "revoke"]
    requested_count: int
    changed_count: int
    skipped_count: int


class ServiceBaseUrlJsonRow(BaseModel):
    key: str = Field(min_length=1, max_length=100)
    test: str = Field(min_length=1)
    uat: str = Field(min_length=1)
    live: str = Field(min_length=1)


class ServiceIdEntryBase(BaseModel):
    business_function: str = Field(min_length=1, max_length=20)
    business_description: str = Field(min_length=1, max_length=50)
    service_id: str = Field(min_length=1, max_length=200)
    service_type: str = Field(min_length=1, max_length=100)
    psga_availability: str = Field(min_length=1, max_length=100)
    package_name: str = Field(min_length=1, max_length=200)
    scope_type: str = Field(min_length=1, max_length=100)
    apn_type: str = Field(min_length=1, max_length=100)
    access_link_desc: str = Field(min_length=1, max_length=20)
    base_url_mode: ServiceBaseUrlMode
    base_url_json_key: Optional[str] = Field(default=None, max_length=100)
    base_url_test_input: str = Field(min_length=1)
    base_url_uat_input: str = Field(min_length=1)
    base_url_live_input: str = Field(min_length=1)
    base_url_json_rows: List[ServiceBaseUrlJsonRow] = Field(default_factory=list)
    extra_fields: Dict[str, Any] = Field(default_factory=dict)


class ServiceIdEntryCreate(ServiceIdEntryBase):
    pass


class ServiceIdEntryUpdate(ServiceIdEntryBase):
    id: int


class ServiceIdEntryInDB(BaseModel):
    id: int
    tool_id: int
    business_function: str
    business_description: str
    service_id: str
    service_type: str
    psga_availability: str
    package_name: str
    scope_type: str
    apn_type: str
    access_link_desc: str
    base_url_mode: ServiceBaseUrlMode
    base_url_json_key: Optional[str] = None
    base_url_test: str
    base_url_uat: str
    base_url_live: str
    extra_fields: Dict[str, Any] = Field(default_factory=dict)
    created_by: int
    updated_by: int
    created_by_name: Optional[str] = None
    updated_by_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ServiceIdEntryListResponse(BaseModel):
    can_manage_all: bool
    total: int
    items: List[ServiceIdEntryInDB]


class ServiceIdRuleOptionCreate(BaseModel):
    category: ServiceRuleCategory
    value: str = Field(min_length=1, max_length=100)


class ServiceIdRuleOptionUpdate(BaseModel):
    id: int
    value: Optional[str] = Field(default=None, min_length=1, max_length=100)
    is_active: Optional[bool] = None


class ServiceIdRuleOptionDelete(BaseModel):
    id: int


class ServiceIdRuleOptionInDB(BaseModel):
    id: int
    tool_id: int
    category: ServiceRuleCategory
    value: str
    is_active: bool
    created_by: int
    updated_by: int
    created_at: datetime
    updated_at: datetime


class ServiceIdRuleOptionGroupResponse(BaseModel):
    service_type: List[ServiceIdRuleOptionInDB] = Field(default_factory=list)
    psga: List[ServiceIdRuleOptionInDB] = Field(default_factory=list)
    scope_type: List[ServiceIdRuleOptionInDB] = Field(default_factory=list)
    apn_type: List[ServiceIdRuleOptionInDB] = Field(default_factory=list)


class PaginatedServiceIdRuleOptions(BaseModel):
    total: int
    items: List[ServiceIdRuleOptionInDB]


class ServiceIdFieldConfigItem(BaseModel):
    field_key: str
    label: str
    input_type: Literal["text", "textarea", "single_select", "multi_select"] = "text"
    is_builtin: bool = False
    sort_order: int = 0
    help_text: Optional[str] = None
    required: bool
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    regex_pattern: Optional[str] = None
    regex_error_message: Optional[str] = None
    allowed_values: List[str] = Field(default_factory=list)


class ServiceIdFieldConfigListResponse(BaseModel):
    items: List[ServiceIdFieldConfigItem]


class ServiceIdFieldConfigUpdateItem(BaseModel):
    field_key: str
    label: Optional[str] = Field(default=None, min_length=1, max_length=100)
    input_type: Optional[Literal["text", "textarea", "single_select", "multi_select"]] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = Field(default=None, ge=0, le=100000)
    help_text: Optional[str] = Field(default=None, max_length=500)
    required: Optional[bool] = None
    min_length: Optional[int] = Field(default=None, ge=0, le=5000)
    max_length: Optional[int] = Field(default=None, ge=0, le=5000)
    regex_pattern: Optional[str] = Field(default=None, max_length=500)
    regex_error_message: Optional[str] = Field(default=None, max_length=200)
    allowed_values: Optional[List[str]] = None


class ServiceIdFieldConfigUpdateRequest(BaseModel):
    items: List[ServiceIdFieldConfigUpdateItem]


class ServiceIdFieldConfigCreateRequest(BaseModel):
    field_key: str = Field(min_length=1, max_length=64)
    label: str = Field(min_length=1, max_length=100)
    input_type: Literal["text", "textarea", "single_select", "multi_select"] = "text"
    help_text: Optional[str] = Field(default=None, max_length=500)
    required: Optional[bool] = None
    min_length: Optional[int] = Field(default=None, ge=0, le=5000)
    max_length: Optional[int] = Field(default=None, ge=0, le=5000)
    regex_pattern: Optional[str] = Field(default=None, max_length=500)
    regex_error_message: Optional[str] = Field(default=None, max_length=200)
    allowed_values: Optional[List[str]] = None


class ServiceIdFieldConfigDeleteRequest(BaseModel):
    field_key: str = Field(min_length=1, max_length=64)


class ServiceIdExportColumnItem(BaseModel):
    key: str = Field(min_length=1, max_length=80)
    header: str = Field(min_length=1, max_length=200)


class ServiceIdExportColumnOption(BaseModel):
    key: str
    default_header: str
    group: Literal["builtin", "custom"] = "builtin"


class ServiceIdExportConfigResponse(BaseModel):
    options: List[ServiceIdExportColumnOption]
    columns: List[ServiceIdExportColumnItem]


class ServiceIdExportConfigUpdateRequest(BaseModel):
    columns: List[ServiceIdExportColumnItem] = Field(min_length=1, max_length=64)


class APIAccessLogInDB(BaseModel):
    id: int
    user_id: Optional[int] = None
    username: Optional[str] = None
    method: str
    path: str
    query_string: Optional[str] = None
    status_code: int
    latency_ms: int
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None
    tool_id: Optional[int] = None
    feature_name: Optional[str] = None
    behavior_label: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class APIAccessLogWithUser(APIAccessLogInDB):
    user: Optional[UserInDB] = None


class PaginatedAPIAccessLogs(BaseModel):
    total: int
    items: List[APIAccessLogWithUser]

# Notification schemas
class NotificationBase(BaseModel):
    title: str
    message: str
    notification_type: str = "system"
    related_id: Optional[int] = None

class NotificationCreate(NotificationBase):
    user_id: int

class NotificationInDB(NotificationBase):
    id: int
    user_id: int
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True

# Response schemas
class SuccessResponse(BaseModel):
    success: bool = True
    message: str


# Feedback
FeedbackCategoryLiteral = Literal["tool_usage", "new_tool_suggestion", "system_feedback"]


class FeedbackCreate(BaseModel):
    category: FeedbackCategoryLiteral
    title: Optional[str] = None
    content: str
    tool_id: Optional[int] = None


class FeedbackInDB(BaseModel):
    id: int
    user_id: int
    tool_id: Optional[int] = None
    category: str
    title: Optional[str] = None
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class FeedbackWithUser(FeedbackInDB):
    user: UserInDB


class PaginatedFeedbackWithUser(BaseModel):
    total: int
    items: List[FeedbackWithUser]


class FeedbackCountsResponse(BaseModel):
    """管理员首页角标：系统反馈 + 新工具建议条数"""

    system_feedback: int
    new_tool_suggestion: int
    total: int

class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    details: Optional[dict] = None


ToolEnvLiteral = Literal["uat", "live"]
SimProviderLiteral = Literal["unicom", "ctcc"]
UnicomSimProjectLiteral = Literal["CEI", "Audi_5G", "GP"]
X509ActionLiteral = Literal["check", "sign", "parse_csr", "parse_cert"]
UatEnrollmentActionLiteral = Literal["query_sp_info", "bind", "unbind"]
VehicleImportTargetLiteral = Literal["sp", "cdp", "afdp"]


class ToolFeatureResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None


class ToolVersionMetaResponse(BaseModel):
    version: str
    spec_revision: Optional[str] = None
    title: str
    changelog: str


class X509FeatureRequest(BaseModel):
    action: X509ActionLiteral
    env: ToolEnvLiteral = "uat"
    iam_sns: List[str] = Field(default_factory=list)
    csrs: List[str] = Field(default_factory=list)
    csr: Optional[str] = None
    cert: Optional[str] = None


class SimQueryRequest(BaseModel):
    provider: SimProviderLiteral
    project: Optional[UnicomSimProjectLiteral] = None
    search_value: Optional[str] = None
    iccid: Optional[str] = None
    msisdn: Optional[str] = None
    imsi: Optional[str] = None


class UatAfDpQueryRequest(BaseModel):
    vin: Optional[str] = None
    zxdsn: Optional[str] = None
    iamsn: Optional[str] = None
    iccid: Optional[str] = None


class UatSpQueryRequest(BaseModel):
    action: UatEnrollmentActionLiteral
    vin: str = Field(min_length=1)
    phone: Optional[str] = None


class UatVehicleImportRequest(BaseModel):
    target: VehicleImportTargetLiteral
    check_duplicated: bool = False
    vehicle_data: Dict[str, Any]


class UatVehicleConfigGenerateRequest(BaseModel):
    project: str = Field(min_length=1)
    car_software_version: str = Field(min_length=1)
    hu_fazit_id: str = Field(min_length=1)
    ocu_iccid: str = Field(min_length=1)
    msisdn: str = Field(min_length=1)
    ocu_fazit_id: str = Field(min_length=1)
    vehicle_vin: str = Field(min_length=1)
    application_department: str = Field(min_length=1)


class MosVehicleRuleRequest(BaseModel):
    rule: Dict[str, Any]


class MosVehicleRuleBulkImportRequest(BaseModel):
    rules: List[Dict[str, Any]]
    dry_run: bool = True


class MosRuntimeCredentialsUpdateRequest(BaseModel):
    uat_mos_portal_account: Optional[str] = None
    uat_mos_portal_password: Optional[str] = None
    oa_account: Optional[str] = None
    oa_password: Optional[str] = None
    request_timeout_seconds: Optional[int] = Field(default=None, ge=1, le=600)


class MosDbOptimizationUpdateRequest(BaseModel):
    pool_size: Optional[int] = Field(default=None, ge=1, le=32)
    max_overflow: Optional[int] = Field(default=None, ge=0, le=32)
    pool_timeout_seconds: Optional[int] = Field(default=None, ge=5, le=120)
    pool_recycle_seconds: Optional[int] = Field(default=None, ge=30, le=7200)
    workers: Optional[int] = Field(default=None, ge=1, le=16)
    statement_timeout_ms: Optional[int] = Field(default=None, ge=1000, le=120000)
    apply_to_env: bool = False


ToolRuntimeEnvLiteral = Literal["internal", "external"]


class ToolVisibilityConfigUpdate(BaseModel):
    external_hosts: Optional[List[str]] = None
    internal_visible_tool_keys: Optional[List[str]] = None
    external_visible_tool_keys: Optional[List[str]] = None


class ToolVisibilityConfigResponse(BaseModel):
    current_runtime_env: ToolRuntimeEnvLiteral
    runtime_env_source: str
    external_hosts: List[str]
    internal_visible_tool_keys: List[str]
    external_visible_tool_keys: List[str]
    all_tools: List[ToolInDB]


class MosTokenPreloadRequest(BaseModel):
    scopes: Optional[List[str]] = None
    wait: bool = False
    timeout_seconds: int = Field(default=60, ge=1, le=600)
    force_refresh: bool = False


class RsaLivestreamConfigResponse(BaseModel):
    stream_page_url: str
    resolved_stream_flv_url: Optional[str] = None
    internal_flv_proxy_url: str
    stream_server: str
    stream_key: str
    placeholder_enabled: bool
    placeholder_title: str
    placeholder_message: str
    updated_at: datetime


class RsaLivestreamConfigUpdateRequest(BaseModel):
    stream_page_url: Optional[str] = Field(default=None, min_length=1, max_length=2000)
    stream_server: Optional[str] = Field(default=None, min_length=1, max_length=255)
    stream_key: Optional[str] = Field(default=None, min_length=1, max_length=255)
    placeholder_enabled: Optional[bool] = None
    placeholder_title: Optional[str] = Field(default=None, min_length=1, max_length=120)
    placeholder_message: Optional[str] = Field(default=None, min_length=1, max_length=1000)


DataSecureQuestionTypeLiteral = Literal["yes_no"]


class DataSecureProjectSpaceCreate(BaseModel):
    space_key: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=1000)
    is_active: bool = True
    copy_from_project_space_id: Optional[int] = Field(
        default=None,
        description="复制源项目空间 ID；填写时须同时填写 change_reason；新建后复制问卷、相关性规则、生命周期表头、分类树、分类分级/安全要求绑定、关键词规则与显式矩阵（不含主表数据与填报记录）",
    )
    change_reason: Optional[str] = Field(default=None, min_length=5, max_length=1000)


class DataSecureProjectSpaceDeleteRequest(BaseModel):
    id: int
    change_reason: str = Field(min_length=5, max_length=1000)


class DataSecureProjectSpaceDeleteResult(BaseModel):
    ok: bool = True


DataSecureIdentifierKeyTarget = Literal["space_key", "question_key", "lifecycle_field_key", "taxonomy_node_key"]


class DataSecureSuggestIdentifierKeyRequest(BaseModel):
    source_text: str = Field(min_length=1, max_length=800)
    target: DataSecureIdentifierKeyTarget


class DataSecureSuggestIdentifierKeyResponse(BaseModel):
    key: str


class DataSecureProjectSpaceUpdate(BaseModel):
    id: int
    space_key: Optional[str] = Field(default=None, min_length=1, max_length=64)
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=1000)
    is_active: Optional[bool] = None


class DataSecureProjectSpaceInDB(BaseModel):
    id: int
    tool_id: int
    space_key: str
    name: str
    description: Optional[str] = None
    is_active: bool
    created_by: int
    updated_by: int
    created_at: datetime
    updated_at: datetime


class PaginatedDataSecureProjectSpaces(BaseModel):
    total: int
    items: List[DataSecureProjectSpaceInDB]


class DataSecureQuestionCreate(BaseModel):
    project_space_id: int
    question_key: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]{1,64}$")
    title: str = Field(min_length=1, max_length=300)
    help_text: Optional[str] = Field(default=None, max_length=8000)
    question_type: DataSecureQuestionTypeLiteral = "yes_no"
    is_required: bool = True
    sort_order: int = Field(default=0, ge=0, le=100000)
    is_active: bool = True


class DataSecureQuestionUpdate(BaseModel):
    id: int
    title: Optional[str] = Field(default=None, min_length=1, max_length=300)
    help_text: Optional[str] = Field(default=None, max_length=8000)
    is_required: Optional[bool] = None
    sort_order: Optional[int] = Field(default=None, ge=0, le=100000)
    is_active: Optional[bool] = None


class DataSecureQuestionDeleteRequest(BaseModel):
    id: int
    change_reason: str = Field(min_length=5, max_length=1000)


class DataSecureQuestionDeleteResult(BaseModel):
    ok: bool = True


class DataSecureQuestionInDB(BaseModel):
    id: int
    tool_id: int
    project_space_id: int
    question_key: str
    title: str
    help_text: Optional[str] = None
    question_type: DataSecureQuestionTypeLiteral
    is_required: bool
    sort_order: int
    is_active: bool
    created_by: int
    updated_by: int
    created_at: datetime
    updated_at: datetime


class PaginatedDataSecureQuestions(BaseModel):
    total: int
    items: List[DataSecureQuestionInDB]


class DataSecureRelevanceRuleUpsert(BaseModel):
    project_space_id: int
    min_yes_count: int = Field(ge=0, le=1000)
    logic_operator: Literal["and", "or"] = "and"
    question_keys: List[str] = Field(default_factory=list)
    logic_expression: Optional[str] = Field(default=None, max_length=2000)
    notes: Optional[str] = Field(default=None, max_length=1000)
    change_reason: str = Field(min_length=5, max_length=1000)


class DataSecureRelevanceRuleInDB(BaseModel):
    id: int
    tool_id: int
    project_space_id: int
    min_yes_count: int
    logic_operator: Literal["and", "or"] = "and"
    question_keys: List[str] = Field(default_factory=list)
    logic_expression: Optional[str] = None
    notes: Optional[str] = None
    updated_by: int
    updated_at: datetime


class DataSecureAssessmentAnswerInput(BaseModel):
    question_id: int
    answer_bool: bool
    answer_text: Optional[str] = Field(default=None, max_length=1000)


class DataSecureAssessmentSubmitRequest(BaseModel):
    project_space_id: int
    function_name: str = Field(min_length=1, max_length=500)
    function_description: Optional[str] = Field(default=None, max_length=2000)
    answers: List[DataSecureAssessmentAnswerInput] = Field(min_length=1)


class DataSecureAssessmentAnswerInDB(BaseModel):
    question_id: int
    question_key: str
    question_title: str
    answer_bool: bool
    answer_text: Optional[str] = None


class DataSecureAssessmentSubmissionInDB(BaseModel):
    id: int
    tool_id: int
    project_space_id: int
    project_space_name: str
    submitted_by: int
    submitted_by_name: Optional[str] = None
    function_name: str
    function_description: Optional[str] = None
    yes_count: int
    total_count: int
    is_related: bool
    result_summary: str
    submitted_at: datetime
    answers: List[DataSecureAssessmentAnswerInDB] = Field(default_factory=list)


class PaginatedDataSecureAssessmentSubmissions(BaseModel):
    total: int
    items: List[DataSecureAssessmentSubmissionInDB]


DataSecureFieldRequestStatusLiteral = Literal["pending", "approved", "rejected"]
DataSecureFieldInputTypeLiteral = Literal["text", "textarea", "single_select", "multi_select"]


class DataSecureLifecycleFieldConfigItem(BaseModel):
    field_key: str
    label: str
    input_type: DataSecureFieldInputTypeLiteral = "text"
    is_builtin: bool = False
    sort_order: int = 0
    help_text: Optional[str] = None
    required: bool
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    regex_pattern: Optional[str] = None
    regex_error_message: Optional[str] = None
    allowed_values: List[str] = Field(default_factory=list)


class DataSecureLifecycleFieldConfigListResponse(BaseModel):
    items: List[DataSecureLifecycleFieldConfigItem]


class DataSecureLifecycleFieldConfigUpdateItem(BaseModel):
    field_key: str
    label: Optional[str] = Field(default=None, min_length=1, max_length=100)
    input_type: Optional[DataSecureFieldInputTypeLiteral] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = Field(default=None, ge=0, le=100000)
    help_text: Optional[str] = Field(default=None, max_length=500)
    required: Optional[bool] = None
    min_length: Optional[int] = Field(default=None, ge=0, le=5000)
    max_length: Optional[int] = Field(default=None, ge=0, le=5000)
    regex_pattern: Optional[str] = Field(default=None, max_length=500)
    regex_error_message: Optional[str] = Field(default=None, max_length=200)
    allowed_values: Optional[List[str]] = None


class DataSecureLifecycleFieldConfigUpdateRequest(BaseModel):
    project_space_id: int
    items: List[DataSecureLifecycleFieldConfigUpdateItem]
    change_reason: str = Field(min_length=5, max_length=1000)


class DataSecureLifecycleFieldConfigCreateRequest(BaseModel):
    project_space_id: int
    field_key: str = Field(min_length=1, max_length=64)
    label: str = Field(min_length=1, max_length=100)
    input_type: DataSecureFieldInputTypeLiteral = "text"
    help_text: Optional[str] = Field(default=None, max_length=500)
    required: Optional[bool] = None
    min_length: Optional[int] = Field(default=None, ge=0, le=5000)
    max_length: Optional[int] = Field(default=None, ge=0, le=5000)
    regex_pattern: Optional[str] = Field(default=None, max_length=500)
    regex_error_message: Optional[str] = Field(default=None, max_length=200)
    allowed_values: Optional[List[str]] = None
    change_reason: str = Field(min_length=5, max_length=1000)


class DataSecureLifecycleFieldConfigDeleteRequest(BaseModel):
    project_space_id: int
    field_key: str = Field(min_length=1, max_length=64)
    change_reason: str = Field(min_length=5, max_length=1000)


class DataSecureFieldCatalogEntryInDB(BaseModel):
    id: int
    tool_id: int
    project_space_id: int
    field_name: str
    extra_fields: Dict[str, Any] = Field(default_factory=dict)
    created_by: int
    updated_by: int
    created_at: datetime
    updated_at: datetime


class PaginatedDataSecureFieldCatalogEntries(BaseModel):
    total: int
    items: List[DataSecureFieldCatalogEntryInDB]


class DataSecureFieldCatalogExtraUpdate(BaseModel):
    extra_fields: Dict[str, Any] = Field(default_factory=dict)


class DataSecureFieldCatalogEntryCreate(BaseModel):
    project_space_id: int
    field_name: str = Field(min_length=1, max_length=200)
    extra_fields: Dict[str, Any] = Field(default_factory=dict)


class DataSecureFieldCatalogBatchItem(BaseModel):
    field_name: str = Field(min_length=1, max_length=200)
    extra_fields: Dict[str, Any] = Field(default_factory=dict)


class DataSecureFieldCatalogBatchImport(BaseModel):
    project_space_id: int
    items: List[DataSecureFieldCatalogBatchItem] = Field(min_length=1, max_length=500)
    # 导入时由前端汇总：CSV 表头解析出的 field_key -> 展示用列名（用于自动新增填报表单字段的 label）
    auto_field_labels: Dict[str, str] = Field(default_factory=dict)


class DataSecureFieldCatalogBatchImportResult(BaseModel):
    created_count: int = 0
    skipped_duplicate: int = 0
    failed_validation: int = 0
    errors: List[str] = Field(default_factory=list)
    # 本次导入前自动新建的自定义填报表单字段 key（默认单行文本、无额外限制）
    auto_created_field_keys: List[str] = Field(default_factory=list)


class DataSecureFieldCatalogValueOptionsResponse(BaseModel):
    field_key: str
    q: str = ""
    options: List[str] = Field(default_factory=list)


class DataSecureFieldRequestCreate(BaseModel):
    project_space_id: int
    request_type: Literal["data_field", "business_function"] = "data_field"
    field_name: str = Field(min_length=1, max_length=200)
    reason: Optional[str] = Field(default=None, max_length=1000)
    extra_fields: Dict[str, Any] = Field(default_factory=dict)


class DataSecureFieldRequestReview(BaseModel):
    status: Literal["approved", "rejected"]
    review_notes: Optional[str] = Field(default=None, max_length=1000)


class DataSecureFieldRequestInDB(BaseModel):
    id: int
    tool_id: int
    project_space_id: int
    project_space_name: str
    requested_by: int
    requested_by_name: Optional[str] = None
    request_type: Literal["data_field", "business_function"] = "data_field"
    field_name: str
    reason: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    status: DataSecureFieldRequestStatusLiteral
    review_notes: Optional[str] = None
    reviewed_by: Optional[int] = None
    reviewed_by_name: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class PaginatedDataSecureFieldRequests(BaseModel):
    total: int
    items: List[DataSecureFieldRequestInDB]


class DataSecureBusinessFunctionOptionsResponse(BaseModel):
    """相关性判定「功能名称」下拉：来自填报表单「业务功能」列允许值与主表已填值并集。"""

    field_key: Optional[str] = None
    business_function_configured: bool = False
    options: List[str] = Field(default_factory=list)


class DataSecureBusinessFunctionOptionRequestCreate(BaseModel):
    project_space_id: int
    proposed_option: str = Field(min_length=1, max_length=200)
    reason: Optional[str] = Field(default=None, max_length=1000)


class DataSecureBusinessFunctionOptionRequestReview(BaseModel):
    status: Literal["approved", "rejected"]
    review_notes: Optional[str] = Field(default=None, max_length=1000)


class DataSecureBusinessFunctionOptionRequestInDB(BaseModel):
    id: int
    tool_id: int
    project_space_id: int
    project_space_name: str
    requested_by: int
    requested_by_name: Optional[str] = None
    proposed_option: str
    reason: Optional[str] = None
    status: DataSecureFieldRequestStatusLiteral
    review_notes: Optional[str] = None
    reviewed_by: Optional[int] = None
    reviewed_by_name: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class PaginatedDataSecureBusinessFunctionOptionRequests(BaseModel):
    total: int
    items: List[DataSecureBusinessFunctionOptionRequestInDB]


class DataSecureFieldUsageLineCreate(BaseModel):
    catalog_entry_id: int
    extra_fields: Dict[str, Any] = Field(default_factory=dict)


DataSecureUsageReviewStatusLiteral = Literal["pending", "approved", "rejected"]


class DataSecureFieldUsageReportCreate(BaseModel):
    project_space_id: int
    """须与本次问卷判定同一批次：传相关性判定提交记录 id。"""
    assessment_submission_id: int
    """兼容旧客户端：仅传 field_entry_ids 且无其他信息时仍可用。"""
    function_name: Optional[str] = Field(default=None, max_length=500)
    function_description: Optional[str] = Field(default=None, max_length=2000)
    field_entry_ids: Optional[List[int]] = None
    lines: Optional[List[DataSecureFieldUsageLineCreate]] = None
    notes: Optional[str] = Field(default=None, max_length=1000)


class DataSecureFieldUsageReportReviewRequest(BaseModel):
    status: Literal["approved", "rejected"]
    review_notes: Optional[str] = Field(default=None, max_length=1000)


class DataSecureFieldUsageReportInDB(BaseModel):
    id: int
    tool_id: int
    project_space_id: int
    project_space_name: str
    submitted_by: int
    submitted_by_name: Optional[str] = None
    assessment_submission_id: Optional[int] = None
    function_name: str
    function_description: Optional[str] = None
    field_entry_ids: List[int] = Field(default_factory=list)
    field_names: List[str] = Field(default_factory=list)
    notes: Optional[str] = None
    review_status: DataSecureUsageReviewStatusLiteral = "pending"
    review_notes: Optional[str] = None
    reviewed_by: Optional[int] = None
    reviewed_by_name: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    submitted_at: datetime


class PaginatedDataSecureFieldUsageReports(BaseModel):
    total: int
    items: List[DataSecureFieldUsageReportInDB]


class DataSecureWorkOrderRow(BaseModel):
    """一次工单：问卷 +（可选）字段填报与审批。"""

    assessment_submission_id: int
    questionnaire_submitted_at: datetime
    function_name: str
    is_related: bool
    result_summary: str
    field_usage_report_id: Optional[int] = None
    usage_submitted_at: Optional[datetime] = None
    review_status: Optional[str] = None
    review_notes: Optional[str] = None


class PaginatedDataSecureWorkOrders(BaseModel):
    total: int
    items: List[DataSecureWorkOrderRow]


class DataSecureFieldUsageExportRow(BaseModel):
    project_space_name: str
    function_name: str
    function_description: Optional[str] = None
    data_field_name: str
    """该次填报中该数据字段的「其他信息」快照（JSON 字符串）；不参与自动分类分级与安全要求。"""
    other_info_json: Optional[str] = None
    submitted_by_name: Optional[str] = None
    submitted_at: datetime


class DataSecureFieldUsageExportResponse(BaseModel):
    items: List[DataSecureFieldUsageExportRow]


class DataSecureConsolidatedExportRow(BaseModel):
    """过审工单合并行：问卷摘要 + 填报快照 + 主表分类分级 + 安全要求文案（配置级）。"""

    project_space_name: str
    assessment_submission_id: int
    questionnaire_submitted_at: datetime
    is_related: bool
    result_summary: str
    field_usage_report_id: int
    usage_submitted_at: datetime
    submitted_by_name: Optional[str] = None
    data_field_name: str
    other_info_json: str = "{}"
    category: str = ""
    level: str = ""
    auto_category: str = ""
    auto_level: str = ""
    auto_hit_summary: Optional[str] = None
    security_requirements_text: str = ""


class DataSecureConsolidatedExportResponse(BaseModel):
    items: List[DataSecureConsolidatedExportRow]


class DataSecureClassificationRuleInDB(BaseModel):
    id: int
    tool_id: int
    project_space_id: int
    keyword: str
    category: str
    level: str
    priority: int = 100
    notes: Optional[str] = None
    sort_order: int
    is_active: bool
    created_by: int
    updated_by: int
    created_at: datetime
    updated_at: datetime


class DataSecureClassificationRuleCreate(BaseModel):
    project_space_id: int
    keyword: str = Field(min_length=1, max_length=100)
    category: str = Field(min_length=1, max_length=100)
    level: str = Field(min_length=1, max_length=100)
    priority: int = Field(default=100, ge=0, le=1_000_000)
    notes: Optional[str] = Field(default=None, max_length=1000)
    sort_order: int = Field(default=0, ge=0, le=100000)


class DataSecureClassificationRuleUpdate(BaseModel):
    id: int
    keyword: Optional[str] = Field(default=None, min_length=1, max_length=100)
    category: Optional[str] = Field(default=None, min_length=1, max_length=100)
    level: Optional[str] = Field(default=None, min_length=1, max_length=100)
    priority: Optional[int] = Field(default=None, ge=0, le=1_000_000)
    notes: Optional[str] = Field(default=None, max_length=1000)
    sort_order: Optional[int] = Field(default=None, ge=0, le=100000)
    is_active: Optional[bool] = None
    change_reason: str = Field(min_length=5, max_length=1000)


class DataSecureClassificationRuleDeleteResult(BaseModel):
    ok: bool = True


class PaginatedDataSecureClassificationRules(BaseModel):
    total: int
    items: List[DataSecureClassificationRuleInDB]


class DataSecureClassificationMatrixInDB(BaseModel):
    id: int
    tool_id: int
    project_space_id: int
    field_name: str
    extension_match: Dict[str, Any] = Field(default_factory=dict)
    category: str
    level: str
    priority: int = 200
    notes: Optional[str] = None
    sort_order: int = 0
    is_active: bool
    created_by: int
    updated_by: int
    created_at: datetime
    updated_at: datetime


class DataSecureClassificationMatrixCreate(BaseModel):
    project_space_id: int
    field_name: str = Field(min_length=1, max_length=200)
    extension_match: Dict[str, Any] = Field(default_factory=dict)
    category: str = Field(min_length=1, max_length=100)
    level: str = Field(min_length=1, max_length=100)
    priority: int = Field(default=200, ge=0, le=1_000_000)
    notes: Optional[str] = Field(default=None, max_length=1000)
    sort_order: int = Field(default=0, ge=0, le=100000)


class DataSecureClassificationMatrixUpdate(BaseModel):
    id: int
    field_name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    extension_match: Optional[Dict[str, Any]] = None
    category: Optional[str] = Field(default=None, min_length=1, max_length=100)
    level: Optional[str] = Field(default=None, min_length=1, max_length=100)
    priority: Optional[int] = Field(default=None, ge=0, le=1_000_000)
    notes: Optional[str] = Field(default=None, max_length=1000)
    sort_order: Optional[int] = Field(default=None, ge=0, le=100000)
    is_active: Optional[bool] = None
    change_reason: str = Field(min_length=5, max_length=1000)


class DataSecureClassificationMatrixDeleteResult(BaseModel):
    ok: bool = True


class DataSecureClassificationMatrixBatchItem(BaseModel):
    field_name: str = Field(min_length=1, max_length=200)
    extension_match: Dict[str, Any] = Field(default_factory=dict)
    category: str = Field(min_length=1, max_length=100)
    level: str = Field(min_length=1, max_length=100)
    priority: int = Field(default=200, ge=0, le=1_000_000)
    notes: Optional[str] = Field(default=None, max_length=1000)
    sort_order: int = Field(default=0, ge=0, le=100000)


class DataSecureClassificationMatrixBatchImport(BaseModel):
    project_space_id: int
    items: List[DataSecureClassificationMatrixBatchItem] = Field(min_length=1, max_length=500)


class DataSecureClassificationMatrixBatchImportResult(BaseModel):
    created_count: int = 0
    failed_validation: int = 0
    errors: List[str] = Field(default_factory=list)


class PaginatedDataSecureClassificationMatrix(BaseModel):
    total: int
    items: List[DataSecureClassificationMatrixInDB]


class DataSecureClassificationResultInDB(BaseModel):
    id: int
    tool_id: int
    project_space_id: int
    catalog_entry_id: int
    field_name_snapshot: str
    category: str
    level: str
    rule_keyword: Optional[str] = None
    auto_category: str
    auto_level: str
    auto_rule_keyword: Optional[str] = None
    auto_rule_id: Optional[int] = None
    auto_matrix_id: Optional[int] = None
    auto_match_source: str = "keyword"
    auto_hit_summary: Optional[str] = None
    manual_reason: Optional[str] = None
    source: str
    updated_by: int
    updated_by_name: Optional[str] = None
    updated_at: datetime


class PaginatedDataSecureClassificationResults(BaseModel):
    total: int
    items: List[DataSecureClassificationResultInDB]


class DataSecureClassificationRecomputeResponse(BaseModel):
    updated_count: int


class DataSecureClassificationManualOverride(BaseModel):
    category: str = Field(min_length=1, max_length=100)
    level: str = Field(min_length=1, max_length=100)
    reason: str = Field(min_length=1, max_length=500)


class DataSecureClassificationAuditLogInDB(BaseModel):
    id: int
    tool_id: int
    project_space_id: int
    catalog_entry_id: Optional[int] = None
    result_id: Optional[int] = None
    user_id: int
    user_name: Optional[str] = None
    action: str
    detail: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class PaginatedDataSecureClassificationAuditLogs(BaseModel):
    total: int
    items: List[DataSecureClassificationAuditLogInDB]


class DataSecureClassificationExportRow(BaseModel):
    project_space_id: int
    catalog_entry_id: int
    field_name: str
    effective_category: str
    effective_level: str
    effective_rule_keyword: Optional[str] = None
    source: str
    auto_category: str
    auto_level: str
    auto_rule_keyword: Optional[str] = None
    auto_rule_id: Optional[int] = None
    auto_matrix_id: Optional[int] = None
    auto_match_source: str = "keyword"
    auto_hit_summary: Optional[str] = None
    manual_reason: Optional[str] = None
    updated_by_name: Optional[str] = None
    updated_at: datetime


class DataSecureClassificationExportResponse(BaseModel):
    items: List[DataSecureClassificationExportRow]


# --- 结构化治理：分类树（L1/L2）、数据字段分级（C0–C3）、安全要求逻辑表达式 ---


class DataSecureTaxonomyNodeInDB(BaseModel):
    id: int
    tool_id: int
    project_space_id: int
    parent_id: Optional[int] = None
    name: str
    node_key: str
    sort_order: int
    is_active: bool
    created_by: int
    updated_by: int
    created_at: datetime
    updated_at: datetime


class PaginatedDataSecureTaxonomyNodes(BaseModel):
    total: int
    items: List[DataSecureTaxonomyNodeInDB]


class DataSecureTaxonomyNodeCreate(BaseModel):
    project_space_id: int
    parent_id: Optional[int] = None
    name: str = Field(min_length=1, max_length=200)
    node_key: str = Field(min_length=1, max_length=64)
    sort_order: int = Field(default=0, ge=0, le=100000)
    change_reason: str = Field(min_length=5, max_length=1000)


class DataSecureTaxonomyNodeUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    sort_order: Optional[int] = Field(default=None, ge=0, le=100000)
    is_active: Optional[bool] = None
    change_reason: str = Field(min_length=5, max_length=1000)


class DataSecureTaxonomyNodeDeleteResult(BaseModel):
    ok: bool = True


class DataSecureFieldClassGradeInDB(BaseModel):
    id: int
    tool_id: int
    project_space_id: int
    catalog_entry_id: int
    field_name: str = ""
    taxonomy_l1_id: Optional[int] = None
    taxonomy_l2_id: Optional[int] = None
    taxonomy_l1_name: Optional[str] = None
    taxonomy_l2_name: Optional[str] = None
    taxonomy_path: Optional[str] = None
    taxonomy_path_ids: Optional[List[int]] = None
    confidentiality_grade: str
    notes: Optional[str] = None
    created_by: int
    updated_by: int
    created_at: datetime
    updated_at: datetime


class PaginatedDataSecureFieldClassGrades(BaseModel):
    total: int
    items: List[DataSecureFieldClassGradeInDB]


class DataSecureFieldClassGradeUpsert(BaseModel):
    project_space_id: int
    catalog_entry_id: int
    taxonomy_l1_id: Optional[int] = None
    taxonomy_l2_id: Optional[int] = None
    confidentiality_grade: str = Field(min_length=1, max_length=32)
    notes: Optional[str] = Field(default=None, max_length=1000)
    change_reason: str = Field(min_length=5, max_length=1000)


class DataSecureFieldSecurityRequirementInDB(BaseModel):
    id: int
    tool_id: int
    project_space_id: int
    catalog_entry_id: int
    field_name: str = ""
    requirement_text: str
    logic_expression: str
    predicate_map: Dict[str, Any] = Field(default_factory=dict)
    priority: int
    sort_order: int
    is_active: bool
    created_by: int
    updated_by: int
    created_at: datetime
    updated_at: datetime


class PaginatedDataSecureFieldSecurityRequirements(BaseModel):
    total: int
    items: List[DataSecureFieldSecurityRequirementInDB]


class DataSecureFieldSecurityRequirementCreate(BaseModel):
    project_space_id: int
    catalog_entry_id: int
    requirement_text: str = Field(min_length=1, max_length=4000)
    logic_expression: str = Field(min_length=1, max_length=2000)
    predicate_map: Dict[str, Any] = Field(default_factory=dict)
    priority: int = Field(default=100, ge=0, le=1_000_000)
    sort_order: int = Field(default=0, ge=0, le=100000)
    change_reason: str = Field(min_length=5, max_length=1000)


class DataSecureFieldSecurityRequirementUpdate(BaseModel):
    requirement_text: Optional[str] = Field(default=None, min_length=1, max_length=4000)
    logic_expression: Optional[str] = Field(default=None, min_length=1, max_length=2000)
    predicate_map: Optional[Dict[str, Any]] = None
    priority: Optional[int] = Field(default=None, ge=0, le=1_000_000)
    sort_order: Optional[int] = Field(default=None, ge=0, le=100000)
    is_active: Optional[bool] = None
    change_reason: str = Field(min_length=5, max_length=1000)


class DataSecureFieldSecurityRequirementDeleteResult(BaseModel):
    ok: bool = True


class DataSecureGovernanceChangeLogInDB(BaseModel):
    id: int
    tool_id: int
    project_space_id: int
    domain: str
    action: str
    target_type: str
    target_id: str
    change_reason: str
    detail: Dict[str, Any] = Field(default_factory=dict)
    changed_by: int
    changed_by_name: Optional[str] = None
    created_at: datetime


class PaginatedDataSecureGovernanceChangeLogs(BaseModel):
    total: int
    items: List[DataSecureGovernanceChangeLogInDB]


class DataSecureFieldSecurityRequirementEvalRequest(BaseModel):
    project_space_id: int
    catalog_entry_id: int


class DataSecureFieldSecurityRequirementEvalHit(BaseModel):
    requirement_id: int
    requirement_text: str
    logic_expression: str
    matched: bool


class DataSecureFieldSecurityRequirementEvalResponse(BaseModel):
    catalog_entry_id: int
    field_name: str
    confidentiality_grade: str
    category_path: str
    hits: List[DataSecureFieldSecurityRequirementEvalHit]


class DataSecureConfigExportSelection(BaseModel):
    include_spaces: bool = True
    include_questions: bool = True
    include_relevance_rule: bool = True
    include_lifecycle_fields: bool = True
    include_taxonomy_nodes: bool = True
    include_field_class_grades: bool = True
    include_security_requirements: bool = True
    include_classification_rules: bool = False
    include_classification_matrix: bool = False


class DataSecureConfigExportRequest(BaseModel):
    project_space_id: int
    selection: DataSecureConfigExportSelection = Field(default_factory=DataSecureConfigExportSelection)


class DataSecureConfigExportPayload(BaseModel):
    tool_key: str
    project_space_id: int
    exported_at: datetime
    selection: DataSecureConfigExportSelection
    spaces: List[DataSecureProjectSpaceInDB] = Field(default_factory=list)
    questions: List[DataSecureQuestionInDB] = Field(default_factory=list)
    relevance_rule: Optional[DataSecureRelevanceRuleInDB] = None
    lifecycle_fields: List[DataSecureLifecycleFieldConfigItem] = Field(default_factory=list)
    taxonomy_nodes: List[DataSecureTaxonomyNodeInDB] = Field(default_factory=list)
    field_class_grades: List[DataSecureFieldClassGradeInDB] = Field(default_factory=list)
    security_requirements: List[DataSecureFieldSecurityRequirementInDB] = Field(default_factory=list)
    classification_rules: List[DataSecureClassificationRuleInDB] = Field(default_factory=list)
    classification_matrix: List[DataSecureClassificationMatrixInDB] = Field(default_factory=list)


class DataSecureConfigImportRequest(BaseModel):
    target_project_space_id: int
    payload: DataSecureConfigExportPayload
    change_reason: str = Field(min_length=5, max_length=1000)


class DataSecureConfigImportResult(BaseModel):
    target_project_space_id: int
    imported_counts: Dict[str, int] = Field(default_factory=dict)


class DataSecureConfigDeleteDomainItem(BaseModel):
    domain: Literal[
        "question",
        "lifecycle_field",
        "taxonomy_node",
        "field_class_grade",
        "security_requirement",
    ]
    target_id: str = Field(min_length=1, max_length=200)


class DataSecureConfigBatchDeleteRequest(BaseModel):
    project_space_id: int
    change_reason: str = Field(min_length=5, max_length=1000)
    items: List[DataSecureConfigDeleteDomainItem] = Field(default_factory=list, min_length=1, max_length=500)


class DataSecureConfigBatchDeleteResult(BaseModel):
    deleted_count: int
    deleted_items: List[Dict[str, str]] = Field(default_factory=list)
    failed_items: List[Dict[str, str]] = Field(default_factory=list)
