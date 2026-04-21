import { api } from './auth'
import type { PaginatedToolAnnouncements, PaginatedUsers, UserInDB } from './types'

export const usersApi = {
  // 获取用户分页列表（需要管理员权限）
  getUsers(
    skip: number = 0,
    limit: number = 100,
    search?: string,
    approval?: 'pending' | 'approved'
  ): Promise<PaginatedUsers> {
    const params: Record<string, string | number> = { skip, limit }
    const s = search?.trim()
    if (s) params.search = s
    if (approval) params.approval = approval
    return api.get('/users/', { params })
  },

  // 获取单个用户（需要管理员权限）
  getUser(userId: number): Promise<UserInDB> {
    return api.get(`/users/${userId}`)
  },

  getMyAnnouncements(skip: number = 0, limit: number = 20): Promise<PaginatedToolAnnouncements> {
    return api.get('/users/me/announcements', { params: { skip, limit } })
  },
}
