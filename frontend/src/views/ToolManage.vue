<template>
  <div class="tool-manage-page">
    <el-page-header @back="goBack" title="返回">
      <template #content>
        <span class="page-header-title">{{ tool?.name ? `${getToolDisplayName(tool.name)} · 管理` : '工具管理' }}</span>
      </template>
    </el-page-header>

    <el-card class="main-card" v-if="accessDenied">
      <el-empty description="您没有权限管理该工具" />
    </el-card>

    <template v-else>
      <el-card class="main-card manage-shell-card">
        <el-tabs v-model="activeTab" class="manage-tabs">
          <el-tab-pane
            v-for="tab in manageExtraTabs"
            :key="tab.name"
            :label="tab.label"
            :name="tab.name"
          >
            <component :is="tab.component" :tool-id="toolId" />
          </el-tab-pane>

          <el-tab-pane label="通用管理" name="general">
            <el-tabs v-model="generalTab" class="general-modules-tabs">
              <el-tab-pane label="工具状态" name="status">
                <el-card class="nested-card" shadow="never">
                <template #header>工具状态</template>
                <p class="section-hint">
                  「暂不可用」时，除管理员外，即使用户已有权限也无法从列表进入使用；变更后会通知已授权用户与工具负责人。
                </p>
                <el-form :inline="true" class="status-form">
                  <el-form-item label="状态">
                    <el-radio-group v-model="statusFormActive" :disabled="savingStatus">
                      <el-radio :label="true">可用</el-radio>
                      <el-radio :label="false">暂不可用</el-radio>
                    </el-radio-group>
                  </el-form-item>
                  <el-form-item>
                    <el-button type="primary" :loading="savingStatus" @click="saveToolStatus">保存</el-button>
                  </el-form-item>
                </el-form>
              </el-card>
              </el-tab-pane>

              <el-tab-pane label="发版管理" name="release">
                <el-card class="nested-card" shadow="never">
                <template #header>版本发版与更新记录</template>
                <p class="section-hint">
                  发版后「发版版本」与可选的「规格修订」会显示在工具列表与详情；规格修订可与需求模板
                  <code>NEW_TOOL_AGENT_TEMPLATE.md</code> 中 §2.3 的版本号对齐。可勾选向已授权用户与负责人推送通知。
                </p>
                <div v-if="tool" class="release-current-line">
                  <span>当前发版：<strong>{{ tool.version }}</strong></span>
                  <span v-if="tool.spec_revision">　规格修订：<strong>{{ tool.spec_revision }}</strong></span>
                </div>
                <el-form label-width="112px" class="release-form">
                  <el-form-item label="新版本号" required>
                    <el-input v-model="releaseForm.version" placeholder="如 1.2.0" clearable style="max-width: 220px" />
                  </el-form-item>
                  <el-form-item label="规格修订">
                    <el-input
                      v-model="releaseForm.spec_revision"
                      placeholder="如 v0.3（可与需求模板修订记录一致）"
                      clearable
                      style="max-width: 320px"
                    />
                  </el-form-item>
                  <el-form-item label="更新标题">
                    <el-input v-model="releaseForm.title" placeholder="默认：版本更新" clearable style="max-width: 400px" />
                  </el-form-item>
                  <el-form-item label="更新说明" required>
                    <el-input
                      v-model="releaseForm.changelog"
                      type="textarea"
                      :rows="5"
                      placeholder="发版内容、接口或行为变更等"
                      style="max-width: 560px"
                    />
                  </el-form-item>
                  <el-form-item label="通知用户">
                    <el-switch v-model="releaseForm.notify_users" active-text="推送通知" inactive-text="仅记录" />
                  </el-form-item>
                  <el-form-item>
                    <el-button type="primary" :loading="publishingRelease" @click="submitRelease">发版</el-button>
                  </el-form-item>
                </el-form>
                <el-table v-loading="loadingReleases" :data="manageReleaseRows" stripe size="small">
                  <el-table-column prop="published_at" label="时间" width="170">
                    <template #default="scope">{{ formatDate(scope.row.published_at) }}</template>
                  </el-table-column>
                  <el-table-column prop="version" label="版本" width="100" />
                  <el-table-column prop="spec_revision" label="规格" width="100">
                    <template #default="scope">{{ scope.row.spec_revision || '—' }}</template>
                  </el-table-column>
                  <el-table-column prop="title" label="标题" width="160" show-overflow-tooltip />
                  <el-table-column prop="changelog" label="说明" min-width="200" show-overflow-tooltip />
                </el-table>
                <div class="table-pagination">
                  <el-pagination
                    v-model:current-page="releasePage"
                    v-model:page-size="releasePageSize"
                    :total="releaseTotal"
                    :page-sizes="[5, 10, 20]"
                    layout="total, sizes, prev, pager, next"
                    @current-change="onReleasePageChange"
                    @size-change="onReleasePageSizeChange"
                  />
                </div>
              </el-card>
              </el-tab-pane>

              <el-tab-pane label="授权用户" name="license">
                <el-card class="nested-card" shadow="never">
                <template #header>已授权用户</template>
                <p class="section-hint">当前已获批使用本工具的用户、开通时间及最近一次功能调用时间。</p>
                <el-form :inline="true" class="license-filter-form" @submit.prevent="applyLicenseSearch">
                  <el-form-item label="筛选">
                    <el-input
                      v-model="licenseSearchInput"
                      placeholder="用户名 / 邮箱 / 姓名"
                      clearable
                      style="width: 260px"
                      @keyup.enter="applyLicenseSearch"
                    />
                  </el-form-item>
                  <el-form-item>
                    <el-button type="primary" :loading="loadingLicense" @click="applyLicenseSearch">查询</el-button>
                    <el-button @click="resetLicenseSearch">重置</el-button>
                  </el-form-item>
                </el-form>
                <el-table :data="licenseRows" v-loading="loadingLicense" stripe>
                  <el-table-column prop="user.username" label="用户名" width="140" />
                  <el-table-column label="姓名" width="120">
                    <template #default="scope">{{ scope.row.user.full_name || '—' }}</template>
                  </el-table-column>
                  <el-table-column label="邮箱" min-width="200">
                    <template #default="scope">{{ scope.row.user.email }}</template>
                  </el-table-column>
                  <el-table-column label="开通时间" width="180">
                    <template #default="scope">{{ formatDate(scope.row.granted_at) }}</template>
                  </el-table-column>
                  <el-table-column label="到期时间" width="180">
                    <template #default="scope">
                      {{ scope.row.expires_at ? formatDate(scope.row.expires_at) : '—' }}
                    </template>
                  </el-table-column>
                  <el-table-column label="最近一次使用" width="180">
                    <template #default="scope">
                      {{ scope.row.last_used_at ? formatDate(scope.row.last_used_at) : '—' }}
                    </template>
                  </el-table-column>
                  <el-table-column label="操作" width="120" fixed="right">
                    <template #default="scope">
                      <el-button
                        type="danger"
                        size="small"
                        link
                        :loading="revokingUserId === scope.row.user.id"
                        @click="confirmRevokeLicense(scope.row)"
                      >
                        取消授权
                      </el-button>
                    </template>
                  </el-table-column>
                </el-table>
                <div class="table-pagination">
                  <el-pagination
                    v-model:current-page="licensePage"
                    v-model:page-size="licensePageSize"
                    :total="licenseTotal"
                    :page-sizes="[10, 20, 50, 100]"
                    layout="total, sizes, prev, pager, next, jumper"
                    @current-change="onLicensePageChange"
                    @size-change="onLicensePageSizeChange"
                  />
                </div>
              </el-card>
              </el-tab-pane>

              <el-tab-pane label="使用记录" name="usage">
                <el-card class="nested-card" shadow="never">
                <template #header>工具使用记录</template>
                <p class="section-hint">
                  展示用户行为（由本工具在「行为目录」中的定义解析），不再以接口路径为主。目录存于工具元数据，插件迭代时请同步更新目录以穷举可记录行为。
                </p>
                <el-form :inline="true" class="usage-filter-form" @submit.prevent="onUsageSearch">
                  <el-form-item label="用户">
                    <el-input
                      v-model="usageLogUsername"
                      placeholder="用户名模糊匹配"
                      clearable
                      style="width: 180px"
                      @keyup.enter="onUsageSearch"
                    />
                  </el-form-item>
                  <el-form-item label="关键词">
                    <el-input
                      v-model="usageLogKeyword"
                      placeholder="行为说明 / 路径片段 / 方法"
                      clearable
                      style="width: 220px"
                      @keyup.enter="onUsageSearch"
                    />
                  </el-form-item>
                  <el-form-item>
                    <el-button type="primary" :loading="loadingLogs" @click="onUsageSearch">查询</el-button>
                    <el-button @click="onUsageReset">重置</el-button>
                  </el-form-item>
                </el-form>
                <el-table :data="usageLogs" v-loading="loadingLogs" stripe>
                  <el-table-column prop="created_at" label="时间" width="180">
                    <template #default="scope">{{ formatDate(scope.row.created_at) }}</template>
                  </el-table-column>
                  <el-table-column prop="username" label="用户" width="120" />
                  <el-table-column label="行为" min-width="220">
                    <template #default="scope">
                      <span>{{ scope.row.behavior_label || '—' }}</span>
                    </template>
                  </el-table-column>
                  <el-table-column prop="status_code" label="状态" width="80" />
                  <el-table-column prop="latency_ms" label="耗时(ms)" width="100" />
                </el-table>
                <div class="table-pagination">
                  <el-pagination
                    v-model:current-page="usagePage"
                    v-model:page-size="usagePageSize"
                    :total="usageLogsTotal"
                    :page-sizes="[10, 20, 50, 100]"
                    layout="total, sizes, prev, pager, next, jumper"
                    @current-change="onUsagePageChange"
                    @size-change="onUsagePageSizeChange"
                  />
                </div>
              </el-card>
              </el-tab-pane>

              <el-tab-pane label="用户反馈" name="feedback">
                <el-card class="nested-card" shadow="never">
                <template #header>用户反馈</template>
                <p class="section-hint">针对本工具的使用体验与问题反馈（用户在工具列表中提交）。</p>
                <el-table :data="toolFeedbackRows" v-loading="loadingFeedback" stripe>
                  <el-table-column prop="created_at" label="时间" width="180">
                    <template #default="scope">{{ formatDate(scope.row.created_at) }}</template>
                  </el-table-column>
                  <el-table-column prop="user.username" label="用户" width="120" />
                  <el-table-column prop="title" label="标题" width="140">
                    <template #default="scope">{{ scope.row.title || '—' }}</template>
                  </el-table-column>
                  <el-table-column prop="content" label="内容" min-width="220" show-overflow-tooltip />
                </el-table>
                <div class="table-pagination">
                  <el-pagination
                    v-model:current-page="feedbackPage"
                    v-model:page-size="feedbackPageSize"
                    :total="feedbackTotal"
                    :page-sizes="[10, 20, 50, 100]"
                    layout="total, sizes, prev, pager, next, jumper"
                    @current-change="onFeedbackPageChange"
                    @size-change="onFeedbackPageSizeChange"
                  />
                </div>
              </el-card>
              </el-tab-pane>

            </el-tabs>
          </el-tab-pane>
        </el-tabs>
      </el-card>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { toolsApi } from '@/api/tools'
