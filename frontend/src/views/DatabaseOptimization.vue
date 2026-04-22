<template>
  <div class="db-optimization-page">
    <el-page-header @back="goBack" title="返回">
      <template #content>
        <span class="page-header-title">数据库优化</span>
      </template>
    </el-page-header>

    <el-card class="main-card" shadow="never">
      <template #header>
        <div class="header-row">
          <span>连接池与执行参数</span>
          <div class="header-actions">
            <el-button :loading="loadingConfig" @click="loadConfig">刷新</el-button>
            <el-button :loading="pinging" @click="pingDatabase">连通性检测</el-button>
          </div>
        </div>
      </template>
      <el-alert
        title="保存参数后可选择写入 backend/.env；重启后端进程后生效。"
        type="warning"
        :closable="false"
        style="margin-bottom: 12px"
      />
      <el-descriptions :column="2" border size="small" style="margin-bottom: 12px">
        <el-descriptions-item label="数据库地址（脱敏）">{{ meta.database_url_masked || '—' }}</el-descriptions-item>
        <el-descriptions-item label="远程库">{{ meta.is_remote_database ? '是' : '否' }}</el-descriptions-item>
        <el-descriptions-item label="最近检测耗时">{{ pingMs === null ? '未检测' : `${pingMs} ms` }}</el-descriptions-item>
        <el-descriptions-item label="生效说明">{{ meta.note || '保存后重启后端进程生效' }}</el-descriptions-item>
      </el-descriptions>

      <el-form label-width="220px">
        <el-form-item label="连接池大小（pool_size）">
          <el-input-number v-model="form.pool_size" :min="1" :max="32" />
        </el-form-item>
        <el-form-item label="溢出连接数（max_overflow）">
          <el-input-number v-model="form.max_overflow" :min="0" :max="32" />
        </el-form-item>
        <el-form-item label="连接等待超时（秒）">
          <el-input-number v-model="form.pool_timeout_seconds" :min="5" :max="120" />
        </el-form-item>
        <el-form-item label="连接回收时间（秒）">
          <el-input-number v-model="form.pool_recycle_seconds" :min="30" :max="7200" />
        </el-form-item>
        <el-form-item label="Worker 数量（TOOLBOX_WORKERS）">
          <el-input-number v-model="form.workers" :min="1" :max="16" />
        </el-form-item>
        <el-form-item label="SQL 超时（毫秒）">
          <el-input-number v-model="form.statement_timeout_ms" :min="1000" :max="120000" :step="1000" />
        </el-form-item>
        <el-form-item label="应用到 .env">
          <el-switch v-model="applyToEnv" active-text="写入 backend/.env" inactive-text="仅保存页面参数" />
        </el-form-item>
        <el-form-item>
          <el-button :loading="saving" @click="applyRecommendation">套用推荐值</el-button>
          <el-button type="primary" :loading="saving" @click="saveConfig">保存参数</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card class="main-card" shadow="never">
      <template #header>
        <div class="header-row">
          <span>内外网工具可见性</span>
          <div class="header-actions">
            <el-button :loading="loadingVisibility" @click="loadToolVisibility">刷新</el-button>
          </div>
        </div>
      </template>
      <el-alert
        title="系统根据请求 Host 自动识别内/外网环境，并应用对应工具可见性配置。"
        type="info"
        :closable="false"
        style="margin-bottom: 12px"
      />
      <el-descriptions :column="2" border size="small" style="margin-bottom: 12px">
        <el-descriptions-item label="当前运行环境">
          <el-tag :type="visibilityMeta.current_runtime_env === 'external' ? 'warning' : 'success'">
            {{ visibilityMeta.current_runtime_env === 'external' ? '外网' : '内网' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="识别来源">{{ visibilityMeta.runtime_env_source || '—' }}</el-descriptions-item>
      </el-descriptions>

      <el-form label-width="220px">
        <el-form-item label="外网主机/IP（逗号或换行分隔）">
          <el-input
            v-model="visibilityForm.external_hosts_text"
            type="textarea"
            :rows="2"
            placeholder="例如：47.116.180.173"
          />
        </el-form-item>
        <el-form-item label="内网可见工具（留空=全部可见）">
          <el-select
            v-model="visibilityForm.internal_visible_tool_keys"
            multiple
            filterable
            clearable
            collapse-tags
            style="width: 100%"
            placeholder="选择内网可见工具"
          >
            <el-option
              v-for="tool in visibilityMeta.all_tools"
              :key="tool.id"
              :label="tool.display_name || tool.name"
              :value="tool.name"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="外网可见工具（留空=全部可见）">
          <el-select
            v-model="visibilityForm.external_visible_tool_keys"
            multiple
            filterable
            clearable
            collapse-tags
            style="width: 100%"
            placeholder="选择外网可见工具"
          >
            <el-option
              v-for="tool in visibilityMeta.all_tools"
              :key="`external-${tool.id}`"
              :label="tool.display_name || tool.name"
              :value="tool.name"
            />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="savingVisibility" @click="saveToolVisibility">保存可见性配置</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { adminApi } from '@/api/admin'

const router = useRouter()

const loadingConfig = ref(false)
const saving = ref(false)
const pinging = ref(false)
const pingMs = ref<number | null>(null)
const applyToEnv = ref(false)
const loadingVisibility = ref(false)
const savingVisibility = ref(false)
const meta = reactive({
  database_url_masked: '',
  is_remote_database: false,
  note: '',
  recommendation: {
    pool_size: 4,
    max_overflow: 2,
    pool_timeout_seconds: 30,
    pool_recycle_seconds: 1800,
    workers: 2,
    statement_timeout_ms: 15000,
  },
})
const visibilityMeta = reactive({
  current_runtime_env: 'internal' as 'internal' | 'external',
  runtime_env_source: '',
  all_tools: [] as Array<{ id: number; name: string; display_name?: string | null }>,
})
const form = reactive({
  pool_size: 4,
  max_overflow: 2,
  pool_timeout_seconds: 30,
  pool_recycle_seconds: 1800,
  workers: 2,
  statement_timeout_ms: 15000,
})
const visibilityForm = reactive({
  external_hosts_text: '47.116.180.173',
  internal_visible_tool_keys: [] as string[],
  external_visible_tool_keys: [] as string[],
})

const getErrorMessage = (error: any, fallback: string) => {
  return error?.response?.data?.detail || error?.message || fallback
}

const goBack = () => {
  const back = (window.history.state as { back?: unknown } | null)?.back
  if (back != null) {
    router.back()
  } else {
    router.push('/')
  }
}

const loadConfig = async () => {
  loadingConfig.value = true
  try {
    const data = await adminApi.getSystemDbOptimization()
    meta.database_url_masked = data.database_url_masked || ''
    meta.is_remote_database = Boolean(data.is_remote_database)
    meta.note = data.note || ''
    meta.recommendation = { ...meta.recommendation, ...(data.recommendation || {}) }
    const env = data.current_env || {}
    const saved = data.saved_overrides || {}
    form.pool_size = Number(saved.pool_size ?? env.SQLALCHEMY_POOL_SIZE ?? 4)
    form.max_overflow = Number(saved.max_overflow ?? env.SQLALCHEMY_MAX_OVERFLOW ?? 2)
    form.pool_timeout_seconds = Number(saved.pool_timeout_seconds ?? env.SQLALCHEMY_POOL_TIMEOUT ?? 30)
    form.pool_recycle_seconds = Number(saved.pool_recycle_seconds ?? env.SQLALCHEMY_POOL_RECYCLE ?? 1800)
    form.workers = Number(saved.workers ?? env.TOOLBOX_WORKERS ?? 2)
    form.statement_timeout_ms = Number(saved.statement_timeout_ms ?? env.SQLALCHEMY_STATEMENT_TIMEOUT_MS ?? 15000)
  } catch (error: any) {
    ElMessage.error(getErrorMessage(error, '加载数据库优化配置失败'))
  } finally {
    loadingConfig.value = false
  }
}

const applyRecommendation = () => {
  const rec = meta.recommendation
  form.pool_size = Number(rec.pool_size || 4)
  form.max_overflow = Number(rec.max_overflow || 2)
  form.pool_timeout_seconds = Number(rec.pool_timeout_seconds || 30)
  form.pool_recycle_seconds = Number(rec.pool_recycle_seconds || 1800)
  form.workers = Number(rec.workers || 2)
  form.statement_timeout_ms = Number(rec.statement_timeout_ms || 15000)
  ElMessage.success('已套用推荐值，请按需调整后保存')
}

const saveConfig = async () => {
  saving.value = true
  try {
    await adminApi.updateSystemDbOptimization({
      pool_size: form.pool_size,
      max_overflow: form.max_overflow,
      pool_timeout_seconds: form.pool_timeout_seconds,
      pool_recycle_seconds: form.pool_recycle_seconds,
      workers: form.workers,
      statement_timeout_ms: form.statement_timeout_ms,
      apply_to_env: applyToEnv.value,
    })
    ElMessage.success(applyToEnv.value ? '参数已保存并写入 .env' : '参数已保存')
    await loadConfig()
  } catch (error: any) {
    ElMessage.error(getErrorMessage(error, '保存数据库优化参数失败'))
  } finally {
    saving.value = false
  }
}

const pingDatabase = async () => {
  pinging.value = true
  try {
    const data = await adminApi.pingSystemDbOptimization()
    pingMs.value = Number(data.elapsed_ms ?? 0)
    ElMessage.success(`数据库连通检测成功：${pingMs.value} ms`)
  } catch (error: any) {
    ElMessage.error(getErrorMessage(error, '数据库连通检测失败'))
  } finally {
    pinging.value = false
  }
}

const parseHosts = (raw: string): string[] => {
  return Array.from(
    new Set(
      String(raw || '')
        .split(/[\n,;\s]+/)
        .map((v) => v.trim().toLowerCase())
        .filter((v) => !!v)
    )
  )
}

const loadToolVisibility = async () => {
  loadingVisibility.value = true
  try {
    const data = await adminApi.getToolVisibilityConfig()
    visibilityMeta.current_runtime_env = data.current_runtime_env
    visibilityMeta.runtime_env_source = data.runtime_env_source || ''
    visibilityMeta.all_tools = data.all_tools || []
    visibilityForm.external_hosts_text = (data.external_hosts || []).join(', ')
    visibilityForm.internal_visible_tool_keys = [...(data.internal_visible_tool_keys || [])]
    visibilityForm.external_visible_tool_keys = [...(data.external_visible_tool_keys || [])]
  } catch (error: any) {
    ElMessage.error(getErrorMessage(error, '加载工具可见性配置失败'))
  } finally {
    loadingVisibility.value = false
  }
}

const saveToolVisibility = async () => {
  savingVisibility.value = true
  try {
    await adminApi.updateToolVisibilityConfig({
      external_hosts: parseHosts(visibilityForm.external_hosts_text),
      internal_visible_tool_keys: visibilityForm.internal_visible_tool_keys,
      external_visible_tool_keys: visibilityForm.external_visible_tool_keys,
    })
    ElMessage.success('工具可见性配置已保存')
    await loadToolVisibility()
  } catch (error: any) {
    ElMessage.error(getErrorMessage(error, '保存工具可见性配置失败'))
  } finally {
    savingVisibility.value = false
  }
}

onMounted(async () => {
  await loadConfig()
  await loadToolVisibility()
})
</script>

<style scoped>
.db-optimization-page {
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

.header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-actions {
  display: flex;
  gap: 8px;
}
</style>
