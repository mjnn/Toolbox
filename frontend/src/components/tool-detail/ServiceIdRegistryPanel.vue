<template>
  <div class="service-id-panel">
    <el-alert
      type="info"
      :closable="false"
      show-icon
      title="普通用户可新增、修改、删除自己提交的服务 ID。工具负责人可在管理页查看并治理全量数据。"
    />

    <el-card shadow="never">
      <template #header>{{ editingId ? '编辑服务 ID' : '新增服务 ID' }}</template>
      <el-form label-position="top">
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item :label="`业务功能（${form.business_function.length}/${getFieldMaxLength('business_function', 20) || 20}）`">
              <template #label>
                <span class="field-label-with-tip">
                  业务功能（{{ form.business_function.length }}/{{ getFieldMaxLength('business_function', 20) || 20 }}）
                  <el-tooltip v-if="getFieldHelp('business_function')" :content="getFieldHelp('business_function')" placement="top">
                    <el-icon><QuestionFilled /></el-icon>
                  </el-tooltip>
                </span>
              </template>
              <el-input v-model="form.business_function" :maxlength="getFieldMaxLength('business_function', 20)" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item :label="`业务功能描述（${form.business_description.length}/${getFieldMaxLength('business_description', 50) || 50}）`">
              <template #label>
                <span class="field-label-with-tip">
                  业务功能描述（{{ form.business_description.length }}/{{ getFieldMaxLength('business_description', 50) || 50 }}）
                  <el-tooltip v-if="getFieldHelp('business_description')" :content="getFieldHelp('business_description')" placement="top">
                    <el-icon><QuestionFilled /></el-icon>
                  </el-tooltip>
                </span>
              </template>
              <el-input v-model="form.business_description" :maxlength="getFieldMaxLength('business_description', 50)" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="Service ID">
              <template #label>
                <span class="field-label-with-tip">
                  Service ID
                  <el-tooltip v-if="getFieldHelp('service_id')" :content="getFieldHelp('service_id')" placement="top">
                    <el-icon><QuestionFilled /></el-icon>
                  </el-tooltip>
                </span>
              </template>
              <el-input v-model="form.service_id" :maxlength="getFieldMaxLength('service_id', 200)" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="包名（PackageName，仅英文）">
              <template #label>
                <span class="field-label-with-tip">
                  包名（PackageName，仅英文）
                  <el-tooltip v-if="getFieldHelp('package_name')" :content="getFieldHelp('package_name')" placement="top">
                    <el-icon><QuestionFilled /></el-icon>
                  </el-tooltip>
                </span>
              </template>
              <el-input v-model="form.package_name" :maxlength="getFieldMaxLength('package_name', 200)" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="服务类型（ServiceType）">
              <template #label>
                <span class="field-label-with-tip">
                  服务类型（ServiceType）
                  <el-tooltip v-if="getFieldHelp('service_type')" :content="getFieldHelp('service_type')" placement="top">
                    <el-icon><QuestionFilled /></el-icon>
                  </el-tooltip>
                </span>
              </template>
              <el-select v-model="form.service_type" style="width: 100%">
                <el-option v-for="item in options.service_type" :key="item.id" :label="item.value" :value="item.value" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="PSGA 可用域（单选）">
              <template #label>
                <span class="field-label-with-tip">
                  PSGA 可用域（单选）
                  <el-tooltip v-if="getFieldHelp('psga_availability')" :content="getFieldHelp('psga_availability')" placement="top">
                    <el-icon><QuestionFilled /></el-icon>
                  </el-tooltip>
                </span>
              </template>
              <el-select v-model="form.psga_availability" style="width: 100%">
                <el-option v-for="item in options.psga" :key="item.id" :label="item.value" :value="item.value" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="范围类型（ScopeType）">
              <template #label>
                <span class="field-label-with-tip">
                  范围类型（ScopeType）
                  <el-tooltip v-if="getFieldHelp('scope_type')" :content="getFieldHelp('scope_type')" placement="top">
                    <el-icon><QuestionFilled /></el-icon>
                  </el-tooltip>
                </span>
              </template>
              <el-select v-model="form.scope_type" style="width: 100%">
                <el-option v-for="item in options.scope_type" :key="item.id" :label="item.value" :value="item.value" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="网络类型（APNType）">
              <template #label>
                <span class="field-label-with-tip">
                  网络类型（APNType）
                  <el-tooltip v-if="getFieldHelp('apn_type')" :content="getFieldHelp('apn_type')" placement="top">
                    <el-icon><QuestionFilled /></el-icon>
                  </el-tooltip>
                </span>
              </template>
              <el-select v-model="form.apn_type" style="width: 100%">
                <el-option v-for="item in options.apn_type" :key="item.id" :label="item.value" :value="item.value" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item :label="`访问链路说明（${form.access_link_desc.length}/${getFieldMaxLength('access_link_desc', 20) || 20}）`">
          <template #label>
            <span class="field-label-with-tip">
              访问链路说明（{{ form.access_link_desc.length }}/{{ getFieldMaxLength('access_link_desc', 20) || 20 }}）
              <el-tooltip v-if="getFieldHelp('access_link_desc')" :content="getFieldHelp('access_link_desc')" placement="top">
                <el-icon><QuestionFilled /></el-icon>
              </el-tooltip>
            </span>
          </template>
          <el-input v-model="form.access_link_desc" :maxlength="getFieldMaxLength('access_link_desc', 20)" />
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
            :key="`json-row-${idx}`"
            class="json-row"
          >
            <el-row :gutter="12">
              <el-col :span="6">
                <el-form-item label="Key（仅英文）">
                  <template #label>
                    <span class="field-label-with-tip">
                      Key（仅英文）
                      <el-tooltip v-if="getFieldHelp('base_url_json_key')" :content="getFieldHelp('base_url_json_key')" placement="top">
                        <el-icon><QuestionFilled /></el-icon>
                      </el-tooltip>
                    </span>
                  </template>
                  <el-input v-model="row.key" :maxlength="getFieldMaxLength('base_url_json_key', 100)" />
                </el-form-item>
              </el-col>
              <el-col :span="6">
                <el-form-item label="测试（Test）">
                  <template #label>
                    <span class="field-label-with-tip">
                      测试（Test）
                      <el-tooltip v-if="getFieldHelp('base_url_test_input')" :content="getFieldHelp('base_url_test_input')" placement="top">
                        <el-icon><QuestionFilled /></el-icon>
                      </el-tooltip>
                    </span>
                  </template>
                  <el-input v-model="row.test" :maxlength="getFieldMaxLength('base_url_test_input')" />
                </el-form-item>
              </el-col>
              <el-col :span="6">
                <el-form-item label="预发（UAT）">
                  <template #label>
                    <span class="field-label-with-tip">
                      预发（UAT）
                      <el-tooltip v-if="getFieldHelp('base_url_uat_input')" :content="getFieldHelp('base_url_uat_input')" placement="top">
                        <el-icon><QuestionFilled /></el-icon>
                      </el-tooltip>
                    </span>
                  </template>
                  <el-input v-model="row.uat" :maxlength="getFieldMaxLength('base_url_uat_input')" />
                </el-form-item>
              </el-col>
              <el-col :span="6">
                <el-form-item label="生产（Live）">
                  <template #label>
                    <span class="field-label-with-tip">
                      生产（Live）
                      <el-tooltip v-if="getFieldHelp('base_url_live_input')" :content="getFieldHelp('base_url_live_input')" placement="top">
                        <el-icon><QuestionFilled /></el-icon>
                      </el-tooltip>
                    </span>
                  </template>
                  <el-input v-model="row.live" :maxlength="getFieldMaxLength('base_url_live_input')" />
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
            <el-form-item label="测试（Test）">
              <template #label>
                <span class="field-label-with-tip">
                  测试（Test）
                  <el-tooltip v-if="getFieldHelp('base_url_test_input')" :content="getFieldHelp('base_url_test_input')" placement="top">
                    <el-icon><QuestionFilled /></el-icon>
                  </el-tooltip>
                </span>
              </template>
              <el-input v-model="form.base_url_test_input" :maxlength="getFieldMaxLength('base_url_test_input')" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="预发（UAT）">
              <template #label>
                <span class="field-label-with-tip">
                  预发（UAT）
                  <el-tooltip v-if="getFieldHelp('base_url_uat_input')" :content="getFieldHelp('base_url_uat_input')" placement="top">
                    <el-icon><QuestionFilled /></el-icon>
                  </el-tooltip>
                </span>
              </template>
              <el-input v-model="form.base_url_uat_input" :maxlength="getFieldMaxLength('base_url_uat_input')" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="生产（Live）">
              <template #label>
                <span class="field-label-with-tip">
                  生产（Live）
                  <el-tooltip v-if="getFieldHelp('base_url_live_input')" :content="getFieldHelp('base_url_live_input')" placement="top">
                    <el-icon><QuestionFilled /></el-icon>
                  </el-tooltip>
                </span>
              </template>
              <el-input v-model="form.base_url_live_input" :maxlength="getFieldMaxLength('base_url_live_input')" />
            </el-form-item>
          </el-col>
        </el-row>

        <div class="action-row">
          <el-button type="primary" :loading="saving" @click="onSubmit">
            {{ editingId ? '保存修改' : '提交申请' }}
          </el-button>
          <el-button v-if="editingId" @click="resetForm">取消编辑</el-button>
        </div>
      </el-form>
    </el-card>

    <el-card shadow="never">
      <template #header>我提交的服务 ID</template>
      <el-table :data="entries" v-loading="loading" stripe>
        <el-table-column prop="service_id" label="Service ID" min-width="180" />
        <el-table-column prop="business_function" label="业务功能" width="140" />
        <el-table-column prop="service_type" label="服务类型（ServiceType）" width="160" />
        <el-table-column prop="psga_availability" label="PSGA" min-width="160" />
        <el-table-column prop="updated_by_name" label="最后更改人" width="120" />
        <el-table-column label="最后更新时间" width="180">
          <template #default="scope">{{ formatDate(scope.row.updated_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="scope">
            <el-button type="primary" size="small" link @click="startEdit(scope.row)">编辑</el-button>
            <el-button type="danger" size="small" link @click="remove(scope.row.id)">删除</el-button>
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
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import { QuestionFilled } from '@element-plus/icons-vue'
import { toolsApi } from '@/api/tools'
import { formatDateTime as formatDate } from '@/utils/datetime'
import DynamicFieldInputs from '@/components/form-config/DynamicFieldInputs.vue'
import type {
  DynamicFormValues,
  FormFieldConfigItem,
  ServiceBaseUrlMode,
  ServiceBaseUrlJsonRowPayload,
  ServiceIdEntry,
  ServiceIdEntryPayload,
  ServiceIdRuleOptionGroup
} from '@/api/types'

