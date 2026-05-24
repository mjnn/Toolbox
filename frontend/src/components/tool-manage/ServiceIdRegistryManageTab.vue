<template>
  <div class="service-id-manage-tab">
    <el-tabs v-model="moduleTab" class="manage-module-tabs">
      <el-tab-pane label="条目治理" name="entries">
        <el-card shadow="never">
          <template #header>
            <div class="header-row">
              <span>全量服务 ID 管理</span>
              <el-button type="primary" @click="exportCsv">导出 CSV</el-button>
            </div>
          </template>
          <div v-if="canManageAll" v-loading="loadingExportConfig" class="export-csv-config">
            <div class="export-csv-config-head">
              <span class="export-csv-config-title">CSV 导出列</span>
              <div class="export-csv-config-actions">
                <el-select
                  v-model="exportColumnToAdd"
                  placeholder="添加列…"
                  filterable
                  clearable
                  style="width: 240px"
                  @change="onAddExportColumn"
                >
                  <el-option
                    v-for="opt in exportAddCandidates"
                    :key="opt.key"
                    :label="`${opt.default_header} [${opt.key}]`"
                    :value="opt.key"
                  />
                </el-select>
                <el-button :disabled="savingExportConfig || loadingExportConfig" @click="resetExportConfig">
                  恢复默认
                </el-button>
                <el-button
                  type="primary"
                  :loading="savingExportConfig"
                  :disabled="loadingExportConfig || exportColumnsDraft.length === 0"
                  @click="saveExportConfig"
                >
                  保存导出配置
                </el-button>
              </div>
            </div>
            <p class="section-hint export-csv-hint">
              列表自上而下对应 CSV 从左到右的列顺序；表头可按需修改，导出时使用此处文案。自定义字段以 <code>extra__</code> 前缀标识。
            </p>
            <el-table
              v-if="exportColumnsDraft.length"
              :data="exportColumnsDraft"
              border
              size="small"
              class="export-csv-table"
              row-key="key"
            >
              <el-table-column type="index" label="#" width="48" />
              <el-table-column prop="key" label="字段" min-width="200" />
              <el-table-column label="CSV 表头" min-width="260">
                <template #default="scope">
                  <el-input v-model="scope.row.header" maxlength="200" show-word-limit />
                </template>
              </el-table-column>
              <el-table-column label="顺序" width="148" fixed="right">
                <template #default="scope">
                  <el-button
                    link
                    type="primary"
                    :disabled="scope.$index === 0"
                    @click="moveExportColumnUp(scope.$index)"
                  >上移</el-button>
                  <el-button
                    link
                    type="primary"
                    :disabled="scope.$index === exportColumnsDraft.length - 1"
                    @click="moveExportColumnDown(scope.$index)"
                  >下移</el-button>
                  <el-button link type="danger" @click="removeExportColumn(scope.$index)">移除</el-button>
                </template>
              </el-table-column>
            </el-table>
            <el-empty v-else description="请至少保留一列，或点击「恢复默认」" :image-size="56" />
          </div>
          <div class="table-scroll">
            <el-table :data="entries" v-loading="loadingEntries" stripe>
              <el-table-column prop="service_id" label="服务 ID（Service ID）" min-width="180" />
              <el-table-column prop="business_function" label="业务功能" width="120" />
              <el-table-column prop="service_type" label="服务类型（ServiceType）" width="160" />
              <el-table-column prop="scope_type" label="范围（Scope）" width="140" />
              <el-table-column prop="apn_type" label="网络类型（APN）" width="160" />
              <el-table-column prop="updated_by_name" label="更改人" width="120" />
              <el-table-column label="更新时间" width="180">
                <template #default="scope">{{ formatDate(scope.row.updated_at) }}</template>
              </el-table-column>
              <el-table-column label="操作" width="140" fixed="right">
                <template #default="scope">
                  <el-button type="primary" size="small" link @click="openEdit(scope.row)">编辑</el-button>
                  <el-button type="danger" size="small" link @click="removeEntry(scope.row.id)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
          <div class="table-pagination">
            <el-pagination
              v-model:current-page="entriesPage"
              v-model:page-size="entriesPageSize"
              :total="entriesTotal"
              :page-sizes="[10, 20, 50, 100]"
              layout="total, sizes, prev, pager, next, jumper"
              @current-change="onEntriesPageChange"
              @size-change="onEntriesPageSizeChange"
            />
          </div>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="字段配置" name="fields">
        <el-card shadow="never">
          <template #header>
            <div class="header-row">
              <span>字段填写说明与限制</span>
              <el-button type="primary" @click="openCreateField">新增字段</el-button>
            </div>
          </template>
          <p class="section-hint">
            可配置字段悬停说明，以及 required / 长度 / 正则；文本类字段可设逗号分隔允许值。单选、多选通过「配置选项」维护选项列表。
            服务类型 / PSGA / 范围 / 网络类型 四个内置字段的选项在弹窗中走「规则库」维护（与用户填写页下拉一致）。
            录入页字段顺序与导出列顺序均与下表自上而下一致，可在「顺序」列用「上移 / 下移」调整，说明见表下灰色提示。
          </p>
          <field-config-manager-table
            :rows="fieldConfigs"
            :loading="loadingFieldConfigs"
            :saving="savingFieldConfigs"
            :input-type-options="fieldInputTypeOptions"
            :lock-builtin-sort-reorder="false"
            @save="saveFieldConfigs"
            @refresh="loadFieldConfigs"
            @delete="(row) => removeFieldConfig(row.field_key, row.label, row.is_builtin)"
          >
            <template #selectOptionsEditor="{ row }">
              <template v-if="serviceIdRuleCategory(row.field_key)">
                <service-id-rule-category-editor
                  :key="`${row.field_key}-${serviceIdRuleCategory(row.field_key)}`"
                  :tool-id="props.toolId"
                  :category="serviceIdRuleCategory(row.field_key)!"
                  @changed="onServiceIdRuleOptionsChanged"
                />
              </template>
              <select-option-values-editor v-else v-model:text="row.allowed_values_text" />
            </template>
          </field-config-manager-table>
        </el-card>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="editingVisible" title="编辑服务 ID" width="860px">
      <el-form label-position="top">
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="业务功能">
              <el-input v-model="form.business_function" maxlength="20" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="业务功能描述">
              <el-input v-model="form.business_description" maxlength="50" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="服务 ID（Service ID）">
              <el-input v-model="form.service_id" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="包名（PackageName）">
              <el-input v-model="form.package_name" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="服务类型（ServiceType）">
              <el-select v-model="form.service_type" style="width: 100%">
                <el-option v-for="item in options.service_type" :key="item.id" :label="item.value" :value="item.value" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="可用域（PSGA，单选）">
              <el-select v-model="form.psga_availability" style="width: 100%">
                <el-option v-for="item in options.psga" :key="item.id" :label="item.value" :value="item.value" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="范围（Scope）">
              <el-select v-model="form.scope_type" style="width: 100%">
                <el-option v-for="item in options.scope_type" :key="item.id" :label="item.value" :value="item.value" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="网络类型（APN）">
              <el-select v-model="form.apn_type" style="width: 100%">
                <el-option v-for="item in options.apn_type" :key="item.id" :label="item.value" :value="item.value" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="访问链路说明">
          <el-input v-model="form.access_link_desc" maxlength="20" />
        </el-form-item>
        <dynamic-field-inputs
          :fields="customFieldConfigs"
          :model-value="(form.extra_fields || {}) as DynamicFormValues"
          @update:model-value="(value) => { form.extra_fields = value }"
        />
        <el-form-item label="Base URL 填写方式">
          <el-radio-group v-model="form.base_url_mode">
            <el-radio label="string">字符串</el-radio>
            <el-radio label="json">JSON</el-radio>
          </el-radio-group>
        </el-form-item>
        <div v-if="form.base_url_mode === 'json'" class="json-mode-block">
          <div class="json-mode-header">
            <span>JSON 行配置（key + Test/UAT/Live）</span>
            <el-button type="primary" link @click="addJsonRow">新增一行</el-button>
          </div>
          <div
            v-for="(row, idx) in jsonRows"
            :key="`manage-json-row-${idx}`"
            class="json-row"
          >
            <el-row :gutter="12">
              <el-col :span="6">
                <el-form-item label="Key（仅英文）">
                  <el-input v-model="row.key" />
                </el-form-item>
              </el-col>
              <el-col :span="6">
                <el-form-item label="测试（Test）">
                  <el-input v-model="row.test" />
                </el-form-item>
              </el-col>
              <el-col :span="6">
                <el-form-item label="预发（UAT）">
                  <el-input v-model="row.uat" />
                </el-form-item>
              </el-col>
              <el-col :span="6">
                <el-form-item label="生产（Live）">
                  <el-input v-model="row.live" />
                </el-form-item>
              </el-col>
            </el-row>
            <div class="json-row-actions">
              <el-button type="danger" link :disabled="jsonRows.length <= 1" @click="removeJsonRow(idx)">删除本行</el-button>
            </div>
          </div>
        </div>
        <el-row v-else :gutter="12">
          <el-col :span="8">
            <el-form-item label="测试（Test）"><el-input v-model="form.base_url_test_input" /></el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="预发（UAT）"><el-input v-model="form.base_url_uat_input" /></el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="生产（Live）"><el-input v-model="form.base_url_live_input" /></el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="editingVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingEntry" @click="saveEntry">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="createFieldVisible" title="新增字段" width="520px">
      <el-form label-position="top">
        <el-form-item label="字段 key（仅小写字母、数字、下划线）">
          <el-input v-model="newField.field_key" placeholder="例如: biz_owner_email" />
        </el-form-item>
        <el-form-item label="字段名称">
          <el-input v-model="newField.label" placeholder="例如: 业务负责人邮箱" />
        </el-form-item>
        <el-form-item label="展示形式">
          <el-select v-model="newField.input_type" style="width: 100%">
            <el-option
              v-for="item in fieldInputTypeOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createFieldVisible = false">取消</el-button>
        <el-button type="primary" :loading="creatingField" @click="createField">新增</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import { toolsApi } from '@/api/tools'
