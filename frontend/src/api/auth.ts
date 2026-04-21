import axios from 'axios'
import type {
  LoginRequest,
  TokenResponse,
  RefreshTokenRequest,
  SuccessResponse,
  UserCreate,
  UserInDB,
  UserUpdate,
  RegisterResponse,
  PasswordChangePayload,
  AccountDeleteConfirm,
} from './types'

interface ApiError extends Error {
  detail?: unknown
  status?: number
  data?: unknown
}

const timeoutFromEnv = Number(import.meta.env.VITE_API_TIMEOUT_MS ?? 600000)
const API_TIMEOUT_MS = Number.isFinite(timeoutFromEnv) && timeoutFromEnv >= 1000 ? timeoutFromEnv : 600000

// 创建axios实例
export const api = axios.create({
  baseURL: '/api/v1',
  timeout: API_TIMEOUT_MS,
  headers: {
    'Content-Type': 'application/json'
  }
})

type RetryableRequestConfig = {
  _retry?: boolean
  url?: string
  headers?: Record<string, any>
}

const ACCESS_TOKEN_KEY = 'access_token'
const REFRESH_TOKEN_KEY = 'refresh_token'
const REFRESH_AHEAD_SECONDS = 60
let refreshPromise: Promise<string> | null = null

const parseJwtExp = (token: string): number | null => {
  try {
    const payload = token.split('.')[1]
    if (!payload) return null
    const normalized = payload.replace(/-/g, '+').replace(/_/g, '/')
    const padded = normalized + '='.repeat((4 - (normalized.length % 4)) % 4)
    const decoded = JSON.parse(atob(padded))
    return typeof decoded.exp === 'number' ? decoded.exp : null
  } catch {
    return null
  }
}

const clearLocalTokens = () => {
  localStorage.removeItem(ACCESS_TOKEN_KEY)
  localStorage.removeItem(REFRESH_TOKEN_KEY)
}

const requestRefreshToken = async (): Promise<string> => {
  const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY)
  if (!refreshToken) {
    throw new Error('missing refresh token')
  }
  const response = await axios.post('/api/v1/auth/refresh', { refresh_token: refreshToken }, {
    timeout: API_TIMEOUT_MS,
    headers: { 'Content-Type': 'application/json' }
  })
  const data = response.data as TokenResponse
  if (!data?.access_token || !data?.refresh_token) {
    throw new Error('invalid refresh response')
  }
  localStorage.setItem(ACCESS_TOKEN_KEY, data.access_token)
  localStorage.setItem(REFRESH_TOKEN_KEY, data.refresh_token)
  return data.access_token
}

const ensureFreshAccessToken = async (): Promise<string | null> => {
  const accessToken = localStorage.getItem(ACCESS_TOKEN_KEY)
  if (!accessToken) return null
  const exp = parseJwtExp(accessToken)
  if (!exp) return accessToken
  const now = Math.floor(Date.now() / 1000)
  if (exp - now > REFRESH_AHEAD_SECONDS) {
    return accessToken
  }
  if (!refreshPromise) {
    refreshPromise = requestRefreshToken().finally(() => {
      refreshPromise = null
    })
  }
  return refreshPromise
}

