<template>
  <div class="users-container">
    <el-page-header @back="goBack" title="返回">
      <template #content>
        <span class="page-header-title">用户管理</span>
      </template>
    </el-page-header>
    
    <el-card class="main-card">
      <template #header>
        <div class="card-header">
          <span>用户列表</span>
          <div class="header-actions">
            <el-button
              v-if="isAdmin"
              plain
              :loading="downloadingTemplate"
              @click="downloadImportTemplate"
            >
              下载Excel模板
            </el-button>
            <el-upload
              v-if="isAdmin"
              :show-file-list="false"
              accept=".xlsx,.xlsm"
              :before-upload="beforeExcelUpload"
            >
              <el-button type="primary" plain :loading="importingUsers">Excel 批量导入用户</el-button>
            </el-upload>
            <el-tag type="info" size="small">管理员可配置 tool_user / tool_owner</el-tag>
          </div>
        </div>
      </template>

      <el-form :inline="true" class="filter-form" @submit.prevent="onUserSearch">
        <el-form-item label="审核">
          <el-radio-group v-model="approvalFilter" @change="onApprovalFilterChange">
            <el-radio-button value="all">全部</el-radio-button>
            <el-radio-button value="pending">待审核</el-radio-button>
            <el-radio-button value="approved">已通过</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="搜索">
          <el-input
            v-model="userSearchInput"
            placeholder="用户名 / 邮箱 / 姓名"
            clearable
            style="width: 260px"
            @keyup.enter="onUserSearch"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="onUserSearch">查询</el-button>
          <el-button @click="onUserSearchReset">重置</el-button>
        </el-form-item>
      </el-form>
      
      <el-table
        :data="users"
        v-loading="loading"
        stripe
        style="width: 100%"
      >
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="username" label="用户名" />
        <el-table-column prop="email" label="邮箱" />
        <el-table-column prop="full_name" label="姓名" width="120" />
        <el-table-column prop="department" label="部门" width="120">
          <template #default="scope">{{ scope.row.department || '—' }}</template>
        </el-table-column>
        <el-table-column label="审核" width="100">
          <template #default="scope">
            <el-tag :type="scope.row.is_approved ? 'success' : 'warning'" size="small">
              {{ scope.row.is_approved ? '已通过' : '待审核' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="is_active" label="状态" width="100">
          <template #default="scope">
            <el-tag :type="scope.row.is_active ? 'success' : 'danger'">
              {{ scope.row.is_active ? '活跃' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="is_superuser" label="管理员" width="100">
          <template #default="scope">
            <el-tag :type="scope.row.is_superuser ? 'warning' : 'info'">
              {{ scope.row.is_superuser ? '是' : '否' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="scope">
            {{ formatDate(scope.row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="角色" width="240">
          <template #default="scope">
            <div class="role-tags">
              <el-tag
                v-for="role in getRoles(scope.row.id)"
                :key="`${scope.row.id}-${role}`"
                size="small"
                type="success"
              >
                {{ getRoleLabel(role) }}
              </el-tag>
              <span v-if="getRoles(scope.row.id).length === 0" class="empty-role">未分配</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="420" fixed="right">
          <template #default="scope">
            <el-button
              v-if="!scope.row.is_approved && !scope.row.is_superuser"
              type="success"
              size="small"
              :loading="approvingId === scope.row.id"
              @click="approveUser(scope.row)"
            >
              通过审核
            </el-button>
            <el-button
              type="primary"
              size="small"
              :disabled="!isAdmin"
              @click="openRoleDialog(scope.row)"
            >
              配置角色
            </el-button>
            <el-button
              v-if="isAdmin && scope.row.id !== currentUser?.id"
              type="warning"
              size="small"
              plain
              :loading="resettingUserId === scope.row.id"
              @click="resetUserPassword(scope.row)"
            >
              重置密码
            </el-button>
            <el-button
              v-if="isAdmin && scope.row.id !== currentUser?.id && !scope.row.is_superuser"
              type="danger"
              size="small"
              plain
              :loading="deletingUserId === scope.row.id"
              @click="deleteUserAdmin(scope.row)"
            >
              注销用户
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <el-dialog
      v-model="roleDialogVisible"
      title="配置用户角色"
      width="460px"
    >
      <div v-if="selectedUser" class="role-dialog-content">
        <div class="role-dialog-user">
          用户：{{ selectedUser.username }}（{{ selectedUser.email }}）
        </div>
        <el-checkbox v-model="roleForm.tool_user">工具用户（可申请工具权限）</el-checkbox>
        <el-checkbox v-model="roleForm.tool_owner">工具负责人（可审批被指派工具）</el-checkbox>
      </div>
      <template #footer>
        <el-button @click="roleDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingRoles" @click="saveRoleConfig">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="importResultVisible" title="批量导入结果" width="620px">
      <div v-if="importResult" class="import-result">
        <el-alert
          :title="`共解析 ${importResult.total_rows} 行，成功 ${importResult.created_count} 行，跳过 ${importResult.skipped_count} 行。`"
          type="success"
          :closable="false"
        />
        <el-alert
          v-if="importResult.skipped_items.length > 0"
          :title="skippedPreviewText"
          type="warning"
          :closable="false"
          style="margin-top: 12px"
        />
      </div>
      <template #footer>
        <el-button type="primary" @click="importResultVisible = false">知道了</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { usersApi } from '@/api/users'
import { adminApi } from '@/api/admin'
import { useAuthStore } from '@/stores/auth'
import type { AdminUserImportResponse, RoleName, UserInDB } from '@/api/types'
import { formatDateTime as formatDate } from '@/utils/datetime'
import { goBackOrFallback } from '@/utils/navigation'

const router = useRouter()
const authStore = useAuthStore()
const loading = ref(false)
const users = ref<UserInDB[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const userSearchInput = ref('')
const appliedUserSearch = ref('')
const roleMap = ref<Record<number, RoleName[]>>({})
const roleDialogVisible = ref(false)
const savingRoles = ref(false)
const selectedUser = ref<UserInDB | null>(null)
const roleForm = ref({ tool_user: false, tool_owner: false })
const approvalFilter = ref<'all' | 'pending' | 'approved'>('all')
const approvingId = ref<number | null>(null)
const resettingUserId = ref<number | null>(null)
const deletingUserId = ref<number | null>(null)
const importingUsers = ref(false)
const downloadingTemplate = ref(false)
const importResultVisible = ref(false)
const importResult = ref<AdminUserImportResponse | null>(null)

const currentUser = computed(() => authStore.userInfo)
const isAdmin = computed(() => currentUser.value?.is_superuser || false)

const goBack = () => {
  goBackOrFallback(router, '/')
}

const onUserSearch = () => {
  appliedUserSearch.value = userSearchInput.value.trim()
  currentPage.value = 1
  fetchUsers()
}

const onUserSearchReset = () => {
  userSearchInput.value = ''
  appliedUserSearch.value = ''
  approvalFilter.value = 'all'
  currentPage.value = 1
  fetchUsers()
}

const onApprovalFilterChange = () => {
  currentPage.value = 1
  fetchUsers()
}

const fetchUsers = async () => {
  try {
    loading.value = true
    const skip = (currentPage.value - 1) * pageSize.value
    const res = await usersApi.getUsers(
      skip,
      pageSize.value,
      appliedUserSearch.value || undefined,
      approvalFilter.value === 'all' ? undefined : approvalFilter.value
    )
    users.value = res.items
    total.value = res.total
    if (isAdmin.value) {
      await fetchUserRoles(res.items)
    }
  } catch (error: any) {
    console.error('获取用户列表失败:', error)
    ElMessage.error(error.message || '获取用户列表失败')
  } finally {
    loading.value = false
  }
}

const fetchUserRoles = async (targetUsers: UserInDB[]) => {
  const pairs: Array<[number, RoleName[]]> = await Promise.all(
    targetUsers.map(async (user) => {
      try {
        const res = await adminApi.getUserRoles(user.id)
        return [user.id, [...res.roles]]
      } catch {
        return [user.id, []]
      }
    })
  )
  const nextMap: Record<number, RoleName[]> = {}
  for (const [id, roles] of pairs) {
    nextMap[id] = roles
  }
  roleMap.value = nextMap
}

const handleSizeChange = (val: number) => {
  pageSize.value = val
  currentPage.value = 1
  fetchUsers()
}

const handleCurrentChange = (val: number) => {
  currentPage.value = val
  fetchUsers()
}

const getRoles = (userId: number): RoleName[] => {
  return roleMap.value[userId] || []
}

const getRoleLabel = (role: RoleName): string => {
  if (role === 'tool_owner') return '工具负责人'
  return '工具用户'
}

const skippedPreviewText = computed(() => {
  const items = importResult.value?.skipped_items || []
  if (items.length === 0) return ''
  const lines = items.slice(0, 8).map((item) => {
    const email = item.email ? `（${item.email}）` : ''
    return `第 ${item.row} 行${email}：${item.reason}`
  })
  if (items.length > 8) lines.push(`... 其余 ${items.length - 8} 行请修正后重试`)
  return lines.join('\n')
})

const beforeExcelUpload = async (file: File) => {
  const lower = file.name.toLowerCase()
  if (!(lower.endsWith('.xlsx') || lower.endsWith('.xlsm'))) {
    ElMessage.warning('仅支持 .xlsx / .xlsm 文件')
    return false
  }
  importingUsers.value = true
  try {
    const result = await adminApi.importUsersByExcel(file)
    importResult.value = result
    importResultVisible.value = true
    ElMessage.success(`导入完成：新增 ${result.created_count} 个账号`)
    await fetchUsers()
  } catch (error: any) {
    ElMessage.error(error.message || '批量导入失败')
  } finally {
    importingUsers.value = false
  }
  return false
}

const downloadImportTemplate = async () => {
  downloadingTemplate.value = true
  try {
    const blob = await adminApi.downloadUserImportTemplate()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'user-import-template.xlsx'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    ElMessage.success('模板下载成功')
  } catch (error: any) {
    ElMessage.error(error.message || '模板下载失败')
  } finally {
    downloadingTemplate.value = false
  }
}

const deleteUserAdmin = async (user: UserInDB) => {
  if (user.id === currentUser.value?.id) {
    ElMessage.warning('请使用「个人资料」中的注销账号')
    return
  }
  if (user.is_superuser) {
    ElMessage.warning('超管账号不可通过用户管理注销')
    return
  }
  try {
    await ElMessageBox.confirm(
      `确定注销用户「${user.username}」？该用户的数据将删除且不可恢复。`,
      '注销用户',
      { type: 'warning', confirmButtonText: '确定注销', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  deletingUserId.value = user.id
  try {
    await adminApi.deleteUser(user.id)
    ElMessage.success('用户已注销')
    await fetchUsers()
  } catch (error: any) {
    ElMessage.error(error.message || '操作失败')
  } finally {
    deletingUserId.value = null
  }
}

const approveUser = async (user: UserInDB) => {
  approvingId.value = user.id
  try {
    await adminApi.approveUser(user.id)
    ElMessage.success('已通过审核，用户可登录系统')
    await fetchUsers()
  } catch (error: any) {
    ElMessage.error(error.message || '操作失败')
  } finally {
    approvingId.value = null
  }
}

const resetUserPassword = async (user: UserInDB) => {
  let newPassword = ''
  try {
    const { value } = await ElMessageBox.prompt(
      `请为用户「${user.username}」设置新的临时密码（至少 8 位）。`,
      '重置密码',
      {
        confirmButtonText: '确认重置',
        cancelButtonText: '取消',
        inputType: 'password',
        inputPattern: /^.{8,}$/,
        inputErrorMessage: '密码至少 8 位',
      }
    )
    newPassword = String(value || '')
  } catch {
    return
  }

  resettingUserId.value = user.id
  try {
    await adminApi.resetUserPassword(user.id, { new_password: newPassword })
    ElMessage.success('密码已重置，请线下告知用户新密码，并提醒其登录后尽快修改')
  } catch (error: any) {
    ElMessage.error(error.message || '重置密码失败')
  } finally {
    resettingUserId.value = null
  }
}

const openRoleDialog = (user: UserInDB) => {
  selectedUser.value = user
  const roles = getRoles(user.id)
  roleForm.value = {
    tool_user: roles.includes('tool_user'),
    tool_owner: roles.includes('tool_owner'),
  }
  roleDialogVisible.value = true
}

const saveRoleConfig = async () => {
  if (!selectedUser.value) return
  try {
    savingRoles.value = true
    const userId = selectedUser.value.id
    const currentRoles = new Set(getRoles(userId))
    const desiredRoles: RoleName[] = []
    if (roleForm.value.tool_user) desiredRoles.push('tool_user')
    if (roleForm.value.tool_owner) desiredRoles.push('tool_owner')

    for (const role of desiredRoles) {
      if (!currentRoles.has(role)) {
        await adminApi.assignUserRole(userId, { role_name: role })
      }
    }
    for (const role of Array.from(currentRoles)) {
      if (!desiredRoles.includes(role)) {
        await adminApi.revokeUserRole(userId, role)
      }
    }

    roleMap.value[userId] = desiredRoles
    roleDialogVisible.value = false
    ElMessage.success('角色已更新')
  } catch (error: any) {
    ElMessage.error(error.message || '角色更新失败')
  } finally {
    savingRoles.value = false
  }
}

onMounted(() => {
  if (!isAdmin.value) {
    ElMessage.warning('您没有管理员权限，只能查看用户列表')
  }
  fetchUsers()
})
</script>

<style scoped>
.users-container {
  padding: 20px;
}

.page-header-title {
  font-size: 18px;
  font-weight: bold;
}

.main-card {
  margin-top: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.role-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.empty-role {
  color: #999;
  font-size: 12px;
}

.role-dialog-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.role-dialog-user {
  color: #666;
  font-size: 14px;
}

.pagination-wrapper {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}

.filter-form {
  margin-bottom: 12px;
}

.import-result {
  display: flex;
  flex-direction: column;
}
</style>