import { formatDateTime as formatDate } from '@/utils/datetime'
import DynamicFieldInputs from '@/components/form-config/DynamicFieldInputs.vue'
import FieldConfigManagerTable from '@/components/form-config/FieldConfigManagerTable.vue'
import SelectOptionValuesEditor from '@/components/form-config/SelectOptionValuesEditor.vue'
import ServiceIdRuleCategoryEditor from '@/components/tool-manage/ServiceIdRuleCategoryEditor.vue'
import type {
  DynamicFormValues,
  FormFieldConfigItem,
  FormFieldInputType,
  ServiceBaseUrlJsonRowPayload,
  ServiceIdEntry,
  ServiceIdEntryPayload,
  ServiceIdExportColumnItem,
  ServiceIdExportColumnOption,
  ServiceIdRuleOptionGroup,
  ServiceRuleCategory
} from '@/api/types'

const props = defineProps<{ toolId: number }>()
const route = useRoute()
const router = useRouter()

const loadingEntries = ref(false)
const canManageAll = ref(false)
const loadingExportConfig = ref(false)
const savingExportConfig = ref(false)
const exportOptions = ref<ServiceIdExportColumnOption[]>([])
const exportColumnsDraft = ref<ServiceIdExportColumnItem[]>([])
const exportColumnToAdd = ref<string | undefined>(undefined)
const loadingFieldConfigs = ref(false)
const savingEntry = ref(false)
const savingFieldConfigs = ref(false)
const entries = ref<ServiceIdEntry[]>([])
const entriesTotal = ref(0)
const entriesPage = ref(1)
const entriesPageSize = ref(20)
const options = ref<ServiceIdRuleOptionGroup>({
  service_type: [],
  psga: [],
  scope_type: [],
  apn_type: []
})
const editingVisible = ref(false)
const editingId = ref<number | null>(null)
const moduleTab = ref<'entries' | 'fields'>('entries')
const fieldConfigs = ref<Array<FormFieldConfigItem & { allowed_values_text: string }>>([])
const customFieldConfigs = computed(() => fieldConfigs.value.filter((item) => !item.is_builtin))

