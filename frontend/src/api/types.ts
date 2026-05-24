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
  /** 平台「管理员」角色（与超级管理员不同） */
  is_platform_admin?: boolean
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

/** 与后端 ToolRuntimeStatus 一致；发版维护时可设为 updating 阻止业务使用 */
export type ToolRuntimeStatus = 'active' | 'updating'

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
  /** 运行中/更新中；为 updating 时除系统超级管理员外不可调用工具 API */
  runtime_status?: ToolRuntimeStatus
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

export interface ToolVersionSyncPayload {
  notify_users?: boolean
}

export interface ToolVersionSyncResult {
  status: 'recorded' | 'no_change'
  message: string
  release: ToolReleaseInDB
}

export type RoleName = 'tool_owner' | 'tool_user' | 'platform_admin'

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

export interface AdminToolAssignmentOption {
  id: number
  name: string
  display_name?: string | null
  is_active: boolean
  runtime_status?: ToolRuntimeStatus
}

export interface AdminUserAllowedToolsResponse {
  tool_ids: number[]
}

export interface AdminUserAllowedToolsPayload {
  tool_ids: number[]
}

export interface ToolTrafficRow {
  tool_id: number
  tool_name: string
  request_count: number
}

export interface ToolTrafficDashboardResponse {
  period: 'day' | 'week' | 'month'
  range_start: string
  range_end: string
  rows: ToolTrafficRow[]
}

