<template>
  <div class="db-optimization-page">
    <el-page-header @back="goBack" title="返回">
      <template #content>
        <span class="page-header-title">系统配置</span>
      </template>
    </el-page-header>

    <el-card class="main-card" shadow="never">
      <template #header>
        <div class="header-row">
          <span>环境变量（.env 全文）</span>
          <div class="header-actions">
            <el-button :loading="loadingEnv" @click="loadEnv">刷新</el-button>
            <el-button type="primary" :loading="savingEnv" @click="saveEnv">保存</el-button>
          </div>
        </div>
      </template>
      <el-alert
        title="此处编辑的是后端工作区根目录下的 .env；保存后敏感项仍可能被进程缓存，通常需重启后端。误改可能导致服务无法启动，请先备份。"
        type="warning"
        :closable="false"
        style="margin-bottom: 12px"
      />
      <el-input
        v-model="envContent"
        type="textarea"
        :rows="20"
        class="env-textarea"
        placeholder="加载中…"
        spellcheck="false"
      />
      <div class="env-actions">
        <el-button type="danger" plain :loading="restarting" @click="requestBackendRestart">重启后端…</el-button>
      </div>
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

    <el-card class="main-card" shadow="never">
      <template #header>
        <div class="header-row">
          <span>数据库连接（只读）</span>
          <div class="header-actions">
            <el-button :loading="loadingConfig" @click="loadConfig">刷新</el-button>
            <el-button :loading="pinging" @click="pingDatabase">连通性检测</el-button>
          </div>
        </div>
      </template>
      <el-alert
        title="连接池、Worker、SQL 超时等请在「系统配置」编辑 .env（需相应权限）或维护期编辑部署机环境变量；此处仅查看当前进程读到的环境值与已保存的 overrides，并可做连通性检测。"
        type="info"
        :closable="false"
        style="margin-bottom: 12px"
      />
      <el-descriptions :column="2" border size="small" style="margin-bottom: 12px">
        <el-descriptions-item label="数据库地址（脱敏）">{{ meta.database_url_masked || '—' }}</el-descriptions-item>
        <el-descriptions-item label="远程库">{{ meta.is_remote_database ? '是' : '否' }}</el-descriptions-item>
        <el-descriptions-item label="最近检测耗时">{{ pingMs === null ? '未检测' : `${pingMs} ms` }}</el-descriptions-item>
        <el-descriptions-item label="说明">{{ meta.note || '—' }}</el-descriptions-item>
      </el-descriptions>

      <div class="subsection-title">当前进程环境（.env / 默认）</div>
      <el-descriptions :column="2" border size="small" style="margin-bottom: 16px">
        <el-descriptions-item label="连接池大小 (SQLALCHEMY_POOL_SIZE)">
          {{ meta.current_env.SQLALCHEMY_POOL_SIZE }}
        </el-descriptions-item>
        <el-descriptions-item label="溢出连接 (SQLALCHEMY_MAX_OVERFLOW)">
          {{ meta.current_env.SQLALCHEMY_MAX_OVERFLOW }}
        </el-descriptions-item>
        <el-descriptions-item label="连接等待超时秒 (SQLALCHEMY_POOL_TIMEOUT)">
          {{ meta.current_env.SQLALCHEMY_POOL_TIMEOUT }}
        </el-descriptions-item>
        <el-descriptions-item label="连接回收秒 (SQLALCHEMY_POOL_RECYCLE)">
          {{ meta.current_env.SQLALCHEMY_POOL_RECYCLE }}
        </el-descriptions-item>
        <el-descriptions-item label="Worker 数 (TOOLBOX_WORKERS)">{{ meta.current_env.TOOLBOX_WORKERS }}</el-descriptions-item>
        <el-descriptions-item label="SQL 超时毫秒 (SQLALCHEMY_STATEMENT_TIMEOUT_MS)">
          {{ meta.current_env.SQLALCHEMY_STATEMENT_TIMEOUT_MS }}
        </el-descriptions-item>
      </el-descriptions>

      <div class="subsection-title">已保存 overrides（runtime/db_optimization.json）</div>
      <el-empty v-if="!savedOverrideKeys.length" description="暂无 overrides 文件或文件为空" :image-size="64" />
      <el-descriptions v-else :column="2" border size="small" style="margin-bottom: 16px">
        <el-descriptions-item v-for="key in savedOverrideKeys" :key="key" :label="overrideLabel(key)">
          {{ String((meta.saved_overrides as Record<string, number>)[key]) }}
        </el-descriptions-item>
      </el-descriptions>

      <div class="subsection-title">推荐参考值（只读）</div>
      <el-descriptions :column="2" border size="small">
        <el-descriptions-item label="pool_size">{{ meta.recommendation.pool_size }}</el-descriptions-item>
        <el-descriptions-item label="max_overflow">{{ meta.recommendation.max_overflow }}</el-descriptions-item>
        <el-descriptions-item label="pool_timeout_seconds">{{ meta.recommendation.pool_timeout_seconds }}</el-descriptions-item>
        <el-descriptions-item label="pool_recycle_seconds">{{ meta.recommendation.pool_recycle_seconds }}</el-descriptions-item>
        <el-descriptions-item label="workers">{{ meta.recommendation.workers }}</el-descriptions-item>
        <el-descriptions-item label="statement_timeout_ms">{{ meta.recommendation.statement_timeout_ms }}</el-descriptions-item>
      </el-descriptions>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { adminApi } from '@/api/admin'

