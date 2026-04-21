import { api } from './auth'
import type { 
  PermissionCreate, 
  PermissionInDB, 
  PermissionWithDetails,
  PermissionUpdate 
} from './types'

export const permissionsApi = {
  // 申请权限
  applyForPermission(toolId: number, data: PermissionCreate): Promise<PermissionInDB> {
    return api.post(`/permissions/apply/${toolId}`, data)
  },

  // 获取我的权限
  getMyPermissions(): Promise<PermissionWithDetails[]> {
    return api.get('/permissions/my-permissions')
  },

  // 获取待审核权限（需要管理员权限）
  getPendingPermissions(skip: number = 0, limit: number = 100): Promise<PermissionWithDetails[]> {
    return api.get('/admin/permissions/pending', { params: { skip, limit } })
  },

  // 批准权限（需要管理员权限）
  approvePermission(permissionId: number, data: PermissionUpdate): Promise<any> {
    return api.post(`/admin/permissions/${permissionId}/approve`, data)
  },

  // 拒绝权限（需要管理员权限）
  rejectPermission(permissionId: number, data: PermissionUpdate): Promise<any> {
    return api.post(`/admin/permissions/${permissionId}/reject`, data)
  }
}
