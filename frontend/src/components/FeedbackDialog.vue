<template>
  <el-dialog
    :model-value="modelValue"
    :title="dialogTitle"
    width="520px"
    destroy-on-close
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <p v-if="hint" class="dialog-hint">{{ hint }}</p>
    <el-form label-width="72px">
      <el-form-item label="标题">
        <el-input v-model="title" placeholder="可选" maxlength="120" show-word-limit clearable />
      </el-form-item>
      <el-form-item label="内容" required>
        <el-input
          v-model="content"
          type="textarea"
          :rows="7"
          :placeholder="contentPlaceholder"
          maxlength="8000"
          show-word-limit
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="close">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="submit">提交</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { feedbackApi } from '@/api/feedback'
import type { FeedbackCategory } from '@/api/types'

const props = defineProps<{
  modelValue: boolean
  category: FeedbackCategory
  toolId?: number
  toolName?: string
}>()

const emit = defineEmits<{
  'update:modelValue': [boolean]
  submitted: []
}>()

const title = ref('')
const content = ref('')
const submitting = ref(false)

const dialogTitle = computed(() => {
  const m: Record<FeedbackCategory, string> = {
    tool_usage: '工具使用与问题反馈',
    new_tool_suggestion: '新增工具建议',
    system_feedback: '系统使用与问题反馈',
  }
  return m[props.category]
})

const hint = computed(() => {
  if (props.category === 'tool_usage' && props.toolName) {
    return `工具：${props.toolName}`
  }
  return ''
})

const contentPlaceholder = computed(() =>
  props.category === 'new_tool_suggestion'
    ? '请描述希望增加的工具、场景或优先级…'
    : '请尽量描述问题现象、复现步骤或建议…'
)

watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      title.value = ''
      content.value = ''
    }
  }
)

const close = () => emit('update:modelValue', false)

const submit = async () => {
  const t = content.value.trim()
  if (t.length < 5) {
    ElMessage.warning('内容至少 5 个字符')
    return
  }
  if (props.category === 'tool_usage' && props.toolId == null) {
    ElMessage.error('缺少工具信息')
    return
  }
  submitting.value = true
  try {
    await feedbackApi.submit({
      category: props.category,
      title: title.value.trim() || undefined,
      content: t,
      tool_id: props.category === 'tool_usage' ? props.toolId : undefined,
    })
    ElMessage.success('已提交，感谢您的反馈')
    emit('submitted')
    close()
  } catch (e: any) {
    ElMessage.error(e.message || '提交失败')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.dialog-hint {
  color: #909399;
  font-size: 13px;
  margin: 0 0 12px;
}
</style>
