import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { UserInDB } from '@/api/types'

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref<string | null>(localStorage.getItem('access_token'))
  const refreshToken = ref<string | null>(localStorage.getItem('refresh_token'))
  const userInfo = ref<UserInDB | null>(null)

  const isAuthenticated = computed(() => !!accessToken.value)

  function setTokens(access: string, refresh: string) {
    accessToken.value = access
    refreshToken.value = refresh
    localStorage.setItem('access_token', access)
    localStorage.setItem('refresh_token', refresh)
  }

  function clearTokens() {
    accessToken.value = null
    refreshToken.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    userInfo.value = null
  }

  function setAccessToken(token: string) {
    accessToken.value = token
    localStorage.setItem('access_token', token)
  }

  function setRefreshToken(token: string) {
    refreshToken.value = token
    localStorage.setItem('refresh_token', token)
  }

  function setUserInfo(info: UserInDB) {
    userInfo.value = info
  }

  return {
    accessToken,
    refreshToken,
    userInfo,
    isAuthenticated,
    setTokens,
    clearTokens,
    setAccessToken,
    setRefreshToken,
    setUserInfo
  }
})
