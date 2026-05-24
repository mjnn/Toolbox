<template>
  <el-card class="result-card" role="status" aria-live="polite" shadow="never">
    <template #header>
      <div class="result-header">
        <span>响应结果</span>
        <div class="result-actions">
          <el-button text :disabled="!hasData" @click="onCopy">复制</el-button>
          <el-button text :disabled="!hasData" @click="onDownload">下载JSON</el-button>
          <el-button text :disabled="!hasData" @click="onClear">清空</el-button>
        </div>
      </div>
    </template>
    <div v-if="!hasData" class="result-empty">
      <p v-if="envelopeMessage" class="result-message">{{ envelopeMessage }}</p>
      <p v-else>暂无结果</p>
    </div>
    <json-nested-tabs-viewer v-else :data="dataOnly" />
  </el-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { ElMessage } from 'element-plus'
import JsonNestedTabsViewer from '@/components/tool-detail/JsonNestedTabsViewer.vue'

const props = defineProps<{ payload?: unknown; downloadName?: string }>()
const emit = defineEmits<{ (e: 'clear'): void }>()

const envelope = computed(() => (props.payload || null) as Record<string, unknown> | null)

const dataOnly = computed(() => envelope.value?.data)

const hasData = computed(() => dataOnly.value !== null && dataOnly.value !== undefined)

const envelopeMessage = computed(() => {
  const p = envelope.value
  if (!p) return ''
  const msg = typeof p.message === 'string' ? p.message.trim() : ''
  if (!msg) return ''
  const ok = p.success === true ? '成功' : p.success === false ? '失败' : ''
  return ok ? `【${ok}】${msg}` : msg
})

const onCopy = async () => {
  const text = JSON.stringify(dataOnly.value ?? null, null, 2)
  if (!text.trim()) {
    ElMessage.warning('暂无可复制内容')
    return
  }
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('结果已复制')
  } catch {
    ElMessage.error('复制失败，请检查浏览器权限')
  }
}

const onDownload = () => {
  const text = JSON.stringify(dataOnly.value ?? null, null, 2)
  if (!text.trim()) {
    ElMessage.warning('暂无可下载内容')
    return
  }
  const blob = new Blob([text], { type: 'application/json;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${props.downloadName || 'mos-toolbox-result'}-${Date.now()}.json`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

const onClear = () => {
  emit('clear')
}
</script>

<style scoped>
.result-card {
  margin-top: 12px;
}

.result-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.result-actions {
  display: flex;
  gap: 6px;
}

.result-empty {
  color: #606266;
  text-align: center;
  padding: 24px 0;
}

.result-message {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
}

@media (max-width: 768px) {
  .result-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }

  .result-actions {
    flex-wrap: wrap;
  }
}
</style>