const exportKeysInDraft = computed(() => new Set(exportColumnsDraft.value.map((c) => c.key)))
const exportAddCandidates = computed(() =>
  exportOptions.value.filter((o) => !exportKeysInDraft.value.has(o.key))
)
const creatingField = ref(false)
const createFieldVisible = ref(false)
const newField = reactive<{
  field_key: string
  label: string
  input_type: FormFieldInputType
}>({
  field_key: '',
  label: '',
  input_type: 'text'
})
const fieldInputTypeOptions: Array<{ label: string; value: FormFieldInputType }> = [
  { label: '填空', value: 'text' },
  { label: '长文本', value: 'textarea' },
  { label: '单选', value: 'single_select' },
  { label: '多选', value: 'multi_select' }
]

/** 内置字段与规则库类别的对应（选项在字段配置弹窗中维护，不再单独「规则治理」Tab） */
const SERVICE_ID_RULE_FIELD_MAP: Partial<Record<string, ServiceRuleCategory>> = {
  service_type: 'service_type',
  psga_availability: 'psga',
  scope_type: 'scope_type',
  apn_type: 'apn_type'
}

const serviceIdRuleCategory = (fieldKey: string): ServiceRuleCategory | undefined =>
  SERVICE_ID_RULE_FIELD_MAP[fieldKey]

