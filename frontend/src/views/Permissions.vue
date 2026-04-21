<template>
  <div class="permissions-container">
    <el-page-header @back="goBack" title="返回">
      <template #content>
        <span class="page-header-title">权限管理</span>
      </template>
    </el-page-header>
    
    <el-tabs v-model="activeTab" class="permissions-tabs">
      <el-tab-pane label="我的权限" name="my">
        <el-card class="tab-content">
          <template #header>
            <div class="card-header">
              <span>我的权限申请</span>
            </div>
          </template>

          <el-form :inline="true" class="filter-form">
            <el-form-item label="状态">
              <el-select v-model="myStatusFilter" placeholder="全部" clearable style="width: 140px">
                <el-option label="待审核" value="pending" />
                <el-option label="已批准" value="approved" />
                <el-option label="已拒绝" value="rejected" />
              </el-select>
            </el-form-item>
            <el-form-item label="搜索">
              <el-input
                v-model="mySearch"
                placeholder="工具名、理由、审核意见"
                clearable
                style="width: 260px"
              />
            </el-form-item>
          </el-form>
          
          <div v-if="filteredMyPermissions.length === 0" class="empty-state">
            <el-empty :description="myPermissions.length === 0 ? '暂无权限申请记录' : '无匹配记录'" />
          </div>
          
          <div v-else class="permissions-list">
            <div v-for="perm in filteredMyPermissions" :key="perm.id" class="permission-item">
              <div class="permission-header">
                <span class="tool-name">{{ perm.tool?.name || '未知工具' }}</span>
                <el-tag :type="getStatusTagType(perm.status)" size="small">
                  {{ getStatusText(perm.status) }}
                </el-tag>
              </div>
              <div class="permission-reason">
                {{ perm.applied_reason }}
              </div>
              <div class="permission-meta">
                <span>申请时间: {{ formatDate(perm.applied_at) }}</span>
                <span v-if="perm.reviewed_at">
                  审核时间: {{ formatDate(perm.reviewed_at) }}
                </span>
                <span v-if="perm.review_notes">
                  审核意见: {{ perm.review_notes }}
                </span>
              </div>
            </div>
          </div>
        </el-card>
      </el-tab-pane>
      
      <el-tab-pane label="待审批权限" name="pending" v-if="canReview">
        <el-card class="tab-content">
          <template #header>
            <div class="card-header">
              <span>待审核权限申请</span>
            </div>
          </template>

          <el-form :inline="true" class="filter-form">
            <el-form-item label="搜索">
              <el-input
                v-model="pendingSearch"
                placeholder="工具名、申请人、申请理由"
                clearable
                style="width: 280px"
              />
            </el-form-item>
          </el-form>
          
          <div v-if="filteredPendingPermissions.length === 0" class="empty-state">
            <el-empty :description="pendingPermissions.length === 0 ? '暂无待审核的权限申请' : '无匹配记录'" />
          </div>
          
          <div v-else class="permissions-list">
            <div v-for="perm in filteredPendingPermissions" :key="perm.id" class="permission-item">
              <div class="permission-header">
                <span class="tool-name">{{ perm.tool?.name || '未知工具' }}</span>
                <span class="applicant">申请人: {{ perm.user?.username || '未知用户' }}</span>
              </div>
              <div class="permission-reason">
                {{ perm.applied_reason }}
              </div>
              <div class="permission-actions">
                <el-button type="success" size="small" @click="handleApprove(perm)">
                  批准
                </el-button>
                <el-button type="danger" size="small" @click="handleReject(perm)">
                  拒绝
                </el-button>
              </div>
            </div>
          </div>
        </el-card>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { permissionsApi } from '@/api/permissions'
import { formatDateTime as formatDate } from '@/utils/datetime'
import { goBackOrFallback } from '@/utils/navigation'
import type { PermissionWithDetails } from '@/api/types'

const router = useRouter()
const activeTab = ref('my')
const myPermissions = ref<PermissionWithDetails[]>([])
const pendingPermissions = ref<PermissionWithDetails[]>([])
const canReview = ref(false)
const mySearch = ref('')
const myStatusFilter = ref<string | ''>('')
const pendingSearch = ref('')

