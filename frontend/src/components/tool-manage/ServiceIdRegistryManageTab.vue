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

      <el-tab-pane label="规则治理" name="rules">
        <el-card shadow="never">
          <template #header>规则定义（服务类型 / PSGA / 范围 / APN）</template>
          <el-tabs v-model="ruleTab">
            <el-tab-pane label="服务类型（ServiceType）" name="service_type" />
            <el-tab-pane label="可用域（PSGA）" name="psga" />
            <el-tab-pane label="范围（Scope）" name="scope_type" />
            <el-tab-pane label="网络类型（APN）" name="apn_type" />
          </el-tabs>

          <div class="rule-create-row">
            <el-input v-model="newRuleValue" placeholder="新增规则值（仅负责人可维护）" />
            <el-button type="primary" :loading="savingRule" @click="createRule">新增</el-button>
          </div>

          <el-table :data="currentRuleRows" v-loading="loadingRules" stripe>
            <el-table-column prop="value" label="值" />
            <el-table-column label="启用" width="120">
              <template #default="scope">
                <el-switch
                  :model-value="scope.row.is_active"
                  @change="(v:boolean) => toggleRule(scope.row.id, v)"
                />
              </template>
            </el-table-column>
            <el-table-column label="操作" width="120">
              <template #default="scope">
                <el-button type="danger" size="small" link @click="removeRule(scope.row.id)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <div class="table-pagination">
            <el-pagination
              v-model:current-page="rulePage"
              v-model:page-size="rulePageSize"
              :total="ruleTotal"
              :page-sizes="[10, 20, 50, 100]"
              layout="total, sizes, prev, pager, next, jumper"
              @current-change="onRulePageChange"
              @size-change="onRulePageSizeChange"
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
          <p class="section-hint">可配置字段悬停说明，以及 required / 长度 / 正则 / 允许值限制，实时作用于用户填写页与后端校验。</p>
          <field-config-manager-table
            :rows="fieldConfigs"
            :loading="loadingFieldConfigs"
            :saving="savingFieldConfigs"
            :input-type-options="fieldInputTypeOptions"
            @save="saveFieldConfigs"
            @refresh="loadFieldConfigs"
            @delete="(row) => removeFieldConfig(row.field_key, row.label, row.is_builtin)"
          />
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
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import { toolsApi } from '@/api/tools'
import { formatDateTime as formatDate } from '@/utils/datetime'
import DynamicFieldInputs from '@/components/form-config/DynamicFieldInputs.vue'
import FieldConfigManagerTable from '@/components/form-config/FieldConfigManagerTable.vue'
import type {
  DynamicFormValues,
  FormFieldConfigItem,
  FormFieldInputType,
  ServiceBaseUrlJsonRowPayload,
  ServiceIdEntry,
  ServiceIdEntryPayload,
  ServiceIdRuleOption,
  ServiceIdRuleOptionGroup,
  ServiceRuleCategory
} from '@/api/types'

const props = defineProps<{ toolId: number }>()
const route = useRoute()
const router = useRouter()

const loadingEntries = ref(false)
const loadingRules = ref(false)
const loadingFieldConfigs = ref(false)
const savingRule = ref(false)
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
const moduleTab = ref<'entries' | 'rules' | 'fields'>('entries')
const ruleTab = ref<ServiceRuleCategory>('service_type')
const currentRuleRows = ref<ServiceIdRuleOption[]>([])
const ruleTotal = ref(0)
const rulePage = ref(1)
const rulePageSize = ref(20)
const newRuleValue = ref('')
const fieldConfigs = ref<Array<FormFieldConfigItem & { allowed_values_text: string }>>([])
const customFieldConfigs = computed(() => fieldConfigs.value.filter((item) => !item.is_builtin))
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
    entries.value = res.items
    entriesTotal.value = res.total
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

const loadRulePage = async () => {
  loadingRules.value = true
  try {
    const res = await toolsApi.getServiceIdRuleOptionsPage(
      props.toolId,
      ruleTab.value,
      (rulePage.value - 1) * rulePageSize.value,
      rulePageSize.value,
      true
    )
    currentRuleRows.value = res.items
    ruleTotal.value = res.total
  } finally {
    loadingRules.value = false
  }
}

const onRulePageChange = (page: number) => {
  rulePage.value = page
  updateQuery({ sidRulePage: String(page) })
  void loadRulePage()
}

const onRulePageSizeChange = (size: number) => {
  rulePageSize.value = size
  rulePage.value = 1
  updateQuery({ sidRulePageSize: String(size), sidRulePage: '1' })
  void loadRulePage()
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

const createRule = async () => {
  const value = newRuleValue.value.trim()
  if (!value) {
    ElMessage.warning('请输入规则值')
    return
  }
  savingRule.value = true
  try {
    await toolsApi.createServiceIdRuleOption(props.toolId, {
      category: ruleTab.value,
      value
    })
    newRuleValue.value = ''
    ElMessage.success('规则已新增')
    await loadRules()
    await loadRulePage()
  } catch (error: any) {
    ElMessage.error(error.message || '新增规则失败')
  } finally {
    savingRule.value = false
  }
}

const toggleRule = async (id: number, value: boolean) => {
  try {
    await toolsApi.updateServiceIdRuleOption(props.toolId, { id, is_active: value })
    await loadRules()
    await loadRulePage()
  } catch (error: any) {
    ElMessage.error(error.message || '更新规则状态失败')
  }
}

const removeRule = async (id: number) => {
  try {
    await ElMessageBox.confirm('确定删除该规则？', '提示', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch {
    return
  }
  try {
    await toolsApi.deleteServiceIdRuleOption(props.toolId, id)
    ElMessage.success('规则已删除')
    await loadRules()
    if (rulePage.value > 1 && currentRuleRows.value.length <= 1) {
      rulePage.value -= 1
    }
    await loadRulePage()
  } catch (error: any) {
    ElMessage.error(error.message || '删除规则失败')
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

watch(ruleTab, () => {
  rulePage.value = 1
  updateQuery({ sidRuleTab: ruleTab.value, sidRulePage: '1' })
  void loadRulePage()
})

watch(moduleTab, (value) => {
  updateQuery({ sidManageTab: value })
})

onMounted(async () => {
  const q = route.query
  const sidManageTab = queryFirst(q.sidManageTab)
  const sidRuleTab = queryFirst(q.sidRuleTab)
  moduleTab.value = (
    sidManageTab === 'rules' ||
    sidManageTab === 'fields'
  ) ? sidManageTab : 'entries'
  ruleTab.value = (
    sidRuleTab === 'service_type' ||
    sidRuleTab === 'psga' ||
    sidRuleTab === 'scope_type' ||
    sidRuleTab === 'apn_type'
  ) ? sidRuleTab : 'service_type'
  entriesPage.value = toPositiveInt(queryFirst(q.sidEntriesPage), 1)
  entriesPageSize.value = toPositiveInt(queryFirst(q.sidEntriesPageSize), 20)
  rulePage.value = toPositiveInt(queryFirst(q.sidRulePage), 1)
  rulePageSize.value = toPositiveInt(queryFirst(q.sidRulePageSize), 20)
  try {
    await loadEntries()
    await loadRules()
    await loadRulePage()
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

.rule-create-row {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.section-hint {
  color: #909399;
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

</style>