import { adminApi } from '@/api/admin'
import { getToolDisplayName } from '@/utils/toolDisplay'
import { formatDateTime as formatDate } from '@/utils/datetime'
import { resolveManageExtraTabs } from '@/tools/registry'
import type {
  ToolInDB,
  ToolReleaseInDB,
  APIAccessLogWithUser,
  ToolLicenseUserRow,
  FeedbackWithUser,
} from '@/api/types'

const route = useRoute()
const router = useRouter()

const toolId = Number(route.params.toolId)
const tool = ref<ToolInDB | null>(null)
const licenseRows = ref<ToolLicenseUserRow[]>([])
const loadingLicense = ref(false)
const licenseTotal = ref(0)
const licensePage = ref(1)
const licensePageSize = ref(20)
const usageLogs = ref<APIAccessLogWithUser[]>([])
const loadingLogs = ref(false)
const usageLogsTotal = ref(0)
const usagePage = ref(1)
const usagePageSize = ref(20)
const usageLogUsername = ref('')
const usageLogKeyword = ref('')
const appliedUsageUsername = ref('')
const appliedUsageQ = ref('')
const accessDenied = ref(false)
const licenseSearchInput = ref('')
const appliedLicenseSearch = ref('')
const statusFormActive = ref(true)
const savingStatus = ref(false)
const revokingUserId = ref<number | null>(null)
const toolFeedbackRows = ref<FeedbackWithUser[]>([])
const loadingFeedback = ref(false)
const feedbackTotal = ref(0)
const feedbackPage = ref(1)
const feedbackPageSize = ref(20)
const activeTab = ref('general')
const generalTab = ref('status')
const GENERAL_TAB_NAMES = ['status', 'release', 'license', 'usage', 'feedback'] as const

