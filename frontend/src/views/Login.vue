<template>
  <div class="login-container">
    <div class="login-card">
      <div class="logo">
        <h1>MOS综合工具箱</h1>
        <p>欢迎回来，请登录您的账户</p>
      </div>
      
      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        class="login-form"
        @submit.prevent="handleLogin"
      >
        <el-form-item prop="username">
          <el-input
            v-model="formData.username"
            placeholder="用户名"
            size="large"
            :prefix-icon="User"
          />
        </el-form-item>
        
        <el-form-item prop="password">
          <el-input
            v-model="formData.password"
            type="password"
            placeholder="密码"
            size="large"
            :prefix-icon="Lock"
            show-password
          />
        </el-form-item>
        
        <el-form-item>
          <el-checkbox v-model="rememberMe">记住我</el-checkbox>
        </el-form-item>
        
        <el-button
          type="primary"
          size="large"
          :loading="loading"
          native-type="submit"
          class="login-btn"
        >
          登录
        </el-button>
        
        <div class="links">
          <el-link type="info" @click="showForgotPasswordTip">
            忘记密码
          </el-link>
          <el-link type="primary" @click="$router.push('/register')">
            注册新账户
          </el-link>
        </div>
      </el-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import { authApi } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const formRef = ref<FormInstance>()
const loading = ref(false)
const rememberMe = ref(false)

const formData = reactive({
  username: '',
  password: ''
})

const formRules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' }
  ]
}

// 错误消息映射（英文 -> 中文）
const errorMessageMap: Record<string, string> = {
  'Incorrect username or password': '用户名或密码错误',
  'Username already registered': '用户名已被注册',
  'Email already registered': '邮箱已被注册',
  'Password must be at least 8 characters': '密码必须至少8个字符',
  'Account pending admin approval': '账号尚在审核中，请等待管理员通过后再登录',
}

const getFriendlyErrorMessage = (error: any): string => {
  const message = error.message || ''
  
  // 查找映射表中的错误消息
  for (const [key, value] of Object.entries(errorMessageMap)) {
    if (message.includes(key)) {
      return value
    }
  }
  
  // 如果没有匹配，返回原始消息
  return message || '登录失败'
}

const showForgotPasswordTip = async () => {
  await ElMessageBox.alert(
    '当前暂不支持邮件找回密码，请联系系统管理员重置密码。拿到新密码后，请尽快登录并在个人资料页修改密码。',
    '忘记密码',
    {
      confirmButtonText: '我知道了'
    }
  )
}

const handleLogin = async () => {
  if (!formRef.value) return
  
  try {
    await formRef.value.validate()
    loading.value = true
    
    const loginData = {
      username: formData.username,
      password: formData.password,
      grant_type: 'password'
    }
    
    // 1. 获取令牌
    const tokenResponse = await authApi.login(loginData)
    
    // 2. 存储令牌
    authStore.setTokens(tokenResponse.access_token, tokenResponse.refresh_token)
    
    // 3. 获取用户信息
    const userInfo = await authApi.getCurrentUser()
    authStore.setUserInfo(userInfo)
    
    ElMessage.success('登录成功')
    router.push('/')
  } catch (error: any) {
    console.error('登录失败:', error)
    const friendlyMessage = getFriendlyErrorMessage(error)
    ElMessage.error(friendlyMessage)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-card {
  width: 400px;
  padding: 40px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.1);
}

.logo {
  text-align: center;
  margin-bottom: 30px;
}

.logo h1 {
  font-size: 28px;
  color: #333;
  margin-bottom: 8px;
}

.logo p {
  color: #666;
  font-size: 14px;
}

.login-form :deep(.el-form-item) {
  margin-bottom: 22px;
}

.login-btn {
  width: 100%;
  margin-top: 10px;
  height: 45px;
  font-size: 16px;
}

.links {
  display: flex;
  justify-content: space-between;
  margin-top: 20px;
}
</style>
