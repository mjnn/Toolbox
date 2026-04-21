const TOOL_DISPLAY_NAME_MAP: Record<string, string> = {
  'service-id-registry': 'Service ID 注册管理',
  'mos-integration-toolbox': 'MOS 集成工具箱'
}

export const getToolDisplayName = (toolName?: string | null): string => {
  const normalized = (toolName || '').trim()
  if (!normalized) return ''
  return TOOL_DISPLAY_NAME_MAP[normalized] || normalized
}