const releaseForm = ref({
  version: '',
  spec_revision: '',
  title: '版本更新',
  changelog: '',
  notify_users: true,
})
const manageReleaseRows = ref<ToolReleaseInDB[]>([])
const loadingReleases = ref(false)
const publishingRelease = ref(false)
const releasePage = ref(1)
const releasePageSize = ref(10)
const releaseTotal = ref(0)

const manageExtraTabs = computed(() => resolveManageExtraTabs(tool.value?.name))

const queryFirst = (value: unknown): string | undefined => {
  if (typeof value === 'string') return value
  if (Array.isArray(value) && typeof value[0] === 'string') return value[0]
  return undefined
}

const updateQuery = (patch: Record<string, string | undefined>) => {
  const nextQuery: Record<string, any> = { ...route.query, ...patch }
  Object.keys(nextQuery).forEach((key) => {
    if (nextQuery[key] === undefined) delete nextQuery[key]
  })
  const changed = Object.keys(patch).some((key) => {
    const current = queryFirst(route.query[key])
    const next = nextQuery[key] == null ? undefined : String(nextQuery[key])
    return current !== next
  })
  if (changed) {
    router.replace({ query: nextQuery })
  }
}

let topTabInitialized = false
watch(
  manageExtraTabs,
  (tabs) => {
    const available = ['general', ...tabs.map((tab) => tab.name)]
    if (!topTabInitialized) {
      const queryTopTab = queryFirst(route.query.manageTab)
      activeTab.value = queryTopTab && available.includes(queryTopTab)
        ? queryTopTab
        : (tabs.length > 0 ? tabs[0].name : 'general')
      topTabInitialized = true
      return
    }
    if (!available.includes(activeTab.value)) {
      activeTab.value = tabs.length > 0 ? tabs[0].name : 'general'
    }
  },
  { immediate: true }
)

