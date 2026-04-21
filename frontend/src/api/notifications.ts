import { api } from './auth'
import type { NotificationInDB, SuccessResponse } from './types'

export const notificationsApi = {
  list(): Promise<NotificationInDB[]> {
    return api.get('/users/me/notifications')
  },

  markRead(notificationId: number): Promise<NotificationInDB> {
    return api.patch(`/users/me/notifications/${notificationId}`)
  },

  deleteOne(notificationId: number): Promise<SuccessResponse> {
    return api.delete(`/users/me/notifications/${notificationId}`)
  },

  clearAll(): Promise<SuccessResponse> {
    return api.delete('/users/me/notifications')
  },
}