// 请求拦截器：添加token
api.interceptors.request.use(
  async (config) => {
    const isAuthEndpoint = String(config.url || '').includes('/auth/login') || String(config.url || '').includes('/auth/refresh')
    const token = isAuthEndpoint ? localStorage.getItem(ACCESS_TOKEN_KEY) : await ensureFreshAccessToken()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器：处理错误
api.interceptors.response.use(
  (response) => {
    // 后端直接返回数据，没有包裹结构
    return response.data
  },
  async (error) => {
    const originalRequest = (error.config || {}) as RetryableRequestConfig
    const status = error.response?.status
    const data = error.response?.data
    
    console.log('API错误响应:', { status, data, error, pathname: window.location.pathname })
    
    const reqUrl = String(originalRequest.url || '')
    const isAuthLogin = reqUrl.includes('/auth/login')
    const isAuthRefresh = reqUrl.includes('/auth/refresh')
    if (status === 401 && !originalRequest._retry && !isAuthLogin && !isAuthRefresh) {
      originalRequest._retry = true
      try {
        if (!refreshPromise) {
          refreshPromise = requestRefreshToken().finally(() => {
            refreshPromise = null
          })
        }
        const nextToken = await refreshPromise
        originalRequest.headers = originalRequest.headers || {}
        originalRequest.headers.Authorization = `Bearer ${nextToken}`
        return api.request(originalRequest as any)
      } catch {
        if (window.location.pathname !== '/login') {
          clearLocalTokens()
          window.location.href = '/login'
        }
        return Promise.reject(new Error('认证已过期，请重新登录'))
      }
    }

    if (status === 401 && window.location.pathname !== '/login') {
      clearLocalTokens()
      window.location.href = '/login'
      return Promise.reject(new Error('认证已过期，请重新登录'))
    }
    
    // 统一错误格式处理
    const unifiedError: ApiError = new Error()
    
    if (data?.detail) {
      if (Array.isArray(data.detail)) {
        // 422 验证错误格式: {detail: [{loc, msg, type}]}
        unifiedError.message = data.detail.map((err: any) => err.msg).join(', ')
        unifiedError.detail = data.detail
      } else {
        // 400/401 业务错误格式: {detail: "错误消息"}
        unifiedError.message = data.detail
        unifiedError.detail = data.detail
      }
    } else if (data?.message) {
      unifiedError.message = data.message
    } else if (error.message) {
      unifiedError.message = error.message
    } else {
      unifiedError.message = `请求失败: ${status || '未知错误'}`
    }
    
    unifiedError.status = status
    unifiedError.data = data
    
    return Promise.reject(unifiedError)
  }
)

export const authApi = {
  // 登录 - 使用 application/x-www-form-urlencoded
  login(data: LoginRequest): Promise<TokenResponse> {
    const formData = new URLSearchParams()
    formData.append('username', data.username)
    formData.append('password', data.password)
    
    // OAuth2PasswordRequestForm需要grant_type字段
    formData.append('grant_type', data.grant_type || 'password')
    
    // 可选字段
    if (data.scope) formData.append('scope', data.scope)
    if (data.client_id != null) formData.append('client_id', data.client_id)
    if (data.client_secret != null) formData.append('client_secret', data.client_secret)
    
    // 直接使用axios实例发送，确保代理正常工作
    return api.post('/auth/login', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      },
      transformRequest: [(data) => data], // 防止axios自动转换
    })
  },

  // 注册（普通用户需管理员审核）
  register(data: UserCreate): Promise<RegisterResponse> {
    return api.post('/auth/register', data)
  },

  // 刷新令牌
  refreshToken(data: RefreshTokenRequest): Promise<TokenResponse> {
    return api.post('/auth/refresh', data)
  },

  // 获取当前用户信息
  getCurrentUser(): Promise<UserInDB> {
    return api.get('/users/me')
  },

  // 更新当前用户信息
  updateCurrentUser(data: UserUpdate): Promise<UserInDB> {
    return api.put('/users/me', data)
  },

  changePassword(data: PasswordChangePayload): Promise<SuccessResponse> {
    return api.post('/users/me/password', data)
  },

  uploadAvatar(file: File): Promise<UserInDB> {
    const fd = new FormData()
    fd.append('file', file)
    return api.post('/users/me/avatar', fd)
  },

  // 登出
  logout(): Promise<SuccessResponse> {
    return api.post('/auth/logout')
  },

  /** 注销当前账号（需密码） */
  deleteAccount(data: AccountDeleteConfirm): Promise<SuccessResponse> {
    return api.delete('/users/me', { data })
  },
}
