<template>
  <div class="tools-container">
    <el-page-header v-if="!isAnonymousView" @back="goBack" title="返回">
      <template #content>
        <span class="page-header-title">{{ pageTitle }}</span>
      </template>
    </el-page-header>
    <div v-else class="welcome-header">
      <div>
        <h2 class="page-header-title">欢迎使用 MOS 综合工具箱</h2>
        <p class="welcome-hint">匿名访客可查看工具、注册登录、申请工具使用与提交新增工具建议。</p>
      </div>
      <div class="welcome-actions">
        <el-button type="primary" @click="router.push('/login')">登录</el-button>
        <el-button @click="router.push('/register')">注册</el-button>
      </div>
    </div>

    <el-form :inline="true" class="tool-filter-form" @submit.prevent="applyToolSearch">
      <el-form-item label="搜索">
        <el-input
          v-model="toolSearchInput"
          placeholder="名称或描述"
          clearable
          style="width: 260px"
          @keyup.enter="applyToolSearch"
        />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="loading" @click="applyToolSearch">查询</el-button>
        <el-button @click="resetToolSearch">重置</el-button>
      </el-form-item>
    </el-form>
    
    <div v-loading="loading" class="tools-grid-wrap">
      <el-empty
        v-if="!loading && displayedTools.length === 0"
        :description="isMyToolsOnly ? '暂无有权限使用的工具' : '暂无匹配的工具'"
      />
      <div v-else class="tools-grid">
      <el-card 
        v-for="tool in displayedTools" 
        :key="tool.id"
        class="tool-card"
        :class="{ 'inactive': !tool.is_active }"
      >
        <template #header>
          <div class="tool-header">
            <span class="tool-name">{{ resolveToolDisplayName(tool.name, tool.display_name) }}</span>
            <el-tag :type="tool.is_active ? 'success' : 'warning'" size="small">
              {{ tool.is_active ? '可用' : '暂不可用' }}
            </el-tag>
          </div>
        </template>
        
        <div class="tool-content">
          <div class="tool-description">
            {{ resolveToolDisplayDescription(tool.description, tool.display_description) }}
          </div>
          <div class="tool-owners" v-if="isAdmin">
            <span class="meta-label">负责人:</span>
            <div class="owner-tags">
              <el-tag
                v-for="owner in getOwners(tool.id)"
                :key="`owner-${tool.id}-${owner.user_id}`"
                size="small"
                type="warning"
              >
                {{ owner.user.username }}
              </el-tag>
              <span v-if="getOwners(tool.id).length === 0" class="empty-owner">未分配</span>
            </div>
          </div>
          <div class="tool-meta">
            <div class="meta-item">
              <span class="meta-label">发版版本:</span>
              <span class="meta-value">{{ tool.version }}</span>
            </div>
            <div class="meta-item" v-if="tool.spec_revision">
              <span class="meta-label">规格修订:</span>
              <span class="meta-value">{{ tool.spec_revision }}</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">创建时间:</span>
              <span class="meta-value">{{ formatDate(tool.created_at) }}</span>
            </div>
          </div>
        </div>
        
        <template #footer>
          <div class="tool-footer">
            <el-button 
              type="primary" 
              size="small"
              @click="handleViewTool(tool)"
              :disabled="!canStartUsing(tool)"
            >
              开始使用
            </el-button>
            <el-button
              v-if="canOpenToolManage(tool.id)"
              type="info"
              size="small"
              plain
              @click="handleToolManage(tool)"
            >
              工具管理
            </el-button>
            <el-button 
              type="success" 
              size="small"
              @click="handleApplyPermission(tool)"
              v-if="tool.is_active && canShowApply(tool.id)"
            >
              {{ isAnonymousView ? '注册并申请' : '申请使用' }}
            </el-button>
            <el-button
              v-if="isAdmin"
              type="warning"
              size="small"
              @click="openOwnerDialog(tool)"
            >
              配置负责人
            </el-button>
            <el-button
              v-if="!isAdmin"
              type="default"
              size="small"
              plain
              @click="openToolFeedback(tool)"
            >
              反馈
            </el-button>
          </div>
        </template>
      </el-card>
      </div>
    </div>

    <el-card v-if="!isMyToolsOnly" class="suggestion-card">
      <template #header>新增工具建议</template>
      <p class="suggestion-hint">有好的工具想法或业务场景？欢迎提交，管理员会在「反馈管理」中查看。</p>
      <el-button type="primary" @click="openSuggestionDialog">提交建议</el-button>
    </el-card>
    
    <!-- 申请权限对话框 -->
    <el-dialog
      v-model="applyDialogVisible"
      :title="isAnonymousView ? '注册并申请使用权限' : '申请使用权限'"
      width="500px"
    >
      <el-form
        ref="applyFormRef"
        :model="applyForm"
        :rules="applyRules"
        label-width="100px"
      >
        <el-form-item label="工具名称" prop="toolName">
          <el-input v-model="applyForm.toolName" disabled />
        </el-form-item>
        <el-form-item label="申请理由" prop="reason" required>
          <el-input
            v-model="applyForm.reason"
            type="textarea"
            :rows="4"
            placeholder="请详细说明您需要使用此工具的理由..."
            maxlength="500"
            show-word-limit
          />
        </el-form-item>
        <template v-if="isAnonymousView">
          <el-divider>注册信息</el-divider>
          <el-form-item label="用户名" prop="username">
            <el-input v-model="anonymousRegisterForm.username" placeholder="请输入用户名" />
          </el-form-item>
          <el-form-item label="邮箱" prop="email">
            <el-input v-model="anonymousRegisterForm.email" placeholder="请输入邮箱" />
          </el-form-item>
          <el-form-item label="姓名" prop="fullName">
            <el-input v-model="anonymousRegisterForm.fullName" placeholder="请输入姓名" />
          </el-form-item>
          <el-form-item label="部门" prop="department">
            <el-input v-model="anonymousRegisterForm.department" placeholder="请输入部门" />
          </el-form-item>
          <el-form-item label="密码" prop="password">
            <el-input
              v-model="anonymousRegisterForm.password"
              type="password"
              show-password
              placeholder="至少 8 位"
            />
          </el-form-item>
          <el-form-item label="确认密码" prop="confirmPassword">
            <el-input
              v-model="anonymousRegisterForm.confirmPassword"
              type="password"
              show-password
              placeholder="请再次输入密码"
            />
          </el-form-item>
        </template>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="applyDialogVisible = false">取消</el-button>
          <el-button 
            type="primary" 
            :loading="applying"
            @click="submitApply"
          >
            提交申请
          </el-button>
        </span>
      </template>
    </el-dialog>

    <el-dialog
      v-model="ownerDialogVisible"
      title="配置工具负责人"
      width="520px"
    >
      <div v-if="selectedTool" class="owner-dialog-content">
        <div class="owner-dialog-title">工具：{{ resolveToolDisplayName(selectedTool.name, selectedTool.display_name) }}</div>
        <el-select
          v-model="selectedOwnerIds"
          multiple
          filterable
          style="width: 100%"
          placeholder="请选择负责人（可多选）"
        >
          <el-option
            v-for="user in ownerCandidates"
            :key="user.id"
            :label="`${user.username} (${user.email})`"
            :value="user.id"
          />
        </el-select>
      </div>
      <template #footer>
        <el-button @click="ownerDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingOwners" @click="saveOwners">保存</el-button>
      </template>
    </el-dialog>

    <FeedbackDialog
      v-model="toolFeedbackDialogVisible"
      category="tool_usage"
      :tool-id="feedbackTargetTool?.id"
      :tool-name="feedbackTargetTool ? resolveToolDisplayName(feedbackTargetTool.name, feedbackTargetTool.display_name) : undefined"
    />
    <FeedbackDialog
      v-if="!isAnonymousView"
      v-model="suggestionDialogVisible"
      category="new_tool_suggestion"
    />
    <el-dialog v-else v-model="anonymousSuggestionDialogVisible" title="提交新增工具建议" width="520px">
      <el-form ref="anonymousSuggestionFormRef" :model="anonymousSuggestionForm" :rules="anonymousSuggestionRules" label-width="96px">
        <el-form-item label="称呼" prop="nickname">
          <el-input v-model="anonymousSuggestionForm.nickname" placeholder="例如：张三" />
        </el-form-item>
        <el-form-item label="联系方式" prop="contact">
          <el-input v-model="anonymousSuggestionForm.contact" placeholder="可选：邮箱/企业微信/电话" />
        </el-form-item>
        <el-form-item label="建议内容" prop="content">
          <el-input
            v-model="anonymousSuggestionForm.content"
            type="textarea"
            :rows="4"
            maxlength="2000"
            show-word-limit
            placeholder="请描述期望新增的工具及使用场景"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="anonymousSuggestionDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submittingAnonymousSuggestion" @click="submitAnonymousSuggestion">提交</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import FeedbackDialog from '@/components/FeedbackDialog.vue'
