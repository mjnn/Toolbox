<template>
  <div class="tool-detail-container">
    <el-page-header @back="goBack" title="返回">
      <template #content>
        <span class="page-header-title">{{ tool ? resolveToolDisplayName(tool.name, tool.display_name) : '工具详情' }}</span>
      </template>
    </el-page-header>

    <el-card class="tool-summary-card" v-if="tool">
      <div class="tool-summary">
        <div class="tool-name">{{ resolveToolDisplayName(tool.name, tool.display_name) }}</div>
        <div class="tool-desc">{{ resolveToolDisplayDescription(tool.description, tool.display_description) }}</div>
        <div class="tool-meta">
          <span>发版版本 {{ tool.version }}</span>
          <span v-if="tool.spec_revision" class="spec-rev">规格修订 {{ tool.spec_revision }}</span>
          <el-tag :type="tool.is_active ? 'success' : 'warning'" size="small" style="margin-left: 8px">
            {{ tool.is_active ? '可用' : '暂不可用' }}
          </el-tag>
        </div>
      </div>
    </el-card>

    <el-card v-if="tool && releasesTotal > 0" class="releases-card" shadow="never">
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
        <el-button type="primary" link @click="loadMoreReleases">加载更多</el-button>
      </div>
    </el-card>

    <el-alert
      v-if="tool && !tool.is_active && !isAdmin"
      type="warning"
      :closable="false"
      show-icon
      title="该工具当前为「暂不可用」，功能已暂停。管理员仍可调试。"
      class="inactive-alert"
    />

    <el-card v-if="tool && detailPanel" class="feature-tabs-card">
      <component :is="detailPanel" :tool-id="toolId" />
    </el-card>

    <el-card v-else-if="tool" class="feature-tabs-card">
      <el-empty description="该工具暂无可视化功能页，请联系管理员。" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { toolsApi } from '@/api/tools'
import { useAuthStore } from '@/stores/auth'
import { resolveToolDisplayDescription, resolveToolDisplayName } from '@/utils/toolDisplay'
import { formatDateTime as formatDate } from '@/utils/datetime'
import { resolveToolDetailPanel } from '@/tools/registry'
import { goBackOrFallback } from '@/utils/navigation'
import type { ToolInDB, ToolReleaseInDB } from '@/api/types'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const tool = ref<ToolInDB | null>(null)
const toolId = Number(route.params.toolId)
const releaseItems = ref<ToolReleaseInDB[]>([])
const releasesTotal = ref(0)
const releaseLimit = ref(15)

const isAdmin = computed(() => !!authStore.userInfo?.is_superuser)
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

onMounted(async () => {
  try {
    await fetchTool()
    await fetchReleases(false)
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

.tool-summary-card {
  margin-top: 20px;
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
  color: #999;
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
  margin-top: 16px;
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
  margin-top: 16px;
}

.feature-tabs-card {
  margin-top: 16px;
}
</style>