const onServiceIdRuleOptionsChanged = async () => {
  await loadRules()
}

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
  router.replace({ query: nextQuery })
}

const form = reactive<ServiceIdEntryPayload>({
  business_function: '',
  business_description: '',
  service_id: '',
  service_type: '',
  psga_availability: '',
  package_name: '',
  scope_type: '',
  apn_type: '',
  access_link_desc: '',
  base_url_mode: 'string',
  base_url_json_key: '',
  base_url_test_input: '',
  base_url_uat_input: '',
  base_url_live_input: '',
  extra_fields: {}
})
const createEmptyJsonRow = (): ServiceBaseUrlJsonRowPayload => ({ key: '', test: '', uat: '', live: '' })
const jsonRows = ref<ServiceBaseUrlJsonRowPayload[]>([createEmptyJsonRow()])

const addJsonRow = () => {
  jsonRows.value.push(createEmptyJsonRow())
}

const removeJsonRow = (idx: number) => {
  if (jsonRows.value.length <= 1) return
  jsonRows.value.splice(idx, 1)
}

const parseJsonObject = (text: string): Record<string, string> | null => {
  try {
    const parsed = JSON.parse(text)
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return null
    const next: Record<string, string> = {}
    for (const [key, value] of Object.entries(parsed as Record<string, unknown>)) {
      if (typeof value !== 'string') return null
      next[key] = value
    }
    return next
  } catch {
    return null
  }
}

const buildJsonRowsFromEntry = (item: ServiceIdEntry): ServiceBaseUrlJsonRowPayload[] => {
  const testMap = parseJsonObject(item.base_url_test)
  const uatMap = parseJsonObject(item.base_url_uat)
  const liveMap = parseJsonObject(item.base_url_live)
  if (testMap && uatMap && liveMap) {
    const keys = Array.from(new Set([...Object.keys(testMap), ...Object.keys(uatMap), ...Object.keys(liveMap)]))
    if (keys.length) {
      return keys.map((key) => ({
        key,
        test: testMap[key] || '',
        uat: uatMap[key] || '',
        live: liveMap[key] || ''
      }))
    }
  }
  return [{
    key: item.base_url_json_key || '',
    test: item.base_url_test,
    uat: item.base_url_uat,
    live: item.base_url_live
  }]
}