watch(activeTab, (value) => {
  updateQuery({ manageTab: value })
})

watch(generalTab, (value) => {
  updateQuery({ manageGeneralTab: value })
})

watch(
  () => tool.value?.is_active,
  (v) => {
    if (v !== undefined) statusFormActive.value = v
  }
)

/** 返回进入管理页前的页面（如「我的工具」）；无站内历史时回到全部工具 */
const leaveManagePage = () => {
  const back = (window.history.state as { back?: unknown } | null)?.back
  if (back != null) {
    router.back()
  } else {
    router.push('/tools')
  }
}

const goBack = () => {
  leaveManagePage()
}

const applyLicenseSearch = () => {
  appliedLicenseSearch.value = licenseSearchInput.value.trim()
  licensePage.value = 1
  fetchLicenseUsers()
}

const resetLicenseSearch = () => {
  licenseSearchInput.value = ''
  appliedLicenseSearch.value = ''
  licensePage.value = 1
  fetchLicenseUsers()
}

const onLicensePageChange = (page: number) => {
  licensePage.value = page
  fetchLicenseUsers()
}

const onLicensePageSizeChange = (size: number) => {
  licensePageSize.value = size
  licensePage.value = 1
  fetchLicenseUsers()
}

const confirmRevokeLicense = async (row: ToolLicenseUserRow) => {
  try {
    await ElMessageBox.confirm(
      `确定取消用户「${row.user.username}」对本工具的使用权限？该用户将收到通知。`,
      '取消授权',
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }
    )
  } catch {
    return
  }
  revokingUserId.value = row.user.id
  try {
    await adminApi.revokeToolUserLicense(toolId, row.user.id)
    ElMessage.success('已取消授权')
    await fetchLicenseUsers()
  } catch (error: any) {
    ElMessage.error(error.message || '取消授权失败')
  } finally {
    revokingUserId.value = null
  }
}

