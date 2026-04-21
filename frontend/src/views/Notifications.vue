<template>
  <div class="notifications-page">
    <el-page-header @back="goBack" title="返回">
      <template #content>
        <span class="page-header-title">通知</span>
      </template>
    </el-page-header>

    <el-card class="main-card">
      <template #header>
        <div class="card-header">
          <span>消息列表</span>
          <div class="card-header-actions">
            <el-button
              type="danger"
              plain
              size="small"
              :disabled="list.length === 0 || clearingAll"
              :loading="clearingAll"
              @click="confirmClearAll"
            >
              清除全部
            </el-button>
            <el-radio-group v-model="typeFilter" size="small">
              <el-radio-button label="all">全部</el-radio-button>
              <el-radio-button label="permission">权限</el-radio-button>
              <el-radio-button label="tool">工具</el-radio-button>
              <el-radio-button label="system">其他</el-radio-button>
            </el-radio-group>
          </div>
        </div>
      </template>

      <div v-loading="loading">
        <el-empty v-if="!loading && filteredList.length === 0" description="暂无通知" />
        <div v-else class="notification-list">
          <div
            v-for="item in filteredList"
            :key="item.id"
            class="notification-item"
            :class="{ unread: !item.is_read }"
            @click="onClickItem(item)"
          >
            <div class="notification-title-row">
              <span class="notification-title">{{ item.title }}</span>
              <el-tag v-if="!item.is_read" type="danger" size="small">未读</el-tag>
              <el-tag v-else type="info" size="small" effect="plain">已读</el-tag>
              <span class="notification-time">{{ formatDate(item.created_at) }}</span>
            </div>
            <div class="notification-message">{{ item.message }}</div>
            <div class="notification-meta">
              <el-tag size="small" effect="plain">{{ typeLabel(item.notification_type) }}</el-tag>
              <el-button
                type="danger"
                link
                size="small"
                :loading="deletingId === item.id"
                @click.stop="confirmRemoveOne(item)"
              >
                清除
              </el-button>
            </div>
          </div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { notificationsApi } from '@/api/notifications'
import { formatDateTime as formatDate } from '@/utils/datetime'
import { resolveNotificationTarget } from '@/utils/notificationTarget'
import { goBackOrFallback } from '@/utils/navigation'
import type { NotificationInDB } from '@/api/types'

const router = useRouter()
const loading = ref(false)
const clearingAll = ref(false)
const deletingId = ref<number | null>(null)
const list = ref<NotificationInDB[]>([])
const typeFilter = ref<'all' | 'permission' | 'tool' | 'system'>('all')

const filteredList = computed(() => {
  if (typeFilter.value === 'all') return list.value
  if (typeFilter.value === 'permission') {
    return list.value.filter((n) => n.notification_type === 'permission')
  }
  if (typeFilter.value === 'tool') {
    return list.value.filter((n) =>
      n.notification_type === 'tool' || n.notification_type === 'tool_release'
    )
  }
  return list.value.filter(
    (n) =>
      n.notification_type !== 'permission' &&
      n.notification_type !== 'tool' &&
      n.notification_type !== 'tool_release'
  )
})

const goBack = () => {
  goBackOrFallback(router, '/')
}

const typeLabel = (t: string) => {
  if (t === 'permission') return '权限'
  if (t === 'tool') return '工具'
  if (t === 'tool_release') return '工具发版'
  return '系统'
}

const load = async () => {
  loading.value = true
  try {
    list.value = await notificationsApi.list()
  } catch (error: any) {
    ElMessage.error(error.message || '加载通知失败')
  } finally {
    loading.value = false
  }
}

const onClickItem = async (item: NotificationInDB) => {
  if (!item.is_read) {
    try {
      const updated = await notificationsApi.markRead(item.id)
      const idx = list.value.findIndex((n) => n.id === item.id)
      if (idx >= 0) list.value[idx] = updated
    } catch (error: any) {
      ElMessage.error(error.message || '标记已读失败')
      return
    }
  }
  const target = resolveNotificationTarget(item)
  if (target) {
    await router.push(target)
  }
}

const confirmClearAll = async () => {
  if (list.value.length === 0) return
  try {
    await ElMessageBox.confirm(
      '确定删除当前账号下的全部通知？此操作不可恢复。',
      '清除全部通知',
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }
    )
  } catch {
    return
  }
  clearingAll.value = true
  try {
    await notificationsApi.clearAll()
    list.value = []
    ElMessage.success('已清除全部通知')
  } catch (error: any) {
    ElMessage.error(error.message || '清除失败')
  } finally {
    clearingAll.value = false
  }
}

const confirmRemoveOne = async (item: NotificationInDB) => {
  try {
    await ElMessageBox.confirm('确定删除这条通知？', '清除通知', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    return
  }
  deletingId.value = item.id
  try {
    await notificationsApi.deleteOne(item.id)
    list.value = list.value.filter((n) => n.id !== item.id)
    ElMessage.success('已清除')
  } catch (error: any) {
    ElMessage.error(error.message || '清除失败')
  } finally {
    deletingId.value = null
  }
}

onMounted(() => {
  load()
})
</script>

<style scoped>
.notifications-page {
  padding: 20px;
}

.page-header-title {
  font-size: 18px;
  font-weight: bold;
}

.main-card {
  margin-top: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}

.card-header-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}

.notification-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.notification-item {
  padding: 14px 16px;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s;
}

.notification-item:hover {
  background: #f5f7fa;
}

.notification-item.unread {
  border-color: #c6e2ff;
  background: #ecf5ff;
}

.notification-title-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 8px;
}

.notification-title {
  font-weight: 600;
  flex: 1;
  min-width: 120px;
}

.notification-time {
  font-size: 12px;
  color: #909399;
  margin-left: auto;
}

.notification-message {
  color: #606266;
  line-height: 1.5;
  font-size: 14px;
}

.notification-meta {
  margin-top: 8px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
</style>
