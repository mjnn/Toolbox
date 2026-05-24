import type { DataSecureConsolidatedExportRow, DataSecureFieldUsageExportRow } from '@/api/types'

/** Escape CSV cell only when needed (comma, quote, CR/LF). */
export function escapeCsvMinimalCell(value: unknown): string {
  const t = String(value ?? '')
  if (/[",\n\r]/.test(t)) return `"${t.replace(/"/g, '""')}"`
  return t
}

/** Always wrap in double quotes (legacy usage / field导出). */
export function escapeCsvQuotedCell(value: unknown): string {
  return `"${String(value ?? '').replace(/"/g, '""')}"`
}

export function joinCsvRow(cells: string[]): string {
  return cells.join(',')
}

export function downloadUtf8BomCsv(filename: string, lines: string[]): void {
  const body = `\uFEFF${lines.join('\n')}\n`
  const blob = new Blob([body], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename.endsWith('.csv') ? filename : `${filename}.csv`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

const CONSOLIDATED_HEADER_LABELS = [
  '项目空间',
  '问卷提交时间',
  '字段填报时间',
  '数据字段',
  '其他信息JSON',
  '展示分类',
  '展示分级',
  '自动分类',
  '自动分级',
  '命中说明',
  '安全要求（配置）'
] as const

export function buildApprovedConsolidatedCsvLines(items: DataSecureConsolidatedExportRow[]): string[] {
  const head = joinCsvRow(CONSOLIDATED_HEADER_LABELS.map((h) => escapeCsvMinimalCell(h)))
  const rows = items.map((r) =>
    joinCsvRow([
      escapeCsvMinimalCell(r.project_space_name),
      escapeCsvMinimalCell(r.questionnaire_submitted_at),
      escapeCsvMinimalCell(r.usage_submitted_at),
      escapeCsvMinimalCell(r.data_field_name),
      escapeCsvMinimalCell(r.other_info_json),
      escapeCsvMinimalCell(r.category),
      escapeCsvMinimalCell(r.level),
      escapeCsvMinimalCell(r.auto_category),
      escapeCsvMinimalCell(r.auto_level),
      escapeCsvMinimalCell(r.auto_hit_summary || ''),
      escapeCsvMinimalCell(r.security_requirements_text)
    ])
  )
  return [head, ...rows]
}

export function downloadApprovedConsolidatedCsv(filename: string, items: DataSecureConsolidatedExportRow[]): void {
  downloadUtf8BomCsv(filename, buildApprovedConsolidatedCsvLines(items))
}

export function buildFieldUsageExportCsvLines(rows: DataSecureFieldUsageExportRow[]): string[] {
  const header = ['项目空间', '功能名称', '功能描述', '数据字段', '其他信息JSON', '提交人', '提交时间']
  const head = joinCsvRow(header.map((h) => escapeCsvQuotedCell(h)))
  const data = rows.map((row) =>
    joinCsvRow([
      escapeCsvQuotedCell(row.project_space_name),
      escapeCsvQuotedCell(row.function_name),
      escapeCsvQuotedCell(row.function_description ?? ''),
      escapeCsvQuotedCell(row.data_field_name),
      escapeCsvQuotedCell(row.other_info_json ?? ''),
      escapeCsvQuotedCell(row.submitted_by_name ?? ''),
      escapeCsvQuotedCell(row.submitted_at)
    ])
  )
  return [head, ...data]
}

export function downloadFieldUsageExportCsv(filename: string, rows: DataSecureFieldUsageExportRow[]): void {
  downloadUtf8BomCsv(filename, buildFieldUsageExportCsvLines(rows))
}
