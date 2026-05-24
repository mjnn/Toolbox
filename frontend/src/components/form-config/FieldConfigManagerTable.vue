<template>
  <el-table :data="rows" :loading="loading" stripe>
    <el-table-column label="字段名称" width="180">
      <template #default="scope">
        <el-input v-model="scope.row.label" :disabled="isRowStructureLocked(scope.row)" />
      </template>
    </el-table-column>
    <el-table-column prop="field_key" label="字段 Key" width="180" />
    <el-table-column label="展示形式" width="160">
      <template #default="scope">
        <el-select v-model="scope.row.input_type" style="width: 100%" :disabled="isRowStructureLocked(scope.row)">
          <el-option
            v-for="item in inputTypeOptions"
            :key="item.value"
            :label="item.label"
            :value="item.value"
          />
        </el-select>
      </template>
    </el-table-column>
    <el-table-column label="填写说明" min-width="260">
      <template #default="scope">
        <el-input
          v-model="scope.row.help_text"
          type="textarea"
          :rows="2"
          maxlength="500"
          show-word-limit
          placeholder="鼠标悬停时展示"
          :disabled="isRowStructureLocked(scope.row)"
        />
      </template>
    </el-table-column>
    <el-table-column label="必填" width="90">
      <template #default="scope">
        <el-switch v-model="scope.row.required" :disabled="isRowStructureLocked(scope.row)" />
      </template>
    </el-table-column>
    <el-table-column label="最小长度" width="130">
      <template #default="scope">
        <el-input-number
          v-model="scope.row.min_length"
          :min="0"
          :max="5000"
          controls-position="right"
          :disabled="isRowStructureLocked(scope.row)"
        />
      </template>
    </el-table-column>
    <el-table-column label="最大长度" width="130">
      <template #default="scope">
        <el-input-number
          v-model="scope.row.max_length"
          :min="0"
          :max="5000"
          controls-position="right"
          :disabled="isRowStructureLocked(scope.row)"
        />
      </template>
    </el-table-column>
    <el-table-column label="正则" min-width="200">
      <template #default="scope">
        <el-input
          v-model="scope.row.regex_pattern"
          maxlength="500"
          placeholder="可选，如 ^[A-Za-z0-9_]+$"
          :disabled="isRowStructureLocked(scope.row)"
        />
      </template>
    </el-table-column>
    <el-table-column label="正则错误提示" min-width="200">
      <template #default="scope">
        <el-input
          v-model="scope.row.regex_error_message"
          maxlength="200"
          placeholder="可选"
          :disabled="isRowStructureLocked(scope.row)"
        />
      </template>
    </el-table-column>
    <el-table-column label="允许值 / 选项" min-width="220">
      <template #default="scope">
        <template v-if="scope.row.input_type === 'text' || scope.row.input_type === 'textarea'">
          <el-input
            v-model="scope.row.allowed_values_text"
            placeholder="可选；逗号分隔，填写后仅允许这些值"
            :disabled="isAllowedValuesLocked(scope.row)"
          />
        </template>
        <template v-else>
          <el-button type="primary" link :disabled="isAllowedValuesLocked(scope.row)" @click="openOptionsDialog(scope.row)">
            {{ selectOptionsSummary(scope.row) }}
          </el-button>
        </template>
      </template>
    </el-table-column>
    <el-table-column v-if="enableSortReorder" label="顺序" width="148" fixed="right">
      <template #default="scope">
        <el-button
          link
          type="primary"
          :disabled="isMoveUpDisabled(scope.$index)"
          @click="moveRowUp(scope.$index)"
        >
          上移
        </el-button>
        <el-button
          link
          type="primary"
          :disabled="isMoveDownDisabled(scope.$index)"
          @click="moveRowDown(scope.$index)"
        >
          下移
        </el-button>
      </template>
    </el-table-column>
    <el-table-column label="操作" width="120" fixed="right">
      <template #default="scope">
        <el-button
          type="danger"
          size="small"
          link
          :disabled="isRowDeleteDisabled(scope.row)"
          @click="$emit('delete', scope.row)"
        >
          删除
        </el-button>
      </template>
    </el-table-column>
  </el-table>

  <el-dialog
    v-model="optionsDialogVisible"
    :title="optionsDialogTitle"
    width="800px"
    destroy-on-close
    @closed="optionsDialogRow = null"
  >
    <template v-if="optionsDialogRow">
      <slot name="selectOptionsEditor" :row="optionsDialogRow">
        <select-option-values-editor v-model:text="optionsDialogRow.allowed_values_text" />
      </slot>
    </template>
    <template #footer>
      <el-button
        v-if="optionsDialogRow && loadDistinctValuesByFieldKey"
        :loading="collectingDistinctValues"
        @click="fillDistinctOptionsFromFieldValues(optionsDialogRow)"
      >
        使用该字段已有值（去重）
      </el-button>
      <el-button type="primary" @click="optionsDialogVisible = false">完成</el-button>
    </template>
  </el-dialog>

  <div class="action-row">
    <p v-if="enableSortReorder" class="field-order-hint">{{ orderHintResolved }}</p>
    <el-button type="primary" :loading="saving" @click="$emit('save')">保存字段配置</el-button>
    <el-button @click="$emit('refresh')">刷新</el-button>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { FormFieldConfigItem, FormFieldInputType } from '@/api/types'
import SelectOptionValuesEditor from '@/components/form-config/SelectOptionValuesEditor.vue'
import { FIELD_CONFIG_MANAGER_ORDER_HINT_DEFAULT } from '@/components/form-config/fieldConfigManagerConstants'

export type FieldConfigTableRow = FormFieldConfigItem & { allowed_values_text: string }