const fetchLicenseUsers = async () => {
  loadingLicense.value = true
  try {
    const response = await adminApi.getToolLicenseUsers(
      toolId,
      (licensePage.value - 1) * licensePageSize.value,
      licensePageSize.value,
      {
      search: appliedLicenseSearch.value || undefined,
      }
    )
    licenseRows.value = response.items
    licenseTotal.value = response.total
  } catch (error: any) {
    if (error.status === 403) {
      accessDenied.value = true
      licenseRows.value = []
      licenseTotal.value = 0
      throw error
    }
    ElMessage.error(error.message || '加载授权用户失败')
  } finally {
    loadingLicense.value = false
  }
}

const onUsageSearch = () => {
  appliedUsageUsername.value = usageLogUsername.value.trim()
  appliedUsageQ.value = usageLogKeyword.value.trim()
  usagePage.value = 1
  fetchUsageLogs()
}

const onUsageReset = () => {
  usageLogUsername.value = ''
  usageLogKeyword.value = ''
  appliedUsageUsername.value = ''
  appliedUsageQ.value = ''
  usagePage.value = 1
  fetchUsageLogs()
}

const onUsagePageChange = (page: number) => {
  usagePage.value = page
  fetchUsageLogs()
}

const onUsagePageSizeChange = (size: number) => {
  usagePageSize.value = size
  usagePage.value = 1
  fetchUsageLogs()
}

const fetchManageReleases = async () => {
  if (accessDenied.value) return
  loadingReleases.value = true
  try {
    const res = await toolsApi.getToolReleases(
      toolId,
      (releasePage.value - 1) * releasePageSize.value,
      releasePageSize.value
    )
    manageReleaseRows.value = res.items
    releaseTotal.value = res.total
  } catch (error: any) {
    if (error.status === 403) {
      accessDenied.value = true
      manageReleaseRows.value = []
      releaseTotal.value = 0
      return
    }
    ElMessage.error(error.message || '加载发版记录失败')
  } finally {
    loadingReleases.value = false
  }
}

const onReleasePageChange = (page: number) => {
  releasePage.value = page
  void fetchManageReleases()
}

const onReleasePageSizeChange = (size: number) => {
  releasePageSize.value = size
  releasePage.value = 1
  void fetchManageReleases()
}

const submitRelease = async () => {
  const v = releaseForm.value.version.trim()
  const log = releaseForm.value.changelog.trim()
  if (!v || !log) {
    ElMessage.warning('请填写新版本号与更新说明')
    return
  }
  publishingRelease.value = true
  try {
    await adminApi.publishToolRelease(toolId, {
      version: v,
      spec_revision: releaseForm.value.spec_revision.trim() || undefined,
      title: releaseForm.value.title.trim() || '版本更新',
      changelog: log,
      notify_users: releaseForm.value.notify_users,
    })
    tool.value = await toolsApi.getTool(toolId)
    releaseForm.value.changelog = ''
    releaseForm.value.version = ''
    releaseForm.value.spec_revision = ''
    ElMessage.success('发版成功')
    releasePage.value = 1
    await fetchManageReleases()
  } catch (error: any) {
    ElMessage.error(error.message || '发版失败')
  } finally {
    publishingRelease.value = false
  }
}

