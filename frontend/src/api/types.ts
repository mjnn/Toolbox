// 认证相关类型
export interface LoginRequest {
  username: string
  password: string
  grant_type?: string
  scope?: string
  client_id?: string | null
  client_secret?: string | null
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface RefreshTokenRequest {
  refresh_token: string
}

export interface SuccessResponse {
  success: boolean
  message: string
}

// 用户相关类型
export interface UserCreate {
  username: string
  email: string
  full_name: string
  department: string
  password: string
  requested_tool_id?: number
  requested_tool_reason?: string
  registration_entry?: 'direct_register' | 'apply_tool'
}

export interface UserUpdate {
  full_name?: string | null
  email?: string | null
  department?: string | null
}

export interface UserInDB {
  id: number
  username: string
  email: string
  full_name?: string | null
  department?: string | null
  is_active: boolean
  is_superuser: boolean
  /** false 时不可登录，需管理员审核 */
  is_approved: boolean
  avatar_url?: string | null
  created_at: string
  updated_at: string
}

export interface AccountDeleteConfirm {
  password: string
}

export interface RegisterResponse {
  message: string
  username: string
}

export interface PublicNewToolSuggestionPayload {
  nickname: string
  contact?: string
  content: string
}

export interface PasswordChangePayload {
  old_password: string
  new_password: string
}

export interface PaginatedUsers {
  total: number
  items: UserInDB[]
}

export interface NotificationInDB {
  id: number
  user_id: number
  title: string
  message: string
  notification_type: string
  related_id?: number | null
  is_read: boolean
  created_at: string
}

// 工具相关类型
export interface ToolCreate {
  name: string
  description?: string | null
  version?: string
}

export interface ToolInDB {
  id: number
  name: string
  description?: string | null
  display_name?: string | null
  display_description?: string | null
  version: string
  /** 需求/模板修订版本（如 v0.2），与发版时填写一致 */
  spec_revision?: string | null
  /** JSON 字符串：[{key,label}] 行为目录，供使用记录解析展示 */
  behavior_catalog_json?: string | null
  is_active: boolean
  created_at: string
}

export interface ToolReleaseInDB {
  id: number
  tool_id: number
  version: string
  spec_revision?: string | null
  title: string
  changelog: string
  published_at: string
  published_by: number
}

export interface PaginatedToolReleases {
  total: number
  items: ToolReleaseInDB[]
}

export interface ToolAnnouncementInDB {
  id: number
  tool_id?: number | null
  title: string
  content: string
  is_enabled: boolean
  start_at?: string | null
  end_at?: string | null
  visibility: 'global' | 'tool'
  priority: 'urgent' | 'notice' | 'reminder'
  scroll_speed_seconds: number
  font_family?: string | null
  font_size_px: number
  text_color?: string | null
  background_color?: string | null
  disable_feature_slugs: string[]
  created_by: number
  created_at: string
  updated_at: string
}

export interface PaginatedToolAnnouncements {
  total: number
  items: ToolAnnouncementInDB[]
}

export interface ToolReleasePublishPayload {
  version: string
  spec_revision?: string | null
  title?: string
  changelog: string
  notify_users?: boolean
}

export type RoleName = 'tool_owner' | 'tool_user'

export interface UserRolesResponse {
  user_id: number
  roles: RoleName[]
}

export interface AdminUserImportIssue {
  row: number
  email?: string | null
  username?: string | null
  reason: string
}

export interface AdminUserImportResponse {
  total_rows: number
  created_count: number
  skipped_count: number
  created_users: UserInDB[]
  skipped_items: AdminUserImportIssue[]
}

export interface RoleAssignmentRequest {
  role_name: RoleName
}

export interface AdminResetPasswordPayload {
  new_password: string
}

export interface ToolOwnerInDB {
  id: number
  tool_id: number
  user_id: number
  assigned_at: string
}

export interface ToolOwnerWithUser extends ToolOwnerInDB {
  user: UserInDB
}

/** 某工具已授权用户（管理员/负责人可见） */
export interface ToolLicenseUserRow {
  user: UserInDB
  granted_at: string
  expires_at?: string | null
  last_used_at?: string | null
}

export interface PaginatedToolLicenseUsers {
  total: number
  items: ToolLicenseUserRow[]
}

export type FormFieldInputType = 'text' | 'textarea' | 'single_select' | 'multi_select'
export type FormFieldValue = string | string[]
export type DynamicFormValues = Record<string, FormFieldValue>

export interface FormFieldConfigItem {
  field_key: string
  label: string
  input_type: FormFieldInputType
  is_builtin: boolean
  sort_order: number
  help_text?: string | null
  required: boolean
  min_length?: number | null
  max_length?: number | null
  regex_pattern?: string | null
  regex_error_message?: string | null
  allowed_values: string[]
}

export interface FormFieldConfigListResponse {
  items: FormFieldConfigItem[]
}

export interface FormFieldConfigCreatePayload {
  field_key: string
  label: string
  input_type: FormFieldInputType
  help_text?: string | null
  required?: boolean | null
  min_length?: number | null
  max_length?: number | null
  regex_pattern?: string | null
  regex_error_message?: string | null
  allowed_values?: string[] | null
}

export type ServiceBaseUrlMode = 'string' | 'json'
export type ServiceRuleCategory = 'service_type' | 'psga' | 'scope_type' | 'apn_type'
export type ServiceFieldInputType = FormFieldInputType

export interface ServiceBaseUrlJsonRowPayload {
  key: string
  test: string
  uat: string
  live: string
}

export interface ServiceIdEntryPayload {
  business_function: string
  business_description: string
  service_id: string
  service_type: string
  psga_availability: string
  package_name: string
  scope_type: string
  apn_type: string
  access_link_desc: string
  base_url_mode: ServiceBaseUrlMode
  base_url_json_key?: string | null
  base_url_test_input: string
  base_url_uat_input: string
  base_url_live_input: string
  base_url_json_rows?: ServiceBaseUrlJsonRowPayload[]
  extra_fields?: DynamicFormValues
}

export interface ServiceIdEntry extends Omit<ServiceIdEntryPayload, 'base_url_test_input' | 'base_url_uat_input' | 'base_url_live_input'> {
  id: number
  tool_id: number
  base_url_test: string
  base_url_uat: string
  base_url_live: string
  extra_fields: DynamicFormValues
  created_by: number
  updated_by: number
  created_by_name?: string | null
  updated_by_name?: string | null
  created_at: string
  updated_at: string
}

export interface ServiceIdEntryUpdatePayload extends ServiceIdEntryPayload {
  id: number
}

export interface ServiceIdEntryListResponse {
  can_manage_all: boolean
  total: number
  items: ServiceIdEntry[]
}

export interface ServiceIdRuleOption {
  id: number
  tool_id: number
  category: ServiceRuleCategory
  value: string
  is_active: boolean
  created_by: number
  updated_by: number
  created_at: string
  updated_at: string
}

export interface ServiceIdRuleOptionGroup {
  service_type: ServiceIdRuleOption[]
  psga: ServiceIdRuleOption[]
  scope_type: ServiceIdRuleOption[]
  apn_type: ServiceIdRuleOption[]
}

export interface PaginatedServiceIdRuleOptions {
  total: number
  items: ServiceIdRuleOption[]
}

export type ServiceIdFieldConfigItem = FormFieldConfigItem
export type ServiceIdFieldConfigListResponse = FormFieldConfigListResponse
export type ServiceIdFieldConfigCreatePayload = FormFieldConfigCreatePayload

export interface RsaLivestreamConfig {
  stream_page_url: string
  resolved_stream_flv_url?: string | null
  internal_flv_proxy_url: string
  stream_server: string
  stream_key: string
  placeholder_enabled: boolean
  placeholder_title: string
  placeholder_message: string
  updated_at: string
}

export interface RsaLivestreamConfigUpdatePayload {
  stream_page_url?: string
  stream_server?: string
  stream_key?: string
  placeholder_enabled?: boolean
  placeholder_title?: string
  placeholder_message?: string
}

export interface APIAccessLogInDB {
  id: number
  user_id?: number | null
  username?: string | null
  method: string
  path: string
  query_string?: string | null
  status_code: number
  latency_ms: number
  client_ip?: string | null
  user_agent?: string | null
  tool_id?: number | null
  feature_name?: string | null
  /** 中文行为说明（由工具行为目录解析） */
  behavior_label?: string | null
  created_at: string
}

export interface APIAccessLogWithUser extends APIAccessLogInDB {
  user?: UserInDB | null
}

export interface PaginatedAPIAccessLogs {
  total: number
  items: APIAccessLogWithUser[]
}

/** 用户反馈 */
export type FeedbackCategory = 'tool_usage' | 'new_tool_suggestion' | 'system_feedback'

export interface FeedbackCreatePayload {
  category: FeedbackCategory
  title?: string | null
  content: string
  tool_id?: number | null
}

export interface FeedbackInDB {
  id: number
  user_id: number
  tool_id?: number | null
  category: string
  title?: string | null
  content: string
  created_at: string
}

export interface FeedbackWithUser extends FeedbackInDB {
  user: UserInDB
}

export interface PaginatedFeedbackWithUser {
  total: number
  items: FeedbackWithUser[]
}

export interface FeedbackCountsResponse {
  system_feedback: number
  new_tool_suggestion: number
  total: number
}

export type ToolRuntimeEnv = 'internal' | 'external'

export interface ToolVisibilityConfigResponse {
  current_runtime_env: ToolRuntimeEnv
  runtime_env_source: string
  external_hosts: string[]
  internal_visible_tool_keys: string[]
  external_visible_tool_keys: string[]
  all_tools: ToolInDB[]
}

export interface ToolVisibilityConfigUpdatePayload {
  external_hosts?: string[]
  internal_visible_tool_keys?: string[]
  external_visible_tool_keys?: string[]
}

// 权限状态枚举
export enum PermissionStatus {
  PENDING = 'pending',
  APPROVED = 'approved',
  REJECTED = 'rejected'
}

// 权限相关类型
export interface PermissionCreate {
  tool_id: number
  applied_reason: string
}

export interface PermissionUpdate {
  status?: string | null
  review_notes?: string | null
  expires_at?: string | null
}

export interface PermissionInDB {
  id: number
  user_id: number
  tool_id: number
  status: string
  applied_reason: string
  applied_at: string
  reviewed_by?: number | null
  reviewed_at?: string | null
  review_notes?: string | null
  expires_at?: string | null
}

export interface PermissionWithDetails {
  id: number
  user_id: number
  tool_id: number
  status: string
  applied_reason: string
  applied_at: string
  reviewed_by?: number | null
  reviewed_at?: string | null
  review_notes?: string | null
  expires_at?: string | null
  user: UserInDB
  tool: ToolInDB
  reviewer?: UserInDB | null
}

// 错误响应类型
export interface ValidationError {
  loc: Array<string | number>
  msg: string
  type: string
  input?: any
  ctx?: Record<string, any>
}

export interface HTTPValidationError {
  detail: ValidationError[]
}

// 通用API响应类型（适配后端的返回格式）
export interface ApiResponse<T = any> {
  data?: T
  // 注意：后端可能直接返回数据，没有包裹的code/message结构
  // 所以这里不强制要求code和message字段
}