const props = withDefaults(
  defineProps<{
    rows: FieldConfigTableRow[]
    loading: boolean
    saving: boolean
    inputTypeOptions: Array<{ label: string; value: FormFieldInputType }>
    /** 禁止删除的 field_key（如 data-secure 保留的 business_function） */
    deleteDisabledFieldKeys?: string[]
    /** 禁止改名称/类型/校验的 field_key（仍允许编辑允许值/选项，便于维护业务功能清单） */
    structureLockedFieldKeys?: string[]
    /** 可选：返回某字段在业务数据中的去重值列表（用于一键生成单选/多选选项） */
    loadDistinctValuesByFieldKey?: (fieldKey: string) => Promise<string[]> | string[]
    /** 是否启用「上移/下移」调整 sort_order（自上而下对应展示与导出顺序） */
    enableSortReorder?: boolean
    /** 禁止调整顺序的 field_key（仍可编辑其余列）；常与 `deleteDisabledFieldKeys` 对齐以固定内置主键列 */
    sortReorderLockedFieldKeys?: string[]
    /** 为 true 时所有 `is_builtin` 行不允许与相邻行换位（适用于仅含少量内置列的工具；Service ID 等请保持 false） */
    lockBuiltinSortReorder?: boolean
    /** 覆盖表下顺序说明文案；默认见 `FIELD_CONFIG_MANAGER_ORDER_HINT_DEFAULT` */
    orderHint?: string | null
  }>(),
  {
    deleteDisabledFieldKeys: () => [],
    structureLockedFieldKeys: () => [],
    loadDistinctValuesByFieldKey: undefined,
    enableSortReorder: true,
    sortReorderLockedFieldKeys: () => [],
    lockBuiltinSortReorder: false,
    orderHint: null
  }
)

const orderHintResolved = computed(() => {
  const t = props.orderHint?.trim()
  return t || FIELD_CONFIG_MANAGER_ORDER_HINT_DEFAULT
})

const isRowStructureLocked = (row: FieldConfigTableRow) => props.structureLockedFieldKeys.includes(row.field_key)

const isRowDeleteDisabled = (row: FieldConfigTableRow) =>
  Boolean(row.is_builtin) || props.deleteDisabledFieldKeys.includes(row.field_key)

/** 内置「数据字段」行的允许值不允许改；「业务功能」为内置列但允许维护选项/允许值 */
const isAllowedValuesLocked = (row: FieldConfigTableRow) => row.field_key === 'field_name'

const isRowSortLocked = (row: FieldConfigTableRow) =>
  props.sortReorderLockedFieldKeys.includes(row.field_key) ||
  (props.lockBuiltinSortReorder && Boolean(row.is_builtin))

const isMoveUpDisabled = (index: number) => {
  if (index <= 0) return true
  const cur = props.rows[index] as FieldConfigTableRow
  const prev = props.rows[index - 1] as FieldConfigTableRow
  return isRowSortLocked(cur) || isRowSortLocked(prev)
}

const isMoveDownDisabled = (index: number) => {
  if (index >= props.rows.length - 1) return true
  const cur = props.rows[index] as FieldConfigTableRow
  const next = props.rows[index + 1] as FieldConfigTableRow
  return isRowSortLocked(cur) || isRowSortLocked(next)
}

const syncSortOrderAfterReorder = () => {
  props.rows.forEach((row, i) => {
    row.sort_order = i
  })
}

const moveRowUp = (index: number) => {
  if (isMoveUpDisabled(index)) return
  const arr = props.rows
  const row = arr.splice(index, 1)[0]
  arr.splice(index - 1, 0, row)
  syncSortOrderAfterReorder()
}

const moveRowDown = (index: number) => {
  if (isMoveDownDisabled(index)) return
  const arr = props.rows
  const row = arr.splice(index, 1)[0]
  arr.splice(index + 1, 0, row)
  syncSortOrderAfterReorder()
}

defineEmits<{
  (e: 'save'): void
  (e: 'refresh'): void
  (e: 'delete', row: FieldConfigTableRow): void
}>()

const optionsDialogVisible = ref(false)
const optionsDialogRow = ref<FieldConfigTableRow | null>(null)
const collectingDistinctValues = ref(false)

const optionsDialogTitle = computed(() => {
  const row = optionsDialogRow.value
  if (!row) return '选项定义'
  return `选项定义 — ${row.label}（${row.field_key}）`
})

const selectOptionsSummary = (row: FieldConfigTableRow): string => {
  const n = (row.allowed_values_text || '')
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean).length
  return n ? `已配置 ${n} 个选项` : '配置选项'
}

const openOptionsDialog = (row: FieldConfigTableRow) => {
  if (isAllowedValuesLocked(row)) return
  optionsDialogRow.value = row
  optionsDialogVisible.value = true
}

const fillDistinctOptionsFromFieldValues = async (row: FieldConfigTableRow) => {
  if (!props.loadDistinctValuesByFieldKey) return
  collectingDistinctValues.value = true
  try {
    const values = await props.loadDistinctValuesByFieldKey(row.field_key)
    const current = (row.allowed_values_text || '')
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean)
    const merged = Array.from(new Set([...current, ...(values || []).map((v) => String(v || '').trim()).filter(Boolean)]))
    row.allowed_values_text = merged.join(', ')
    ElMessage.success(`已合并 ${merged.length} 个去重选项`)
  } catch (error: any) {
    ElMessage.error(error?.message || '读取该字段已有值失败')
  } finally {
    collectingDistinctValues.value = false
  }
}
</script>

<style scoped>
.action-row {
  margin-top: 12px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.field-order-hint {
  width: 100%;
  margin: 0 0 4px;
  font-size: 13px;
  color: #606266;
}
</style>
