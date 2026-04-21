<template>
  <div class="feedback-admin-page">
    <el-page-header @back="goBack" title="返回">
      <template #content>
        <span class="page-header-title">反馈管理</span>
      </template>
    </el-page-header>

    <el-card class="main-card">
      <el-tabs v-model="activeTab">
        <el-tab-pane label="系统使用与问题" name="system">
          <div v-loading="loadingSystem">
            <el-empty v-if="!loadingSystem && systemList.length === 0" description="暂无反馈" />
            <el-table v-else :data="systemList" stripe>
              <el-table-column prop="created_at" label="时间" width="180">
                <template #default="scope">{{ formatDate(scope.row.created_at) }}</template>
              </el-table-column>
              <el-table-column prop="user.username" label="用户" width="120" />
              <el-table-column prop="title" label="标题" width="160">
                <template #default="scope">{{ scope.row.title || '—' }}</template>
              </el-table-column>
              <el-table-column prop="content" label="内容" min-width="280" show-overflow-tooltip />
            </el-table>
            <div class="table-pagination">
              <el-pagination
                v-model:current-page="systemPage"
                v-model:page-size="systemPageSize"
                :total="systemTotal"
                :page-sizes="[10, 20, 50, 100]"
                layout="total, sizes, prev, pager, next, jumper"
                @current-change="onSystemPageChange"
                @size-change="onSystemPageSizeChange"
              />
            </div>
          </div>
        </el-tab-pane>
        <el-tab-pane label="新增工具建议" name="suggestion">
          <div v-loading="loadingSuggestion">
            <el-empty v-if="!loadingSuggestion && suggestionList.length === 0" description="暂无建议" />
            <el-table v-else :data="suggestionList" stripe>
              <el-table-column prop="created_at" label="时间" width="180">
                <template #default="scope">{{ formatDate(scope.row.created_at) }}</template>
              </el-table-column>
              <el-table-column prop="user.username" label="用户" width="120" />
              <el-table-column prop="title" label="标题" width="160">
                <template #default="scope">{{ scope.row.title || '—' }}</template>
              </el-table-column>
              <el-table-column prop="content" label="内容" min-width="280" show-overflow-tooltip />
            </el-table>
            <div class="table-pagination">
              <el-pagination
                v-model:current-page="suggestionPage"
                v-model:page-size="suggestionPageSize"
                :total="suggestionTotal"
                :page-sizes="[10, 20, 50, 100]"
                layout="total, sizes, prev, pager, next, jumper"
                @current-change="onSuggestionPageChange"
                @size-change="onSuggestionPageSizeChange"
              />
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { adminApi } from '@/api/admin'
import { useAuthStore } from '@/stores/auth'
import { markFeedbackAdminSeen } from '@/utils/feedbackAdminBadge'
import { formatDateTime as formatDate } from '@/utils/datetime'
import { goBackOrFallback } from '@/utils/navigation'
import type { FeedbackWithUser } from '@/api/types'

const authStore = useAuthStore()

const router = useRouter()
const activeTab = ref('system')
const systemList = ref<FeedbackWithUser[]>([])
const suggestionList = ref<FeedbackWithUser[]>([])
const loadingSystem = ref(false)
const loadingSuggestion = ref(false)
const systemTotal = ref(0)
const systemPage = ref(1)
const systemPageSize = ref(20)
const suggestionTotal = ref(0)
const suggestionPage = ref(1)
const suggestionPageSize = ref(20)

const goBack = () => {
  goBackOrFallback(router, '/')
}

const loadSystem = async () => {
  loadingSystem.value = true
  try {
    const response = await adminApi.getGlobalFeedback(
      'system_feedback',
      (systemPage.value - 1) * systemPageSize.value,
      systemPageSize.value
    )
    systemList.value = response.items
    systemTotal.value = response.total
  } catch (e: any) {
    ElMessage.error(e.message || '加载失败')
  } finally {
    loadingSystem.value = false
  }
}

const loadSuggestion = async () => {
  loadingSuggestion.value = true
  try {
    const response = await adminApi.getGlobalFeedback(
      'new_tool_suggestion',
      (suggestionPage.value - 1) * suggestionPageSize.value,
      suggestionPageSize.value
    )
    suggestionList.value = response.items
    suggestionTotal.value = response.total
  } catch (e: any) {
    ElMessage.error(e.message || '加载失败')
  } finally {
    loadingSuggestion.value = false
  }
}

const onSystemPageChange = (page: number) => {
  systemPage.value = page
  void loadSystem()
}

const onSystemPageSizeChange = (size: number) => {
  systemPageSize.value = size
  systemPage.value = 1
  void loadSystem()
}

const onSuggestionPageChange = (page: number) => {
  suggestionPage.value = page
  void loadSuggestion()
}

const onSuggestionPageSizeChange = (size: number) => {
  suggestionPageSize.value = size
  suggestionPage.value = 1
  void loadSuggestion()
}

watch(activeTab, (tab) => {
  if (tab === 'system' && systemList.value.length === 0 && !loadingSystem.value) loadSystem()
  if (tab === 'suggestion' && suggestionList.value.length === 0 && !loadingSuggestion.value)
    loadSuggestion()
})

onMounted(async () => {
  await loadSystem()
  const uid = authStore.userInfo?.id
  if (uid) {
    try {
      const fc = await adminApi.getFeedbackCounts()
      markFeedbackAdminSeen(fc.total, uid)
    } catch {
      /* ignore */
    }
  }
})
</script>

<style scoped>
.feedback-admin-page {
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

.table-pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}
</style>
