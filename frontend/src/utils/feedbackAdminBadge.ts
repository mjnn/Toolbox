/** 反馈管理角标：表示「自上次在反馈管理页同步以来新增的条数」；进入该页会写入当前库总数，角标清零直至再有新反馈 */

const key = (userId: number) => `feedback_admin_seen_total_${userId}_v1`

/**
 * @param serverTotal 当前库中两类全局反馈总数
 * @param userId 当前超管用户 id
 */
export function getFeedbackAdminBadgeCount(serverTotal: number, userId: number): number {
  if (!userId) return 0
  const raw = localStorage.getItem(key(userId))
  const seen = raw === null || raw === '' ? 0 : Number(raw)
  if (Number.isNaN(seen)) {
    return Math.max(0, serverTotal)
  }
  if (serverTotal < seen) {
    localStorage.setItem(key(userId), String(serverTotal))
    return 0
  }
  return Math.max(0, serverTotal - seen)
}

/** 在打开「反馈管理」页并拉到当前总数后调用，清除角标直至有新反馈 */
export function markFeedbackAdminSeen(serverTotal: number, userId: number): void {
  if (!userId) return
  localStorage.setItem(key(userId), String(serverTotal))
}
