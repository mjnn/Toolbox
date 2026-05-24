<template>
  <div class="json-nested-viewer">
    <el-tabs v-if="shouldRenderTabs" v-model="activeTab" class="json-nested-tabs">
      <el-tab-pane
        v-for="[childKey, childValue] in collectionEntries"
        :key="childKey"
        :label="childKey"
        :name="childKey"
      >
        <JsonNestedTabsViewer :data="normalizeChildNode(childKey, childValue)" />
      </el-tab-pane>
    </el-tabs>

    <div v-else class="json-leaf-table">
      <el-table :data="leafRows" size="small" stripe>
        <el-table-column prop="key" label="字段" min-width="220" show-overflow-tooltip />
        <el-table-column prop="value" label="值" min-width="320">
          <template #default="scope">
            <span class="json-value-text">{{ scope.row.value }}</span>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

defineOptions({ name: 'JsonNestedTabsViewer' })

const props = defineProps<{ data: unknown }>()

const activeTab = ref('')

const isCollection = (value: unknown): value is Record<string, unknown> | unknown[] => {
  return Array.isArray(value) || (value !== null && typeof value === 'object')
}

const getEntries = (value: unknown): Array<[string, unknown]> => {
  if (Array.isArray(value)) {
    return value.map((item, index) => [String(index), item])
  }
  if (value !== null && typeof value === 'object') {
    return Object.entries(value as Record<string, unknown>)
  }
  return []
}

const hasNestedChildren = (value: unknown): boolean => {
  if (!isCollection(value)) return false
  return getEntries(value).some(([, child]) => isCollection(child))
}

const collectionEntries = computed(() => getEntries(props.data))

const shouldRenderTabs = computed(() => {
  return isCollection(props.data) && hasNestedChildren(props.data)
})

const formatLeafValue = (value: unknown): string => {
  if (value === null) return 'null'
  if (value === undefined) return 'undefined'
  if (typeof value === 'string') return value
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)
  try {
    return JSON.stringify(value)
  } catch {
    return String(value)
  }
}

const leafRows = computed(() => {
  if (Array.isArray(props.data)) {
    return props.data.map((item, index) => ({
      key: String(index),
      value: formatLeafValue(item)
    }))
  }
  if (props.data !== null && typeof props.data === 'object') {
    return Object.entries(props.data as Record<string, unknown>).map(([key, value]) => ({
      key,
      value: formatLeafValue(value)
    }))
  }
  return [{ key: '值', value: formatLeafValue(props.data) }]
})

const normalizeChildNode = (childKey: string, childValue: unknown): unknown => {
  if (isCollection(childValue)) return childValue
  return { [childKey]: childValue }
}

watch(
  collectionEntries,
  (entries) => {
    if (!entries.length) {
      activeTab.value = ''
      return
    }
    const hasCurrent = entries.some(([key]) => key === activeTab.value)
    if (!hasCurrent) {
      activeTab.value = entries[0][0]
    }
  },
  { immediate: true }
)
</script>

<style scoped>
.json-nested-viewer {
  width: 100%;
}

.json-nested-tabs {
  width: 100%;
}

.json-leaf-table {
  width: 100%;
}

.json-value-text {
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
