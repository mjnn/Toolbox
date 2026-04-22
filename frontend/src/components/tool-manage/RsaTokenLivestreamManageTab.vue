<template>
  <div class="rsa-livestream-manage-tab" v-loading="loading">
    <el-card shadow="never">
      <template #header>直播与占位配置</template>
      <p class="section-hint">
        建议填写“部署机转发后的内网直播地址”。开启占位后，工具使用页会隐藏直播画面并显示提示信息。
      </p>

      <el-form label-position="top">
        <el-form-item label="占位页开关">
          <el-switch
            v-model="form.placeholder_enabled"
            active-text="开启占位页（隐藏直播）"
            inactive-text="关闭占位页（显示直播）"
          />
        </el-form-item>

        <el-form-item label="占位标题">
          <el-input v-model="form.placeholder_title" maxlength="120" show-word-limit />
        </el-form-item>

        <el-form-item label="占位说明">
          <el-input
            v-model="form.placeholder_message"
            type="textarea"
            :rows="3"
            maxlength="1000"
            show-word-limit
          />
        </el-form-item>

        <el-form-item label="内网直播展示地址（建议为部署机转发地址）">
          <el-input v-model="form.stream_page_url" placeholder="例如 http://内网IP:端口/players/srs_player.html?... 或 .flv 地址" />
        </el-form-item>
        <el-form-item label="系统解析出的 FLV 源地址（只读）">
          <el-input :model-value="form.resolved_stream_flv_url || '未解析到 FLV 地址'" readonly />
        </el-form-item>
        <el-form-item label="系统内网转发地址（只读）">
          <el-input :model-value="form.internal_flv_proxy_url" readonly />
        </el-form-item>

        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="推流服务器">
              <el-input v-model="form.stream_server" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="推流码">
              <el-input v-model="form.stream_key" />
            </el-form-item>
          </el-col>
        </el-row>

        <div class="action-row">
          <el-button type="primary" :loading="saving" @click="saveConfig">保存配置</el-button>
          <span v-if="form.updated_at" class="updated-time">
            最近更新：{{ formatDate(form.updated_at) }}
          </span>
        </div>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { toolsApi } from '@/api/tools'
import { formatDateTime as formatDate } from '@/utils/datetime'
import type { RsaLivestreamConfig } from '@/api/types'

const props = defineProps<{ toolId: number }>()

const loading = ref(false)
const saving = ref(false)
const form = reactive<RsaLivestreamConfig>({
  stream_page_url: '',
  resolved_stream_flv_url: '',
  internal_flv_proxy_url: '',
  stream_server: '',
  stream_key: '',
  placeholder_enabled: true,
  placeholder_title: '',
  placeholder_message: '',
  updated_at: '',
})

const applyConfig = (cfg: RsaLivestreamConfig) => {
  Object.assign(form, cfg)
}

const loadConfig = async () => {
  loading.value = true
  try {
    const res = await toolsApi.getRsaLivestreamConfig(props.toolId)
    applyConfig(res)
  } finally {
    loading.value = false
  }
}

const saveConfig = async () => {
  saving.value = true
  try {
    const res = await toolsApi.updateRsaLivestreamManageConfig(props.toolId, {
      stream_page_url: form.stream_page_url,
      stream_server: form.stream_server,
      stream_key: form.stream_key,
      placeholder_enabled: form.placeholder_enabled,
      placeholder_title: form.placeholder_title,
      placeholder_message: form.placeholder_message,
    })
    applyConfig(res)
    ElMessage.success('直播配置已保存')
  } catch (error: any) {
    ElMessage.error(error.message || '保存配置失败')
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  try {
    await loadConfig()
  } catch (error: any) {
    ElMessage.error(error.message || '加载直播配置失败')
  }
})
</script>

<style scoped>
.rsa-livestream-manage-tab {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.section-hint {
  color: #909399;
  font-size: 13px;
  margin: 0 0 12px;
}

.action-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.updated-time {
  color: #909399;
  font-size: 12px;
}
</style>
