<template>
  <div class="cloud-md-editor">
    <div class="cloud-md-toolbar">
      <el-button-group>
        <el-button size="small" @click="wrapSelection('**', '**', '加粗文本')">加粗</el-button>
        <el-button size="small" @click="wrapSelection('*', '*', '斜体文本')">斜体</el-button>
        <el-button size="small" @click="wrapSelection('`', '`', '代码')">行内代码</el-button>
      </el-button-group>
      <el-button-group>
        <el-button size="small" @click="insertBlock('# ', '一级标题')">H1</el-button>
        <el-button size="small" @click="insertBlock('## ', '二级标题')">H2</el-button>
        <el-button size="small" @click="insertBlock('- ', '列表项')">列表</el-button>
        <el-button size="small" @click="insertBlock('> ', '引用')">引用</el-button>
      </el-button-group>
      <el-button-group>
        <el-button size="small" @click="insertTemplate('[链接文字](https://example.com)')">链接</el-button>
        <el-button size="small" @click="insertTemplate('![图片说明](https://example.com/image.png)')">图片</el-button>
        <el-button size="small" @click="insertTemplate('| 列1 | 列2 |\\n| --- | --- |\\n| 内容1 | 内容2 |')">表格</el-button>
      </el-button-group>
    </div>

    <el-tabs v-model="viewMode" class="cloud-md-tabs">
      <el-tab-pane label="编辑" name="edit">
        <el-input
          ref="inputRef"
          :model-value="modelValue"
          type="textarea"
          :rows="rows"
          :maxlength="maxlength"
          show-word-limit
          :placeholder="placeholder"
          @update:model-value="onInputChange"
        />
      </el-tab-pane>
      <el-tab-pane label="预览" name="preview">
        <div class="cloud-md-preview markdown-body" v-html="previewHtml"></div>
      </el-tab-pane>
      <el-tab-pane label="分屏" name="split">
        <div class="cloud-md-split">
          <el-input
            ref="splitInputRef"
            :model-value="modelValue"
            type="textarea"
            :rows="rows"
            :maxlength="maxlength"
            show-word-limit
            :placeholder="placeholder"
            @update:model-value="onInputChange"
          />
          <div class="cloud-md-preview markdown-body" v-html="previewHtml"></div>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { renderMarkdown } from '@/utils/markdown'

const props = withDefaults(
  defineProps<{
    modelValue: string
    rows?: number
    maxlength?: number
    placeholder?: string
  }>(),
  {
    rows: 10,
    maxlength: 8000,
    placeholder: ''
  }
)

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
}>()

const viewMode = ref<'edit' | 'preview' | 'split'>('split')
const inputRef = ref<any>(null)
const splitInputRef = ref<any>(null)

const previewHtml = computed(() => renderMarkdown(props.modelValue || ''))

const onInputChange = (value: string) => {
  emit('update:modelValue', value)
}

const getActiveTextarea = (): HTMLTextAreaElement | null => {
  const primary = inputRef.value?.textarea as HTMLTextAreaElement | undefined
  const split = splitInputRef.value?.textarea as HTMLTextAreaElement | undefined
  return primary || split || null
}

const wrapSelection = (prefix: string, suffix: string, fallbackText: string) => {
  const textarea = getActiveTextarea()
  const current = props.modelValue || ''
  if (!textarea) {
    emit('update:modelValue', `${current}${prefix}${fallbackText}${suffix}`)
    return
  }
  const start = textarea.selectionStart ?? current.length
  const end = textarea.selectionEnd ?? current.length
  const selected = current.slice(start, end) || fallbackText
  const next = `${current.slice(0, start)}${prefix}${selected}${suffix}${current.slice(end)}`
  emit('update:modelValue', next)
  requestAnimationFrame(() => {
    const target = getActiveTextarea()
    if (!target) return
    target.focus()
    const pos = start + prefix.length + selected.length + suffix.length
    target.setSelectionRange(pos, pos)
  })
}

const insertBlock = (prefix: string, fallbackText: string) => {
  const textarea = getActiveTextarea()
  const current = props.modelValue || ''
  if (!textarea) {
    emit('update:modelValue', `${current}${current ? '\n' : ''}${prefix}${fallbackText}`)
    return
  }
  const start = textarea.selectionStart ?? current.length
  const end = textarea.selectionEnd ?? current.length
  const selected = current.slice(start, end) || fallbackText
  const block = selected
    .split('\n')
    .map((line) => `${prefix}${line}`)
    .join('\n')
  const next = `${current.slice(0, start)}${block}${current.slice(end)}`
  emit('update:modelValue', next)
}

const insertTemplate = (template: string) => {
  const textarea = getActiveTextarea()
  const current = props.modelValue || ''
  if (!textarea) {
    emit('update:modelValue', `${current}${current ? '\n\n' : ''}${template}`)
    return
  }
  const start = textarea.selectionStart ?? current.length
  const end = textarea.selectionEnd ?? current.length
  const next = `${current.slice(0, start)}${template}${current.slice(end)}`
  emit('update:modelValue', next)
}
</script>

<style scoped>
.cloud-md-editor {
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
  padding: 10px;
  background: var(--el-bg-color);
}

.cloud-md-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 8px;
}

.cloud-md-tabs :deep(.el-tabs__header) {
  margin-bottom: 8px;
}

.cloud-md-preview {
  min-height: 220px;
  max-height: 420px;
  overflow: auto;
  border: 1px solid var(--el-border-color-light);
  border-radius: 6px;
  padding: 10px;
  background: var(--el-fill-color-blank);
}

.cloud-md-split {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.markdown-body :deep(table) {
  border-collapse: collapse;
  width: 100%;
}

.markdown-body :deep(th),
.markdown-body :deep(td) {
  border: 1px solid var(--el-border-color);
  padding: 6px 8px;
}

.markdown-body :deep(img) {
  max-width: 100%;
}
</style>