import { toolsApi } from '@/api/tools'
import { permissionsApi } from '@/api/permissions'
import { usersApi } from '@/api/users'
import { adminApi } from '@/api/admin'
import { authApi } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'
import { resolveToolDisplayDescription, resolveToolDisplayName } from '@/utils/toolDisplay'
import { formatDateOnly as formatDate } from '@/utils/datetime'
import { goBackOrFallback } from '@/utils/navigation'
import type { ToolInDB, ToolOwnerWithUser, UserInDB, PermissionWithDetails } from '@/api/types'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const isMyToolsOnly = computed(() => route.meta.toolsView === 'my')
const isAnonymousView = computed(() => !authStore.isAuthenticated || route.meta.publicTools === true)

const pageTitle = computed(() => (isMyToolsOnly.value ? '我的工具' : '所有工具'))

const loading = ref(false)
const tools = ref<ToolInDB[]>([])
const toolSearchInput = ref('')
const appliedToolSearch = ref('')
const applyDialogVisible = ref(false)
const applying = ref(false)
const selectedTool = ref<ToolInDB | null>(null)
const applyFormRef = ref<FormInstance>()
const ownerDialogVisible = ref(false)
const savingOwners = ref(false)
const selectedOwnerIds = ref<number[]>([])
const ownerCandidates = ref<UserInDB[]>([])
const ownerMap = ref<Record<number, ToolOwnerWithUser[]>>({})
const approvedToolIds = ref<Set<number>>(new Set())
const ownedToolIds = ref<Set<number>>(new Set())