const router = useRouter()

const envContent = ref('')
const loadingEnv = ref(false)
const savingEnv = ref(false)
const restarting = ref(false)

const loadingConfig = ref(false)
const pinging = ref(false)
const pingMs = ref<number | null>(null)
const loadingVisibility = ref(false)
const savingVisibility = ref(false)
const meta = reactive({
  database_url_masked: '',
  is_remote_database: false,
  note: '',
  current_env: {
    SQLALCHEMY_POOL_SIZE: 4,
    SQLALCHEMY_MAX_OVERFLOW: 2,
    SQLALCHEMY_POOL_TIMEOUT: 30,
    SQLALCHEMY_POOL_RECYCLE: 1800,
    TOOLBOX_WORKERS: 2,
    SQLALCHEMY_STATEMENT_TIMEOUT_MS: 15000,
  },
  saved_overrides: {} as Record<string, number>,
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
const visibilityForm = reactive({
  external_hosts_text: '47.116.180.173',
  internal_visible_tool_keys: [] as string[],
  external_visible_tool_keys: [] as string[],
})

const savedOverrideKeys = computed(() =>
  Object.keys(meta.saved_overrides || {}).filter((k) => meta.saved_overrides[k as keyof typeof meta.saved_overrides] != null),
)

const overrideLabel = (key: string) => {
  const map: Record<string, string> = {
    pool_size: 'pool_size',
    max_overflow: 'max_overflow',
    pool_timeout_seconds: 'pool_timeout_seconds',
    pool_recycle_seconds: 'pool_recycle_seconds',
    workers: 'workers',
    statement_timeout_ms: 'statement_timeout_ms',
  }
  return map[key] || key
}

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
    meta.current_env = {
      SQLALCHEMY_POOL_SIZE: Number(env.SQLALCHEMY_POOL_SIZE ?? 4),
      SQLALCHEMY_MAX_OVERFLOW: Number(env.SQLALCHEMY_MAX_OVERFLOW ?? 2),
      SQLALCHEMY_POOL_TIMEOUT: Number(env.SQLALCHEMY_POOL_TIMEOUT ?? 30),
      SQLALCHEMY_POOL_RECYCLE: Number(env.SQLALCHEMY_POOL_RECYCLE ?? 1800),
      TOOLBOX_WORKERS: Number(env.TOOLBOX_WORKERS ?? 2),
      SQLALCHEMY_STATEMENT_TIMEOUT_MS: Number(env.SQLALCHEMY_STATEMENT_TIMEOUT_MS ?? 15000),
    }
    meta.saved_overrides = { ...(data.saved_overrides || {}) }
  } catch (error: any) {
    ElMessage.error(getErrorMessage(error, '加载数据库配置失败'))
  } finally {
    loadingConfig.value = false
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

const loadEnv = async () => {
  loadingEnv.value = true
  try {
    const data = await adminApi.getEnvFile()
    envContent.value = data.content ?? ''
  } catch (error: any) {
    ElMessage.error(getErrorMessage(error, '加载 .env 失败'))
  } finally {
    loadingEnv.value = false
  }
}

const saveEnv = async () => {
  savingEnv.value = true
  try {
    await adminApi.putEnvFile(envContent.value)
    ElMessage.success('.env 已保存')
  } catch (error: any) {
    ElMessage.error(getErrorMessage(error, '保存 .env 失败'))
  } finally {
    savingEnv.value = false
  }
}

const requestBackendRestart = async () => {
  try {
    await ElMessageBox.confirm(
      '重启将导致当前后端进程退出并由外部命令重新拉起，期间 API 会短暂不可用。确定继续？',
      '重启后端',
      { type: 'warning', confirmButtonText: '继续', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  try {
    await ElMessageBox.confirm(
      '请再次确认：已保存 .env，且已在服务器配置 TOOLBOX_BACKEND_RESTART_CMD（如 nssm / systemctl 脚本）。',
      '二次确认',
      { type: 'warning', confirmButtonText: '确认重启', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  restarting.value = true
  try {
    await adminApi.restartBackend('CONFIRM_BACKEND_RESTART')
    ElMessage.success('重启指令已提交')
  } catch (error: any) {
    ElMessage.error(getErrorMessage(error, '提交重启失败'))
  } finally {
    restarting.value = false
  }
}

onMounted(async () => {
  await loadToolVisibility()
  await loadConfig()
  await loadEnv()
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

.subsection-title {
  font-size: 14px;
  font-weight: 600;
  color: #606266;
  margin-bottom: 8px;
}

.env-textarea :deep(textarea) {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
  font-size: 13px;
}

.env-actions {
  margin-top: 12px;
}
</style>
