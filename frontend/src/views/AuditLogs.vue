<template>
  <div class="audit-container">
    <el-page-header @back="goBack" title="返回">
      <template #content>
        <span class="page-header-title">全量行为日志</span>
      </template>
    </el-page-header>

    <el-card class="main-card">
      <template #header>
        <div class="card-header">
          <span>管理员审计日志</span>
          <div class="header-actions">
            <el-button
              v-if="isSuperuser"
              type="danger"
              size="small"
              plain
              @click="confirmClearLogs"
              :loading="clearing"
            >
              清空全部日志
            </el-button>
            <el-button size="small" @click="exportCsv" :loading="exporting">导出 CSV</el-button>
            <el-button size="small" @click="fetchLogs" :loading="loading">刷新</el-button>
          </div>
        </div>
      </template>

      <el-form :inline="true" class="filter-form" @submit.prevent="onSearch">
        <el-form-item label="用户名">
          <el-input
            v-model="filterUsername"
            placeholder="模糊匹配"
            clearable
            style="width: 200px"
            @keyup.enter="onSearch"
          />
        </el-form-item>
        <el-form-item label="工具">
          <el-select
            v-model="filterToolId"
            placeholder="全部工具"
            clearable
            filterable
            style="width: 220px"
          >
            <el-option
              v-for="t in tools"
              :key="t.id"
              :label="t.name"
              :value="t.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="关键词">
          <el-input
            v-model="filterKeyword"
            placeholder="路径 / 功能 / 方法"
            clearable
            style="width: 220px"
            @keyup.enter="onSearch"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="onSearch">查询</el-button>
          <el-button @click="onReset">重置</el-button>
        </el-form-item>
      </el-form>

      <div v-if="!isMobile" class="table-scroll">
        <el-table :data="logs" v-loading="loading" stripe>
          <el-table-column prop="created_at" label="时间" width="180">
            <template #default="scope">{{ formatDate(scope.row.created_at) }}</template>
          </el-table-column>
          <el-table-column prop="username" label="用户" width="140" />
          <el-table-column label="工具" width="160">
            <template #default="scope">{{ toolName(scope.row.tool_id) }}</template>
          </el-table-column>
          <el-table-column label="行为" min-width="200">
            <template #default="scope">{{ scope.row.behavior_label || scope.row.feature_name || '—' }}</template>
          </el-table-column>
          <el-table-column prop="method" label="方法" width="90" />
          <el-table-column prop="path" label="接口路径" min-width="200" show-overflow-tooltip />
          <el-table-column prop="status_code" label="状态" width="90" />
          <el-table-column prop="latency_ms" label="耗时(ms)" width="100" />
        </el-table>
      </div>
      <div v-else class="mobile-log-list" v-loading="loading">
        <el-empty v-if="logs.length === 0" description="暂无日志数据" />
        <el-card v-for="log in logs" :key="log.id" class="mobile-log-card" shadow="never">
          <div class="mobile-log-top">
            <span>{{ log.username || '未知用户' }}</span>
            <el-tag size="small" :type="(log.status_code || 0) >= 400 ? 'danger' : 'success'">
              {{ log.status_code ?? '—' }}
            </el-tag>
          </div>
          <div class="mobile-log-meta">时间：{{ formatDate(log.created_at) }}</div>
          <div class="mobile-log-meta">工具：{{ toolName(log.tool_id) }}</div>
          <div class="mobile-log-meta">行为：{{ log.behavior_label || log.feature_name || '—' }}</div>
          <div class="mobile-log-meta">方法：{{ log.method || '—' }} / 耗时：{{ log.latency_ms ?? '—' }}ms</div>
          <div class="mobile-log-path">路径：{{ log.path || '—' }}</div>
        </el-card>
      </div>

      <div class="pager-wrap">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next"
          background
          @current-change="fetchLogs"
          @size-change="onPageSizeChange"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onBeforeUnmount, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { adminApi } from '@/api/admin'
import { useAuthStore } from '@/stores/auth'
import { toolsApi } from '@/api/tools'
import { formatDateTime as formatDate } from '@/utils/datetime'
import { goBackOrFallback } from '@/utils/navigation'
import type { APIAccessLogWithUser, ToolInDB } from '@/api/types'

const router = useRouter()
const authStore = useAuthStore()
const logs = ref<APIAccessLogWithUser[]>([])
const total = ref(0)
const loading = ref(false)
const exporting = ref(false)
const clearing = ref(false)
const tools = ref<ToolInDB[]>([])

