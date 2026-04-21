/** 全站展示用东八区（UTC+8），与后端存储的 UTC 时刻一致 */
const TZ = 'Asia/Shanghai'

function parseInput(value: string | Date | null | undefined): Date | null {
  if (value === null || value === undefined || value === '') return null
  if (value instanceof Date) {
    return Number.isNaN(value.getTime()) ? null : value
  }
  const d = new Date(value)
  return Number.isNaN(d.getTime()) ? null : d
}

/** 日期+时间，表格/时间线常用 */
export function formatDateTime(value: string | Date | null | undefined): string {
  const d = parseInput(value)
  if (!d) return typeof value === 'string' ? value : '—'
  return new Intl.DateTimeFormat('zh-CN', {
    timeZone: TZ,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  }).format(d)
}

/** 仅日期（卡片元数据等） */
export function formatDateOnly(value: string | Date | null | undefined): string {
  const d = parseInput(value)
  if (!d) return typeof value === 'string' ? value : '—'
  return new Intl.DateTimeFormat('zh-CN', {
    timeZone: TZ,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(d)
}

/** 仪表盘顶部「当前东八区日期 + 星期」 */
export function formatShanghaiCalendarHeader(date: Date = new Date()): string {
  const dtf = new Intl.DateTimeFormat('zh-CN', {
    timeZone: TZ,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    weekday: 'long',
  })
  const parts = dtf.formatToParts(date)
  const get = (type: string) => parts.find((p) => p.type === type)?.value ?? ''
  const y = get('year')
  const m = get('month')
  const day = get('day')
  const wd = get('weekday')
  return `${y}年${m}月${day}日 ${wd}`
}
