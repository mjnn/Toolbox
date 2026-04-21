<template>
  <div class="rsa-livestream-panel" v-loading="loading">
    <el-alert
      type="info"
      :closable="false"
      show-icon
      title="直播地址由工具负责人统一维护。若显示占位页，表示当前直播已临时关闭。"
    />

    <el-card shadow="never">
      <template #header>RSA Token 直播</template>

      <el-alert
        v-if="loadError"
        type="error"
        :closable="false"
        show-icon
        :title="loadError"
      />

      <template v-else-if="config">
        <el-empty
          v-if="config.placeholder_enabled"
          :description="config.placeholder_message"
        >
          <template #image>
            <div class="placeholder-title">{{ config.placeholder_title }}</div>
          </template>
        </el-empty>

        <div v-else class="stream-wrapper">
          <div class="stream-meta">
            <el-tag type="success">直播中</el-tag>
            <span>推流服务器：{{ config.stream_server }}</span>
            <span>推流码：{{ config.stream_key }}</span>
          </div>
          <iframe
            class="stream-frame"
            :src="config.stream_page_url"
            title="RSA Token 直播画面"
            allow="autoplay; fullscreen"
          />
        </div>
      </template>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { toolsApi } from '@/api/tools'
import type { RsaLivestreamConfig } from '@/api/types'

const props = defineProps<{ toolId: number }>()

const loading = ref(false)
const loadError = ref('')
const config = ref<RsaLivestreamConfig | null>(null)

const loadConfig = async () => {
  loading.value = true
  loadError.value = ''
  try {
    config.value = await toolsApi.getRsaLivestreamConfig(props.toolId)
  } catch (error: any) {
    const message = error.message || '直播配置加载失败'
    loadError.value = message
    ElMessage.error(message)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  void loadConfig()
})
</script>

<style scoped>
.rsa-livestream-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.placeholder-title {
  color: #909399;
  font-size: 20px;
  font-weight: 600;
  padding-top: 12px;
}

.stream-wrapper {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.stream-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  color: #606266;
  font-size: 13px;
}

.stream-frame {
  width: 100%;
  min-height: 560px;
  border: 1px solid #ebeef5;
  border-radius: 4px;
}
</style>