const filterUsername = ref('')
const filterToolId = ref<number | undefined>(undefined)
const filterKeyword = ref('')
const page = ref(1)
const pageSize = ref(20)
const isMobile = ref(false)

const isSuperuser = computed(() => !!authStore.userInfo?.is_superuser)

const appliedUsername = ref('')
const appliedToolId = ref<number | undefined>(undefined)
const appliedKeyword = ref('')

const toolMap = computed(() => {
  const m = new Map<number, string>()
  for (const t of tools.value) m.set(t.id, t.name)
  return m
})

const goBack = () => {
  goBackOrFallback(router, '/')
}

const updateViewportState = () => {
  isMobile.value = window.innerWidth <= 768
}

const toolName = (toolId: number | null | undefined) => {
  if (toolId == null) return '—'
  return toolMap.value.get(toolId) ?? `#${toolId}`
}

const fetchLogs = async () => {
  loading.value = true
  try {
    const skip = (page.value - 1) * pageSize.value
    const res = await adminApi.getAuditLogs({
      skip,
      limit: pageSize.value,
      username: appliedUsername.value || undefined,
      tool_id: appliedToolId.value ?? undefined,
      q: appliedKeyword.value || undefined,
    })
    logs.value = res.items
    total.value = res.total
  } catch (error: any) {
    ElMessage.error(error.message || '加载审计日志失败')
  } finally {
    loading.value = false
  }
}

const loadTools = async () => {
  try {
    tools.value = await toolsApi.getTools(0, 200)
  } catch {
    /* 工具列表失败时仍可看日志 */
  }
}

const onSearch = () => {
  appliedUsername.value = filterUsername.value
  appliedToolId.value = filterToolId.value
  appliedKeyword.value = filterKeyword.value.trim()
  page.value = 1
  fetchLogs()
}

const onReset = () => {
  filterUsername.value = ''
  filterToolId.value = undefined
  filterKeyword.value = ''
  appliedUsername.value = ''
  appliedToolId.value = undefined
  appliedKeyword.value = ''
  page.value = 1
  fetchLogs()
}

const onPageSizeChange = () => {
  page.value = 1
  fetchLogs()
}

const confirmClearLogs = async () => {
  try {
    await ElMessageBox.confirm(
      '将删除数据库中全部行为日志记录，且不可恢复。是否继续？',
      '清空行为日志',
      { type: 'warning', confirmButtonText: '确认清空', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  clearing.value = true
  try {
    const res = await adminApi.clearAuditLogs()
    ElMessage.success(res.message || '已清空')
    page.value = 1
    await fetchLogs()
  } catch (error: any) {
    ElMessage.error(error.message || '清空失败')
  } finally {
    clearing.value = false
  }
}

const exportCsv = async () => {
  exporting.value = true
  try {
    const blob = await adminApi.exportAuditLogsCsv({
      username: appliedUsername.value || undefined,
      tool_id: appliedToolId.value ?? undefined,
      q: appliedKeyword.value || undefined,
    })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'audit-logs.csv'
    a.click()
    URL.revokeObjectURL(url)
    ElMessage.success('已开始下载')
  } catch (error: any) {
    ElMessage.error(error.message || '导出失败')
  } finally {
    exporting.value = false
  }
}

onMounted(async () => {
  updateViewportState()
  window.addEventListener('resize', updateViewportState)
  await loadTools()
  fetchLogs()
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', updateViewportState)
})
</script>

<style scoped>
.audit-container {
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
  gap: 8px;
}

.filter-form {
  margin-bottom: 12px;
}

.pager-wrap {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

.table-scroll {
  width: 100%;
  overflow-x: auto;
}

.mobile-log-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.mobile-log-card {
  border: 1px solid #ebeef5;
}

.mobile-log-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
}

.mobile-log-meta {
  margin-top: 6px;
  color: #606266;
  font-size: 13px;
}

.mobile-log-path {
  margin-top: 8px;
  color: #303133;
  font-size: 13px;
  word-break: break-all;
}

@media (max-width: 768px) {
  .audit-container {
    padding: 12px;
  }

  .card-header,
  .header-actions {
    flex-wrap: wrap;
  }

  .page-header-title {
    font-size: 16px;
  }

  .main-card {
    margin-top: 12px;
  }

  .pager-wrap {
    justify-content: flex-start;
    margin-top: 12px;
  }
}
</style>
