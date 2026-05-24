<template>
  <div class="service-id-rule-category-editor">
    <p class="hint">
      此处维护的选项会同步到用户填写页的下拉框，并在提交时由后端校验。仅工具负责人可维护。
    </p>
    <div class="rule-create-row">
      <el-input v-model="newRuleValue" placeholder="新增规则值" maxlength="200" />
      <el-button type="primary" :loading="savingRule" @click="createRule">新增</el-button>
    </div>
    <div class="table-scroll">
      <el-table :data="rows" v-loading="loading" stripe>
        <el-table-column prop="value" label="值" min-width="160" />
        <el-table-column label="启用" width="120">
          <template #default="scope">
            <el-switch
              :model-value="scope.row.is_active"
              @change="(v: boolean) => toggleRule(scope.row.id, v)"
            />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100">
          <template #default="scope">
            <el-button type="danger" size="small" link @click="removeRule(scope.row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
    <div class="table-pagination">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        @current-change="loadPage"
        @size-change="onPageSizeChange"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { toolsApi } from '@/api/tools'
import type { ServiceIdRuleOption, ServiceRuleCategory } from '@/api/types'

const props = defineProps<{
  toolId: number
  category: ServiceRuleCategory
}>()

const emit = defineEmits<{
  (e: 'changed'): void
}>()

const loading = ref(false)
const savingRule = ref(false)
const rows = ref<ServiceIdRuleOption[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const newRuleValue = ref('')

const loadPage = async () => {
  loading.value = true
  try {
    const res = await toolsApi.getServiceIdRuleOptionsPage(
      props.toolId,
      props.category,
      (page.value - 1) * pageSize.value,
      pageSize.value,
      true
    )
    rows.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

const onPageSizeChange = () => {
  page.value = 1
  void loadPage()
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
      category: props.category,
      value
    })
    newRuleValue.value = ''
    ElMessage.success('规则已新增')
    emit('changed')
    await loadPage()
  } catch (error: any) {
    ElMessage.error(error.message || '新增规则失败')
  } finally {
    savingRule.value = false
  }
}

const toggleRule = async (id: number, value: boolean) => {
  try {
    await toolsApi.updateServiceIdRuleOption(props.toolId, { id, is_active: value })
    emit('changed')
    await loadPage()
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
    emit('changed')
    if (page.value > 1 && rows.value.length <= 1) {
      page.value -= 1
    }
    await loadPage()
  } catch (error: any) {
    ElMessage.error(error.message || '删除规则失败')
  }
}

watch(
  () => props.category,
  () => {
    page.value = 1
    void loadPage()
  }
)

onMounted(() => {
  void loadPage()
})
</script>

<style scoped>
.service-id-rule-category-editor {
  min-height: 200px;
}

.hint {
  margin: 0 0 12px;
  font-size: 13px;
  color: #606266;
}

.rule-create-row {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.table-pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}

.table-scroll {
  width: 100%;
  overflow-x: auto;
}
</style>
