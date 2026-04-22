<template>
  <el-table :data="rows" :loading="loading" stripe>
    <el-table-column label="字段名称" width="180">
      <template #default="scope">
        <el-input v-model="scope.row.label" :disabled="scope.row.is_builtin" />
      </template>
    </el-table-column>
    <el-table-column prop="field_key" label="字段 Key" width="180" />
    <el-table-column label="展示形式" width="160">
      <template #default="scope">
        <el-select v-model="scope.row.input_type" style="width: 100%">
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
        />
      </template>
    </el-table-column>
    <el-table-column label="必填" width="90">
      <template #default="scope">
        <el-switch v-model="scope.row.required" />
      </template>
    </el-table-column>
    <el-table-column label="最小长度" width="130">
      <template #default="scope">
        <el-input-number v-model="scope.row.min_length" :min="0" :max="5000" controls-position="right" />
      </template>
    </el-table-column>
    <el-table-column label="最大长度" width="130">
      <template #default="scope">
        <el-input-number v-model="scope.row.max_length" :min="0" :max="5000" controls-position="right" />
      </template>
    </el-table-column>
    <el-table-column label="正则" min-width="200">
      <template #default="scope">
        <el-input v-model="scope.row.regex_pattern" maxlength="500" placeholder="可选，如 ^[A-Za-z0-9_]+$" />
      </template>
    </el-table-column>
    <el-table-column label="正则错误提示" min-width="200">
      <template #default="scope">
        <el-input v-model="scope.row.regex_error_message" maxlength="200" placeholder="可选" />
      </template>
    </el-table-column>
    <el-table-column label="允许值（逗号分隔）" min-width="240">
      <template #default="scope">
        <el-input
          v-model="scope.row.allowed_values_text"
          placeholder="可选；填写后仅允许这些值"
        />
      </template>
    </el-table-column>
    <el-table-column label="操作" width="120" fixed="right">
      <template #default="scope">
        <el-button
          type="danger"
          size="small"
          link
          :disabled="scope.row.is_builtin"
          @click="$emit('delete', scope.row)"
        >
          删除
        </el-button>
      </template>
    </el-table-column>
  </el-table>
  <div class="action-row">
    <el-button type="primary" :loading="saving" @click="$emit('save')">保存字段配置</el-button>
    <el-button @click="$emit('refresh')">刷新</el-button>
  </div>
</template>

<script setup lang="ts">
import type { FormFieldConfigItem, FormFieldInputType } from '@/api/types'

defineProps<{
  rows: Array<FormFieldConfigItem & { allowed_values_text: string }>
  loading: boolean
  saving: boolean
  inputTypeOptions: Array<{ label: string; value: FormFieldInputType }>
}>()

defineEmits<{
  (e: 'save'): void
  (e: 'refresh'): void
  (e: 'delete', row: FormFieldConfigItem & { allowed_values_text: string }): void
}>()
</script>

<style scoped>
.action-row {
  margin-top: 12px;
  display: flex;
  gap: 8px;
}
</style>