const props = defineProps<{ toolId: number }>()
const route = useRoute()
const router = useRouter()

const loading = ref(false)
const saving = ref(false)
const editingId = ref<number | null>(null)
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
const fieldConfigMap = ref<Record<string, FormFieldConfigItem>>({})
const fieldConfigs = ref<FormFieldConfigItem[]>([])
const customFieldConfigs = computed(() => fieldConfigs.value.filter((item) => !item.is_builtin))

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

const emptyForm: ServiceIdEntryPayload = {
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
}

const form = reactive<ServiceIdEntryPayload>({ ...emptyForm })
const createEmptyJsonRow = (): ServiceBaseUrlJsonRowPayload => ({ key: '', test: '', uat: '', live: '' })
const jsonRows = ref<ServiceBaseUrlJsonRowPayload[]>([createEmptyJsonRow()])

const resetForm = () => {
  Object.assign(form, emptyForm)
  jsonRows.value = [createEmptyJsonRow()]
  editingId.value = null
}

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

const getFieldConfig = (fieldKey: string): FormFieldConfigItem | undefined => fieldConfigMap.value[fieldKey]

const getFieldHelp = (fieldKey: string): string => String(getFieldConfig(fieldKey)?.help_text || '').trim()

const getFieldMaxLength = (fieldKey: string, fallback?: number): number | undefined => {
  const value = getFieldConfig(fieldKey)?.max_length
  if (typeof value === 'number' && value > 0) return value
  return fallback
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
  const normalizedExtraFields = Object.entries(form.extra_fields || {}).reduce<Record<string, string | string[]>>((acc, [key, value]) => {
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

const loadOptions = async () => {
  options.value = await toolsApi.getServiceIdRuleOptions(props.toolId, false)
}

const loadFieldConfigs = async () => {
  const res = await toolsApi.getServiceIdFieldConfigs(props.toolId)
  fieldConfigs.value = res.items
  const next: Record<string, FormFieldConfigItem> = {}
  res.items.forEach((item) => {
    next[item.field_key] = item
  })
  fieldConfigMap.value = next
}

const loadEntries = async () => {
  loading.value = true
  try {
    const res = await toolsApi.getServiceIdEntries(
      props.toolId,
      (entriesPage.value - 1) * entriesPageSize.value,
      entriesPageSize.value
    )
    entries.value = res.items
    entriesTotal.value = res.total
  } finally {
    loading.value = false
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

const startEdit = (item: ServiceIdEntry) => {
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
    base_url_mode: item.base_url_mode as ServiceBaseUrlMode,
    base_url_json_key: item.base_url_json_key || '',
    base_url_test_input: item.base_url_test,
    base_url_uat_input: item.base_url_uat,
    base_url_live_input: item.base_url_live,
    extra_fields: { ...(item.extra_fields || {}) }
  })
  jsonRows.value = item.base_url_mode === 'json'
    ? buildJsonRowsFromEntry(item)
    : [createEmptyJsonRow()]
}

const onSubmit = async () => {
  saving.value = true
  try {
    const payload = buildSubmitPayload()
    if (editingId.value) {
      await toolsApi.updateServiceIdEntry(props.toolId, { id: editingId.value, ...payload })
      ElMessage.success('已更新')
    } else {
      await toolsApi.createServiceIdEntry(props.toolId, payload)
      ElMessage.success('已提交')
    }
    await loadEntries()
    resetForm()
  } catch (error: any) {
    ElMessage.error(error.message || '提交失败')
  } finally {
    saving.value = false
  }
}

const remove = async (id: number) => {
  try {
    await ElMessageBox.confirm('确定删除该条记录？', '提示', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消'
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

onMounted(async () => {
  entriesPage.value = toPositiveInt(queryFirst(route.query.sidEntriesPage), 1)
  entriesPageSize.value = toPositiveInt(queryFirst(route.query.sidEntriesPageSize), 20)
  try {
    await loadFieldConfigs()
    await loadOptions()
    await loadEntries()
  } catch (error: any) {
    ElMessage.error(error.message || '加载数据失败')
  }
})
</script>

<style scoped>
.service-id-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.action-row {
  display: flex;
  gap: 8px;
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

.field-label-with-tip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
</style>
