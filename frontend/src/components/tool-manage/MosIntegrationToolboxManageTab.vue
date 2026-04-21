<template>
  <div class="mos-manage-tab">
    <el-tabs v-model="moduleTab" class="manage-module-tabs" @update:model-value="onModuleTabChange">
      <el-tab-pane label="规则管理" name="rules">
        <el-card shadow="never">
          <template #header>
            <div class="header-row">
              <span>项目匹配规则管理</span>
              <div class="header-actions">
                <el-button @click="loadVehicleRules">刷新</el-button>
                <el-button @click="openBulkImportDialog">批量导入</el-button>
                <el-button type="primary" @click="openCreateRule">新增规则</el-button>
              </div>
            </div>
          </template>
          <el-alert
            title="规则以 JSON 原文编辑；保存后会立即影响“UAT 车辆配置导入”的规则匹配。"
            type="warning"
            :closable="false"
            style="margin-bottom: 12px"
          />
          <el-table :data="vehicleRules" v-loading="loadingRules" stripe>
            <el-table-column prop="rule_index" label="#" width="70" />
            <el-table-column label="项目" min-width="200">
              <template #default="scope">{{ scope.row['项目版本号'] || '—' }}</template>
            </el-table-column>
            <el-table-column label="推荐软件版本模式" min-width="260" show-overflow-tooltip>
              <template #default="scope">
                {{ Array.isArray(scope.row['车机软件版本号']) ? scope.row['车机软件版本号'].join('，') : '—' }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="160" fixed="right">
              <template #default="scope">
                <el-button type="primary" size="small" link @click="openEditRule(scope.row)">编辑</el-button>
                <el-button type="primary" size="small" link @click="openCloneRule(scope.row)">复制</el-button>
                <el-button type="danger" size="small" link @click="removeRule(scope.row.rule_index)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <div class="table-pagination">
            <el-pagination
              background
              layout="total, prev, pager, next, sizes"
              :total="vehicleRulePagination.total"
              :current-page="vehicleRulePagination.page"
              :page-size="vehicleRulePagination.pageSize"
              :page-sizes="[10, 20, 50, 100]"
              @update:current-page="onVehicleRulePageChange"
              @update:page-size="onVehicleRulePageSizeChange"
            />
          </div>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="后端配置" name="credentials">
        <el-card shadow="never">
          <template #header>后端配置管理（爬虫登录账号等）</template>
          <el-form label-width="180px">
            <el-divider content-position="left">uat_mos_portal</el-divider>
            <el-form-item label="账号">
              <el-input v-model="credentialForm.uat_mos_portal_account" placeholder="请输入账号" />
            </el-form-item>
            <el-form-item label="密码">
              <el-input
                v-model="credentialForm.uat_mos_portal_password"
                placeholder="留空表示不修改；当前为掩码显示"
                show-password
              />
              <div class="hint">当前：{{ maskedCredentials.uat_mos_portal.password_masked || '未设置' }}</div>
            </el-form-item>

            <el-divider content-position="left">oa</el-divider>
            <el-form-item label="账号">
              <el-input v-model="credentialForm.oa_account" placeholder="请输入账号" />
            </el-form-item>
            <el-form-item label="密码">
              <el-input
                v-model="credentialForm.oa_password"
                placeholder="留空表示不修改；当前为掩码显示"
                show-password
              />
              <div class="hint">当前：{{ maskedCredentials.oa.password_masked || '未设置' }}</div>
            </el-form-item>

            <el-divider content-position="left">请求超时配置</el-divider>
            <el-form-item label="请求超时（秒）">
              <el-input-number
                v-model="credentialForm.request_timeout_seconds"
                :min="1"
                :max="600"
                :step="1"
                controls-position="right"
              />
              <div class="hint">
                当前生效：{{ maskedCredentials.runtime.request_timeout_seconds }} 秒（影响 MOS 工具箱后端请求超时）
              </div>
            </el-form-item>

            <el-form-item>
              <el-button @click="loadCredentials">重置</el-button>
              <el-button type="primary" :loading="savingCredentials" @click="saveCredentials">保存配置</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="变更记录" name="logs">
        <el-card shadow="never">
          <template #header>
            <div class="header-row">
              <span>配置变更记录</span>
              <el-button @click="loadChangeLogs">刷新</el-button>
            </div>
          </template>
          <el-table :data="changeLogs" v-loading="loadingChangeLogs" stripe>
            <el-table-column label="时间" width="180">
              <template #default="scope">{{ formatDate(scope.row.created_at) }}</template>
            </el-table-column>
            <el-table-column prop="changed_by_name" label="操作人" width="120" />
            <el-table-column prop="target" label="对象" width="180" />
            <el-table-column prop="action" label="动作" width="120" />
            <el-table-column prop="summary" label="说明" min-width="240" show-overflow-tooltip />
          </el-table>
          <div class="table-pagination">
            <el-pagination
              background
              layout="total, prev, pager, next, sizes"
              :total="changeLogPagination.total"
              :current-page="changeLogPagination.page"
              :page-size="changeLogPagination.pageSize"
              :page-sizes="[10, 20, 50, 100]"
              @update:current-page="onChangeLogPageChange"
              @update:page-size="onChangeLogPageSizeChange"
            />
          </div>
        </el-card>
      </el-tab-pane>

      <el-tab-pane v-if="false" label="公告与维护" name="announcement">
        <el-card shadow="never">
          <template #header>
            <div class="header-row">
              <span>公告发布与模块维护</span>
              <el-button @click="loadAnnouncements">刷新</el-button>
            </div>
          </template>
          <el-alert
            title="此处公告仅在当前工具内部可见（不会进入全站顶栏）。可设置优先级与滚动样式，并可临时禁用功能模块。"
            type="info"
            :closable="false"
            style="margin-bottom: 12px"
          />
          <el-form label-width="140px">
            <el-form-item label="公告标题">
              <el-input v-model="announcementForm.title" maxlength="200" show-word-limit placeholder="例如：UAT 环境维护通知" />
            </el-form-item>
            <el-form-item label="公告内容">
              <el-input
                v-model="announcementForm.content"
                type="textarea"
                :rows="4"
                maxlength="4000"
                show-word-limit
                placeholder="请输入面向用户的中文公告内容"
              />
            </el-form-item>
            <el-form-item label="优先级">
              <el-radio-group v-model="announcementForm.priority">
                <el-radio-button label="urgent">紧急维护</el-radio-button>
                <el-radio-button label="notice">通知</el-radio-button>
                <el-radio-button label="reminder">提醒</el-radio-button>
              </el-radio-group>
            </el-form-item>
            <el-form-item label="生效区间">
              <el-date-picker
                v-model="announcementRange"
                type="datetimerange"
                range-separator="至"
                start-placeholder="开始时间（可空）"
                end-placeholder="结束时间（可空）"
                value-format="YYYY-MM-DDTHH:mm:ss"
              />
            </el-form-item>
            <el-form-item label="滚动速度(秒)">
              <el-input-number v-model="announcementForm.scroll_speed_seconds" :min="10" :max="300" />
            </el-form-item>
            <el-form-item label="字体">
              <el-input v-model="announcementForm.font_family" placeholder="如 Microsoft YaHei, SimHei，可留空" />
            </el-form-item>
            <el-form-item label="字号(px)">
              <el-input-number v-model="announcementForm.font_size_px" :min="12" :max="32" />
            </el-form-item>
            <el-form-item label="文字颜色">
              <el-color-picker v-model="announcementForm.text_color" />
            </el-form-item>
            <el-form-item label="背景颜色">
              <el-color-picker v-model="announcementForm.background_color" />
            </el-form-item>
            <el-form-item label="禁用功能模块">
              <el-select
                v-model="announcementForm.disable_feature_slugs"
                multiple
                filterable
                clearable
                placeholder="可多选，留空表示仅公告不禁用"
                style="width: 100%"
              >
                <el-option
                  v-for="item in announcementFeatureOptions"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="启用状态">
              <el-switch v-model="announcementForm.is_enabled" active-text="启用" inactive-text="停用" />
            </el-form-item>
            <el-form-item>
              <el-button @click="resetAnnouncementForm">重置</el-button>
              <el-button type="primary" :loading="savingAnnouncement" @click="saveAnnouncement">
                {{ editingAnnouncementId === null ? '发布公告' : '保存编辑' }}
              </el-button>
            </el-form-item>
          </el-form>

          <el-table :data="announcements" v-loading="loadingAnnouncements" stripe>
            <el-table-column label="状态" width="100">
              <template #default="scope">
                <el-tag :type="scope.row.is_enabled ? 'success' : 'info'">
                  {{ scope.row.is_enabled ? '启用' : '停用' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="title" label="标题" min-width="180" show-overflow-tooltip />
            <el-table-column label="优先级" width="110">
              <template #default="scope">
                <el-tag :type="scope.row.priority === 'urgent' ? 'danger' : scope.row.priority === 'reminder' ? 'warning' : 'info'">
                  {{ scope.row.priority === 'urgent' ? '紧急维护' : scope.row.priority === 'reminder' ? '提醒' : '通知' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="content" label="内容" min-width="260" show-overflow-tooltip />
            <el-table-column label="样式" min-width="260" show-overflow-tooltip>
              <template #default="scope">
                速度 {{ scope.row.scroll_speed_seconds }}s / 字号 {{ scope.row.font_size_px }}px /
                字体 {{ scope.row.font_family || '默认' }} /
                文字 {{ scope.row.text_color || '默认' }} /
                背景 {{ scope.row.background_color || '默认' }}
              </template>
            </el-table-column>
            <el-table-column label="禁用模块" min-width="240" show-overflow-tooltip>
              <template #default="scope">{{ (scope.row.disable_feature_slugs || []).join('，') || '—' }}</template>
            </el-table-column>
            <el-table-column label="生效时间" width="320">
              <template #default="scope">
                {{ scope.row.start_at ? formatDate(scope.row.start_at) : '立即生效' }} 至
                {{ scope.row.end_at ? formatDate(scope.row.end_at) : '长期有效' }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="180" fixed="right">
              <template #default="scope">
                <el-button type="primary" link @click="editAnnouncement(scope.row)">编辑</el-button>
                <el-button type="primary" link @click="toggleAnnouncement(scope.row)">
                  {{ scope.row.is_enabled ? '停用' : '启用' }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>
          <div class="table-pagination">
            <el-pagination
              background
              layout="total, prev, pager, next, sizes"
              :total="announcementPagination.total"
              :current-page="announcementPagination.page"
              :page-size="announcementPagination.pageSize"
              :page-sizes="[10, 20, 50]"
              @update:current-page="onAnnouncementPageChange"
              @update:page-size="onAnnouncementPageSizeChange"
            />
          </div>
        </el-card>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="ruleDialogVisible" :title="editingRuleIndex === null ? '新增规则' : '编辑规则'" width="760px">
      <el-tabs v-model="ruleEditorMode">
        <el-tab-pane label="结构化编辑" name="structured">
          <el-form label-width="130px">
            <el-form-item label="项目版本号">
              <el-select
                v-model="ruleForm.project"
                filterable
                allow-create
                default-first-option
                clearable
                placeholder="请选择或输入项目版本号，例如 MOS3_GP"
                style="width: 100%"
              >
                <el-option v-for="project in knownProjects" :key="project" :label="project" :value="project" />
              </el-select>
            </el-form-item>
            <el-form-item label="车机软件版本号">
              <el-select
                v-model="versionPatternTags"
                multiple
                filterable
                allow-create
                default-first-option
                clearable
                placeholder="输入后回车，可添加多个，例如 01XX / C1XX"
                style="width: 100%"
              >
                <el-option
                  v-for="pattern in commonVersionPatterns"
                  :key="pattern"
                  :label="pattern"
                  :value="pattern"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="PRNR">
              <el-input
                v-model="ruleForm.prnr"
                type="textarea"
                :rows="3"
                placeholder="每行一条，例如 ~28DK~27UY~2EL8"
              />
              <div class="prnr-actions">
                <el-button text @click="normalizePrnrLines">规范化PRNR（去空行/去重）</el-button>
              </div>
            </el-form-item>
            <el-row :gutter="12">
              <el-col :span="12">
                <el-form-item label="OCU类型">
                  <el-select v-model="ruleForm.ocuType" filterable allow-create clearable style="width: 100%">
                    <el-option v-for="item in ocuTypeOptions" :key="item" :label="item" :value="item" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="品牌">
                  <el-select v-model="ruleForm.brand" clearable style="width: 100%">
                    <el-option v-for="item in brandOptions" :key="item" :label="item" :value="item" />
                  </el-select>
                </el-form-item>
              </el-col>
            </el-row>
            <el-row :gutter="12">
              <el-col :span="12">
                <el-form-item label="车机类型">
                  <el-select v-model="ruleForm.huType" filterable allow-create clearable style="width: 100%">
                    <el-option v-for="item in huTypeOptions" :key="item" :label="item" :value="item" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="燃油类型">
                  <el-select v-model="ruleForm.fuelType" clearable style="width: 100%">
                    <el-option v-for="item in fuelTypeOptions" :key="item" :label="item" :value="item" />
                  </el-select>
                </el-form-item>
              </el-col>
            </el-row>
            <el-row :gutter="12">
              <el-col :span="12">
                <el-form-item label="发电机号"><el-input v-model="ruleForm.generatorNo" /></el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="运营商">
                  <el-select v-model="ruleForm.operator" clearable style="width: 100%">
                    <el-option v-for="item in operatorOptions" :key="item" :label="item" :value="item" />
                  </el-select>
                </el-form-item>
              </el-col>
            </el-row>
            <el-row :gutter="12">
              <el-col :span="12">
                <el-form-item label="产线平台"><el-input v-model="ruleForm.plantPlatform" /></el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="HU零件号"><el-input v-model="ruleForm.huPartNo" /></el-form-item>
              </el-col>
            </el-row>
            <el-form-item label="OCU零件号"><el-input v-model="ruleForm.ocuPartNo" /></el-form-item>
            <el-alert
              title="建议使用结构化编辑，未填写字段会自动写入“空”。"
              type="info"
              :closable="false"
            />
          </el-form>
        </el-tab-pane>
        <el-tab-pane label="高级JSON" name="json">
          <el-input
            v-model="ruleDraft"
            type="textarea"
            :rows="16"
            placeholder="请输入单条规则 JSON（对象）"
          />
        </el-tab-pane>
      </el-tabs>
      <template #footer>
        <el-button @click="ruleDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingRule" @click="saveRule">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="bulkImportVisible" title="批量导入规则" width="900px">
      <el-alert
        title="请粘贴 JSON 数组，数组每一项为单条规则对象。建议先点“预校验”，确认通过后再导入。"
        type="info"
        :closable="false"
        style="margin-bottom: 12px"
      />
      <el-input
        v-model="bulkImportRaw"
        type="textarea"
        :rows="10"
        placeholder='示例：[{"项目版本号":"MOS3_GP",...}]'
      />
      <div class="bulk-actions">
        <el-button :loading="bulkValidating" @click="runBulkValidate">预校验</el-button>
        <el-button type="primary" :loading="bulkImporting" @click="runBulkImport">确认导入</el-button>
      </div>
      <div v-if="bulkPreview" class="bulk-preview">
        <div class="bulk-summary">
          总数：{{ bulkPreview.total || 0 }}，有效：{{ bulkPreview.valid_count || 0 }}，无效：{{ bulkPreview.invalid_count || 0 }}
        </div>
        <el-table :data="bulkPreview.items || []" stripe size="small" max-height="280">
          <el-table-column prop="index" label="#" width="60" />
          <el-table-column label="项目" min-width="180">
            <template #default="scope">{{ scope.row.project || '—' }}</template>
          </el-table-column>
          <el-table-column label="校验结果" width="100">
            <template #default="scope">
              <el-tag :type="scope.row.valid ? 'success' : 'danger'">{{ scope.row.valid ? '通过' : '失败' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="错误信息" min-width="320" show-overflow-tooltip>
            <template #default="scope">{{ (scope.row.errors || []).join('；') || '—' }}</template>
          </el-table-column>
        </el-table>
      </div>
      <template #footer>
        <el-button @click="bulkImportVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { toolsApi } from '@/api/tools'
import { formatDateTime as formatDate } from '@/utils/datetime'
import type { ToolAnnouncementInDB } from '@/api/types'

const props = defineProps<{ toolId: number }>()
const route = useRoute()
const router = useRouter()
const moduleTab = ref<'rules' | 'credentials' | 'logs' | 'announcement'>('rules')

const loadingRules = ref(false)
const savingRule = ref(false)
const ruleDialogVisible = ref(false)
const editingRuleIndex = ref<number | null>(null)
const ruleEditorMode = ref<'structured' | 'json'>('structured')
const ruleDraft = ref('')
const vehicleRules = ref<Array<Record<string, any>>>([])
const bulkImportVisible = ref(false)
const bulkImportRaw = ref('')
const bulkPreview = ref<{
  total?: number
  valid_count?: number
  invalid_count?: number
  has_errors?: boolean
  items?: Array<{ index: number; valid: boolean; project: string; errors: string[] }>
} | null>(null)
const bulkValidating = ref(false)
const bulkImporting = ref(false)
const loadingChangeLogs = ref(false)
const changeLogs = ref<Array<Record<string, any>>>([])
const ruleForm = reactive({
  project: '',
  prnr: '',
  ocuType: '',
  brand: '',
  huType: '',
  fuelType: '',
  generatorNo: '',
  operator: '',
  plantPlatform: '',
  huPartNo: '',
  ocuPartNo: ''
})
const versionPatternTags = ref<string[]>([])
const brandOptions = ['VW', 'AUDI']
const fuelTypeOptions = ['FV', 'PHEV', 'BEV', 'EREV']
const operatorOptions = ['CMCC', 'CUSC', 'CTCC']
const ocuTypeOptions = ['LOW', 'HIGH', 'OCB', 'Conmod5G', 'PNS', 'OCU4', 'Conbox', 'Conmod', 'IAM', 'CDCU']
const huTypeOptions = ['CNS2.0', 'CRS3.0', 'CNS3.0', 'SOC', 'PNS', 'ICAS3', 'MIB3', 'HCP3', 'ZXD', 'ICC', 'CDCU']
const commonVersionPatterns = [
  '0138', '0135', '00XX', '01XX', '02XX', '03XX', '04XX', '05XX', '06XX', '07XX', '08XX', '09XX',
  'C1XX', 'C2XX', 'C3XX', 'C4XX', 'C5XX', 'C6XX', 'C7XX', 'C8XX', 'C9XX', '0XXX', '1XXX'
]
const knownProjects = ref<string[]>([])
const vehicleRulePagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

const savingCredentials = ref(false)
const maskedCredentials = reactive({
  uat_mos_portal: { account: '', password_masked: '' },
  oa: { account: '', password_masked: '' },
  runtime: { request_timeout_seconds: 30 }
})
const credentialForm = reactive({
  uat_mos_portal_account: '',
  uat_mos_portal_password: '',
  oa_account: '',
  oa_password: '',
  request_timeout_seconds: 30
})
const changeLogPagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})
const loadingAnnouncements = ref(false)
const savingAnnouncement = ref(false)
const announcements = ref<ToolAnnouncementInDB[]>([])
const announcementRange = ref<[string, string] | null>(null)
const editingAnnouncementId = ref<number | null>(null)
const announcementForm = reactive({
  title: '',
  content: '',
  is_enabled: true,
  priority: 'notice' as 'urgent' | 'notice' | 'reminder',
  scroll_speed_seconds: 45,
  font_family: '',
  font_size_px: 14,
  text_color: '#102a43',
  background_color: '#e8f4fd',
  disable_feature_slugs: [] as string[]
})
const announcementPagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})
const announcementFeatureOptions: Array<{ label: string; value: string }> = [
  { label: 'IAM X509', value: 'x509-cert' },
  { label: 'Token 预热', value: 'token-preload' },
  { label: 'SIM 查询', value: 'sim-query' },
  { label: 'UAT AF DP 查询', value: 'uat-af-dp-query' },
  { label: 'UAT Enrollment', value: 'uat-sp-query' },
  { label: 'UAT 车辆配置导入', value: 'uat-vehicle-import' }
]

const toPositiveInt = (value: unknown, fallback: number): number => {
  const n = Number(value)
  return Number.isInteger(n) && n > 0 ? n : fallback
}

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
  void router.replace({ query: nextQuery })
}

const getErrorMessage = (error: any, fallback: string) => {
  return error?.response?.data?.detail || error?.message || fallback
}

const toPickerDateTime = (value?: string | null): string | null => {
  if (!value) return null
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return null
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

const loadVehicleRules = async () => {
  loadingRules.value = true
  try {
    const res = await toolsApi.listMosVehicleRules(props.toolId, {
      skip: (vehicleRulePagination.page - 1) * vehicleRulePagination.pageSize,
      limit: vehicleRulePagination.pageSize
    })
    vehicleRules.value = res?.data?.items || []
    vehicleRulePagination.total = Number(res?.data?.total || 0)
    knownProjects.value = Array.from(
      new Set(
        vehicleRules.value
          .map((row) => String(row['项目版本号'] || '').trim())
          .filter(Boolean)
      )
    ).sort((a, b) => a.localeCompare(b))
  } catch (error: any) {
    ElMessage.error(getErrorMessage(error, '加载规则失败'))
  } finally {
    loadingRules.value = false
  }
}

const resetRuleForm = () => {
  ruleForm.project = ''
  ruleForm.prnr = ''
  ruleForm.ocuType = ''
  ruleForm.brand = ''
  ruleForm.huType = ''
  ruleForm.fuelType = ''
  ruleForm.generatorNo = '空'
  ruleForm.operator = ''
  ruleForm.plantPlatform = ''
  ruleForm.huPartNo = '空'
  ruleForm.ocuPartNo = '空'
  versionPatternTags.value = []
}

const mapRuleToForm = (rule: Record<string, any>) => {
  ruleForm.project = String(rule['项目版本号'] || '')
  versionPatternTags.value = Array.isArray(rule['车机软件版本号'])
    ? rule['车机软件版本号'].map((item: unknown) => String(item || '').trim().toUpperCase()).filter(Boolean)
    : []
  ruleForm.prnr = String(rule['PRNR'] || '')
  ruleForm.ocuType = String(rule['OCU类型'] || '')
  ruleForm.brand = String(rule['品牌'] || '')
  ruleForm.huType = String(rule['车机类型'] || '')
  ruleForm.fuelType = String(rule['燃油类型'] || '')
  ruleForm.generatorNo = String(rule['发电机号'] || '空')
  ruleForm.operator = String(rule['运营商'] || '')
  ruleForm.plantPlatform = String(rule['产线平台'] || '')
  ruleForm.huPartNo = String(rule['HU零件号'] || '空')
  ruleForm.ocuPartNo = String(rule['OCU零件号'] || '空')
}

const buildRuleFromForm = (): Record<string, any> => {
  const versionPatterns = versionPatternTags.value
    .map((item: string) => item.trim().toUpperCase())
    .filter(Boolean)
  if (!ruleForm.project.trim()) {
    throw new Error('项目版本号不能为空')
  }
  if (!versionPatterns.length) {
    throw new Error('车机软件版本号至少填写一个模式')
  }
  return {
    项目版本号: ruleForm.project.trim(),
    OCU类型: ruleForm.ocuType.trim(),
    品牌: ruleForm.brand.trim(),
    车机类型: ruleForm.huType.trim(),
    燃油类型: ruleForm.fuelType.trim(),
    车机软件版本号: versionPatterns,
    PRNR: ruleForm.prnr.trim(),
    发电机号: ruleForm.generatorNo.trim() || '空',
    运营商: ruleForm.operator.trim(),
    产线平台: ruleForm.plantPlatform.trim(),
    HU零件号: ruleForm.huPartNo.trim() || '空',
    OCU零件号: ruleForm.ocuPartNo.trim() || '空'
  }
}

const normalizePrnrLines = () => {
  const unique = Array.from(
    new Set(
      ruleForm.prnr
        .split('\n')
        .map((line) => line.trim())
        .filter(Boolean)
    )
  )
  ruleForm.prnr = unique.join('\n')
}

const openCreateRule = () => {
  editingRuleIndex.value = null
  ruleEditorMode.value = 'structured'
  resetRuleForm()
  ruleDraft.value = JSON.stringify(
    {
      项目版本号: '',
      OCU类型: '',
      品牌: '',
      车机类型: '',
      燃油类型: '',
      车机软件版本号: [],
      PRNR: '',
      发电机号: '空',
      运营商: '',
      产线平台: '',
      HU零件号: '空',
      OCU零件号: '空'
    },
    null,
    2
  )
  ruleDialogVisible.value = true
}

const openEditRule = (row: Record<string, any>) => {
  editingRuleIndex.value = Number(row.rule_index)
  const next = { ...row }
  delete next.rule_index
  ruleDraft.value = JSON.stringify(next, null, 2)
  mapRuleToForm(next)
  ruleEditorMode.value = 'structured'
  ruleDialogVisible.value = true
}

const openCloneRule = (row: Record<string, any>) => {
  editingRuleIndex.value = null
  const next = { ...row }
  delete next.rule_index
  mapRuleToForm(next)
  // 引导用户创建新项目或派生项目
  if (ruleForm.project.trim()) {
    ruleForm.project = `${ruleForm.project.trim()}_COPY`
  }
  ruleDraft.value = JSON.stringify(next, null, 2)
  ruleEditorMode.value = 'structured'
  ruleDialogVisible.value = true
}

const openBulkImportDialog = () => {
  bulkImportVisible.value = true
  bulkPreview.value = null
}

const parseBulkRules = (): Array<Record<string, any>> => {
  let parsed: unknown
  try {
    parsed = JSON.parse(bulkImportRaw.value)
  } catch {
    throw new Error('JSON 解析失败，请检查格式')
  }
  if (!Array.isArray(parsed)) {
    throw new Error('内容必须是 JSON 数组')
  }
  return parsed as Array<Record<string, any>>
}

const runBulkValidate = async () => {
  let rules: Array<Record<string, any>>
  try {
    rules = parseBulkRules()
  } catch (error: any) {
    ElMessage.error(error?.message || '解析失败')
    return
  }
  bulkValidating.value = true
  try {
    const res = await toolsApi.bulkImportMosVehicleRules(props.toolId, {
      rules,
      dry_run: true
    })
    bulkPreview.value = {
      total: res.data.total,
      valid_count: res.data.valid_count,
      invalid_count: res.data.invalid_count,
      has_errors: res.data.has_errors,
      items: res.data.items
    }
    ElMessage.success('预校验完成')
  } catch (error: any) {
    ElMessage.error(getErrorMessage(error, '预校验失败'))
  } finally {
    bulkValidating.value = false
  }
}

const runBulkImport = async () => {
  let rules: Array<Record<string, any>>
  try {
    rules = parseBulkRules()
  } catch (error: any) {
    ElMessage.error(error?.message || '解析失败')
    return
  }
  bulkImporting.value = true
  try {
    const res = await toolsApi.bulkImportMosVehicleRules(props.toolId, {
      rules,
      dry_run: false
    })
    ElMessage.success(`已导入 ${res.data.imported_count || 0} 条规则`)
    await loadVehicleRules()
    await loadChangeLogs()
    bulkImportVisible.value = false
  } catch (error: any) {
    ElMessage.error(getErrorMessage(error, '批量导入失败，请先预校验'))
  } finally {
    bulkImporting.value = false
  }
}

const saveRule = async () => {
  let parsed: Record<string, any>
  if (ruleEditorMode.value === 'structured') {
    try {
      parsed = buildRuleFromForm()
      ruleDraft.value = JSON.stringify(parsed, null, 2)
    } catch (error: any) {
      ElMessage.error(error?.message || '结构化规则校验失败')
      return
    }
  } else {
    try {
      parsed = JSON.parse(ruleDraft.value)
      if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
        throw new Error('规则必须是 JSON 对象')
      }
      mapRuleToForm(parsed)
    } catch (error: any) {
      ElMessage.error(error?.message || 'JSON 格式错误')
      return
    }
  }

  savingRule.value = true
  try {
    if (editingRuleIndex.value === null) {
      await toolsApi.createMosVehicleRule(props.toolId, parsed)
    } else {
      await toolsApi.updateMosVehicleRule(props.toolId, editingRuleIndex.value, parsed)
    }
    ElMessage.success('规则已保存')
    ruleDialogVisible.value = false
    await loadVehicleRules()
    await loadChangeLogs()
  } catch (error: any) {
    ElMessage.error(getErrorMessage(error, '保存规则失败'))
  } finally {
    savingRule.value = false
  }
}

const removeRule = async (ruleIndex: number) => {
  try {
    await ElMessageBox.confirm('确定删除这条规则？', '提示', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消'
    })
  } catch {
    return
  }
  try {
    await toolsApi.deleteMosVehicleRule(props.toolId, ruleIndex)
    ElMessage.success('规则已删除')
    await loadVehicleRules()
    await loadChangeLogs()
  } catch (error: any) {
    ElMessage.error(getErrorMessage(error, '删除规则失败'))
  }
}

const loadCredentials = async () => {
  try {
    const res = await toolsApi.getMosRuntimeCredentials(props.toolId)
    maskedCredentials.uat_mos_portal.account = res.data.uat_mos_portal.account || ''
    maskedCredentials.uat_mos_portal.password_masked = res.data.uat_mos_portal.password_masked || ''
    maskedCredentials.oa.account = res.data.oa.account || ''
    maskedCredentials.oa.password_masked = res.data.oa.password_masked || ''
    maskedCredentials.runtime.request_timeout_seconds = Number(res.data.runtime?.request_timeout_seconds || 30)
    credentialForm.uat_mos_portal_account = maskedCredentials.uat_mos_portal.account
    credentialForm.uat_mos_portal_password = ''
    credentialForm.oa_account = maskedCredentials.oa.account
    credentialForm.oa_password = ''
    credentialForm.request_timeout_seconds = maskedCredentials.runtime.request_timeout_seconds
  } catch (error: any) {
    ElMessage.error(getErrorMessage(error, '加载后端配置失败'))
  }
}

const loadChangeLogs = async () => {
  loadingChangeLogs.value = true
  try {
    const res = await toolsApi.listMosManageChangeLogs(props.toolId, {
      skip: (changeLogPagination.page - 1) * changeLogPagination.pageSize,
      limit: changeLogPagination.pageSize
    })
    changeLogs.value = res?.data?.items || []
    changeLogPagination.total = Number(res?.data?.total || 0)
  } catch (error: any) {
    ElMessage.error(getErrorMessage(error, '加载变更记录失败'))
  } finally {
    loadingChangeLogs.value = false
  }
}

const loadAnnouncements = async () => {
  loadingAnnouncements.value = true
  try {
    const res = await toolsApi.listMosManageAnnouncements(props.toolId, {
      skip: (announcementPagination.page - 1) * announcementPagination.pageSize,
      limit: announcementPagination.pageSize
    })
    announcements.value = res.items || []
    announcementPagination.total = Number(res.total || 0)
  } catch (error: any) {
    ElMessage.error(getErrorMessage(error, '加载公告失败'))
  } finally {
    loadingAnnouncements.value = false
  }
}

const resetAnnouncementForm = () => {
  editingAnnouncementId.value = null
  announcementForm.title = ''
  announcementForm.content = ''
  announcementForm.is_enabled = true
  announcementForm.priority = 'notice'
  announcementForm.scroll_speed_seconds = 45
  announcementForm.font_family = ''
  announcementForm.font_size_px = 14
  announcementForm.text_color = '#102a43'
  announcementForm.background_color = '#e8f4fd'
  announcementForm.disable_feature_slugs = []
  announcementRange.value = null
}

const editAnnouncement = (row: ToolAnnouncementInDB) => {
  editingAnnouncementId.value = row.id
  announcementForm.title = row.title || ''
  announcementForm.content = row.content || ''
  announcementForm.is_enabled = row.is_enabled
  announcementForm.priority = row.priority || 'notice'
  announcementForm.scroll_speed_seconds = Number(row.scroll_speed_seconds || 45)
  announcementForm.font_family = row.font_family || ''
  announcementForm.font_size_px = Number(row.font_size_px || 14)
  announcementForm.text_color = row.text_color || '#102a43'
  announcementForm.background_color = row.background_color || '#e8f4fd'
  announcementForm.disable_feature_slugs = [...(row.disable_feature_slugs || [])]
  const start = toPickerDateTime(row.start_at)
  const end = toPickerDateTime(row.end_at)
  announcementRange.value = start && end ? [start, end] : null
}

const saveAnnouncement = async () => {
  const title = announcementForm.title.trim()
  const content = announcementForm.content.trim()
  if (!title || !content) {
    ElMessage.warning('请填写公告标题和内容')
    return
  }
  savingAnnouncement.value = true
  try {
    const payload = {
      title,
      content,
      is_enabled: announcementForm.is_enabled,
      priority: announcementForm.priority,
      scroll_speed_seconds: announcementForm.scroll_speed_seconds,
      font_family: announcementForm.font_family?.trim() || null,
      font_size_px: announcementForm.font_size_px,
      text_color: announcementForm.text_color || null,
      background_color: announcementForm.background_color || null,
      start_at: announcementRange.value?.[0] || null,
      end_at: announcementRange.value?.[1] || null,
      disable_feature_slugs: announcementForm.disable_feature_slugs
    }
    if (editingAnnouncementId.value === null) {
      await toolsApi.createMosManageAnnouncement(props.toolId, payload)
      ElMessage.success('公告发布成功')
    } else {
      await toolsApi.updateMosManageAnnouncement(props.toolId, editingAnnouncementId.value, payload)
      ElMessage.success('公告更新成功')
    }
    resetAnnouncementForm()
    announcementPagination.page = 1
    await loadAnnouncements()
    await loadChangeLogs()
  } catch (error: any) {
    ElMessage.error(getErrorMessage(error, '发布公告失败'))
  } finally {
    savingAnnouncement.value = false
  }
}

const toggleAnnouncement = async (row: ToolAnnouncementInDB) => {
  try {
    await toolsApi.updateMosManageAnnouncement(props.toolId, row.id, {
      is_enabled: !row.is_enabled
    })
    ElMessage.success(!row.is_enabled ? '公告已启用' : '公告已停用')
    await loadAnnouncements()
    await loadChangeLogs()
  } catch (error: any) {
    ElMessage.error(getErrorMessage(error, '更新公告状态失败'))
  }
}

const onVehicleRulePageChange = async (page: number) => {
  vehicleRulePagination.page = page
  updateQuery({ mosRulePage: String(page) })
  await loadVehicleRules()
}

const onVehicleRulePageSizeChange = async (size: number) => {
  vehicleRulePagination.pageSize = size
  vehicleRulePagination.page = 1
  updateQuery({ mosRulePageSize: String(size), mosRulePage: '1' })
  await loadVehicleRules()
}

const onChangeLogPageChange = async (page: number) => {
  changeLogPagination.page = page
  updateQuery({ mosLogPage: String(page) })
  await loadChangeLogs()
}

const onChangeLogPageSizeChange = async (size: number) => {
  changeLogPagination.pageSize = size
  changeLogPagination.page = 1
  updateQuery({ mosLogPageSize: String(size), mosLogPage: '1' })
  await loadChangeLogs()
}

const onAnnouncementPageChange = async (page: number) => {
  announcementPagination.page = page
  updateQuery({ mosAnnouncementPage: String(page) })
  await loadAnnouncements()
}

const onAnnouncementPageSizeChange = async (size: number) => {
  announcementPagination.pageSize = size
  announcementPagination.page = 1
  updateQuery({ mosAnnouncementPageSize: String(size), mosAnnouncementPage: '1' })
  await loadAnnouncements()
}

const saveCredentials = async () => {
  savingCredentials.value = true
  try {
    await toolsApi.updateMosRuntimeCredentials(props.toolId, {
      uat_mos_portal_account: credentialForm.uat_mos_portal_account,
      uat_mos_portal_password: credentialForm.uat_mos_portal_password || undefined,
      oa_account: credentialForm.oa_account,
      oa_password: credentialForm.oa_password || undefined,
      request_timeout_seconds: credentialForm.request_timeout_seconds,
    })
    ElMessage.success('后端配置已更新')
    await loadCredentials()
    await loadChangeLogs()
  } catch (error: any) {
    ElMessage.error(getErrorMessage(error, '更新后端配置失败'))
  } finally {
    savingCredentials.value = false
  }
}

onMounted(async () => {
  const q = route.query
  const tab = queryFirst(q.mosManageTab)
  moduleTab.value = tab === 'credentials' || tab === 'logs' || tab === 'announcement' ? tab : 'rules'
  vehicleRulePagination.page = toPositiveInt(queryFirst(q.mosRulePage), 1)
  vehicleRulePagination.pageSize = toPositiveInt(queryFirst(q.mosRulePageSize), 20)
  changeLogPagination.page = toPositiveInt(queryFirst(q.mosLogPage), 1)
  changeLogPagination.pageSize = toPositiveInt(queryFirst(q.mosLogPageSize), 20)
  announcementPagination.page = toPositiveInt(queryFirst(q.mosAnnouncementPage), 1)
  announcementPagination.pageSize = toPositiveInt(queryFirst(q.mosAnnouncementPageSize), 20)

  await loadVehicleRules()
  await loadCredentials()
  await loadChangeLogs()
  await loadAnnouncements()
})

const onModuleTabChange = (value: string) => {
  if (value !== 'rules' && value !== 'credentials' && value !== 'logs' && value !== 'announcement') return
  moduleTab.value = value
  updateQuery({ mosManageTab: value })
}
</script>

<style scoped>
.mos-manage-tab {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.manage-module-tabs {
  width: 100%;
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

.hint {
  margin-top: 6px;
  font-size: 12px;
  color: #909399;
}

.prnr-actions {
  margin-top: 6px;
}

.bulk-actions {
  margin-top: 12px;
  display: flex;
  gap: 8px;
}

.bulk-preview {
  margin-top: 12px;
}

.bulk-summary {
  margin-bottom: 8px;
  color: #606266;
}

.table-pagination {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}
</style>