const toolFeedbackDialogVisible = ref(false)
const suggestionDialogVisible = ref(false)
const feedbackTargetTool = ref<ToolInDB | null>(null)
const anonymousSuggestionDialogVisible = ref(false)
const submittingAnonymousSuggestion = ref(false)
const anonymousSuggestionFormRef = ref<FormInstance>()

const isAdmin = computed(() => !!authStore.userInfo?.is_superuser)

const applyForm = ref({
  toolName: '',
  reason: ''
})
const anonymousRegisterForm = ref({
  username: '',
  email: '',
  fullName: '',
  department: '',
  password: '',
  confirmPassword: ''
})
const anonymousSuggestionForm = ref({
  nickname: '',
  contact: '',
  content: ''
})

const applyRules: FormRules = {
  reason: [
    { required: true, message: '请填写申请理由', trigger: 'blur' },
    { min: 10, message: '申请理由至少需要10个字符', trigger: 'blur' }
  ],
  username: [
    {
      validator: (_rule, value, callback) => {
        if (!isAnonymousView.value) return callback()
        const v = String(value || '').trim()
        if (!v) return callback(new Error('请输入用户名'))
        if (v.length < 3) return callback(new Error('用户名至少 3 个字符'))
        callback()
      },
      trigger: 'blur'
    }
  ],
  email: [
    {
      validator: (_rule, value, callback) => {
        if (!isAnonymousView.value) return callback()
        const v = String(value || '').trim()
        if (!v) return callback(new Error('请输入邮箱'))
        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v)) return callback(new Error('邮箱格式不正确'))
        callback()
      },
      trigger: 'blur'
    }
  ],
  fullName: [
    {
      validator: (_rule, value, callback) => {
        if (!isAnonymousView.value) return callback()
        if (!String(value || '').trim()) return callback(new Error('请输入姓名'))
        callback()
      },
      trigger: 'blur'
    }
  ],
  department: [
    {
      validator: (_rule, value, callback) => {
        if (!isAnonymousView.value) return callback()
        if (!String(value || '').trim()) return callback(new Error('请输入部门'))
        callback()
      },
      trigger: 'blur'
    }
  ],
  password: [
    {
      validator: (_rule, value, callback) => {
        if (!isAnonymousView.value) return callback()
        if (String(value || '').length < 8) return callback(new Error('密码至少 8 位'))
        callback()
      },
      trigger: 'blur'
    }
  ],
  confirmPassword: [
    {
      validator: (_rule, value, callback) => {
        if (!isAnonymousView.value) return callback()
        if (value !== anonymousRegisterForm.value.password) return callback(new Error('两次输入的密码不一致'))
        callback()
      },
      trigger: 'blur'
    }
  ]
}
const anonymousSuggestionRules: FormRules = {
  nickname: [{ required: true, message: '请填写称呼', trigger: 'blur' }],
  content: [
    { required: true, message: '请填写建议内容', trigger: 'blur' },
    { min: 5, message: '建议内容至少 5 个字符', trigger: 'blur' }
  ]
}