const saveToolStatus = async () => {
  if (!tool.value) return
  if (statusFormActive.value === tool.value.is_active) {
    ElMessage.info('状态未变更')
    return
  }
  savingStatus.value = true
  try {
    tool.value = await adminApi.updateToolStatus(toolId, statusFormActive.value)
    ElMessage.success('工具状态已更新，相关用户将收到通知')
  } catch (error: any) {
    ElMessage.error(error.message || '更新工具状态失败')
  } finally {
    savingStatus.value = false
  }
}

const fetchUsageLogs = async () => {
  if (accessDenied.value) return
  loadingLogs.value = true
  try {
    const response = await adminApi.getToolUsageLogs(
      toolId,
      (usagePage.value - 1) * usagePageSize.value,
      usagePageSize.value,
      {
      username: appliedUsageUsername.value || undefined,
      q: appliedUsageQ.value || undefined,
      }
    )
    usageLogs.value = response.items
    usageLogsTotal.value = response.total
  } catch (error: any) {
    if (error.status === 403) {
      accessDenied.value = true
      usageLogs.value = []
      usageLogsTotal.value = 0
      return
    }
    ElMessage.error(error.message || '加载工具使用记录失败')
  } finally {
    loadingLogs.value = false
  }
}

const fetchToolFeedback = async () => {
  if (accessDenied.value) return
  loadingFeedback.value = true
  try {
    const response = await adminApi.getToolFeedback(
      toolId,
      (feedbackPage.value - 1) * feedbackPageSize.value,
      feedbackPageSize.value
    )
    toolFeedbackRows.value = response.items
    feedbackTotal.value = response.total
  } catch (error: any) {
    if (error.status === 403) {
      accessDenied.value = true
      toolFeedbackRows.value = []
      feedbackTotal.value = 0
      return
    }
    ElMessage.error(error.message || '加载用户反馈失败')
  } finally {
    loadingFeedback.value = false
  }
}

const onFeedbackPageChange = (page: number) => {
  feedbackPage.value = page
  fetchToolFeedback()
}

const onFeedbackPageSizeChange = (size: number) => {
  feedbackPageSize.value = size
  feedbackPage.value = 1
  fetchToolFeedback()
}

onMounted(async () => {
  const queryGeneralTab = queryFirst(route.query.manageGeneralTab)
  generalTab.value = queryGeneralTab && GENERAL_TAB_NAMES.includes(queryGeneralTab as typeof GENERAL_TAB_NAMES[number])
    ? queryGeneralTab
    : 'status'
  try {
    tool.value = await toolsApi.getTool(toolId)
    if (tool.value) statusFormActive.value = tool.value.is_active
    accessDenied.value = false
    await fetchLicenseUsers()
    if (!accessDenied.value) {
      await fetchManageReleases()
      await fetchUsageLogs()
      await fetchToolFeedback()
    }
  } catch (error: any) {
    if (error.status === 403) {
      accessDenied.value = true
      return
    }
    if (accessDenied.value) return
    ElMessage.error(error.message || '加载工具失败')
    leaveManagePage()
  }
})
</script>

<style scoped>
.tool-manage-page {
  padding: 20px;
}

.page-header-title {
  font-size: 18px;
  font-weight: bold;
  color: #303133;
}

.main-card {
  margin-top: 20px;
}

.manage-shell-card :deep(.el-card__body) {
  padding-top: 8px;
}

.manage-tabs {
  width: 100%;
}

.general-modules-tabs {
  width: 100%;
}

.nested-card {
  border: 1px solid #ebeef5;
  margin-top: 4px;
}

.section-hint {
  color: #909399;
  font-size: 13px;
  margin: 0 0 12px;
}

.status-form {
  margin-bottom: 0;
}

.license-filter-form {
  margin-bottom: 12px;
}

.usage-filter-form {
  margin-bottom: 12px;
}

.table-pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}

.release-current-line {
  margin-bottom: 12px;
  font-size: 13px;
  color: #606266;
}

.release-form {
  margin-bottom: 16px;
  max-width: 640px;
}

</style>
