import type { ToolInDB } from '@/api/types'

const TOOL_DISPLAY_NAME_MAP: Record<string, string> = {
  'service-id-registry': 'Service ID 注册管理',
  'mos-integration-toolbox': 'MOS 集成工具箱',
  'rsa-token-livestream': 'RSA Token 直播'
}

export const getToolDisplayName = (toolName?: string | null): string => {
  const normalized = (toolName || '').trim()
  if (!normalized) return ''
  return TOOL_DISPLAY_NAME_MAP[normalized] || normalized
}

export const resolveToolDisplayName = (
  toolName?: string | null,
  displayName?: string | null
): string => {
  const custom = (displayName || '').trim()
  if (custom) return custom
  return getToolDisplayName(toolName)
}

export const resolveToolDisplayDescription = (
  description?: string | null,
  displayDescription?: string | null
): string => {
  const custom = (displayDescription || '').trim()
  if (custom) return custom
  const fallback = (description || '').trim()
  return fallback || '暂无描述'
}

/** 与后端一致：更新中/停用时，仅系统超级管理员可继续调用业务 API */
export const isToolBusinessAvailable = (tool: ToolInDB, isSuperuser: boolean): boolean => {
  if (isSuperuser) return true
  if (!tool.is_active) return false
  if (tool.runtime_status === 'updating') return false
  return true
}

export const getToolStatusLabel = (tool: ToolInDB): string => {
  if (!tool.is_active) return '暂不可用'
  if (tool.runtime_status === 'updating') return '更新中'
  return '可用'
}

export const getToolStatusTagType = (tool: ToolInDB): 'success' | 'warning' | 'info' => {
  if (!tool.is_active) return 'warning'
  if (tool.runtime_status === 'updating') return 'info'
  return 'success'
}
