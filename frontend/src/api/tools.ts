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
  ServiceIdRuleOption,
  ServiceIdRuleOptionGroup,
  PaginatedServiceIdRuleOptions,
  ServiceRuleCategory
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

  exportServiceIdEntries(toolId: number): Promise<Blob> {
    return api.get(`/tools/${toolId}/features/service-id-export`, {
      responseType: 'blob'
    })
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
  }
}
