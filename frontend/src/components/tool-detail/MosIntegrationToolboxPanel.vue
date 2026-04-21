<template>
  <el-card v-if="canManageTokenPreload" class="token-preload-card" shadow="never">
    <template #header>
      <div class="token-header">
        <span>Token 预加载状态</span>
        <div class="result-actions">
          <el-button text :loading="tokenPreloadLoading" @click="triggerTokenPreload(false)">后台预热</el-button>
          <el-button text :loading="tokenPreloadLoading" @click="loadAllTokenStatuses">查看全部 Token</el-button>
        </div>
      </div>
    </template>
    <el-table :data="tokenPreloadItems" size="small" stripe>
      <el-table-column prop="label" label="Token" min-width="220" />
      <el-table-column label="状态" width="120">
        <template #default="scope">
          <el-tag :type="tokenStatusTagType(scope.row.status)">{{ tokenStatusText(scope.row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="缓存剩余(s)" width="120">
        <template #default="scope">{{ scope.row.cache_expires_in_seconds ?? 0 }}</template>
      </el-table-column>
      <el-table-column prop="features" label="消费功能" min-width="260">
        <template #default="scope">{{ (scope.row.features || []).join(' / ') || '—' }}</template>
      </el-table-column>
      <el-table-column label="池子状态" width="120">
        <template #default="scope">
          <el-tag :type="scope.row.pool_inflight ? 'warning' : 'info'">
            {{ scope.row.pool_event || '—' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="池子统计" min-width="220">
        <template #default="scope">
          <span>
            命中 {{ scope.row.pool_stats?.hits ?? 0 }} / 等待 {{ scope.row.pool_stats?.waits ?? 0 }} / 新建 {{ scope.row.pool_stats?.misses ?? 0 }}
          </span>
        </template>
      </el-table-column>
      <el-table-column prop="last_error" label="最近错误" min-width="220" show-overflow-tooltip />
      <el-table-column label="操作" width="120" fixed="right">
        <template #default="scope">
          <el-button
            text
            type="primary"
            :loading="tokenPreloadLoading && refreshingScope === scope.row.scope"
            @click="refreshSingleToken(scope.row.scope)"
          >
            立刻刷新
          </el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>

  <el-tabs v-model="activeTab">
    <el-tab-pane label="IAM X509" name="x509-cert">
      <el-form label-width="120px">
        <el-form-item label="环境">
          <el-radio-group v-model="x509Env">
            <el-radio-button label="uat">UAT</el-radio-button>
            <el-radio-button label="live">LIVE</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="动作">
          <el-select v-model="x509Action" style="width: 220px">
            <el-option label="证书查询" value="check" />
            <el-option label="证书签发" value="sign" />
            <el-option label="解析CSR" value="parse_csr" />
            <el-option label="解析证书" value="parse_cert" />
          </el-select>
        </el-form-item>
        <el-form-item label="输入文本">
          <el-input v-model="x509Input" type="textarea" :rows="5" placeholder="按动作输入，每行一条（查询SN/签发CSR）或单条hex" />
        </el-form-item>
        <el-form-item label="批量导入">
          <input type="file" accept=".txt,.csv,.log" @change="onX509InputFileChange" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="x509Loading" @click="runX509">执行</el-button>
        </el-form-item>
      </el-form>
    </el-tab-pane>

    <el-tab-pane label="SIM 查询" name="sim-query">
      <el-form label-width="120px">
        <el-form-item label="运营商">
          <el-radio-group v-model="simProvider">
            <el-radio-button label="unicom">联通</el-radio-button>
            <el-radio-button label="ctcc">电信</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-alert
          v-if="simProvider === 'unicom'"
          title="联通查询首次请求可能较慢，请耐心等待，最长约 3 分钟。"
          type="warning"
          :closable="false"
          style="margin-bottom: 12px"
        />
        <template v-if="simProvider === 'unicom'">
          <el-form-item label="项目">
            <el-select v-model="unicomProject" placeholder="请选择项目" style="width: 220px">
              <el-option
                v-for="p in UNICOM_SIM_PROJECTS"
                :key="p"
                :label="p"
                :value="p"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="查询值">
            <el-input v-model="unicomSearchValue" placeholder="search_value" />
          </el-form-item>
        </template>
        <template v-else>
          <el-form-item label="ICCID">
            <el-input v-model="ctccIccid" placeholder="可选" />
          </el-form-item>
          <el-form-item label="MSISDN">
            <el-input v-model="ctccMsisdn" placeholder="可选" />
          </el-form-item>
          <el-form-item label="IMSI">
            <el-input v-model="ctccImsi" placeholder="可选" />
          </el-form-item>
        </template>
        <el-form-item>
          <el-button type="primary" :loading="simLoading" @click="runSimQuery">查询</el-button>
        </el-form-item>
      </el-form>
    </el-tab-pane>

    <el-tab-pane label="UAT AF DP" name="uat-af-dp-query">
      <el-form inline>
        <el-form-item label="VIN">
          <el-input v-model="afDpVin" placeholder="可选" />
        </el-form-item>
        <el-form-item label="ZXD SN">
          <el-input v-model="afDpZxdsn" placeholder="可选" />
        </el-form-item>
        <el-form-item label="IAM SN">
          <el-input v-model="afDpIamsn" placeholder="可选" />
        </el-form-item>
        <el-form-item label="ICCID">
          <el-input v-model="afDpIccid" placeholder="可选" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="afDpLoading" @click="runAfDpQuery">查询</el-button>
        </el-form-item>
      </el-form>
    </el-tab-pane>

    <el-tab-pane label="UAT Enrollment" name="uat-sp-query">
      <el-form inline>
        <el-form-item label="动作">
          <el-select v-model="spAction" style="width: 180px">
            <el-option label="查询SP信息" value="query_sp_info" />
            <el-option label="绑车" value="bind" />
            <el-option label="解绑" value="unbind" />
          </el-select>
        </el-form-item>
        <el-form-item label="VIN">
          <el-input v-model="spVin" placeholder="请输入VIN" style="width: 280px" />
        </el-form-item>
        <el-form-item v-if="spAction === 'bind'" label="手机号">
          <el-input v-model="spPhone" placeholder="请输入主账号手机号" style="width: 220px" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="spLoading" @click="runSpQuery">执行</el-button>
        </el-form-item>
      </el-form>
    </el-tab-pane>

    <el-tab-pane label="UAT 车辆配置导入" name="uat-vehicle-import">
      <el-form label-width="140px">
        <el-form-item v-if="hasVehicleRecentMemory" label="最近使用">
          <div class="vehicle-memory-row">
            <span>项目：{{ vehicleRecentMemory?.project }}，版本：{{ vehicleRecentMemory?.car_software_version }}</span>
            <div>
              <el-button text @click="applyVehicleRecentMemory">一键填充</el-button>
              <el-button text @click="clearVehicleRecentMemory">清除记忆</el-button>
            </div>
          </div>
        </el-form-item>
        <el-form-item label="所属项目">
          <el-select
            v-model="vehicleProject"
            filterable
            clearable
            placeholder="请选择所属项目"
            style="width: 360px"
          >
            <el-option
              v-for="project in vehicleRuleProjects"
              :key="project"
              :label="project"
              :value="project"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="车机软件版本号">
          <el-select
            v-model="vehicleCarSoftwareVersion"
            filterable
            allow-create
            default-first-option
            clearable
            placeholder="请选择或输入车机软件版本号"
            style="width: 360px"
          >
            <el-option
              v-for="pattern in vehicleVersionPatterns"
              :key="pattern"
              :label="pattern"
              :value="pattern"
            />
          </el-select>
          <div class="vehicle-hint">
            <template v-if="vehicleVersionPatterns.length">
              当前项目推荐版本格式：{{ vehicleVersionPatterns.join('，') }}（X 代表 0-9/A-Z 任意字符）
            </template>
            <template v-else>
              请先选择所属项目，系统将自动给出版本号格式建议。
            </template>
          </div>
        </el-form-item>
        <el-form-item label="HU Fazit ID">
          <el-input v-model="vehicleHuFazitId" placeholder="请输入 HU SN" />
        </el-form-item>
        <el-form-item label="OCU ICCID">
          <el-input v-model="vehicleOcuIccid" placeholder="请输入 ICCID" />
        </el-form-item>
        <el-form-item label="MSISDN">
          <el-input v-model="vehicleMsisdn" placeholder="请输入 MSISDN" />
        </el-form-item>
        <el-form-item label="OCU Fazit ID">
          <el-input v-model="vehicleOcuFazitId" placeholder="请输入 OCU SN" />
        </el-form-item>
        <el-form-item label="车辆VIN码">
          <el-input v-model="vehicleVin" placeholder="请输入17位VIN" />
        </el-form-item>
        <el-form-item label="申请部门">
          <el-input v-model="vehicleApplicationDepartment" placeholder="例如 智能网联测试部" />
        </el-form-item>
        <el-form-item label="目标系统">
          <el-radio-group v-model="importTarget">
            <el-radio-button label="sp">SP</el-radio-button>
            <el-radio-button label="cdp">CDP</el-radio-button>
            <el-radio-button label="afdp">AF DP</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="检查重复">
          <el-switch v-model="importCheckDuplicated" />
        </el-form-item>
        <el-form-item label="规则匹配结果">
          <el-input v-model="generatedVehicleJson" type="textarea" :rows="8" readonly />
        </el-form-item>
        <el-form-item>
          <el-button :loading="generateVehicleLoading" @click="generateVehicleConfig">生成配置</el-button>
          <el-button type="primary" :loading="importLoading" @click="runVehicleImport">导入</el-button>
        </el-form-item>
      </el-form>
    </el-tab-pane>
  </el-tabs>

  <el-card class="result-card">
    <template #header>
      <div class="result-header">
        <span>响应结果</span>
        <div class="result-actions">
          <el-button text @click="copyResult">复制</el-button>
          <el-button text @click="downloadResultJson">下载JSON</el-button>
          <el-button text @click="clearResult">清空</el-button>
        </div>
      </div>
    </template>
    <div v-if="resultTableRows.length === 0" class="result-empty">暂无结果</div>
    <template v-else>
      <el-table :data="paginatedResultRows" stripe>
        <el-table-column
          v-for="col in resultTableColumns"
          :key="col"
          :prop="col"
          :label="col"
          min-width="180"
          show-overflow-tooltip
        />
      </el-table>
      <div class="result-pagination-row" v-if="resultTableRows.length > resultPagination.pageSize">
        <el-pagination
          background
          layout="total, prev, pager, next, sizes"
          :total="resultTableRows.length"
          :current-page="resultPagination.page"
          :page-size="resultPagination.pageSize"
          :page-sizes="[10, 20, 50, 100]"
          @update:current-page="onResultPageChange"
          @update:page-size="onResultPageSizeChange"
        />
      </div>
    </template>
  </el-card>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { toolsApi } from '@/api/tools'

const props = defineProps<{ toolId: number }>()
const activeTab = ref('x509-cert')
const resultPagination = reactive({ page: 1, pageSize: 20 })
const canManageTokenPreload = ref(false)
const refreshingScope = ref<string | null>(null)
const resultByTab = reactive<Record<string, unknown>>({})

type TokenStatus = 'idle' | 'loading' | 'ready' | 'error'
type TokenPreloadItem = {
  scope: string
  label: string
  features: string[]
  status: TokenStatus
  last_error?: string | null
  cache_expires_in_seconds?: number
  pool_event?: string
  pool_inflight?: boolean
  pool_stats?: {
    requests: number
    hits: number
    misses: number
    waits: number
    errors: number
    refreshes: number
  }
}
const tokenPreloadLoading = ref(false)
const tokenPreloadItems = ref<TokenPreloadItem[]>([])
const tokenPreloadItemsByScope = reactive<Record<string, TokenPreloadItem>>({})
const TOKEN_SCOPE_BY_FEATURE = {
  x509_ua: ['zone-uat'],
  x509_live: ['zone-live'],
  uat_afdp_query: ['zone-uat'],
  uat_sp: ['sp-tool'],
  vehicle_import_sp: ['sp-tool'],
  vehicle_import_cdp: ['vmp-cookies'],
  vehicle_import_afdp: ['zone-uat']
} as const

const x509Env = ref<'uat' | 'live'>('uat')
const x509Action = ref<'check' | 'sign' | 'parse_csr' | 'parse_cert'>('check')
const x509Input = ref('')
const x509Loading = ref(false)

const simProvider = ref<'unicom' | 'ctcc'>('unicom')
const UNICOM_SIM_PROJECTS = ['CEI', 'Audi_5G', 'GP'] as const
type UnicomSimProject = (typeof UNICOM_SIM_PROJECTS)[number]
const unicomProject = ref<UnicomSimProject>('CEI')
const unicomSearchValue = ref('')
const ctccIccid = ref('')
const ctccMsisdn = ref('')
const ctccImsi = ref('')
const simLoading = ref(false)

const afDpVin = ref('')
const afDpZxdsn = ref('')
const afDpIamsn = ref('')
const afDpIccid = ref('')
const afDpLoading = ref(false)

const spAction = ref<'query_sp_info' | 'bind' | 'unbind'>('query_sp_info')
const spVin = ref('')
const spPhone = ref('')
const spLoading = ref(false)

const importTarget = ref<'sp' | 'cdp' | 'afdp'>('sp')
const importCheckDuplicated = ref(false)
const vehicleProject = ref('')
const vehicleCarSoftwareVersion = ref('')
const vehicleHuFazitId = ref('')
const vehicleOcuIccid = ref('')
const vehicleMsisdn = ref('')
const vehicleOcuFazitId = ref('')
const vehicleVin = ref('')
const vehicleApplicationDepartment = ref('')
const generatedVehicleData = ref<Record<string, any> | null>(null)
const generatedVehicleJson = ref('')
const generateVehicleLoading = ref(false)
const importLoading = ref(false)
const vehicleRuleProjects = ref<string[]>([])
const vehicleVersionPatternMap = ref<Record<string, string[]>>({})
const VEHICLE_FORM_MEMORY_KEY = `mos-vehicle-import-memory-${props.toolId}`
const vehicleRecentMemory = ref<{
  project: string
  car_software_version: string
  application_department: string
} | null>(null)

const vehicleVersionPatterns = computed(() => {
  return vehicleVersionPatternMap.value[vehicleProject.value] || []
})
const hasVehicleRecentMemory = computed(() => Boolean(vehicleRecentMemory.value?.project))

const normalizeCell = (value: unknown): string | number | boolean => {
  if (value === null || value === undefined) return ''
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') return value
  return JSON.stringify(value)
}

const resultDataOnly = computed(() => {
  const payload = (resultByTab[activeTab.value] || null) as Record<string, unknown> | null
  return payload?.data
})

const resultTableRows = computed(() => {
  const data = resultDataOnly.value
  if (Array.isArray(data)) {
    if (data.every((item) => item && typeof item === 'object' && !Array.isArray(item))) {
      return data.map((item) => {
        const obj = item as Record<string, unknown>
        const out: Record<string, string | number | boolean> = {}
        Object.keys(obj).forEach((k) => {
          out[k] = normalizeCell(obj[k])
        })
        return out
      })
    }
    return data.map((item, idx) => ({
      序号: idx + 1,
      值: normalizeCell(item)
    }))
  }
  if (data && typeof data === 'object') {
    return Object.entries(data as Record<string, unknown>).map(([k, v]) => ({
      字段: k,
      值: normalizeCell(v)
    }))
  }
  if (data === null || data === undefined) return []
  return [{ 值: normalizeCell(data) }]
})

const resultTableColumns = computed(() => {
  const first = resultTableRows.value[0]
  if (!first) return []
  return Object.keys(first)
})

const paginatedResultRows = computed(() => {
  const start = (resultPagination.page - 1) * resultPagination.pageSize
  const end = start + resultPagination.pageSize
  return resultTableRows.value.slice(start, end)
})

const onResultPageSizeChange = (size: number) => {
  resultPagination.pageSize = size
  resultPagination.page = 1
}

const onResultPageChange = (page: number) => {
  resultPagination.page = page
}

const setResult = (payload: unknown, tabKey: string = activeTab.value) => {
  resultByTab[tabKey] = payload
  resultPagination.page = 1
}

const VIN_REGEX = /^[A-HJ-NPR-Z0-9]{17}$/
const ICCID_REGEX = /^\d{19,20}$/
const MSISDN_REGEX = /^\d{11,13}$/
const IMSI_REGEX = /^\d{15}$/

const normalizeVin = (value: string) => value.trim().toUpperCase()

const splitNonEmptyLines = (value: string) => value.split('\n').map((s) => s.trim()).filter(Boolean)

const getErrorMessage = (error: any, fallback: string) => {
  return error?.response?.data?.detail || error?.message || fallback
}

const tokenStatusText = (status: TokenStatus) => {
  if (status === 'ready') return '已就绪'
  if (status === 'loading') return '预热中'
  if (status === 'error') return '失败'
  return '未加载'
}

const tokenStatusTagType = (status: TokenStatus): 'success' | 'warning' | 'danger' | 'info' => {
  if (status === 'ready') return 'success'
  if (status === 'loading') return 'warning'
  if (status === 'error') return 'danger'
  return 'info'
}

const requestTokenPreload = async (
  scopes?: string[],
  wait: boolean = false,
  forceRefresh: boolean = false
) => {
  const res = await toolsApi.preloadMosTokens(props.toolId, {
    scopes,
    wait,
    force_refresh: forceRefresh,
    timeout_seconds: 60
  })
  const items = Array.isArray(res?.data?.items) ? res.data.items : []
  items.forEach((item) => {
    tokenPreloadItemsByScope[item.scope] = item
  })
  tokenPreloadItems.value = Object.values(tokenPreloadItemsByScope)
  return res
}

const loadAllTokenStatuses = async () => {
  tokenPreloadLoading.value = true
  try {
    await requestTokenPreload(undefined, false, false)
    ElMessage.success('已切换为全部 Token 视图')
  } catch (error: any) {
    ElMessage.error(getErrorMessage(error, '加载全部 Token 状态失败'))
  } finally {
    tokenPreloadLoading.value = false
  }
}

const loadTokenPreloadVisibility = async () => {
  try {
    const res = await toolsApi.getMosTokenPreloadVisibility(props.toolId)
    canManageTokenPreload.value = Boolean(res?.data?.can_manage)
  } catch {
    canManageTokenPreload.value = false
  }
}

const triggerTokenPreload = async (forceRefresh: boolean) => {
  tokenPreloadLoading.value = true
  try {
    await requestTokenPreload(undefined, false, forceRefresh)
    ElMessage.success(forceRefresh ? '已触发强制预热' : '已触发后台预热')
  } catch (error: any) {
    ElMessage.error(getErrorMessage(error, 'Token 预热请求失败'))
  } finally {
    tokenPreloadLoading.value = false
  }
}

const refreshSingleToken = async (scope: string) => {
  tokenPreloadLoading.value = true
  refreshingScope.value = scope
  try {
    await requestTokenPreload([scope], false, true)
    ElMessage.success(`已触发 ${scope} 刷新`)
  } catch (error: any) {
    ElMessage.error(getErrorMessage(error, `${scope} 刷新失败`))
  } finally {
    refreshingScope.value = null
    tokenPreloadLoading.value = false
  }
}

const ensureTokenScopes = async (scopes: string[], actionLabel: string) => {
  if (!scopes.length) return
  tokenPreloadLoading.value = true
  try {
    const res = await requestTokenPreload(scopes, true, false)
    if (!res.success || res?.data?.has_errors) {
      throw new Error(`${actionLabel} 需要的 token 预热失败，请稍后重试`)
    }
  } catch (error: any) {
    throw new Error(getErrorMessage(error, `${actionLabel} 需要的 token 获取失败`))
  } finally {
    tokenPreloadLoading.value = false
  }
}

const readFileAsText = (file: File): Promise<string> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result || ''))
    reader.onerror = () => reject(new Error('读取文件失败'))
    reader.readAsText(file, 'utf-8')
  })
}