const buildSubmitPayload = (): ServiceIdEntryPayload => {
  const normalizedExtraFields = Object.entries(form.extra_fields || {}).reduce<DynamicFormValues>((acc, [key, value]) => {
    if (Array.isArray(value)) {
      const next = value.map((item) => String(item || '').trim()).filter(Boolean)
      if (next.length) acc[key] = next
      return acc
    }
    const text = String(value || '').trim()
    if (text) acc[key] = text
    return acc
  }, {})
  if (form.base_url_mode !== 'json') {
    return {
      ...form,
      extra_fields: normalizedExtraFields,
      base_url_json_rows: []
    }
  }
  const rows = jsonRows.value.map((row) => ({
    key: row.key.trim(),
    test: row.test.trim(),
    uat: row.uat.trim(),
    live: row.live.trim()
  }))
  const first = rows[0] || createEmptyJsonRow()
  return {
    ...form,
    base_url_json_key: first.key,
    base_url_test_input: first.test,
    base_url_uat_input: first.uat,
    base_url_live_input: first.live,
    extra_fields: normalizedExtraFields,
    base_url_json_rows: rows
  }
}

const loadExportConfig = async () => {
  if (!canManageAll.value) return
  loadingExportConfig.value = true
  try {
    const res = await toolsApi.getServiceIdExportConfig(props.toolId)
    exportOptions.value = res.options
    exportColumnsDraft.value = res.columns.map((c) => ({ key: c.key, header: c.header }))
  } catch (error: any) {
    ElMessage.error(error.message || '加载导出配置失败')
  } finally {
    loadingExportConfig.value = false
  }
}

const onAddExportColumn = async (key: string | undefined) => {
  if (!key) return
  const opt = exportOptions.value.find((o) => o.key === key)
  if (!opt || exportColumnsDraft.value.some((c) => c.key === key)) {
    exportColumnToAdd.value = undefined
    return
  }
  exportColumnsDraft.value.push({ key, header: opt.default_header })
  await nextTick()
  exportColumnToAdd.value = undefined
}

const moveExportColumnUp = (idx: number) => {
  if (idx <= 0) return
  const arr = exportColumnsDraft.value
  const t = arr[idx - 1]
  arr[idx - 1] = arr[idx]
  arr[idx] = t
}

const moveExportColumnDown = (idx: number) => {
  const arr = exportColumnsDraft.value
  if (idx >= arr.length - 1) return
  const t = arr[idx + 1]
  arr[idx + 1] = arr[idx]
  arr[idx] = t
}

const removeExportColumn = (idx: number) => {
  if (exportColumnsDraft.value.length <= 1) {
    ElMessage.warning('至少保留一列')
    return
  }
  exportColumnsDraft.value.splice(idx, 1)
}

const saveExportConfig = async () => {
  if (!exportColumnsDraft.value.length) {
    ElMessage.warning('至少保留一列')
    return
  }
  savingExportConfig.value = true
  try {
    const res = await toolsApi.updateServiceIdExportConfig(props.toolId, exportColumnsDraft.value)
    exportColumnsDraft.value = res.columns.map((c) => ({ key: c.key, header: c.header }))
    ElMessage.success('导出配置已保存')
  } catch (error: any) {
    ElMessage.error(error.message || '保存失败')
  } finally {
    savingExportConfig.value = false
  }
}

const resetExportConfig = async () => {
  try {
    await ElMessageBox.confirm(
      '将删除已保存的布局并恢复为内置默认列（不含自定义扩展字段）。是否继续？',
      '恢复默认',
      { confirmButtonText: '恢复', cancelButtonText: '取消', type: 'warning' }
    )
  } catch {
    return
  }
  savingExportConfig.value = true
  try {
    const res = await toolsApi.resetServiceIdExportConfig(props.toolId)
    exportOptions.value = res.options
    exportColumnsDraft.value = res.columns.map((c) => ({ key: c.key, header: c.header }))
    ElMessage.success('已恢复默认导出列')
  } catch (error: any) {
    ElMessage.error(error.message || '恢复失败')
  } finally {
    savingExportConfig.value = false
  }
}

const loadEntries = async () => {
  loadingEntries.value = true
  try {
    const res = await toolsApi.getServiceIdEntries(
      props.toolId,
      (entriesPage.value - 1) * entriesPageSize.value,
      entriesPageSize.value
    )
    if (!res.can_manage_all) {
      ElMessage.warning('当前账号不是该工具负责人，无法查看全量数据')
    }
    canManageAll.value = res.can_manage_all
    entries.value = res.items
    entriesTotal.value = res.total
    if (res.can_manage_all) {
      await loadExportConfig()
    }
  } finally {
    loadingEntries.value = false
  }
}

