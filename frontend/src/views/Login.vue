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
        <el-form-item prop="username" label="用户名">
          <el-input
            v-model="formData.username"
            placeholder="用户名"
            size="large"
            :prefix-icon="User"
            autocomplete="username"
          />
        </el-form-item>
        
        <el-form-item prop="password" label="密码">
          <el-input
            v-model="formData.password"
            type="password"
            placeholder="密码"
            size="large"
            :prefix-icon="Lock"
            show-password
            autocomplete="current-password"
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
import { getFriendlyApiErrorMessage } from '@/utils/apiError'

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
    const friendlyMessage = getFriendlyApiErrorMessage(error, '登录失败')
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
  padding: 16px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-card {
  width: min(400px, 100%);
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

.login-form :deep(.el-form-item__label) {
  font-weight: 600;
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

@media (max-width: 768px) {
  .login-card {
    padding: 24px 18px;
    border-radius: 10px;
  }

  .logo {
    margin-bottom: 20px;
  }

  .logo h1 {
    font-size: 22px;
  }
}
</style>