const onX509InputFileChange = async (event: Event) => {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return
  try {
    x509Input.value = await readFileAsText(file)
    ElMessage.success('已载入批量文本')
  } catch (error: any) {
    ElMessage.error(getErrorMessage(error, '文件读取失败'))
  } finally {
    target.value = ''
  }
}

const copyResult = async () => {
  const text = JSON.stringify(resultDataOnly.value ?? null, null, 2)
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

const downloadResultJson = () => {
  const text = JSON.stringify(resultDataOnly.value ?? null, null, 2)
  if (!text.trim()) {
    ElMessage.warning('暂无可下载内容')
    return
  }
  const blob = new Blob([text], { type: 'application/json;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `mos-toolbox-result-${Date.now()}.json`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

const clearResult = () => {
  delete resultByTab[activeTab.value]
  resultPagination.page = 1
}

const clearGeneratedVehicle = () => {
  generatedVehicleData.value = null
  generatedVehicleJson.value = ''
}

const persistVehicleMemory = () => {
  const payload = {
    project: vehicleProject.value.trim(),
    car_software_version: vehicleCarSoftwareVersion.value.trim(),
    application_department: vehicleApplicationDepartment.value.trim()
  }
  if (!payload.project) return
  localStorage.setItem(VEHICLE_FORM_MEMORY_KEY, JSON.stringify(payload))
  vehicleRecentMemory.value = payload
}

const loadVehicleRecentMemory = () => {
  const raw = localStorage.getItem(VEHICLE_FORM_MEMORY_KEY)
  if (!raw) return
  try {
    const parsed = JSON.parse(raw)
    if (!parsed?.project) return
    vehicleRecentMemory.value = {
      project: String(parsed.project || ''),
      car_software_version: String(parsed.car_software_version || ''),
      application_department: String(parsed.application_department || '')
    }
  } catch {
    localStorage.removeItem(VEHICLE_FORM_MEMORY_KEY)
  }
}

const applyVehicleRecentMemory = () => {
  if (!vehicleRecentMemory.value) return
  vehicleProject.value = vehicleRecentMemory.value.project
  vehicleCarSoftwareVersion.value = vehicleRecentMemory.value.car_software_version
  if (!vehicleApplicationDepartment.value.trim()) {
    vehicleApplicationDepartment.value = vehicleRecentMemory.value.application_department
  }
  ElMessage.success('已应用最近使用项目')
}

const clearVehicleRecentMemory = () => {
  localStorage.removeItem(VEHICLE_FORM_MEMORY_KEY)
  vehicleRecentMemory.value = null
  ElMessage.success('已清除最近使用记忆')
}

const loadVehicleRules = async () => {
  try {
    const res = await toolsApi.getUatVehicleConfigRules(props.toolId)
    vehicleRuleProjects.value = res?.data?.projects || []
    vehicleVersionPatternMap.value = res?.data?.version_patterns_by_project || {}
  } catch (error: any) {
    ElMessage.error(getErrorMessage(error, '加载车辆规则失败'))
  }
}

watch(vehicleProject, () => {
  const patterns = vehicleVersionPatternMap.value[vehicleProject.value] || []
  vehicleCarSoftwareVersion.value = patterns[0] || ''
  clearGeneratedVehicle()
})

watch(
  [
    vehicleCarSoftwareVersion,
    vehicleHuFazitId,
    vehicleOcuIccid,
    vehicleMsisdn,
    vehicleOcuFazitId,
    vehicleVin,
    vehicleApplicationDepartment
  ],
  () => {
    clearGeneratedVehicle()
  }
)

onMounted(() => {
  loadVehicleRules()
  loadVehicleRecentMemory()
  loadTokenPreloadVisibility()
  requestTokenPreload(undefined, false, false).catch(() => {})
  if (vehicleRecentMemory.value && !vehicleProject.value) {
    applyVehicleRecentMemory()
  }
})

const runX509 = async () => {
  const rawInput = x509Input.value.trim()
  if (!rawInput) {
    ElMessage.warning('请输入请求内容')
    return
  }
  try {
    x509Loading.value = true
    await ensureTokenScopes(
      x509Env.value === 'live' ? [...TOKEN_SCOPE_BY_FEATURE.x509_live] : [...TOKEN_SCOPE_BY_FEATURE.x509_ua],
      'IAM X509'
    )
    const lines = splitNonEmptyLines(rawInput)
    const payload: any = { action: x509Action.value, env: x509Env.value }
    if (x509Action.value === 'check') {
      payload.iam_sns = lines
      if (!lines.length) {
        ElMessage.warning('请至少输入一个 IAM SN')
        return
      }
    }
    if (x509Action.value === 'sign') {
      payload.csrs = lines
      if (!lines.length) {
        ElMessage.warning('请至少输入一条 CSR')
        return
      }
    }
    if (x509Action.value === 'parse_csr') payload.csr = rawInput
    if (x509Action.value === 'parse_cert') payload.cert = rawInput
    const res = await toolsApi.runX509Feature(props.toolId, payload)
    setResult(res, 'x509-cert')
  } catch (error: any) {
    ElMessage.error(getErrorMessage(error, 'IAM X509 请求失败'))
  } finally {
    x509Loading.value = false
  }
}

const runSimQuery = async () => {
  const project = unicomProject.value
  const searchValue = unicomSearchValue.value.trim()
  const iccid = ctccIccid.value.trim()
  const msisdn = ctccMsisdn.value.trim()
  const imsi = ctccImsi.value.trim()

  if (simProvider.value === 'unicom' && (!project || !searchValue)) {
    ElMessage.warning('联通查询需要填写项目和查询值')
    return
  }

  if (simProvider.value === 'ctcc') {
    if (!iccid && !msisdn && !imsi) {
      ElMessage.warning('电信查询至少填写 ICCID/MSISDN/IMSI 之一')
      return
    }
    if (iccid && !ICCID_REGEX.test(iccid)) {
      ElMessage.warning('ICCID 格式不正确，应为19-20位数字')
      return
    }
    if (msisdn && !MSISDN_REGEX.test(msisdn)) {
      ElMessage.warning('MSISDN 格式不正确，应为11-13位数字')
      return
    }
    if (imsi && !IMSI_REGEX.test(imsi)) {
      ElMessage.warning('IMSI 格式不正确，应为15位数字')
      return
    }
  }

  try {
    simLoading.value = true
    const payload = simProvider.value === 'unicom'
      ? { provider: 'unicom' as const, project, search_value: searchValue }
      : {
        provider: 'ctcc' as const,
        iccid: iccid || undefined,
        msisdn: msisdn || undefined,
        imsi: imsi || undefined
      }
    const res = await toolsApi.querySim(props.toolId, payload)
    setResult(res, 'sim-query')
  } catch (error: any) {
    ElMessage.error(getErrorMessage(error, 'SIM 查询失败'))
  } finally {
    simLoading.value = false
  }
}

const runAfDpQuery = async () => {
  const vin = normalizeVin(afDpVin.value)
  const zxdsn = afDpZxdsn.value.trim().toUpperCase()
  const iamsn = afDpIamsn.value.trim().toUpperCase()
  const iccid = afDpIccid.value.trim()

  if (!vin && !zxdsn && !iamsn && !iccid) {
    ElMessage.warning('请至少填写一个查询条件')
    return
  }
  if (vin && !VIN_REGEX.test(vin)) {
    ElMessage.warning('VIN 格式不正确')
    return
  }
  if (iccid && !ICCID_REGEX.test(iccid)) {
    ElMessage.warning('ICCID 格式不正确')
    return
  }

  try {
    afDpLoading.value = true
    await ensureTokenScopes([...TOKEN_SCOPE_BY_FEATURE.uat_afdp_query], 'UAT AF DP 查询')
    const res = await toolsApi.queryUatAfDp(props.toolId, {
      vin: vin || undefined,
      zxdsn: zxdsn || undefined,
      iamsn: iamsn || undefined,
      iccid: iccid || undefined
    })
    setResult(res, 'uat-af-dp-query')
  } catch (error: any) {
    ElMessage.error(getErrorMessage(error, 'UAT AF DP 查询失败'))
  } finally {
    afDpLoading.value = false
  }
}

const runSpQuery = async () => {
  const vin = normalizeVin(spVin.value)
  if (!VIN_REGEX.test(vin)) {
    ElMessage.warning('VIN 格式不正确')
    return
  }
  const phone = spPhone.value.trim()
  if (spAction.value === 'bind' && !phone) {
    ElMessage.warning('绑车操作需要填写手机号')
    return
  }
  try {
    spLoading.value = true
    await ensureTokenScopes([...TOKEN_SCOPE_BY_FEATURE.uat_sp], 'UAT Enrollment')
    const res = await toolsApi.queryUatSp(props.toolId, {
      action: spAction.value,
      vin,
      phone: spAction.value === 'bind' ? phone : undefined
    })
    setResult(res, 'uat-sp-query')
  } catch (error: any) {
    ElMessage.error(getErrorMessage(error, 'UAT Enrollment 操作失败'))
  } finally {
    spLoading.value = false
  }
}

const generateVehicleConfig = async () => {
  const vin = normalizeVin(vehicleVin.value)
  if (!VIN_REGEX.test(vin)) {
    ElMessage.warning('车辆VIN码必须是17位大写字母数字（不含 I/O/Q）')
    return
  }
  if (!vehicleProject.value.trim() || !vehicleCarSoftwareVersion.value.trim() || !vehicleHuFazitId.value.trim() ||
      !vehicleOcuIccid.value.trim() || !vehicleMsisdn.value.trim() || !vehicleOcuFazitId.value.trim() ||
      !vehicleApplicationDepartment.value.trim()) {
    ElMessage.warning('请完整填写车辆配置必填字段')
    return
  }

  try {
    generateVehicleLoading.value = true
    const res = await toolsApi.generateUatVehicleConfig(props.toolId, {
      project: vehicleProject.value.trim(),
      car_software_version: vehicleCarSoftwareVersion.value.trim().toUpperCase(),
      hu_fazit_id: vehicleHuFazitId.value.trim(),
      ocu_iccid: vehicleOcuIccid.value.trim(),
      msisdn: vehicleMsisdn.value.trim(),
      ocu_fazit_id: vehicleOcuFazitId.value.trim(),
      vehicle_vin: vin,
      application_department: vehicleApplicationDepartment.value.trim()
    })
    generatedVehicleData.value = (res?.data || null) as Record<string, any> | null
    generatedVehicleJson.value = JSON.stringify(generatedVehicleData.value || {}, null, 2)
    persistVehicleMemory()
    setResult(res, 'uat-vehicle-import')
  } catch (error: any) {
    ElMessage.error(getErrorMessage(error, '规则匹配失败'))
  } finally {
    generateVehicleLoading.value = false
  }
}

const runVehicleImport = async () => {
  if (!generatedVehicleData.value) {
    ElMessage.warning('请先点击“生成配置”，确认规则匹配成功后再导入')
    return
  }
  try {
    importLoading.value = true
    if (importTarget.value === 'sp') {
      await ensureTokenScopes([...TOKEN_SCOPE_BY_FEATURE.vehicle_import_sp], 'SP 车辆导入')
    } else if (importTarget.value === 'cdp') {
      await ensureTokenScopes([...TOKEN_SCOPE_BY_FEATURE.vehicle_import_cdp], 'CDP 车辆导入')
    } else if (importTarget.value === 'afdp') {
      await ensureTokenScopes([...TOKEN_SCOPE_BY_FEATURE.vehicle_import_afdp], 'AF DP 车辆导入')
    }
    const res = await toolsApi.importUatVehicleConfig(props.toolId, {
      target: importTarget.value,
      check_duplicated: importCheckDuplicated.value,
      vehicle_data: generatedVehicleData.value
    })
    setResult(res, 'uat-vehicle-import')
  } catch (error: any) {
    ElMessage.error(getErrorMessage(error, 'UAT 车辆配置导入失败'))
  } finally {
    importLoading.value = false
  }
}
</script>

<style scoped>
.token-preload-card {
  margin-bottom: 16px;
}

.result-card {
  margin-top: 16px;
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
  color: #909399;
  text-align: center;
  padding: 24px 0;
}

.result-pagination-row {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}

.vehicle-hint {
  margin-top: 6px;
  color: #666;
  font-size: 12px;
  line-height: 1.5;
}

.vehicle-memory-row {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  background: #f5f7fa;
  border-radius: 4px;
  padding: 6px 10px;
  color: #606266;
}
</style>
