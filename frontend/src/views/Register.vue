<template>
  <div class="register-container">
    <div class="register-card">
      <div class="logo">
        <h1>注册账户</h1>
        <p>可选择仅注册，或注册并申请指定工具</p>
      </div>
      
      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        class="register-form"
        @submit.prevent="handleRegister"
      >
        <el-form-item prop="username">
          <el-input
            v-model="formData.username"
            placeholder="用户名"
            size="large"
            :prefix-icon="User"
          />
        </el-form-item>
        
        <el-form-item prop="email">
          <el-input
            v-model="formData.email"
            placeholder="邮箱"
            size="large"
            :prefix-icon="Message"
          />
        </el-form-item>
        
        <el-form-item prop="fullName">
          <el-input
            v-model="formData.fullName"
            placeholder="姓名"
            size="large"
            :prefix-icon="User"
          />
        </el-form-item>

        <el-form-item prop="department">
          <el-input
            v-model="formData.department"
            placeholder="部门"
            size="large"
            :prefix-icon="OfficeBuilding"
          />
        </el-form-item>

        <el-form-item prop="registrationMode" label="注册方式">
          <el-radio-group v-model="formData.registrationMode">
            <el-radio value="register_only">仅注册</el-radio>
            <el-radio value="register_with_tool">注册并申请工具</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item
          v-if="formData.registrationMode === 'register_with_tool'"
          prop="requestedToolId"
          label="目标工具"
        >
          <el-select
            v-model="formData.requestedToolId"
            placeholder="请选择要申请的工具"
            filterable
            style="width: 100%"
          >
            <el-option
              v-for="tool in toolOptions"
              :key="tool.id"
              :label="buildToolOptionLabel(tool)"
              :value="tool.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item
          v-if="formData.registrationMode === 'register_with_tool'"
          prop="requestedToolReason"
          label="申请理由"
        >
          <el-input
            v-model="formData.requestedToolReason"
            type="textarea"
            :rows="3"
            maxlength="500"
            show-word-limit
            placeholder="请说明您希望使用该工具的业务场景"
          />
        </el-form-item>
        
        <el-form-item prop="password">
          <el-input
            v-model="formData.password"
            type="password"
            placeholder="密码（至少8个字符）"
            size="large"
            :prefix-icon="Lock"
            show-password
          />
        </el-form-item>
        
        <el-form-item prop="confirmPassword">
          <el-input
            v-model="formData.confirmPassword"
            type="password"
            placeholder="确认密码"
            size="large"
            :prefix-icon="Lock"
            show-password
          />
        </el-form-item>
        
        <el-button
          type="primary"
          size="large"
          :loading="loading"
          native-type="submit"
          class="register-btn"
        >
          注册
        </el-button>
        
        <div class="links">
          <el-link type="primary" @click="$router.push('/login')">
            已有账户？立即登录
          </el-link>
        </div>
      </el-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { User, Lock, Message, OfficeBuilding } from '@element-plus/icons-vue'
import { authApi } from '@/api/auth'
import { toolsApi } from '@/api/tools'
import type { ToolInDB } from '@/api/types'
import { resolveToolDisplayDescription, resolveToolDisplayName } from '@/utils/toolDisplay'

const router = useRouter()
const formRef = ref<FormInstance>()
const loading = ref(false)
const toolOptions = ref<ToolInDB[]>([])

const formData = reactive({
  username: '',
  email: '',
  fullName: '',
  department: '',
  registrationMode: 'register_only',
  requestedToolId: null as number | null,
  requestedToolReason: '',
  password: '',
  confirmPassword: ''
})

// 自定义密码确认验证
const validateConfirmPassword = (rule: any, value: string, callback: any) => {
  if (value !== formData.password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const formRules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名长度在 3 到 20 个字符', trigger: 'blur' }
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' }
  ],
  fullName: [
    { required: true, message: '请输入姓名', trigger: 'blur' },
    { min: 1, max: 100, message: '姓名长度 1～100 个字符', trigger: 'blur' }
  ],
  department: [
    { required: true, message: '请输入部门', trigger: 'blur' },
    { min: 1, max: 100, message: '部门长度 1～100 个字符', trigger: 'blur' }
  ],
  registrationMode: [{ required: true, message: '请选择注册方式', trigger: 'change' }],
  requestedToolId: [
    {
      validator: (_rule, value, callback) => {
        if (formData.registrationMode !== 'register_with_tool') return callback()
        if (!value) return callback(new Error('请选择目标工具'))
        callback()
      },
      trigger: 'change'
    }
  ],
  requestedToolReason: [
    {
      validator: (_rule, value, callback) => {
        if (formData.registrationMode !== 'register_with_tool') return callback()
        if (!String(value || '').trim()) return callback(new Error('请填写申请理由'))
        if (String(value || '').trim().length < 5) return callback(new Error('申请理由至少 5 个字符'))
        callback()
      },
      trigger: 'blur'
    }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 8, max: 72, message: '密码长度在 8 到 72 个字符', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' }
  ]
}

// 错误消息映射（英文 -> 中文）
const errorMessageMap: Record<string, string> = {
  'Username already registered': '用户名已被注册',
  'Email already registered': '邮箱已被注册',
  'Password must be at least 8 characters': '密码必须至少8个字符',
  'Incorrect username or password': '用户名或密码错误'
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
  return message || '注册失败'
}

const buildToolOptionLabel = (tool: ToolInDB): string => {
  const displayName = resolveToolDisplayName(tool.name, tool.display_name)
  const desc = resolveToolDisplayDescription(tool.description, tool.display_description)
  return `${displayName}（${desc}）`
}

const handleRegister = async () => {
  if (!formRef.value) return
  
  try {
    await formRef.value.validate()
    loading.value = true
    
    const registerData = {
      username: formData.username,
      email: formData.email,
      password: formData.password,
      full_name: formData.fullName.trim(),
      department: formData.department.trim(),
      requested_tool_id:
        formData.registrationMode === 'register_with_tool' ? formData.requestedToolId ?? undefined : undefined,
      requested_tool_reason:
        formData.registrationMode === 'register_with_tool'
          ? formData.requestedToolReason.trim()
          : undefined,
      registration_entry: 'direct_register' as const
    }
    
    const res = await authApi.register(registerData)

    ElMessage.success(res.message || `已提交注册：${res.username}`)
    router.push('/login')
  } catch (error: any) {
    console.error('注册失败:', error)
    const friendlyMessage = getFriendlyErrorMessage(error)
    ElMessage.error(friendlyMessage)
  } finally {
    loading.value = false
  }
}

const loadToolsForRegistration = async () => {
  try {
    const rows = await toolsApi.getTools(0, 500)
    toolOptions.value = rows.filter((tool) => tool.is_active)
  } catch {
    toolOptions.value = []
  }
}

onMounted(() => {
  loadToolsForRegistration()
})
</script>

<style scoped>
.register-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.register-card {
  width: 450px;
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

.register-form :deep(.el-form-item) {
  margin-bottom: 22px;
}

.register-btn {
  width: 100%;
  margin-top: 10px;
  height: 45px;
  font-size: 16px;
}

.links {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}
</style>
