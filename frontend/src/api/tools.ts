import { api } from './auth'
import type {
  PaginatedToolAnnouncements,
  PaginatedToolReleases,
  ToolInDB,
  ToolAnnouncementInDB,
  ServiceIdEntryPayload,
  ServiceIdEntryUpdatePayload,
  ServiceIdEntry,
  ServiceIdEntryListResponse,
  ServiceIdExportConfigResponse,
  ServiceIdExportColumnItem,
  ServiceIdRuleOption,
  ServiceIdRuleOptionGroup,
  PaginatedServiceIdRuleOptions,
  ServiceRuleCategory,
  FormFieldConfigListResponse,
  FormFieldConfigCreatePayload,
  FormFieldInputType,
  DataSecureAssessmentAnswerInput,
  DataSecureAssessmentSubmission,
  DataSecureFieldCatalogBatchImportResult,
  DataSecureFieldCatalogEntry,
  DataSecureFieldCatalogValueOptionsResponse,
  DataSecureFieldRequest,
  DataSecureBusinessFunctionOptionsResponse,
  DataSecureBusinessFunctionOptionRequest,
  PaginatedDataSecureBusinessFunctionOptionRequests,
  DataSecureFieldUsageExportRow,
  DataSecureFieldUsageReport,
  DataSecureClassificationAuditLog,
  DataSecureClassificationExportRow,
  DataSecureClassificationMatrix,
  DataSecureClassificationMatrixBatchImportResult,
  DataSecureClassificationResult,
  DataSecureClassificationRule,
  DataSecureRelevanceRule,
  DataSecureLifecycleFieldConfigListResponse,
  PaginatedDataSecureFieldCatalogEntries,
  PaginatedDataSecureFieldRequests,
  PaginatedDataSecureFieldUsageReports,
  PaginatedDataSecureWorkOrders,
  DataSecureConsolidatedExportResponse,
  PaginatedDataSecureGovernanceChangeLogs,
  PaginatedDataSecureClassificationAuditLogs,
  PaginatedDataSecureClassificationMatrix,
  PaginatedDataSecureClassificationRules,
  PaginatedDataSecureClassificationResults,
  PaginatedDataSecureAssessmentSubmissions,
  PaginatedDataSecureProjectSpaces,
  DataSecureIdentifierKeyTarget,
  DataSecureSuggestIdentifierKeyResponse,
  PaginatedDataSecureQuestions,
  PaginatedDataSecureTaxonomyNodes,
  PaginatedDataSecureFieldClassGrades,
  PaginatedDataSecureFieldSecurityRequirements,
  DataSecureTaxonomyNode,
  DataSecureFieldClassGrade,
  DataSecureFieldSecurityRequirement,
  DataSecureFieldSecurityRequirementEvalResponse,
  DataSecureConfigDeleteDomain,
  DataSecureConfigExportPayload,
  DataSecureConfigExportSelection,
  DataSecureConfigImportResult,
  RsaLivestreamConfig,
  RsaLivestreamConfigUpdatePayload,
} from './types'