const onEntriesPageChange = (page: number) => {
  entriesPage.value = page
  updateQuery({ sidEntriesPage: String(page) })
  void loadEntries()
}

const onEntriesPageSizeChange = (size: number) => {
  entriesPageSize.value = size
  entriesPage.value = 1
  updateQuery({ sidEntriesPageSize: String(size), sidEntriesPage: '1' })
  void loadEntries()
}

const loadRules = async () => {
  options.value = await toolsApi.getServiceIdRuleOptions(props.toolId, true)
}

const loadFieldConfigs = async () => {
  loadingFieldConfigs.value = true
  try {
    const res = await toolsApi.getServiceIdFieldConfigs(props.toolId)
    fieldConfigs.value = res.items.map((item) => ({
      ...item,
      allowed_values_text: (item.allowed_values || []).join(', ')
    }))
  } finally {
    loadingFieldConfigs.value = false
  }
}

const saveFieldConfigs = async () => {
  for (const row of fieldConfigs.value) {
    const minLength = row.min_length
    const maxLength = row.max_length
    if (typeof minLength === 'number' && typeof maxLength === 'number' && minLength > maxLength) {
      ElMessage.warning(`字段「${row.label}」的最小长度不能大于最大长度`)
      return
    }
  }
  savingFieldConfigs.value = true
  try {
    await toolsApi.updateServiceIdFieldConfigs(
      props.toolId,
      fieldConfigs.value.map((row) => ({
        field_key: row.field_key,
        label: row.label,
        input_type: row.input_type,
        sort_order: row.sort_order,
        help_text: (row.help_text || '').trim() || null,
        required: row.required,
        min_length: row.min_length ?? null,
        max_length: row.max_length ?? null,
        regex_pattern: (row.regex_pattern || '').trim() || null,
        regex_error_message: (row.regex_error_message || '').trim() || null,
        allowed_values: (row.allowed_values_text || '')
          .split(',')
          .map((item) => item.trim())
          .filter(Boolean)
      }))
    )
    await loadFieldConfigs()
    ElMessage.success('字段配置已保存')
  } catch (error: any) {
    ElMessage.error(error.message || '保存字段配置失败')
  } finally {
    savingFieldConfigs.value = false
  }
}

const openCreateField = () => {
  Object.assign(newField, {
    field_key: '',
    label: '',
    input_type: 'text' as FormFieldInputType
  })
  createFieldVisible.value = true
}

const createField = async () => {
  const fieldKey = newField.field_key.trim()
  const label = newField.label.trim()
  if (!fieldKey || !label) {
    ElMessage.warning('字段 key 和字段名称都需要填写')
    return
  }
  creatingField.value = true
  try {
    await toolsApi.createServiceIdFieldConfig(props.toolId, {
      field_key: fieldKey,
      label,
      input_type: newField.input_type
    })
    ElMessage.success('字段已新增')
    createFieldVisible.value = false
    await loadFieldConfigs()
  } catch (error: any) {
    ElMessage.error(error.message || '新增字段失败')
  } finally {
    creatingField.value = false
  }
}

