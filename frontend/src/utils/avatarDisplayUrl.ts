/**
 * 头像展示地址：为静态资源追加版本参数，避免同路径文件被覆盖后浏览器仍使用旧缓存。
 */
export function buildAvatarDisplaySrc(
  avatarUrl: string | null | undefined,
  updatedAt?: string | null,
): string | undefined {
  if (!avatarUrl) return undefined
  const ver = (updatedAt ?? '').trim()
  if (!ver) return avatarUrl
  const sep = avatarUrl.includes('?') ? '&' : '?'
  return `${avatarUrl}${sep}v=${encodeURIComponent(ver)}`
}