const filteredMyPermissions = computed(() => {
  let list = myPermissions.value
  if (myStatusFilter.value) {
    list = list.filter((p) => p.status === myStatusFilter.value)
  }
  const q = mySearch.value.trim().toLowerCase()
  if (!q) return list
  return list.filter((p) => {
    const tool = (p.tool?.name || '').toLowerCase()
    const reason = (p.applied_reason || '').toLowerCase()
    const notes = (p.review_notes || '').toLowerCase()
    return tool.includes(q) || reason.includes(q) || notes.includes(q)
  })
})

const filteredPendingPermissions = computed(() => {
  const q = pendingSearch.value.trim().toLowerCase()
  if (!q) return pendingPermissions.value
  return pendingPermissions.value.filter((p) => {
    const tool = (p.tool?.name || '').toLowerCase()
    const user = (p.user?.username || '').toLowerCase()
    const reason = (p.applied_reason || '').toLowerCase()
    return tool.includes(q) || user.includes(q) || reason.includes(q)
  })
})

const goBack = () => {
  goBackOrFallback(router, '/')
}

const getStatusTagType = (status: string) => {
  switch (status) {
    case 'approved': return 'success'
    case 'rejected': return 'danger'
    case 'pending': return 'warning'
    default: return 'info'
  }
}

const getStatusText = (status: string) => {
  switch (status) {
    case 'approved': return '已批准'
    case 'rejected': return '已拒绝'
    case 'pending': return '待审核'
    default: return status
  }
}

const fetchMyPermissions = async () => {
  try {
    const data = await permissionsApi.getMyPermissions()
    myPermissions.value = data
  } catch (error: any) {
    console.error('获取我的权限失败:', error)
    ElMessage.error(error.message || '获取我的权限失败')
  }
}

const fetchPendingPermissions = async () => {
  try {
    const data = await permissionsApi.getPendingPermissions()
    pendingPermissions.value = data
    canReview.value = true
  } catch (error: any) {
    if (error.status === 403) {
      canReview.value = false
      return
    }
    console.error('获取待审核权限失败:', error)
    ElMessage.error(error.message || '获取待审核权限失败')
  }
}

const handleApprove = async (perm: PermissionWithDetails) => {
  try {
    await ElMessageBox.confirm(
      `确定要批准 ${perm.user?.username || '用户'} 对 ${perm.tool?.name || '工具'} 的权限申请吗？`,
      '确认批准',
      {
        confirmButtonText: '批准',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    const data = { review_notes: '已批准', expires_at: null }
    await permissionsApi.approvePermission(perm.id, data)
    ElMessage.success('权限申请已批准')
    
    // 刷新数据
    fetchPendingPermissions()
    fetchMyPermissions()
  } catch {
    // 用户取消
  }
}

const handleReject = async (perm: PermissionWithDetails) => {
  try {
    const { value: reason } = await ElMessageBox.prompt(
      '请输入拒绝理由',
      '确认拒绝',
      {
        confirmButtonText: '拒绝',
        cancelButtonText: '取消',
        inputType: 'textarea',
        inputPlaceholder: '请输入拒绝理由...'
      }
    )
    
    if (reason) {
      const data = { review_notes: reason, expires_at: null }
      await permissionsApi.rejectPermission(perm.id, data)
      ElMessage.success('权限申请已拒绝')
      
      // 刷新数据
      fetchPendingPermissions()
      fetchMyPermissions()
    }
  } catch {
    // 用户取消
  }
}

onMounted(() => {
  fetchMyPermissions()
  fetchPendingPermissions()
})
</script>

<style scoped>
.permissions-container {
  padding: 20px;
}

.page-header-title {
  font-size: 18px;
  font-weight: bold;
}

.permissions-tabs {
  margin-top: 20px;
}

.tab-content {
  margin-top: 10px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.filter-form {
  margin-bottom: 8px;
}

.empty-state {
  padding: 40px 0;
}

.permissions-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.permission-item {
  padding: 16px;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  background-color: #fff;
}

.permission-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.tool-name {
  font-weight: bold;
  font-size: 16px;
}

.applicant {
  color: #666;
  font-size: 14px;
}

.permission-reason {
  margin-bottom: 12px;
  color: #333;
  line-height: 1.5;
}

.permission-meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
  color: #999;
}

.permission-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}
</style>