export const toolsApi = {
  // 获取工具列表（可按名称/描述搜索）
  getTools(skip: number = 0, limit: number = 100, search?: string): Promise<ToolInDB[]> {
    const params: Record<string, string | number> = { skip, limit }
    const s = search?.trim()
    if (s) params.search = s
    return api.get('/tools/', { params })
  },

  // 获取单个工具
  getTool(toolId: number): Promise<ToolInDB> {
    return api.get(`/tools/${toolId}`)
  },

  /** 发版更新记录（需有该工具使用权限） */
  getToolReleases(toolId: number, skip: number = 0, limit: number = 20): Promise<PaginatedToolReleases> {
    return api.get(`/tools/${toolId}/releases`, { params: { skip, limit } })
  },

  getServiceIdEntries(toolId: number, skip: number = 0, limit: number = 20): Promise<ServiceIdEntryListResponse> {
    return api.get(`/tools/${toolId}/features/service-id-entries`, { params: { skip, limit } })
  },

  createServiceIdEntry(toolId: number, data: ServiceIdEntryPayload): Promise<ServiceIdEntry> {
    return api.post(`/tools/${toolId}/features/service-id-entries`, data)
  },

  updateServiceIdEntry(toolId: number, data: ServiceIdEntryUpdatePayload): Promise<ServiceIdEntry> {
    return api.put(`/tools/${toolId}/features/service-id-entries`, data)
  },

  deleteServiceIdEntry(toolId: number, entryId: number): Promise<{ success: boolean; message: string }> {
    return api.delete(`/tools/${toolId}/features/service-id-entries`, { params: { entry_id: entryId } })
  },

  getServiceIdRuleOptions(toolId: number, includeInactive: boolean = false): Promise<ServiceIdRuleOptionGroup> {
    return api.get(`/tools/${toolId}/features/service-id-rule-options`, {
      params: { include_inactive: includeInactive }
    })
  },

  getServiceIdRuleOptionsPage(
    toolId: number,
    category: ServiceRuleCategory,
    skip: number = 0,
    limit: number = 20,
    includeInactive: boolean = false
  ): Promise<PaginatedServiceIdRuleOptions> {
    return api.get(`/tools/${toolId}/features/service-id-rule-options/list`, {
      params: {
        category,
        include_inactive: includeInactive,
        skip,
        limit
      }
    })
  },

  createServiceIdRuleOption(
    toolId: number,
    data: { category: ServiceRuleCategory; value: string }
  ): Promise<ServiceIdRuleOption> {
    return api.post(`/tools/${toolId}/features/service-id-rule-options`, data)
  },

  updateServiceIdRuleOption(
    toolId: number,
    data: { id: number; value?: string; is_active?: boolean }
  ): Promise<ServiceIdRuleOption> {
    return api.put(`/tools/${toolId}/features/service-id-rule-options`, data)
  },

  deleteServiceIdRuleOption(toolId: number, id: number): Promise<{ success: boolean; message: string }> {
    return api.delete(`/tools/${toolId}/features/service-id-rule-options`, { data: { id } })
  },

  getServiceIdFieldConfigs(toolId: number): Promise<FormFieldConfigListResponse> {
    return api.get(`/tools/${toolId}/features/service-id-field-config`)
  },

  updateServiceIdFieldConfigs(
    toolId: number,
    items: Array<{
      field_key: string
      label?: string | null
      input_type?: FormFieldInputType | null
      is_active?: boolean | null
      sort_order?: number | null
      help_text?: string | null
      required?: boolean | null
      min_length?: number | null
      max_length?: number | null
      regex_pattern?: string | null
      regex_error_message?: string | null
      allowed_values?: string[] | null
    }>
  ): Promise<FormFieldConfigListResponse> {
    return api.put(`/tools/${toolId}/features/service-id-field-config`, { items })
  },

  createServiceIdFieldConfig(
    toolId: number,
    payload: FormFieldConfigCreatePayload
  ) {
    return api.post(`/tools/${toolId}/features/service-id-field-config`, payload)
  },

  deleteServiceIdFieldConfig(
    toolId: number,
    fieldKey: string
  ): Promise<{ success: boolean; message: string }> {
    return api.delete(`/tools/${toolId}/features/service-id-field-config`, {
      data: { field_key: fieldKey }
    })
  },

  exportServiceIdEntries(toolId: number): Promise<Blob> {
    return api.get(`/tools/${toolId}/features/service-id-export`, {
      responseType: 'blob'
    })
  },

  getServiceIdExportConfig(toolId: number): Promise<ServiceIdExportConfigResponse> {
    return api.get(`/tools/${toolId}/features/service-id-export-config`)
  },

  updateServiceIdExportConfig(
    toolId: number,
    columns: ServiceIdExportColumnItem[]
  ): Promise<ServiceIdExportConfigResponse> {
    return api.put(`/tools/${toolId}/features/service-id-export-config`, { columns })
  },

  resetServiceIdExportConfig(toolId: number): Promise<ServiceIdExportConfigResponse> {
    return api.delete(`/tools/${toolId}/features/service-id-export-config`)
  },

  runX509Feature(
    toolId: number,
    data: {
      action: 'check' | 'sign' | 'parse_csr' | 'parse_cert'
      env: 'uat' | 'live'
      iam_sns?: string[]
      csrs?: string[]
      csr?: string
      cert?: string
    }
  ): Promise<{ success: boolean; message: string; data: any }> {
    return api.post(`/tools/${toolId}/features/x509-cert`, data)
  },

  preloadMosTokens(
    toolId: number,
    payload: {
      scopes?: string[]
      wait?: boolean
      timeout_seconds?: number
      force_refresh?: boolean
    }
  ): Promise<{
    success: boolean
    message: string
    data: {
      started: boolean
      waited: boolean
      timeout_seconds: number
      has_errors: boolean
      errors: Record<string, string>
      items: Array<{
        scope: string
        label: string
        features: string[]
        status: 'idle' | 'loading' | 'ready' | 'error'
        started_at?: string | null
        finished_at?: string | null
        updated_at?: string | null
        last_error?: string | null
        cache_expires_in_seconds?: number
        pool_event?: string
        pool_inflight?: boolean
        pool_stats?: {
          requests: number
          hits: number
          misses: number
          waits: number
          errors: number
          refreshes: number
        }
      }>
    }
  }> {
    return api.post(`/tools/${toolId}/features/token-preload`, payload)
  },

  getMosTokenPreloadVisibility(
    toolId: number
  ): Promise<{ success: boolean; message: string; data: { can_manage: boolean } }> {
    return api.get(`/tools/${toolId}/features/token-preload/visibility`)
  },

  querySim(
    toolId: number,
    data: {
      provider: 'unicom' | 'ctcc'
      project?: string
      search_value?: string
      iccid?: string
      msisdn?: string
      imsi?: string
    }
  ): Promise<{ success: boolean; message: string; data: any }> {
    return api.post(`/tools/${toolId}/features/sim-query`, data)
  },

  queryUatAfDp(
    toolId: number,
    data: { vin?: string; zxdsn?: string; iamsn?: string; iccid?: string }
  ): Promise<{ success: boolean; message: string; data: any }> {
    return api.post(`/tools/${toolId}/features/uat-af-dp-query`, data)
  },

  queryUatSp(
    toolId: number,
    data: { action: 'query_sp_info' | 'bind' | 'unbind'; vin: string; phone?: string }
  ): Promise<{ success: boolean; message: string; data: any }> {
    return api.post(`/tools/${toolId}/features/uat-sp-query`, data)
  },

  generateUatVehicleConfig(
    toolId: number,
    data: {
      project: string
      car_software_version: string
      hu_fazit_id: string
      ocu_iccid: string
      msisdn: string
      ocu_fazit_id: string
      vehicle_vin: string
      application_department: string
    }
  ): Promise<{ success: boolean; message: string; data: any }> {
    return api.post(`/tools/${toolId}/features/uat-vehicle-config-generate`, data)
  },

  getUatVehicleConfigRules(
    toolId: number
  ): Promise<{
      success: boolean
      message: string
      data: {
        projects: string[]
        version_patterns_by_project: Record<string, string[]>
      }
    }> {
    return api.get(`/tools/${toolId}/features/uat-vehicle-config-rules`)
  },

  getMosAnnouncementFeed(
    toolId: number,
    params: { skip: number; limit: number }
  ): Promise<PaginatedToolAnnouncements> {
    return api.get(`/tools/${toolId}/features/announcement-feed`, { params })
  },

  listMosManageAnnouncements(
    toolId: number,
    params: { skip: number; limit: number }
  ): Promise<PaginatedToolAnnouncements> {
    return api.get(`/tools/${toolId}/features/mos-manage/announcements`, { params })
  },

  createMosManageAnnouncement(
    toolId: number,
    payload: {
      title: string
      content: string
      is_enabled: boolean
      priority: 'urgent' | 'notice' | 'reminder'
      scroll_speed_seconds: number
      font_family?: string | null
      font_size_px: number
      text_color?: string | null
      background_color?: string | null
      start_at?: string | null
      end_at?: string | null
      disable_feature_slugs: string[]
    }
  ): Promise<ToolAnnouncementInDB> {
    return api.post(`/tools/${toolId}/features/mos-manage/announcements`, payload)
  },

  updateMosManageAnnouncement(
    toolId: number,
    announcementId: number,
    payload: {
      title?: string
      content?: string
      is_enabled?: boolean
      priority?: 'urgent' | 'notice' | 'reminder'
      scroll_speed_seconds?: number
      font_family?: string | null
      font_size_px?: number
      text_color?: string | null
      background_color?: string | null
      start_at?: string | null
      end_at?: string | null
      disable_feature_slugs?: string[]
    }
  ): Promise<ToolAnnouncementInDB> {
    return api.patch(`/tools/${toolId}/features/mos-manage/announcements/${announcementId}`, payload)
  },

  listMosVehicleRules(
    toolId: number,
    params: { skip: number; limit: number }
  ): Promise<{ success: boolean; message: string; data: { total: number; items: Array<Record<string, any>> } }> {
    return api.get(`/tools/${toolId}/features/mos-manage/vehicle-rules`, { params })
  },

  createMosVehicleRule(
    toolId: number,
    rule: Record<string, any>
  ): Promise<{ success: boolean; message: string; data: { rules: Array<Record<string, any>> } }> {
    return api.post(`/tools/${toolId}/features/mos-manage/vehicle-rules`, { rule })
  },

  bulkImportMosVehicleRules(
    toolId: number,
    payload: { rules: Array<Record<string, any>>; dry_run: boolean }
  ): Promise<{
    success: boolean
    message: string
    data: {
      dry_run?: boolean
      total?: number
      valid_count?: number
      invalid_count?: number
      has_errors?: boolean
      items?: Array<{ index: number; valid: boolean; project: string; errors: string[] }>
      rules?: Array<Record<string, any>>
      imported_count?: number
    }
  }> {
    return api.post(`/tools/${toolId}/features/mos-manage/vehicle-rules/bulk-import`, payload)
  },

  updateMosVehicleRule(
    toolId: number,
    ruleIndex: number,
    rule: Record<string, any>
  ): Promise<{ success: boolean; message: string; data: { rules: Array<Record<string, any>> } }> {
    return api.put(`/tools/${toolId}/features/mos-manage/vehicle-rules/${ruleIndex}`, { rule })
  },

  deleteMosVehicleRule(
    toolId: number,
    ruleIndex: number
  ): Promise<{ success: boolean; message: string; data: { rules: Array<Record<string, any>> } }> {
    return api.delete(`/tools/${toolId}/features/mos-manage/vehicle-rules/${ruleIndex}`)
  },

  getMosRuntimeCredentials(
    toolId: number
  ): Promise<{
    success: boolean
    message: string
    data: {
      uat_mos_portal: { account: string; password_masked: string }
      oa: { account: string; password_masked: string }
      runtime: { request_timeout_seconds: number }
    }
  }> {
    return api.get(`/tools/${toolId}/features/mos-manage/runtime-credentials`)
  },

  updateMosRuntimeCredentials(
    toolId: number,
    payload: {
      uat_mos_portal_account?: string
      uat_mos_portal_password?: string
      oa_account?: string
      oa_password?: string
      request_timeout_seconds?: number
    }
  ): Promise<{
    success: boolean
    message: string
    data: {
      uat_mos_portal: { account: string; password_masked: string }
      oa: { account: string; password_masked: string }
      runtime: { request_timeout_seconds: number }
    }
  }> {
    return api.put(`/tools/${toolId}/features/mos-manage/runtime-credentials`, payload)
  },

  getMosDbOptimizationConfig(
    toolId: number
  ): Promise<{
    success: boolean
    message: string
    data: {
      database_url_masked: string
      is_remote_database: boolean
      current_env: {
        SQLALCHEMY_POOL_SIZE: number
        SQLALCHEMY_MAX_OVERFLOW: number
        SQLALCHEMY_POOL_TIMEOUT: number
        SQLALCHEMY_POOL_RECYCLE: number
        TOOLBOX_WORKERS: number
        SQLALCHEMY_STATEMENT_TIMEOUT_MS: number
      }
      saved_overrides: Record<string, number>
      recommendation: {
        pool_size: number
        max_overflow: number
        pool_timeout_seconds: number
        pool_recycle_seconds: number
        workers: number
        statement_timeout_ms: number
      }
      requires_restart: boolean
      note: string
    }
  }> {
    return api.get(`/tools/${toolId}/features/mos-manage/db-optimization`)
  },

  updateMosDbOptimizationConfig(
    toolId: number,
    payload: {
      pool_size?: number
      max_overflow?: number
      pool_timeout_seconds?: number
      pool_recycle_seconds?: number
      workers?: number
      statement_timeout_ms?: number
      apply_to_env?: boolean
    }
  ): Promise<{
    success: boolean
    message: string
    data: {
      saved_overrides: Record<string, number>
      applied_to_env: boolean
      requires_restart: boolean
    }
  }> {
    return api.put(`/tools/${toolId}/features/mos-manage/db-optimization`, payload)
  },

  pingMosDbOptimization(
    toolId: number
  ): Promise<{ success: boolean; message: string; data: { elapsed_ms: number } }> {
    return api.post(`/tools/${toolId}/features/mos-manage/db-optimization/ping`)
  },

  listMosManageChangeLogs(
    toolId: number,
    params: { skip: number; limit: number }
  ): Promise<{
    success: boolean
    message: string
    data: {
      total: number
      items: Array<{
        id: number
        action: string
        target: string
        summary: string | null
        changed_by: number
        changed_by_name: string
        created_at: string
      }>
    }
  }> {
    return api.get(`/tools/${toolId}/features/mos-manage/change-logs`, { params })
  },

  importUatVehicleConfig(
    toolId: number,
    data: { target: 'sp' | 'cdp' | 'afdp'; check_duplicated: boolean; vehicle_data: Record<string, any> }
  ): Promise<{ success: boolean; message: string; data: any }> {
    return api.post(`/tools/${toolId}/features/uat-vehicle-import`, data)
  },

  getRsaLivestreamConfig(toolId: number): Promise<RsaLivestreamConfig> {
    return api.get(`/tools/${toolId}/features/livestream/config`)
  },

  getDataSecureProjectSpaces(
    toolId: number,
    skip: number = 0,
    limit: number = 50
  ): Promise<PaginatedDataSecureProjectSpaces> {
    return api.get(`/tools/${toolId}/features/project-spaces`, { params: { skip, limit } })
  },

  suggestDataSecureIdentifierKey(
    toolId: number,
    payload: { source_text: string; target: DataSecureIdentifierKeyTarget }
  ): Promise<DataSecureSuggestIdentifierKeyResponse> {
    return api.post(`/tools/${toolId}/features/suggest-identifier-key`, payload)
  },

  createDataSecureProjectSpace(
    toolId: number,
    payload: {
      space_key: string
      name: string
      description?: string
      is_active?: boolean
      copy_from_project_space_id?: number | null
      change_reason?: string
    }
  ) {
    return api.post(`/tools/${toolId}/features/project-spaces`, payload)
  },

  deleteDataSecureProjectSpace(
    toolId: number,
    payload: { id: number; change_reason: string }
  ): Promise<{ ok: boolean }> {
    return api.post(`/tools/${toolId}/features/project-spaces/delete`, payload)
  },

  updateDataSecureProjectSpace(
    toolId: number,
    payload: {
      id: number
      space_key?: string
      name?: string
      description?: string
      is_active?: boolean
    }
  ) {
    return api.put(`/tools/${toolId}/features/project-spaces`, payload)
  },

  getDataSecureQuestions(
    toolId: number,
    projectSpaceId: number,
    skip: number = 0,
    limit: number = 100
  ): Promise<PaginatedDataSecureQuestions> {
    return api.get(`/tools/${toolId}/features/questionnaire/questions`, {
      params: { project_space_id: projectSpaceId, skip, limit }
    })
  },

  createDataSecureQuestion(
    toolId: number,
    payload: {
      project_space_id: number
      question_key: string
      title: string
      help_text?: string
      question_type?: 'yes_no'
      is_required?: boolean
      sort_order?: number
      is_active?: boolean
    }
  ) {
    return api.post(`/tools/${toolId}/features/questionnaire/questions`, payload)
  },

  updateDataSecureQuestion(
    toolId: number,
    payload: {
      id: number
      title?: string
      help_text?: string | null
      is_required?: boolean
      sort_order?: number
      is_active?: boolean
    }
  ) {
    return api.put(`/tools/${toolId}/features/questionnaire/questions`, payload)
  },

  deleteDataSecureQuestion(
    toolId: number,
    payload: { id: number; change_reason: string }
  ): Promise<{ ok: boolean }> {
    return api.post(`/tools/${toolId}/features/questionnaire/questions/delete`, payload)
  },

  getDataSecureRelevanceRule(toolId: number, projectSpaceId: number): Promise<DataSecureRelevanceRule | null> {
    return api.get(`/tools/${toolId}/features/relevance-rule`, { params: { project_space_id: projectSpaceId } })
  },

  upsertDataSecureRelevanceRule(
    toolId: number,
    payload: {
      project_space_id: number
      min_yes_count: number
      logic_operator: 'and' | 'or'
      question_keys: string[]
      logic_expression?: string
      notes?: string
      change_reason: string
    }
  ): Promise<DataSecureRelevanceRule> {
    return api.put(`/tools/${toolId}/features/relevance-rule`, payload)
  },

  submitDataSecureAssessment(
    toolId: number,
    payload: {
      project_space_id: number
      function_name: string
      function_description?: string
      answers: DataSecureAssessmentAnswerInput[]
    }
  ): Promise<DataSecureAssessmentSubmission> {
    return api.post(`/tools/${toolId}/features/relevance-assessments`, payload)
  },

  getDataSecureAssessments(
    toolId: number,
    projectSpaceId?: number,
    skip: number = 0,
    limit: number = 20
  ): Promise<PaginatedDataSecureAssessmentSubmissions> {
    return api.get(`/tools/${toolId}/features/relevance-assessments`, {
      params: { project_space_id: projectSpaceId, skip, limit }
    })
  },

  getDataSecureLifecycleFieldConfigs(
    toolId: number,
    projectSpaceId: number
  ): Promise<DataSecureLifecycleFieldConfigListResponse> {
    return api.get(`/tools/${toolId}/features/lifecycle-field-config`, { params: { project_space_id: projectSpaceId } })
  },

  createDataSecureLifecycleFieldConfig(
    toolId: number,
    payload: {
      project_space_id: number
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
      change_reason: string
    }
  ): Promise<DataSecureLifecycleFieldConfigListResponse> {
    return api.post(`/tools/${toolId}/features/lifecycle-field-config`, payload)
  },

  updateDataSecureLifecycleFieldConfigs(
    toolId: number,
    payload: {
      project_space_id: number
      items: Array<{
        field_key: string
        label?: string | null
        input_type?: FormFieldInputType | null
        is_active?: boolean | null
        sort_order?: number | null
        help_text?: string | null
        required?: boolean | null
        min_length?: number | null
        max_length?: number | null
        regex_pattern?: string | null
        regex_error_message?: string | null
        allowed_values?: string[] | null
      }>
      change_reason: string
    }
  ): Promise<DataSecureLifecycleFieldConfigListResponse> {
    return api.put(`/tools/${toolId}/features/lifecycle-field-config`, payload)
  },

  deleteDataSecureLifecycleFieldConfig(
    toolId: number,
    payload: { project_space_id: number; field_key: string; change_reason: string }
  ): Promise<DataSecureLifecycleFieldConfigListResponse> {
    return api.delete(`/tools/${toolId}/features/lifecycle-field-config`, { data: payload })
  },

  getDataSecureFieldCatalog(
    toolId: number,
    projectSpaceId: number,
    skip: number = 0,
    limit: number = 20,
    q?: string
  ): Promise<PaginatedDataSecureFieldCatalogEntries> {
    return api.get(`/tools/${toolId}/features/field-catalog`, {
      params: { project_space_id: projectSpaceId, skip, limit, q }
    })
  },

  getDataSecureFieldCatalogValueOptions(
    toolId: number,
    params: { project_space_id: number; field_key: string; q?: string; limit?: number }
  ): Promise<DataSecureFieldCatalogValueOptionsResponse> {
    return api.get(`/tools/${toolId}/features/field-catalog-value-options`, { params })
  },

  createDataSecureFieldCatalogEntry(
    toolId: number,
    payload: { project_space_id: number; field_name: string; extra_fields?: Record<string, any> }
  ): Promise<DataSecureFieldCatalogEntry> {
    return api.post(`/tools/${toolId}/features/field-catalog`, payload)
  },

  batchImportDataSecureFieldCatalog(
    toolId: number,
    payload: {
      project_space_id: number
      items: Array<{ field_name: string; extra_fields?: Record<string, any> }>
      /** field_key -> CSV 列展示名，用于自动新建填报表单字段的 label */
      auto_field_labels?: Record<string, string>
    }
  ): Promise<DataSecureFieldCatalogBatchImportResult> {
    return api.post(`/tools/${toolId}/features/field-catalog/batch-import`, payload)
  },

  updateDataSecureFieldCatalogExtra(
    toolId: number,
    entryId: number,
    payload: { extra_fields: Record<string, any> }
  ): Promise<DataSecureFieldCatalogEntry> {
    return api.put(`/tools/${toolId}/features/field-catalog/${entryId}`, payload)
  },

  createDataSecureFieldRequest(
    toolId: number,
    payload: {
      project_space_id: number
      request_type?: 'data_field' | 'business_function'
      field_name: string
      reason?: string
      extra_fields?: Record<string, any>
    }
  ): Promise<DataSecureFieldRequest> {
    return api.post(`/tools/${toolId}/features/field-requests`, payload)
  },

  getDataSecureFieldRequests(
    toolId: number,
    params: {
      project_space_id?: number
      status?: 'pending' | 'approved' | 'rejected'
      skip?: number
      limit?: number
    }
  ): Promise<PaginatedDataSecureFieldRequests> {
    return api.get(`/tools/${toolId}/features/field-requests`, { params })
  },

  reviewDataSecureFieldRequest(
    toolId: number,
    requestId: number,
    payload: { status: 'approved' | 'rejected'; review_notes?: string }
  ): Promise<DataSecureFieldRequest> {
    return api.put(`/tools/${toolId}/features/field-requests/${requestId}/review`, payload)
  },

  getDataSecureBusinessFunctionOptions(
    toolId: number,
    projectSpaceId: number
  ): Promise<DataSecureBusinessFunctionOptionsResponse> {
    return api.get(`/tools/${toolId}/features/business-function-options`, {
      params: { project_space_id: projectSpaceId }
    })
  },

  createDataSecureBusinessFunctionOptionRequest(
    toolId: number,
    payload: { project_space_id: number; proposed_option: string; reason?: string }
  ): Promise<DataSecureBusinessFunctionOptionRequest> {
    return api.post(`/tools/${toolId}/features/business-function-option-requests`, payload)
  },

  getDataSecureBusinessFunctionOptionRequests(
    toolId: number,
    params: {
      project_space_id?: number
      status?: 'pending' | 'approved' | 'rejected'
      skip?: number
      limit?: number
    }
  ): Promise<PaginatedDataSecureBusinessFunctionOptionRequests> {
    return api.get(`/tools/${toolId}/features/business-function-option-requests`, { params })
  },

  reviewDataSecureBusinessFunctionOptionRequest(
    toolId: number,
    requestId: number,
    payload: { status: 'approved' | 'rejected'; review_notes?: string }
  ): Promise<DataSecureBusinessFunctionOptionRequest> {
    return api.put(`/tools/${toolId}/features/business-function-option-requests/${requestId}/review`, payload)
  },

  createDataSecureFieldUsageReport(
    toolId: number,
    payload: {
      project_space_id: number
      assessment_submission_id: number
      function_name?: string | null
      function_description?: string | null
      field_entry_ids?: number[]
      lines?: Array<{ catalog_entry_id: number; extra_fields?: Record<string, unknown> }>
      notes?: string
    }
  ): Promise<DataSecureFieldUsageReport> {
    return api.post(`/tools/${toolId}/features/field-usage-reports`, payload)
  },

  getDataSecureFieldUsageReports(
    toolId: number,
    params: {
      project_space_id?: number
      review_status?: 'pending' | 'approved' | 'rejected'
      skip?: number
      limit?: number
    }
  ): Promise<PaginatedDataSecureFieldUsageReports> {
    return api.get(`/tools/${toolId}/features/field-usage-reports`, { params })
  },

  reviewDataSecureFieldUsageReport(
    toolId: number,
    reportId: number,
    payload: { status: 'approved' | 'rejected'; review_notes?: string }
  ): Promise<DataSecureFieldUsageReport> {
    return api.post(`/tools/${toolId}/features/field-usage-reports/${reportId}/review`, payload)
  },

  getDataSecureWorkOrders(
    toolId: number,
    params: { project_space_id?: number; skip?: number; limit?: number; mine?: boolean }
  ): Promise<PaginatedDataSecureWorkOrders> {
    return api.get(`/tools/${toolId}/features/work-orders`, { params })
  },

  exportDataSecureApprovedConsolidated(
    toolId: number,
    params: {
      project_space_id: number
      mine?: boolean
      /** 可传多值，序列化为重复 query 键，与 FastAPI list 参数对齐 */
      filter_field_key?: string[]
      filter_value_contains?: string[]
    }
  ): Promise<DataSecureConsolidatedExportResponse> {
    const sp = new URLSearchParams()
    sp.set('project_space_id', String(params.project_space_id))
    if (params.mine) sp.set('mine', 'true')
    for (const k of params.filter_field_key || []) {
      const t = String(k).trim()
      if (t) sp.append('filter_field_key', t)
    }
    for (const v of params.filter_value_contains || []) {
      const t = String(v).trim()
      if (t) sp.append('filter_value_contains', t)
    }
    return api.get(`/tools/${toolId}/features/approved-consolidated-export?${sp.toString()}`)
  },

  exportDataSecureFieldUsageReports(toolId: number, projectSpaceId?: number): Promise<{ items: DataSecureFieldUsageExportRow[] }> {
    return api.get(`/tools/${toolId}/features/field-usage-reports/export`, {
      params: { project_space_id: projectSpaceId }
    })
  },

  getDataSecureClassificationMatrix(
    toolId: number,
    projectSpaceId: number,
    skip: number = 0,
    limit: number = 500
  ): Promise<PaginatedDataSecureClassificationMatrix> {
    return api.get(`/tools/${toolId}/features/classification-matrix`, {
      params: { project_space_id: projectSpaceId, skip, limit }
    })
  },

  createDataSecureClassificationMatrix(
    toolId: number,
    payload: {
      project_space_id: number
      field_name: string
      extension_match?: Record<string, any>
      category: string
      level: string
      priority?: number
      notes?: string
      sort_order?: number
    }
  ): Promise<DataSecureClassificationMatrix> {
    return api.post(`/tools/${toolId}/features/classification-matrix`, payload)
  },

  updateDataSecureClassificationMatrix(
    toolId: number,
    payload: {
      id: number
      field_name?: string
      extension_match?: Record<string, any>
      category?: string
      level?: string
      priority?: number
      notes?: string
      sort_order?: number
      is_active?: boolean
      change_reason: string
    }
  ): Promise<DataSecureClassificationMatrix> {
    return api.put(`/tools/${toolId}/features/classification-matrix`, payload)
  },

  deleteDataSecureClassificationMatrix(
    toolId: number,
    matrixId: number,
    changeReason: string
  ): Promise<{ ok: boolean }> {
    return api.delete(`/tools/${toolId}/features/classification-matrix/${matrixId}`, {
      params: { change_reason: changeReason }
    })
  },

  batchImportDataSecureClassificationMatrix(
    toolId: number,
    payload: {
      project_space_id: number
      items: Array<{
        field_name: string
        extension_match?: Record<string, any>
        category: string
        level: string
        priority?: number
        notes?: string
        sort_order?: number
      }>
    }
  ): Promise<DataSecureClassificationMatrixBatchImportResult> {
    return api.post(`/tools/${toolId}/features/classification-matrix/batch-import`, payload)
  },

  getDataSecureClassificationRules(
    toolId: number,
    projectSpaceId: number,
    skip: number = 0,
    limit: number = 200
  ): Promise<PaginatedDataSecureClassificationRules> {
    return api.get(`/tools/${toolId}/features/classification-rules`, {
      params: { project_space_id: projectSpaceId, skip, limit }
    })
  },

  createDataSecureClassificationRule(
    toolId: number,
    payload: {
      project_space_id: number
      keyword: string
      category: string
      level: string
      priority?: number
      notes?: string
      sort_order?: number
    }
  ): Promise<DataSecureClassificationRule> {
    return api.post(`/tools/${toolId}/features/classification-rules`, payload)
  },

  updateDataSecureClassificationRule(
    toolId: number,
    payload: {
      id: number
      keyword?: string
      category?: string
      level?: string
      priority?: number
      notes?: string
      sort_order?: number
      is_active?: boolean
      change_reason: string
    }
  ): Promise<DataSecureClassificationRule> {
    return api.put(`/tools/${toolId}/features/classification-rules`, payload)
  },

  deleteDataSecureClassificationRule(
    toolId: number,
    ruleId: number,
    changeReason: string
  ): Promise<{ ok: boolean }> {
    return api.delete(`/tools/${toolId}/features/classification-rules/${ruleId}`, {
      params: { change_reason: changeReason }
    })
  },

  recomputeDataSecureClassification(toolId: number, projectSpaceId: number): Promise<{ updated_count: number }> {
    return api.post(`/tools/${toolId}/features/classification-recompute`, null, {
      params: { project_space_id: projectSpaceId }
    })
  },

  getDataSecureClassificationResults(
    toolId: number,
    projectSpaceId: number,
    skip: number = 0,
    limit: number = 200
  ): Promise<PaginatedDataSecureClassificationResults> {
    return api.get(`/tools/${toolId}/features/classification-results`, {
      params: { project_space_id: projectSpaceId, skip, limit }
    })
  },

  manualOverrideDataSecureClassification(
    toolId: number,
    resultId: number,
    payload: { category: string; level: string; reason: string }
  ): Promise<DataSecureClassificationResult> {
    return api.put(`/tools/${toolId}/features/classification-results/${resultId}/manual`, payload)
  },

  revertDataSecureClassificationToAuto(toolId: number, resultId: number): Promise<DataSecureClassificationResult> {
    return api.post(`/tools/${toolId}/features/classification-results/${resultId}/revert-auto`, {})
  },

  getDataSecureClassificationAudit(
    toolId: number,
    projectSpaceId: number,
    skip: number = 0,
    limit: number = 20
  ): Promise<PaginatedDataSecureClassificationAuditLogs> {
    return api.get(`/tools/${toolId}/features/classification-audit`, {
      params: { project_space_id: projectSpaceId, skip, limit }
    })
  },

  exportDataSecureClassification(toolId: number, projectSpaceId: number): Promise<{ items: DataSecureClassificationExportRow[] }> {
    return api.get(`/tools/${toolId}/features/classification-export`, {
      params: { project_space_id: projectSpaceId }
    })
  },

  getDataSecureTaxonomyNodes(
    toolId: number,
    projectSpaceId: number,
    opts?: { parentIsRoot?: boolean; parentId?: number | null; skip?: number; limit?: number }
  ): Promise<PaginatedDataSecureTaxonomyNodes> {
    const params: Record<string, string | number | boolean> = {
      project_space_id: projectSpaceId,
      skip: opts?.skip ?? 0,
      limit: opts?.limit ?? 200
    }
    if (opts?.parentIsRoot) params.parent_is_root = true
    if (opts?.parentId != null && opts?.parentId !== undefined) params.parent_id = opts.parentId
    return api.get(`/tools/${toolId}/features/taxonomy-nodes`, { params })
  },

  createDataSecureTaxonomyNode(
    toolId: number,
    payload: { project_space_id: number; parent_id?: number | null; name: string; node_key: string; sort_order?: number; change_reason: string }
  ): Promise<DataSecureTaxonomyNode> {
    return api.post(`/tools/${toolId}/features/taxonomy-nodes`, payload)
  },

  updateDataSecureTaxonomyNode(
    toolId: number,
    nodeId: number,
    payload: { name?: string; sort_order?: number; is_active?: boolean; change_reason: string }
  ): Promise<DataSecureTaxonomyNode> {
    return api.put(`/tools/${toolId}/features/taxonomy-nodes/${nodeId}`, payload)
  },

  deleteDataSecureTaxonomyNode(
    toolId: number,
    nodeId: number,
    changeReason: string
  ): Promise<{ ok: boolean }> {
    return api.delete(`/tools/${toolId}/features/taxonomy-nodes/${nodeId}`, {
      params: { change_reason: changeReason }
    })
  },

  getDataSecureFieldClassGrades(
    toolId: number,
    projectSpaceId: number,
    skip: number = 0,
    limit: number = 200
  ): Promise<PaginatedDataSecureFieldClassGrades> {
    return api.get(`/tools/${toolId}/features/field-class-grade`, {
      params: { project_space_id: projectSpaceId, skip, limit }
    })
  },

  upsertDataSecureFieldClassGrade(
    toolId: number,
    payload: {
      project_space_id: number
      catalog_entry_id: number
      taxonomy_l1_id?: number | null
      taxonomy_l2_id?: number | null
      confidentiality_grade: string
      notes?: string | null
      change_reason: string
    }
  ): Promise<DataSecureFieldClassGrade> {
    return api.put(`/tools/${toolId}/features/field-class-grade`, payload)
  },

  deleteDataSecureFieldClassGrade(toolId: number, catalogEntryId: number, changeReason: string): Promise<{ ok: boolean }> {
    return api.delete(`/tools/${toolId}/features/field-class-grade/${catalogEntryId}`, { params: { change_reason: changeReason } })
  },

  getDataSecureFieldSecurityRequirements(
    toolId: number,
    projectSpaceId: number,
    opts?: { catalogEntryId?: number; skip?: number; limit?: number }
  ): Promise<PaginatedDataSecureFieldSecurityRequirements> {
    const params: Record<string, string | number> = {
      project_space_id: projectSpaceId,
      skip: opts?.skip ?? 0,
      limit: opts?.limit ?? 200
    }
    if (opts?.catalogEntryId != null) params.catalog_entry_id = opts.catalogEntryId
    return api.get(`/tools/${toolId}/features/field-security-requirements`, { params })
  },

  createDataSecureFieldSecurityRequirement(
    toolId: number,
    payload: {
      project_space_id: number
      catalog_entry_id: number
      requirement_text: string
      logic_expression: string
      predicate_map?: Record<string, unknown>
      priority?: number
      sort_order?: number
      change_reason: string
    }
  ): Promise<DataSecureFieldSecurityRequirement> {
    return api.post(`/tools/${toolId}/features/field-security-requirements`, payload)
  },

  updateDataSecureFieldSecurityRequirement(
    toolId: number,
    requirementId: number,
    payload: {
      requirement_text?: string
      logic_expression?: string
      predicate_map?: Record<string, unknown>
      priority?: number
      sort_order?: number
      is_active?: boolean
      change_reason: string
    }
  ): Promise<DataSecureFieldSecurityRequirement> {
    return api.put(`/tools/${toolId}/features/field-security-requirements/${requirementId}`, payload)
  },

  deleteDataSecureFieldSecurityRequirement(
    toolId: number,
    requirementId: number,
    changeReason: string
  ): Promise<{ ok: boolean }> {
    return api.delete(`/tools/${toolId}/features/field-security-requirements/${requirementId}`, {
      params: { change_reason: changeReason }
    })
  },

  evalDataSecureFieldSecurityRequirements(
    toolId: number,
    payload: { project_space_id: number; catalog_entry_id: number }
  ): Promise<DataSecureFieldSecurityRequirementEvalResponse> {
    return api.post(`/tools/${toolId}/features/field-security-requirements-eval`, payload)
  },

  getDataSecureGovernanceChangeLogs(
    toolId: number,
    params: { project_space_id: number; domain?: string; skip?: number; limit?: number }
  ): Promise<PaginatedDataSecureGovernanceChangeLogs> {
    return api.get(`/tools/${toolId}/features/governance-change-logs`, { params })
  },

  exportDataSecureConfig(
    toolId: number,
    payload: { project_space_id: number; selection: DataSecureConfigExportSelection }
  ): Promise<DataSecureConfigExportPayload> {
    return api.post(`/tools/${toolId}/features/config-export`, payload)
  },

  importDataSecureConfig(
    toolId: number,
    payload: { target_project_space_id: number; payload: DataSecureConfigExportPayload; change_reason: string }
  ): Promise<DataSecureConfigImportResult> {
    return api.post(`/tools/${toolId}/features/config-import`, payload)
  },

  batchDeleteDataSecureConfig(
    toolId: number,
    payload: {
      project_space_id: number
      change_reason: string
      items: Array<{ domain: DataSecureConfigDeleteDomain; target_id: string }>
    }
  ): Promise<{ deleted_count: number; deleted_items: Array<Record<string, string>>; failed_items: Array<Record<string, string>> }> {
    return api.post(`/tools/${toolId}/features/config-batch-delete`, payload)
  },

  updateRsaLivestreamManageConfig(
    toolId: number,
    payload: RsaLivestreamConfigUpdatePayload
  ): Promise<RsaLivestreamConfig> {
    return api.put(`/tools/${toolId}/features/livestream/manage-config`, payload)
  }
}