const goBack = () => {
  goBackOrFallback(router, '/')
}

const applyToolSearch = () => {
  appliedToolSearch.value = toolSearchInput.value.trim()
  fetchTools()
}

const resetToolSearch = () => {
  toolSearchInput.value = ''
  appliedToolSearch.value = ''
  fetchTools()
}

const fetchTools = async () => {
  try {
    loading.value = true
    const data = await toolsApi.getTools(0, 500, appliedToolSearch.value || undefined)
    tools.value = data
    await fetchAccessContext()
    if (isAdmin.value) {
      await fetchOwnersForTools(data)
    }
  } catch (error: any) {
    console.error('获取工具列表失败:', error)
    ElMessage.error(error.message || '获取工具列表失败')
  } finally {
    loading.value = false
  }
}

const fetchAccessContext = async () => {
  if (isAnonymousView.value || isAdmin.value) {
    approvedToolIds.value = new Set()
    ownedToolIds.value = new Set()
    return
  }

  try {
    const myPermissions: PermissionWithDetails[] = await permissionsApi.getMyPermissions()
    const approved = myPermissions
      .filter((item) => item.status === 'approved')
      .map((item) => item.tool_id)
    approvedToolIds.value = new Set(approved)
  } catch {
    approvedToolIds.value = new Set()
  }

  try {
    const owned = await adminApi.getMyOwnerTools()
    ownedToolIds.value = new Set(owned)
  } catch {
    ownedToolIds.value = new Set()
  }
}

const fetchOwnersForTools = async (toolList: ToolInDB[]) => {
  const results: Array<[number, ToolOwnerWithUser[]]> = await Promise.all(
    toolList.map(async (tool) => {
      try {
        const owners = await adminApi.getToolOwners(tool.id)
        return [tool.id, [...owners]]
      } catch {
        return [tool.id, []]
      }
    })
  )
  const nextMap: Record<number, ToolOwnerWithUser[]> = {}
  for (const [toolId, owners] of results) {
    nextMap[toolId] = owners
  }
  ownerMap.value = nextMap
}

const getOwners = (toolId: number): ToolOwnerWithUser[] => {
  return ownerMap.value[toolId] || []
}

const canUseTool = (toolId: number): boolean => {
  if (isAnonymousView.value) return false
  if (isAdmin.value) return true
  if (ownedToolIds.value.has(toolId)) return true
  if (approvedToolIds.value.has(toolId)) return true
  return false
}

