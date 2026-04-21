import { api } from './auth'
import type { FeedbackCreatePayload, FeedbackInDB } from './types'

export const feedbackApi = {
  submit(data: FeedbackCreatePayload): Promise<FeedbackInDB> {
    return api.post('/users/me/feedback', data)
  },
}