export interface EnvFilePayload {
  content: string
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

export interface ToolLicenseCandidateRow {
  user: UserInDB
  currently_authorized: boolean
}

export interface PaginatedToolLicenseCandidates {
  total: number
  items: ToolLicenseCandidateRow[]
}

export interface ToolLicenseBatchUpdatePayload {
  action: 'grant' | 'revoke'
  user_ids: number[]
}

export interface ToolLicenseBatchUpdateResult {
  action: 'grant' | 'revoke'
  requested_count: number
  changed_count: number
  skipped_count: number
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

export interface ServiceIdExportColumnItem {
  key: string
  header: string
}

export interface ServiceIdExportColumnOption {
  key: string
  default_header: string
  group: 'builtin' | 'custom'
}

export interface ServiceIdExportConfigResponse {
  options: ServiceIdExportColumnOption[]
  columns: ServiceIdExportColumnItem[]
}

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

export interface DataSecureProjectSpace {
  id: number
  tool_id: number
  space_key: string
  name: string
  description?: string | null
  is_active: boolean
  created_by: number
  updated_by: number
  created_at: string
  updated_at: string
}

export interface PaginatedDataSecureProjectSpaces {
  total: number
  items: DataSecureProjectSpace[]
}

export type DataSecureIdentifierKeyTarget =
  | 'space_key'
  | 'question_key'
  | 'lifecycle_field_key'
  | 'taxonomy_node_key'

export interface DataSecureSuggestIdentifierKeyResponse {
  key: string
}

export interface DataSecureQuestion {
  id: number
  tool_id: number
  project_space_id: number
  question_key: string
  title: string
  help_text?: string | null
  question_type: 'yes_no'
  is_required: boolean
  sort_order: number
  is_active: boolean
  created_by: number
  updated_by: number
  created_at: string
  updated_at: string
}

export interface PaginatedDataSecureQuestions {
  total: number
  items: DataSecureQuestion[]
}

export interface DataSecureRelevanceRule {
  id: number
  tool_id: number
  project_space_id: number
  min_yes_count: number
  logic_operator: 'and' | 'or'
  question_keys: string[]
  logic_expression?: string | null
  notes?: string | null
  updated_by: number
  updated_at: string
}

export interface DataSecureGovernanceChangeLog {
  id: number
  tool_id: number
  project_space_id: number
  domain: string
  action: string
  target_type: string
  target_id: string
  change_reason: string
  detail: Record<string, unknown>
  changed_by: number
  changed_by_name?: string | null
  created_at: string
}

export interface PaginatedDataSecureGovernanceChangeLogs {
  total: number
  items: DataSecureGovernanceChangeLog[]
}

export interface DataSecureAssessmentAnswerInput {
  question_id: number
  answer_bool: boolean
  answer_text?: string
}

export interface DataSecureAssessmentAnswer {
  question_id: number
  question_key: string
  question_title: string
  answer_bool: boolean
  answer_text?: string | null
}

export interface DataSecureAssessmentSubmission {
  id: number
  tool_id: number
  project_space_id: number
  project_space_name: string
  submitted_by: number
  submitted_by_name?: string | null
  function_name: string
  function_description?: string | null
  yes_count: number
  total_count: number
  is_related: boolean
  result_summary: string
  submitted_at: string
  answers: DataSecureAssessmentAnswer[]
}

export interface PaginatedDataSecureAssessmentSubmissions {
  total: number
  items: DataSecureAssessmentSubmission[]
}

export interface DataSecureLifecycleFieldConfigListResponse {
  items: FormFieldConfigItem[]
}

export interface DataSecureFieldCatalogEntry {
  id: number
  tool_id: number
  project_space_id: number
  field_name: string
  extra_fields: DynamicFormValues
  created_by: number
  updated_by: number
  created_at: string
  updated_at: string
}

export interface PaginatedDataSecureFieldCatalogEntries {
  total: number
  items: DataSecureFieldCatalogEntry[]
}

export interface DataSecureFieldCatalogValueOptionsResponse {
  field_key: string
  q: string
  options: string[]
}

export interface DataSecureFieldCatalogBatchImportResult {
  created_count: number
  skipped_duplicate: number
  failed_validation: number
  errors: string[]
  /** 本次导入时自动新建的填报表单字段 key（单行文本、未配置限制） */
  auto_created_field_keys?: string[]
}

export interface DataSecureFieldRequest {
  id: number
  tool_id: number
  project_space_id: number
  project_space_name: string
  requested_by: number
  requested_by_name?: string | null
  request_type: 'data_field' | 'business_function'
  field_name: string
  reason?: string | null
  payload: DynamicFormValues
  status: 'pending' | 'approved' | 'rejected'
  review_notes?: string | null
  reviewed_by?: number | null
  reviewed_by_name?: string | null
  reviewed_at?: string | null
  created_at: string
  updated_at: string
}

export interface DataSecureBusinessFunctionOptionsResponse {
  field_key?: string | null
  business_function_configured: boolean
  options: string[]
}

export interface DataSecureBusinessFunctionOptionRequest {
  id: number
  tool_id: number
  project_space_id: number
  project_space_name: string
  requested_by: number
  requested_by_name?: string | null
  proposed_option: string
  reason?: string | null
  status: 'pending' | 'approved' | 'rejected'
  review_notes?: string | null
  reviewed_by?: number | null
  reviewed_by_name?: string | null
  reviewed_at?: string | null
  created_at: string
  updated_at: string
}

export interface PaginatedDataSecureBusinessFunctionOptionRequests {
  total: number
  items: DataSecureBusinessFunctionOptionRequest[]
}

export interface PaginatedDataSecureFieldRequests {
  total: number
  items: DataSecureFieldRequest[]
}

export interface DataSecureFieldUsageReport {
  id: number
  tool_id: number
  project_space_id: number
  project_space_name: string
  submitted_by: number
  submitted_by_name?: string | null
  assessment_submission_id?: number | null
  function_name: string
  function_description?: string | null
  field_entry_ids: number[]
  field_names: string[]
  notes?: string | null
  review_status?: 'pending' | 'approved' | 'rejected'
  review_notes?: string | null
  reviewed_by?: number | null
  reviewed_by_name?: string | null
  reviewed_at?: string | null
  submitted_at: string
}

export interface PaginatedDataSecureFieldUsageReports {
  total: number
  items: DataSecureFieldUsageReport[]
}

export interface DataSecureWorkOrderRow {
  assessment_submission_id: number
  questionnaire_submitted_at: string
  function_name: string
  is_related: boolean
  result_summary: string
  field_usage_report_id?: number | null
  usage_submitted_at?: string | null
  review_status?: 'pending' | 'approved' | 'rejected' | null
  review_notes?: string | null
}

export interface PaginatedDataSecureWorkOrders {
  total: number
  items: DataSecureWorkOrderRow[]
}

export interface DataSecureConsolidatedExportRow {
  project_space_name: string
  assessment_submission_id: number
  questionnaire_submitted_at: string
  is_related: boolean
  result_summary: string
  field_usage_report_id: number
  usage_submitted_at: string
  submitted_by_name?: string | null
  data_field_name: string
  other_info_json: string
  category: string
  level: string
  auto_category: string
  auto_level: string
  auto_hit_summary?: string | null
  security_requirements_text: string
}

export interface DataSecureConsolidatedExportResponse {
  items: DataSecureConsolidatedExportRow[]
}

export interface DataSecureFieldUsageExportRow {
  project_space_name: string
  function_name: string
  function_description?: string | null
  data_field_name: string
  /** 填报时「其他信息」快照 JSON；不参与自动分类分级与安全要求 */
  other_info_json?: string | null
  submitted_by_name?: string | null
  submitted_at: string
}

export interface DataSecureClassificationRule {
  id: number
  tool_id: number
  project_space_id: number
  keyword: string
  category: string
  level: string
  /** 越大越优先；同优先级时 sort_order 越小越优先 */
  priority?: number
  notes?: string | null
  sort_order: number
  is_active: boolean
  created_by: number
  updated_by: number
  created_at: string
  updated_at: string
}

export interface PaginatedDataSecureClassificationRules {
  total: number
  items: DataSecureClassificationRule[]
}

export interface DataSecureClassificationMatrix {
  id: number
  tool_id: number
  project_space_id: number
  field_name: string
  extension_match: DynamicFormValues
  category: string
  level: string
  priority: number
  notes?: string | null
  sort_order: number
  is_active: boolean
  created_by: number
  updated_by: number
  created_at: string
  updated_at: string
}

export interface PaginatedDataSecureClassificationMatrix {
  total: number
  items: DataSecureClassificationMatrix[]
}

export interface DataSecureClassificationMatrixBatchImportResult {
  created_count: number
  failed_validation: number
  errors: string[]
}

export interface DataSecureClassificationResult {
  id: number
  tool_id: number
  project_space_id: number
  catalog_entry_id: number
  field_name_snapshot: string
  category: string
  level: string
  rule_keyword?: string | null
  auto_category: string
  auto_level: string
  auto_rule_keyword?: string | null
  auto_rule_id?: number | null
  auto_matrix_id?: number | null
  auto_match_source?: string
  auto_hit_summary?: string | null
  manual_reason?: string | null
  source: string
  updated_by: number
  updated_by_name?: string | null
  updated_at: string
}

export interface PaginatedDataSecureClassificationResults {
  total: number
  items: DataSecureClassificationResult[]
}

export interface DataSecureClassificationAuditLog {
  id: number
  tool_id: number
  project_space_id: number
  catalog_entry_id?: number | null
  result_id?: number | null
  user_id: number
  user_name?: string | null
  action: string
  detail: Record<string, unknown>
  created_at: string
}

export interface PaginatedDataSecureClassificationAuditLogs {
  total: number
  items: DataSecureClassificationAuditLog[]
}

export interface DataSecureClassificationExportRow {
  project_space_id: number
  catalog_entry_id: number
  field_name: string
  effective_category: string
  effective_level: string
  effective_rule_keyword?: string | null
  source: string
  auto_category: string
  auto_level: string
  auto_rule_keyword?: string | null
  auto_rule_id?: number | null
  auto_matrix_id?: number | null
  auto_match_source?: string
  auto_hit_summary?: string | null
  manual_reason?: string | null
  updated_by_name?: string | null
  updated_at: string
}

/** 结构化治理：Level1 / Level2 分类节点（Level3 为数据字段主表行） */
export interface DataSecureTaxonomyNode {
  id: number
  tool_id: number
  project_space_id: number
  parent_id?: number | null
  name: string
  node_key: string
  sort_order: number
  is_active: boolean
  created_by: number
  updated_by: number
  created_at: string
  updated_at: string
}

export interface PaginatedDataSecureTaxonomyNodes {
  total: number
  items: DataSecureTaxonomyNode[]
}

/** 数据字段 + C0–C3 分级 + 分类路径绑定（taxonomy_l2 为最细分类节点） */
export interface DataSecureFieldClassGrade {
  id: number
  tool_id: number
  project_space_id: number
  catalog_entry_id: number
  field_name: string
  taxonomy_l1_id?: number | null
  taxonomy_l2_id?: number | null
  taxonomy_l1_name?: string | null
  taxonomy_l2_name?: string | null
  /** 根到最细分类的展示路径（不含数据字段名） */
  taxonomy_path?: string | null
  taxonomy_path_ids?: number[] | null
  confidentiality_grade: string
  notes?: string | null
  created_by: number
  updated_by: number
  created_at: string
  updated_at: string
}

export interface PaginatedDataSecureFieldClassGrades {
  total: number
  items: DataSecureFieldClassGrade[]
}

/** 安全要求：逻辑表达式 + 谓词映射（与分类分级组合） */
export interface DataSecureFieldSecurityRequirement {
  id: number
  tool_id: number
  project_space_id: number
  catalog_entry_id: number
  field_name: string
  requirement_text: string
  logic_expression: string
  predicate_map: Record<string, unknown>
  priority: number
  sort_order: number
  is_active: boolean
  created_by: number
  updated_by: number
  created_at: string
  updated_at: string
}

export interface PaginatedDataSecureFieldSecurityRequirements {
  total: number
  items: DataSecureFieldSecurityRequirement[]
}

export interface DataSecureFieldSecurityRequirementEvalHit {
  requirement_id: number
  requirement_text: string
  logic_expression: string
  matched: boolean
}

export interface DataSecureFieldSecurityRequirementEvalResponse {
  catalog_entry_id: number
  field_name: string
  confidentiality_grade: string
  category_path: string
  hits: DataSecureFieldSecurityRequirementEvalHit[]
}

export interface DataSecureConfigExportSelection {
  include_spaces: boolean
  include_questions: boolean
  include_relevance_rule: boolean
  include_lifecycle_fields: boolean
  include_taxonomy_nodes: boolean
  include_field_class_grades: boolean
  include_security_requirements: boolean
  include_classification_rules?: boolean
  include_classification_matrix?: boolean
}

export interface DataSecureConfigExportPayload {
  tool_key: string
  project_space_id: number
  exported_at: string
  selection: DataSecureConfigExportSelection
  spaces: DataSecureProjectSpace[]
  questions: DataSecureQuestion[]
  relevance_rule?: DataSecureRelevanceRule | null
  lifecycle_fields: FormFieldConfigItem[]
  taxonomy_nodes: DataSecureTaxonomyNode[]
  field_class_grades: DataSecureFieldClassGrade[]
  security_requirements: DataSecureFieldSecurityRequirement[]
  classification_rules?: DataSecureClassificationRule[]
  classification_matrix?: DataSecureClassificationMatrix[]
}

export interface DataSecureConfigImportResult {
  target_project_space_id: number
  imported_counts: Record<string, number>
}

export type DataSecureConfigDeleteDomain =
  | 'question'
  | 'lifecycle_field'
  | 'taxonomy_node'
  | 'field_class_grade'
  | 'security_requirement'

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
