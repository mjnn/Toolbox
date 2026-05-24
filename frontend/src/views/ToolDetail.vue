<template>
  <div class="tool-detail-container">
    <el-page-header @back="goBack" title="返回">
      <template #content>
        <span class="page-header-title">{{ tool ? resolveToolDisplayName(tool.name, tool.display_name) : '工具详情' }}</span>
      </template>
    </el-page-header>

    <el-tabs v-if="tool" v-model="detailMainTab" class="tool-detail-main-tabs">
      <el-tab-pane label="使用工具" name="use">
        <el-alert
          v-if="!isToolBusinessAvailable(tool, isSuperuser)"
          :type="!tool.is_active ? 'warning' : 'info'"
          :closable="false"
          show-icon
          :title="toolAvailabilityAlertTitle"
          class="inactive-alert"
        />
        <template v-if="canOpenToolFeatures">
          <el-card v-if="detailPanel" class="feature-tabs-card" shadow="never">
            <component :is="detailPanel" :tool-id="toolId" />
          </el-card>
          <el-card v-else class="feature-tabs-card" shadow="never">
            <el-empty description="该工具暂无可视化功能页，请联系管理员。" />
          </el-card>
        </template>
      </el-tab-pane>

      <el-tab-pane label="工具说明" name="summary">
        <el-card class="tool-summary-card" shadow="never">
          <div class="tool-summary">
            <div class="tool-name">{{ resolveToolDisplayName(tool.name, tool.display_name) }}</div>
            <div class="tool-desc">{{ resolveToolDisplayDescription(tool.description, tool.display_description) }}</div>
            <div class="tool-meta">
              <span>发版版本 {{ tool.version }}</span>
              <span v-if="tool.spec_revision" class="spec-rev">规格修订 {{ tool.spec_revision }}</span>
              <el-tag :type="getToolStatusTagType(tool)" size="small" style="margin-left: 8px">
                {{ getToolStatusLabel(tool) }}
              </el-tag>
            </div>
          </div>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="更新记录" name="releases">
        <el-card v-if="releasesTotal > 0" class="releases-card" shadow="never">
          <template #header>更新记录</template>
          <el-timeline>
            <el-timeline-item
              v-for="r in releaseItems"
              :key="r.id"
              :timestamp="formatDate(r.published_at)"
              placement="top"
            >
              <div class="release-item-title">
                <strong>{{ r.title }}</strong>
                <el-tag size="small" type="info" effect="plain">v{{ r.version }}</el-tag>
                <el-tag v-if="r.spec_revision" size="small" effect="plain">规格 {{ r.spec_revision }}</el-tag>
              </div>
              <pre class="release-changelog">{{ r.changelog }}</pre>
            </el-timeline-item>
          </el-timeline>
          <div v-if="releasesTotal > releaseLimit" class="release-more">
            <el-button type="primary" link aria-label="加载更多更新记录" @click="loadMoreReleases">加载更多</el-button>
          </div>
        </el-card>
        <el-card v-else class="releases-card" shadow="never">
          <template #header>更新记录</template>
          <el-empty description="暂无发布记录" />
        </el-card>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { toolsApi } from '@/api/tools'
import { useAuthStore } from '@/stores/auth'
import {
  getToolStatusLabel,
  getToolStatusTagType,
  isToolBusinessAvailable,
  resolveToolDisplayDescription,
  resolveToolDisplayName,
} from '@/utils/toolDisplay'
import { formatDateTime as formatDate } from '@/utils/datetime'
import { resolveToolDetailPanel } from '@/tools/registry'
import { goBackOrFallback } from '@/utils/navigation'
import type { ToolInDB, ToolReleaseInDB } from '@/api/types'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const tool = ref<ToolInDB | null>(null)
/** 默认进入「使用工具」，与列表「开始使用」首屏一致；可用路由 ?tab=summary|releases|use 覆盖 */
const detailMainTab = ref('use')
const toolId = Number(route.params.toolId)
const releaseItems = ref<ToolReleaseInDB[]>([])
const releasesTotal = ref(0)
const releaseLimit = ref(15)

const isSuperuser = computed(() => !!authStore.userInfo?.is_superuser)
const canOpenToolFeatures = computed(() =>
  tool.value ? isToolBusinessAvailable(tool.value, isSuperuser.value) : false
)
const toolAvailabilityAlertTitle = computed(() => {
  if (!tool.value) return ''
  if (!tool.value.is_active) {
    return '该工具当前为「暂不可用」，功能已暂停。仅系统超级管理员可调试。'
  }
  if (tool.value.runtime_status === 'updating') {
    return '该工具正在更新中，功能已暂时关闭（含工具负责人与平台管理员），请稍后再试。'
  }
  return ''
})
const detailPanel = computed(() => resolveToolDetailPanel(tool.value?.name))

const goBack = () => {
  goBackOrFallback(router, '/tools')
}

const fetchTool = async () => {
  tool.value = await toolsApi.getTool(toolId)
}

const fetchReleases = async (append = false) => {
  try {
    const skip = append ? releaseItems.value.length : 0
    const res = await toolsApi.getToolReleases(toolId, skip, releaseLimit.value)
    releasesTotal.value = res.total
    if (append) {
      releaseItems.value = [...releaseItems.value, ...res.items]
    } else {
      releaseItems.value = res.items
    }
  } catch {
    releaseItems.value = []
    releasesTotal.value = 0
  }
}

const loadMoreReleases = async () => {
  await fetchReleases(true)
}

const applyTabFromRouteQuery = () => {
  const q = route.query.tab
  if (typeof q !== 'string') return
  if (q === 'use' || q === 'summary' || q === 'releases') {
    detailMainTab.value = q
  }
}

onMounted(async () => {
  try {
    await fetchTool()
    await fetchReleases(false)
    applyTabFromRouteQuery()
  } catch (error: any) {
    ElMessage.error(error.message || '加载工具失败')
    router.push('/tools')
  }
})
</script>

<style scoped>
.tool-detail-container {
  padding: 20px;
}

.page-header-title {
  font-size: 18px;
  font-weight: bold;
  color: #303133;
}

.tool-detail-main-tabs {
  margin-top: 20px;
}

.tool-summary-card {
  margin-top: 0;
}

.tool-summary {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.tool-name {
  font-size: 18px;
  font-weight: bold;
}

.tool-desc {
  color: #666;
}

.tool-meta {
  color: #606266;
  font-size: 12px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
}

.spec-rev {
  color: #606266;
}

.releases-card {
  margin-top: 0;
}

.release-item-title {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.release-changelog {
  margin: 0;
  white-space: pre-wrap;
  font-family: inherit;
  font-size: 13px;
  line-height: 1.5;
  color: #606266;
}

.release-more {
  margin-top: 8px;
}

.inactive-alert {
  margin-bottom: 12px;
}

.feature-tabs-card {
  margin-top: 0;
}

@media (max-width: 768px) {
  .tool-detail-container {
    padding: 12px;
  }

  .page-header-title,
  .tool-name {
    font-size: 16px;
  }

  .tool-detail-main-tabs {
    margin-top: 12px;
  }
}
</style>