const removeFieldConfig = async (fieldKey: string, label: string, isBuiltin: boolean) => {
  if (isBuiltin) {
    ElMessage.warning('内置字段不支持删除')
    return
  }
  try {
    await ElMessageBox.confirm(`确定删除字段「${label}」？历史记录中的该字段值也会被清理。`, '提示', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch {
    return
  }
  try {
    await toolsApi.deleteServiceIdFieldConfig(props.toolId, fieldKey)
    ElMessage.success('字段已删除')
    await loadFieldConfigs()
  } catch (error: any) {
    ElMessage.error(error.message || '删除字段失败')
  }
}

const openEdit = (item: ServiceIdEntry) => {
  editingId.value = item.id
  Object.assign(form, {
    business_function: item.business_function,
    business_description: item.business_description,
    service_id: item.service_id,
    service_type: item.service_type,
    psga_availability: item.psga_availability,
    package_name: item.package_name,
    scope_type: item.scope_type,
    apn_type: item.apn_type,
    access_link_desc: item.access_link_desc,
    base_url_mode: item.base_url_mode,
    base_url_json_key: item.base_url_json_key || '',
    base_url_test_input: item.base_url_test,
    base_url_uat_input: item.base_url_uat,
    base_url_live_input: item.base_url_live,
    extra_fields: { ...(item.extra_fields || {}) }
  })
  jsonRows.value = item.base_url_mode === 'json'
    ? buildJsonRowsFromEntry(item)
    : [createEmptyJsonRow()]
  editingVisible.value = true
}

const saveEntry = async () => {
  if (!editingId.value) return
  savingEntry.value = true
  try {
    const payload = buildSubmitPayload()
    await toolsApi.updateServiceIdEntry(props.toolId, { id: editingId.value, ...payload })
    ElMessage.success('已保存')
    editingVisible.value = false
    await loadEntries()
  } catch (error: any) {
    ElMessage.error(error.message || '保存失败')
  } finally {
    savingEntry.value = false
  }
}

const removeEntry = async (id: number) => {
  try {
    await ElMessageBox.confirm('确定删除该条记录？', '提示', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch {
    return
  }
  try {
    await toolsApi.deleteServiceIdEntry(props.toolId, id)
    ElMessage.success('已删除')
    await loadEntries()
  } catch (error: any) {
    ElMessage.error(error.message || '删除失败')
  }
}

const exportCsv = async () => {
  try {
    const blob = await toolsApi.exportServiceIdEntries(props.toolId)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = '服务ID注册管理导出.csv'
    a.click()
    URL.revokeObjectURL(url)
  } catch (error: any) {
    ElMessage.error(error.message || '导出失败')
  }
}

watch(moduleTab, (value) => {
  updateQuery({ sidManageTab: value })
  if (value === 'entries' && canManageAll.value) {
    void loadExportConfig()
  }
})

onMounted(async () => {
  const q = route.query
  const sidManageTab = queryFirst(q.sidManageTab)
  if (sidManageTab === 'fields') {
    moduleTab.value = 'fields'
  } else if (sidManageTab === 'rules') {
    moduleTab.value = 'fields'
  } else {
    moduleTab.value = 'entries'
  }
  entriesPage.value = toPositiveInt(queryFirst(q.sidEntriesPage), 1)
  entriesPageSize.value = toPositiveInt(queryFirst(q.sidEntriesPageSize), 20)
  try {
    await loadEntries()
    await loadRules()
    await loadFieldConfigs()
  } catch (error: any) {
    ElMessage.error(error.message || '加载管理数据失败')
  }
})
</script>

<style scoped>
.service-id-manage-tab {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.manage-module-tabs {
  width: 100%;
}

.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.section-hint {
  color: #606266;
  font-size: 13px;
  margin: 0 0 12px;
}

.table-pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}

.json-mode-block {
  border: 1px solid #ebeef5;
  border-radius: 4px;
  padding: 12px;
  margin-bottom: 12px;
}

.json-mode-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
  color: #606266;
  font-size: 13px;
}

.json-row {
  border-top: 1px dashed #ebeef5;
  padding-top: 8px;
  margin-top: 8px;
}

.json-row:first-of-type {
  border-top: none;
  padding-top: 0;
  margin-top: 0;
}

.json-row-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: -6px;
}

.export-csv-config {
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #ebeef5;
}

.export-csv-config-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 6px;
}

.export-csv-config-title {
  font-weight: 600;
  color: #303133;
}

.export-csv-config-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.export-csv-hint {
  margin-bottom: 10px;
}

.export-csv-table {
  margin-top: 4px;
}

.table-scroll {
  width: 100%;
  overflow-x: auto;
}

@media (max-width: 768px) {
  .header-row,
  .json-mode-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .table-pagination {
    justify-content: flex-start;
  }

  :deep(.el-input),
  :deep(.el-select),
  :deep(.el-date-editor),
  :deep(.el-input-number),
  :deep(.el-textarea) {
    width: 100% !important;
    max-width: 100% !important;
  }

  :deep(.el-col) {
    max-width: 100%;
    flex: 0 0 100%;
  }
}

</style>