/** 有使用权限且（管理员 或 工具为可用）时可进入使用页 */
const canStartUsing = (tool: ToolInDB): boolean => {
  if (!canUseTool(tool.id)) return false
  if (isAdmin.value) return true
  return tool.is_active
}

const displayedTools = computed(() => {
  if (!isMyToolsOnly.value) return tools.value
  return tools.value.filter((t) => canUseTool(t.id))
})

const canApplyTool = (toolId: number): boolean => {
  if (isAnonymousView.value) return true
  if (isAdmin.value) return false
  if (ownedToolIds.value.has(toolId)) return false
  if (approvedToolIds.value.has(toolId)) return false
  return true
}

/** 「我的工具」列表仅含已授权工具，不显示申请入口 */
const canShowApply = (toolId: number): boolean => {
  if (isMyToolsOnly.value) return false
  return canApplyTool(toolId)
}

/** 管理员或该工具负责人可进入工具管理（授权用户、使用记录） */
const canOpenToolManage = (toolId: number): boolean => {
  if (isAdmin.value) return true
  return ownedToolIds.value.has(toolId)
}

const handleToolManage = (tool: ToolInDB) => {
  router.push(`/tools/${tool.id}/manage`)
}

const openToolFeedback = (tool: ToolInDB) => {
  if (isAdmin.value) {
    ElMessage.warning('管理员无需通过此入口提交工具反馈')
    return
  }
  feedbackTargetTool.value = tool
  toolFeedbackDialogVisible.value = true
}

const handleViewTool = (tool: ToolInDB) => {
  if (!canUseTool(tool.id)) {
    ElMessage.warning('该工具尚未获批使用，请先提交申请')
    return
  }
  if (!canStartUsing(tool)) {
    ElMessage.warning('该工具暂不可用')
    return
  }
  router.push(`/tools/${tool.id}`)
}

const handleApplyPermission = (tool: ToolInDB) => {
  selectedTool.value = tool
  applyForm.value = {
    toolName: resolveToolDisplayName(tool.name, tool.display_name),
    reason: ''
  }
  if (isAnonymousView.value) {
    anonymousRegisterForm.value = {
      username: '',
      email: '',
      fullName: '',
      department: '',
      password: '',
      confirmPassword: ''
    }
  }
  applyDialogVisible.value = true
}

const openOwnerDialog = async (tool: ToolInDB) => {
  try {
    selectedTool.value = tool
    if (ownerCandidates.value.length === 0) {
      const res = await usersApi.getUsers(0, 200)
      ownerCandidates.value = res.items
    }
    const owners = await adminApi.getToolOwners(tool.id)
    ownerMap.value[tool.id] = owners
    selectedOwnerIds.value = owners.map((item) => item.user_id)
    ownerDialogVisible.value = true
  } catch (error: any) {
    ElMessage.error(error.message || '加载负责人失败')
  }
}

const saveOwners = async () => {
  if (!selectedTool.value) return
  try {
    savingOwners.value = true
    const toolId = selectedTool.value.id
    const current = new Set((ownerMap.value[toolId] || []).map((item) => item.user_id))
    const target = new Set(selectedOwnerIds.value)

    for (const userId of target) {
      if (!current.has(userId)) {
        await adminApi.assignToolOwner(toolId, userId)
      }
    }
    for (const userId of current) {
      if (!target.has(userId)) {
        await adminApi.removeToolOwner(toolId, userId)
      }
    }

    ownerMap.value[toolId] = await adminApi.getToolOwners(toolId)
    ownerDialogVisible.value = false
    ElMessage.success('负责人已更新')
  } catch (error: any) {
    ElMessage.error(error.message || '更新负责人失败')
  } finally {
    savingOwners.value = false
  }
}

