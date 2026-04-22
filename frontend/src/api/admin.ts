import { api } from './auth'
import type {
  AdminResetPasswordPayload,
  AdminUserImportResponse,
  FeedbackCountsResponse,
  FeedbackWithUser,
  PaginatedFeedbackWithUser,
  PaginatedAPIAccessLogs,
  PaginatedToolLicenseUsers,
  RoleAssignmentRequest,
  SuccessResponse,
  ToolInDB,
  ToolReleaseInDB,
  ToolReleasePublishPayload,
  ToolAnnouncementInDB,
  PaginatedToolAnnouncements,
  ToolOwnerWithUser,
  ToolVisibilityConfigResponse,
  ToolVisibilityConfigUpdatePayload,
  UserInDB,
  UserRolesResponse,
} from './types'

export interface AuditLogListParams {
  skip?: number
  limit?: number
  user_id?: number | null
  tool_id?: number | null
  username?: string | null
  /** 关键词：匹配接口路径、功能名、HTTP 方法 */
  q?: string | null
}

export const adminApi = {
  getSystemDbOptimization(): Promise<{
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
  }> {
    return api.get('/admin/system/db-optimization')
  },

  updateSystemDbOptimization(payload: {
    pool_size?: number
    max_overflow?: number
    pool_timeout_seconds?: number
    pool_recycle_seconds?: number
    workers?: number
    statement_timeout_ms?: number
    apply_to_env?: boolean
  }): Promise<{
    saved_overrides: Record<string, number>
    applied_to_env: boolean
    requires_restart: boolean
  }> {
    return api.put('/admin/system/db-optimization', payload)
  },

  pingSystemDbOptimization(): Promise<{ elapsed_ms: number }> {
    return api.post('/admin/system/db-optimization/ping')
  },

  getToolVisibilityConfig(): Promise<ToolVisibilityConfigResponse> {
    return api.get('/admin/system/tool-visibility')
  },

  updateToolVisibilityConfig(payload: ToolVisibilityConfigUpdatePayload): Promise<ToolVisibilityConfigResponse> {
    return api.put('/admin/system/tool-visibility', payload)
  },

  listGlobalAnnouncements(params: { skip: number; limit: number; only_active?: boolean }): Promise<PaginatedToolAnnouncements> {
    return api.get('/admin/announcements/global', { params })
  },

  createGlobalAnnouncement(payload: {
    title: string
    content: string
    is_enabled: boolean
    priority: 'urgent' | 'notice' | 'reminder'
    scroll_speed_seconds: number
    font_family?: string | null
    font_size_px: number
    start_at?: string | null
    end_at?: string | null
    disable_feature_slugs?: string[]
  }): Promise<ToolAnnouncementInDB> {
    return api.post('/admin/announcements/global', payload)
  },

  updateGlobalAnnouncement(
    announcementId: number,
    payload: {
      title?: string
      content?: string
      is_enabled?: boolean
      priority?: 'urgent' | 'notice' | 'reminder'
      scroll_speed_seconds?: number
      font_family?: string | null
      font_size_px?: number
      start_at?: string | null
      end_at?: string | null
      disable_feature_slugs?: string[]
    }
  ): Promise<ToolAnnouncementInDB> {
    return api.patch(`/admin/announcements/global/${announcementId}`, payload)
  },

  getUserRoles(userId: number): Promise<UserRolesResponse> {
    return api.get(`/admin/users/${userId}/roles`)
  },

  assignUserRole(userId: number, data: RoleAssignmentRequest): Promise<SuccessResponse> {
    return api.post(`/admin/users/${userId}/roles`, data)
  },

  revokeUserRole(userId: number, roleName: string): Promise<SuccessResponse> {
    return api.delete(`/admin/users/${userId}/roles/${roleName}`)
  },

  updateToolStatus(toolId: number, is_active: boolean): Promise<ToolInDB> {
    return api.patch(`/admin/tools/${toolId}/status`, { is_active })
  },

  updateToolDisplayConfig(
    toolId: number,
    payload: { display_name?: string | null; display_description?: string | null }
  ): Promise<ToolInDB> {
    return api.put(`/admin/tools/${toolId}/display-config`, payload)
  },

  publishToolRelease(toolId: number, data: ToolReleasePublishPayload): Promise<ToolReleaseInDB> {
    return api.post(`/admin/tools/${toolId}/releases`, {
      version: data.version,
      spec_revision: data.spec_revision ?? undefined,
      title: data.title ?? '版本更新',
      changelog: data.changelog,
      notify_users: data.notify_users !== false,
    })
  },

  getToolOwners(toolId: number): Promise<ToolOwnerWithUser[]> {
    return api.get(`/admin/tools/${toolId}/owners`)
  },

  assignToolOwner(toolId: number, userId: number): Promise<SuccessResponse> {
    return api.post(`/admin/tools/${toolId}/owners/${userId}`)
  },

  removeToolOwner(toolId: number, userId: number): Promise<SuccessResponse> {
    return api.delete(`/admin/tools/${toolId}/owners/${userId}`)
  },

  getToolLicenseUsers(
    toolId: number,
    skip: number = 0,
    limit: number = 20,
    filters?: { search?: string }
  ): Promise<PaginatedToolLicenseUsers> {
    const params: Record<string, string | number> = { skip, limit }
    const s = filters?.search?.trim()
    if (s) params.search = s
    return api.get(`/admin/tools/${toolId}/license-users`, { params })
  },

  revokeToolUserLicense(toolId: number, userId: number): Promise<SuccessResponse> {
    return api.delete(`/admin/tools/${toolId}/license-users/${userId}`)
  },

  getToolUsageLogs(
    toolId: number,
    skip: number = 0,
    limit: number = 100,
    filters?: { username?: string; q?: string }
  ): Promise<PaginatedAPIAccessLogs> {
    const params: Record<string, string | number> = { skip, limit }
    const u = filters?.username?.trim()
    const q = filters?.q?.trim()
    if (u) params.username = u
    if (q) params.q = q
    return api.get(`/admin/tools/${toolId}/usage-logs`, { params })
  },

  getMyOwnerTools(): Promise<number[]> {
    return api.get('/admin/my-owner-tools')
  },

  getAuditLogs(params: AuditLogListParams = {}): Promise<PaginatedAPIAccessLogs> {
    const { skip = 0, limit = 20, user_id, tool_id, username, q } = params
    const query: Record<string, string | number> = { skip, limit }
    if (user_id != null) query.user_id = user_id
    if (tool_id != null) query.tool_id = tool_id
    const u = username?.trim()
    if (u) query.username = u
    const kw = q?.trim()
    if (kw) query.q = kw
    return api.get('/admin/audit-logs', { params: query })
  },

  async exportAuditLogsCsv(params: Omit<AuditLogListParams, 'skip' | 'limit'> = {}): Promise<Blob> {
    const { user_id, tool_id, username, q } = params
    const qs = new URLSearchParams()
    if (user_id != null) qs.set('user_id', String(user_id))
    if (tool_id != null) qs.set('tool_id', String(tool_id))
    const u = username?.trim()
    if (u) qs.set('username', u)
    const kw = q?.trim()
    if (kw) qs.set('q', kw)
    const token = localStorage.getItem('access_token')
    const res = await fetch(`/api/v1/admin/audit-logs/export?${qs}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    if (!res.ok) {
      let message = `导出失败 (${res.status})`
      try {
        const data = await res.json()
        if (typeof data?.detail === 'string') message = data.detail
      } catch {
        /* ignore */
      }
      throw new Error(message)
    }
    return res.blob()
  },

  getToolFeedback(
    toolId: number,
    skip: number = 0,
    limit: number = 20
  ): Promise<PaginatedFeedbackWithUser> {
    return api.get(`/admin/tools/${toolId}/feedback`, { params: { skip, limit } })
  },

  getGlobalFeedback(
    category: 'system_feedback' | 'new_tool_suggestion',
    skip = 0,
    limit = 200
  ): Promise<PaginatedFeedbackWithUser> {
    return api.get('/admin/feedback', { params: { category, skip, limit } })
  },

  getFeedbackCounts(): Promise<FeedbackCountsResponse> {
    return api.get('/admin/feedback/counts')
  },

  approveUser(userId: number): Promise<UserInDB> {
    return api.post(`/admin/users/${userId}/approve`)
  },

  resetUserPassword(userId: number, data: AdminResetPasswordPayload): Promise<SuccessResponse> {
    return api.post(`/admin/users/${userId}/reset-password`, data)
  },

  importUsersByExcel(file: File): Promise<AdminUserImportResponse> {
    const fd = new FormData()
    fd.append('file', file)
    return api.postForm('/admin/users/import-excel', fd)
  },

  async downloadUserImportTemplate(): Promise<Blob> {
    const token = localStorage.getItem('access_token')
    const res = await fetch('/api/v1/admin/users/import-excel/template', {
      headers: token ? { Authorization: `Bearer ${token}` } : {}
    })
    if (!res.ok) {
      let message = `下载模板失败 (${res.status})`
      try {
        const data = await res.json()
        if (typeof data?.detail === 'string') message = data.detail
      } catch {
        /* ignore */
      }
      throw new Error(message)
    }
    return res.blob()
  },

  deleteUser(userId: number): Promise<SuccessResponse> {
    return api.delete(`/admin/users/${userId}`)
  },
}
