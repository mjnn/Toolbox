import type { NotificationInDB } from '@/api/types'

/**
 * 统一通知跳转规则：
 * - permission: 跳转到权限管理
 * - tool/tool_release: 跳转到对应工具详情（无 related_id 则回工具列表）
 * - 其他类型：不跳转
 */
export function resolveNotificationTarget(item: NotificationInDB): string | null {
  if (item.notification_type === 'permission') return '/permissions'
  if (item.notification_type === 'tool' || item.notification_type === 'tool_release') {
    return item.related_id ? `/tools/${item.related_id}` : '/tools'
  }
  return null
}