const submitApply = async () => {
  if (!applyFormRef.value) return
  
  try {
    await applyFormRef.value.validate()
    applying.value = true
    
    if (!selectedTool.value) {
      throw new Error('未选择工具')
    }
    
    if (isAnonymousView.value) {
      const payload = {
        username: anonymousRegisterForm.value.username.trim(),
        email: anonymousRegisterForm.value.email.trim(),
        password: anonymousRegisterForm.value.password,
        full_name: anonymousRegisterForm.value.fullName.trim(),
        department: anonymousRegisterForm.value.department.trim(),
        requested_tool_id: selectedTool.value.id,
        requested_tool_reason: applyForm.value.reason.trim(),
        registration_entry: 'apply_tool' as const
      }
      const res = await authApi.register(payload)
      ElMessage.success(res.message || '注册成功，已提交工具申请')
      applyDialogVisible.value = false
      router.push('/login')
      return
    }

    const data = { tool_id: selectedTool.value.id, applied_reason: applyForm.value.reason }
    await permissionsApi.applyForPermission(selectedTool.value.id, data)
    ElMessage.success('权限申请已提交，请等待审核')
    applyDialogVisible.value = false
  } catch (error: any) {
    console.error('提交申请失败:', error)
    ElMessage.error(error.message || '提交申请失败')
  } finally {
    applying.value = false
  }
}

const openSuggestionDialog = () => {
  if (isAnonymousView.value) {
    anonymousSuggestionForm.value = { nickname: '', contact: '', content: '' }
    anonymousSuggestionDialogVisible.value = true
    return
  }
  suggestionDialogVisible.value = true
}

const submitAnonymousSuggestion = async () => {
  if (!anonymousSuggestionFormRef.value) return
  try {
    await anonymousSuggestionFormRef.value.validate()
    submittingAnonymousSuggestion.value = true
    await authApi.submitPublicNewToolSuggestion({
      nickname: anonymousSuggestionForm.value.nickname.trim(),
      contact: anonymousSuggestionForm.value.contact.trim() || undefined,
      content: anonymousSuggestionForm.value.content.trim()
    })
    ElMessage.success('建议已提交，感谢反馈')
    anonymousSuggestionDialogVisible.value = false
  } catch (error: any) {
    ElMessage.error(error?.message || '提交建议失败')
  } finally {
    submittingAnonymousSuggestion.value = false
  }
}

onMounted(() => {
  fetchTools()
})
</script>

<style scoped>
.tools-container {
  padding: 20px;
}

.tool-filter-form {
  margin-top: 12px;
}

.page-header-title {
  font-size: 18px;
  font-weight: bold;
  color: #303133;
}

.welcome-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.welcome-hint {
  margin: 6px 0 0;
  color: #909399;
  font-size: 13px;
}

.welcome-actions {
  display: flex;
  gap: 8px;
}

.tools-grid-wrap {
  margin-top: 20px;
  min-height: 120px;
}

.tools-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
}

.tool-card {
  height: 100%;
  transition: all 0.3s;
}

.tool-card.inactive {
  opacity: 0.7;
  background-color: #f9f9f9;
}

.tool-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 10px 20px rgba(0, 0, 0, 0.1);
}

.tool-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.tool-name {
  font-size: 16px;
  font-weight: bold;
}

.tool-content {
  min-height: 120px;
}

.tool-description {
  margin-bottom: 15px;
  color: #666;
  line-height: 1.5;
}

.tool-meta {
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 12px;
  color: #999;
}

.tool-owners {
  display: flex;
  margin-bottom: 12px;
  gap: 8px;
}

.owner-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.empty-owner {
  color: #999;
  font-size: 12px;
}

.meta-item {
  display: flex;
}

.meta-label {
  flex: 0 0 60px;
}

.meta-value {
  flex: 1;
}

.tool-footer {
  display: flex;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: 10px;
}

.suggestion-card {
  margin-top: 24px;
}

.suggestion-hint {
  color: #909399;
  font-size: 13px;
  margin: 0 0 16px;
  line-height: 1.5;
}

.owner-dialog-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.owner-dialog-title {
  color: #666;
  font-size: 14px;
}
</style>
