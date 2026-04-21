import type { Router } from 'vue-router'

/**
 * 优先返回上一个站内页面；若无历史则回退到给定路径。
 */
export const goBackOrFallback = (router: Router, fallback: string) => {
  const back = (window.history.state as { back?: unknown } | null)?.back
  if (back != null) {
    router.back()
    return
  }
  router.push(fallback)
}

