from datetime import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, EmailStr, Field
from typing import Literal
from app.models import ServiceBaseUrlMode, ServiceRuleCategory

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
    role_name: Literal["tool_owner", "tool_user"]


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
    """工具管理页：可用 / 暂不可用"""

    is_active: bool


class ToolDisplayConfigUpdate(BaseModel):
    display_name: Optional[str] = Field(default=None, max_length=100)
    display_description: Optional[str] = Field(default=None, max_length=1000)


class ToolInDB(ToolBase):
    id: int
    is_active: bool
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


class ToolReleasePublish(BaseModel):
    """负责人发版：更新工具当前版本/规格修订号并写入发版记录，可选通知已授权用户与负责人。"""

    version: str = Field(..., min_length=1, max_length=32)
    spec_revision: Optional[str] = Field(default=None, max_length=32)
    title: str = Field(default="版本更新", min_length=1, max_length=200)
    changelog: str = Field(..., min_length=1, max_length=8000)
    notify_users: bool = True


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
