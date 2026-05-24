<template>
  <div class="select-option-values-editor">
    <p class="hint">在下框输入选项文本，回车添加；也可删除标签。保存字段配置时一并提交。</p>
    <div class="tags-row">
      <el-tag
        v-for="(tag, idx) in tags"
        :key="`${tag}-${idx}`"
        closable
        class="option-tag"
        @close="removeAt(idx)"
      >
        {{ tag }}
      </el-tag>
    </div>
    <el-input
      v-model="draft"
      placeholder="输入选项文本，回车添加"
      maxlength="200"
      @keydown.enter.prevent="commitDraft"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

const props = defineProps<{
  text: string
}>()

const emit = defineEmits<{
  (e: 'update:text', value: string): void
}>()

const draft = ref('')

const tags = computed(() =>
  (props.text || '')
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean)
)

const syncFromTags = (next: string[]) => {
  emit('update:text', next.join(', '))
}

const removeAt = (idx: number) => {
  const next = tags.value.filter((_, i) => i !== idx)
  syncFromTags(next)
}

const commitDraft = () => {
  const value = draft.value.trim()
  if (!value) return
  const set = new Set(tags.value)
  if (set.has(value)) {
    draft.value = ''
    return
  }
  syncFromTags([...tags.value, value])
  draft.value = ''
}

watch(
  () => props.text,
  () => {
    draft.value = ''
  }
)
</script>

<style scoped>
.select-option-values-editor {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.hint {
  margin: 0;
  font-size: 13px;
  color: #606266;
}

.tags-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.option-tag {
  max-width: 100%;
}
</style>
