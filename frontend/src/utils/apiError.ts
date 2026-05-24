const defaultErrorMessageMap: Record<string, string> = {
  'Incorrect username or password': '用户名或密码错误',
  'Username already registered': '用户名已被注册',
  'Email already registered': '邮箱已被注册',
  'Password must be at least 8 characters': '密码必须至少8个字符',
  'Account pending admin approval': '账号尚在审核中，请等待管理员通过后再登录'
}

export const getFriendlyApiErrorMessage = (
  error: unknown,
  fallback: string,
  customMap?: Record<string, string>
): string => {
  const errorObj = (error ?? {}) as { message?: string }
  const message = errorObj.message || ''
  const mapping = { ...defaultErrorMessageMap, ...(customMap || {}) }

  for (const [key, value] of Object.entries(mapping)) {
    if (message.includes(key)) {
      return value
    }
  }
  return message || fallback
}
