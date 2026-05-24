<template>
  <div class="dashboard-container">
    <el-container class="layout">
      <el-header class="header">
        <div class="header-left">
          <el-button
            class="mobile-menu-btn"
            text
            circle
            aria-label="打开导航菜单"
            @click="mobileNavVisible = true"
          >
            <el-icon><Menu /></el-icon>
          </el-button>
          <h2>MOS综合工具箱</h2>
        </div>
        <div class="header-right">
          <el-dropdown @command="handleCommand">
            <button class="user-info" type="button" aria-label="打开用户菜单">
              <el-avatar :size="36" :src="avatarDisplayUrl" :style="{ backgroundColor: '#409EFF' }">
                {{ userInitial }}
              </el-avatar>
              <span class="username">{{ userInfo?.full_name || userInfo?.username }}</span>
              <el-icon><arrow-down /></el-icon>
            </button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">个人资料</el-dropdown-item>
                <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      
      <el-container class="body-shell">
        <el-aside v-if="!isMobile" width="200px" class="sidebar">
          <el-menu
            :default-active="menuActiveIndex"
            router
            class="sidebar-menu"
            @select="handleMenuSelect"
          >
            <el-menu-item v-for="item in visibleMenuEntries" :key="item.index" :index="item.index">
              <el-icon><component :is="item.icon" /></el-icon>
              <span>{{ item.label }}</span>
            </el-menu-item>
          </el-menu>
        </el-aside>

        <el-drawer v-model="mobileNavVisible" direction="ltr" size="78%" :with-header="false" class="mobile-nav-drawer">
          <el-menu
            :default-active="menuActiveIndex"
            router
            class="mobile-nav-menu"
            @select="handleMenuSelect"
          >
            <el-menu-item v-for="item in visibleMenuEntries" :key="item.index" :index="item.index">
              <el-icon><component :is="item.icon" /></el-icon>
              <span>{{ item.label }}</span>
            </el-menu-item>
          </el-menu>
        </el-drawer>
        
        <el-main class="main-content">
          <div class="welcome-card">
            <el-tabs v-if="isPlatformStaff" v-model="adminDashboardTab" class="admin-dashboard-tabs">
              <el-tab-pane label="数据概览" name="overview">
                <div class="welcome-header">
                  <div>
                    <h1>欢迎回来，{{ userInfo?.full_name || userInfo?.username }}！</h1>
                    <p>今天是 {{ currentDate }}</p>
                  </div>
                  <div class="welcome-actions">
                    <el-badge
                      v-if="isPlatformStaff"
                      :value="feedbackAdminTotal"
                      :hidden="feedbackAdminTotal === 0"
                      class="welcome-feedback-badge"
                    >
                      <el-button type="primary" plain size="small" @click="router.push('/feedback-admin')">
                        反馈管理
                      </el-button>
                    </el-badge>
                    <el-button type="primary" size="small" @click="systemFeedbackVisible = true">系统反馈</el-button>
                  </div>
                </div>

                <div class="stats">
                  <el-card v-if="isPlatformStaff" class="stat-card">
                    <div class="stat-content">
                      <el-icon class="stat-icon" color="#409EFF"><user-filled /></el-icon>
                      <div>
                        <div class="stat-value">{{ userCount }}</div>
                        <div class="stat-label">用户总数</div>
                      </div>
                    </div>
                  </el-card>

                  <el-card
                    class="stat-card stat-card-clickable"
                    role="button"
                    tabindex="0"
                    aria-label="进入我的工具"
                    @click="goMyTools"
                    @keydown.enter.prevent="goMyTools"
                    @keydown.space.prevent="goMyTools"
                  >
                    <div class="stat-content">
                      <el-icon class="stat-icon" color="#67C23A"><folder-opened /></el-icon>
                      <div>
                        <div class="stat-value">{{ myToolsCount }}</div>
                        <div class="stat-label">我的工具</div>
                      </div>
                    </div>
                  </el-card>

                  <el-card
                    class="stat-card stat-card-clickable"
                    role="button"
                    tabindex="0"
                    aria-label="进入通知页面"
                    @click="goNotifications"
                    @keydown.enter.prevent="goNotifications"
                    @keydown.space.prevent="goNotifications"
                  >
                    <div class="stat-content">
                      <el-icon class="stat-icon" color="#E6A23C"><bell /></el-icon>
                      <div>
                        <div class="stat-value">{{ notificationUnreadCount }}</div>
                        <div class="stat-label">通知（未读）</div>
                      </div>
                    </div>
                  </el-card>
                </div>
              </el-tab-pane>

              <el-tab-pane label="工具访问量" name="traffic">
                <el-alert
                  title="统计有「工具维度」的 API 访问日志；已排除超级管理员与平台管理员自身请求。"
                  type="info"
                  :closable="false"
                  style="margin-bottom: 12px"
                />
                <div class="traffic-toolbar">
                  <span class="traffic-label">时间范围</span>
                  <el-radio-group v-model="trafficPeriod" size="small" @change="loadTraffic">
                    <el-radio-button value="day">日（近24小时）</el-radio-button>
                    <el-radio-button value="week">周（近7天）</el-radio-button>
                    <el-radio-button value="month">月（近30天）</el-radio-button>
                  </el-radio-group>
                  <el-button type="primary" plain size="small" :loading="trafficLoading" style="margin-left: 12px" @click="loadTraffic">
                    刷新
                  </el-button>
                </div>
                <p v-if="trafficSummaryText" class="traffic-range">{{ trafficSummaryText }}</p>
                <el-table :data="trafficRows" v-loading="trafficLoading" stripe empty-text="暂无数据">
                  <el-table-column prop="tool_name" label="工具" min-width="160" show-overflow-tooltip />
                  <el-table-column prop="request_count" label="请求量" width="120" />
                  <el-table-column label="相对占比" min-width="220">
                    <template #default="scope">
                      <el-progress
                        :percentage="trafficBarPercent(scope.row.request_count)"
                        :stroke-width="14"
                      />
                    </template>
                  </el-table-column>
                </el-table>
              </el-tab-pane>

              <el-tab-pane v-if="userInfo?.is_superuser" label="公告管理" name="announcement">
                <el-alert
                  title="可在此发布全站公告（固定显示在所有页面顶部滚动条）"
                  type="info"
                  :closable="false"
                  style="margin-bottom: 12px"
                />
                <el-form label-width="120px">
                  <el-form-item label="公告标题">
                    <el-input v-model="adminAnnouncementForm.title" maxlength="200" show-word-limit placeholder="例如：本周末维护公告" />
                  </el-form-item>
                  <el-form-item label="公告内容">
                    <el-input
                      v-model="adminAnnouncementForm.content"
                      type="textarea"
                      :rows="4"
                      maxlength="4000"
                      show-word-limit
                      placeholder="请输入公告正文"
                    />
                  </el-form-item>
                  <el-form-item label="优先级">
                    <el-radio-group v-model="adminAnnouncementForm.priority">
                      <el-radio-button label="urgent">紧急维护</el-radio-button>
                      <el-radio-button label="notice">通知</el-radio-button>
                      <el-radio-button label="reminder">提醒</el-radio-button>
                    </el-radio-group>
                  </el-form-item>
                  <el-form-item label="生效区间">
                    <el-date-picker
                      v-model="adminAnnouncementRange"
                      type="datetimerange"
                      range-separator="至"
                      start-placeholder="开始时间（可空）"
                      end-placeholder="结束时间（可空）"
                      value-format="YYYY-MM-DDTHH:mm:ss"
                    />
                  </el-form-item>
                  <el-form-item label="滚动速度(秒)">
                    <el-input-number v-model="adminAnnouncementForm.scroll_speed_seconds" :min="10" :max="300" />
                  </el-form-item>
                  <el-form-item label="字体">
                    <el-input v-model="adminAnnouncementForm.font_family" placeholder="如 Microsoft YaHei, SimHei，可留空" />
                  </el-form-item>
                  <el-form-item label="字号(px)">
                    <el-input-number v-model="adminAnnouncementForm.font_size_px" :min="12" :max="32" />
                  </el-form-item>
                  <el-form-item label="启用状态">
                    <el-switch v-model="adminAnnouncementForm.is_enabled" active-text="启用" inactive-text="停用" />
                  </el-form-item>
                  <el-form-item>
                    <el-button @click="resetAdminAnnouncementForm">重置</el-button>
                    <el-button type="primary" :loading="savingAdminAnnouncement" @click="saveAdminAnnouncement">
                      {{ editingAdminAnnouncementId === null ? '发布公告' : '保存编辑' }}
                    </el-button>
                  </el-form-item>
                </el-form>

                <el-table :data="adminAnnouncementRows" v-loading="loadingAdminAnnouncements" stripe>
                  <el-table-column label="状态" width="90">
                    <template #default="scope">
                      <el-tag :type="scope.row.is_enabled ? 'success' : 'info'">
                        {{ scope.row.is_enabled ? '启用' : '停用' }}
                      </el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column prop="title" label="标题" min-width="180" show-overflow-tooltip />
                  <el-table-column label="优先级" width="110">
                    <template #default="scope">
                      <el-tag :type="scope.row.priority === 'urgent' ? 'danger' : scope.row.priority === 'reminder' ? 'warning' : 'info'">
                        {{ scope.row.priority === 'urgent' ? '紧急维护' : scope.row.priority === 'reminder' ? '提醒' : '通知' }}
                      </el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column prop="content" label="内容" min-width="260" show-overflow-tooltip />
                  <el-table-column label="样式" min-width="260" show-overflow-tooltip>
                    <template #default="scope">
                      速度 {{ scope.row.scroll_speed_seconds }}s / 字号 {{ scope.row.font_size_px }}px /
                      字体 {{ scope.row.font_family || '默认' }}
                    </template>
                  </el-table-column>
                  <el-table-column label="生效时间" width="320">
                    <template #default="scope">
                      {{ scope.row.start_at ? formatDate(scope.row.start_at) : '立即生效' }} 至
                      {{ scope.row.end_at ? formatDate(scope.row.end_at) : '长期有效' }}
                    </template>
                  </el-table-column>
                  <el-table-column label="操作" width="180" fixed="right">
                    <template #default="scope">
                      <el-button type="primary" link @click="editAdminAnnouncement(scope.row)">编辑</el-button>
                      <el-button type="primary" link @click="toggleAdminAnnouncement(scope.row)">
                        {{ scope.row.is_enabled ? '停用' : '启用' }}
                      </el-button>
                    </template>
                  </el-table-column>
                </el-table>
                <div class="table-pagination">
                  <el-pagination
                    background
                    layout="total, prev, pager, next, sizes"
                    :total="adminAnnouncementTotal"
                    :current-page="adminAnnouncementPage"
                    :page-size="adminAnnouncementPageSize"
                    :page-sizes="[10, 20, 50]"
                    @update:current-page="onAdminAnnouncementPageChange"
                    @update:page-size="onAdminAnnouncementPageSizeChange"
                  />
                </div>
              </el-tab-pane>
            </el-tabs>

            <template v-else>
              <div class="welcome-header">
                <div>
                  <h1>欢迎回来，{{ userInfo?.full_name || userInfo?.username }}！</h1>
                  <p>今天是 {{ currentDate }}</p>
                </div>
                <div class="welcome-actions">
                  <el-badge
                    v-if="isPlatformStaff"
                    :value="feedbackAdminTotal"
                    :hidden="feedbackAdminTotal === 0"
                    class="welcome-feedback-badge"
                  >
                    <el-button type="primary" plain size="small" @click="router.push('/feedback-admin')">
                      反馈管理
                    </el-button>
                  </el-badge>
                  <el-button type="primary" size="small" @click="systemFeedbackVisible = true">系统反馈</el-button>
                </div>
              </div>

              <div class="stats">
                <el-card v-if="isPlatformStaff" class="stat-card">
                  <div class="stat-content">
                    <el-icon class="stat-icon" color="#409EFF"><user-filled /></el-icon>
                    <div>
                      <div class="stat-value">{{ userCount }}</div>
                      <div class="stat-label">用户总数</div>
                    </div>
                  </div>
                </el-card>

                <el-card
                  class="stat-card stat-card-clickable"
                  role="button"
                  tabindex="0"
                  aria-label="进入我的工具"
                  @click="goMyTools"
                  @keydown.enter.prevent="goMyTools"
                  @keydown.space.prevent="goMyTools"
                >
                  <div class="stat-content">
                    <el-icon class="stat-icon" color="#67C23A"><folder-opened /></el-icon>
                    <div>
                      <div class="stat-value">{{ myToolsCount }}</div>
                      <div class="stat-label">我的工具</div>
                    </div>
                  </div>
                </el-card>

                <el-card
                  class="stat-card stat-card-clickable"
                  role="button"
                  tabindex="0"
                  aria-label="进入通知页面"
                  @click="goNotifications"
                  @keydown.enter.prevent="goNotifications"
                  @keydown.space.prevent="goNotifications"
                >
                  <div class="stat-content">
                    <el-icon class="stat-icon" color="#E6A23C"><bell /></el-icon>
                    <div>
                      <div class="stat-value">{{ notificationUnreadCount }}</div>
                      <div class="stat-label">通知（未读）</div>
                    </div>
                  </div>
                </el-card>
              </div>
            </template>
          </div>
        </el-main>
      </el-container>
    </el-container>

    <FeedbackDialog v-model="systemFeedbackVisible" category="system_feedback" @submitted="onSystemFeedbackSubmitted" />
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch, type Component } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  UserFilled,
  User as ProfileMenuIcon,
  Setting,
  Menu,
  ArrowDown,
  FolderOpened,
  Bell,
  Document,
  Tickets,
  ChatLineRound
} from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { authApi } from '@/api/auth'
import { usersApi } from '@/api/users'
import { toolsApi } from '@/api/tools'
import { permissionsApi } from '@/api/permissions'
import { notificationsApi } from '@/api/notifications'
import { adminApi } from '@/api/admin'
import FeedbackDialog from '@/components/FeedbackDialog.vue'
import { getFeedbackAdminBadgeCount } from '@/utils/feedbackAdminBadge'
import { buildAvatarDisplaySrc } from '@/utils/avatarDisplayUrl'
import { formatDateTime as formatDate, formatShanghaiCalendarHeader } from '@/utils/datetime'
import type { ToolAnnouncementInDB, ToolTrafficRow } from '@/api/types'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const userInfo = computed(() => authStore.userInfo)

const menuActiveIndex = computed(() => {
  const p = route.path
  if (p.startsWith('/users')) return '/users'
  if (p.startsWith('/my-tools')) return '/my-tools'
  if (p.startsWith('/notifications')) return '/notifications'
  if (p.startsWith('/profile')) return '/profile'
  if (p.startsWith('/tools')) return '/tools'
  if (p.startsWith('/permissions')) return '/permissions'
  if (p.startsWith('/audit-logs')) return '/audit-logs'
  if (p.startsWith('/feedback-admin')) return '/feedback-admin'
  if (p.startsWith('/system-other-settings') || p.startsWith('/system-db-optimization')) {
    return '/system-other-settings'
  }
  // 首页 `/` 等：不高亮任一菜单项（避免误把「所有工具」当作始终选中）
  return ''
})
const userInitial = computed(() => {
  const name = userInfo.value?.full_name || userInfo.value?.username || 'U'
  return name.charAt(0).toUpperCase()
})

const avatarDisplayUrl = computed(() =>
  buildAvatarDisplaySrc(userInfo.value?.avatar_url, userInfo.value?.updated_at),
)
type MenuEntry = {
  index: string
  label: string
  icon: Component
  /** 超级管理员或平台管理员可见 */
  platformStaff?: boolean
  /** 仅超级管理员 */
  superOnly?: boolean
}
const isMobile = ref(false)
const mobileNavVisible = ref(false)
const menuEntries: MenuEntry[] = [
  { index: '/users', label: '用户管理', icon: UserFilled, platformStaff: true },
  { index: '/my-tools', label: '我的工具', icon: FolderOpened },
  { index: '/tools', label: '所有工具', icon: Setting },
  { index: '/notifications', label: '通知', icon: Bell },
  { index: '/profile', label: '个人资料', icon: ProfileMenuIcon },
  { index: '/permissions', label: '权限管理', icon: Document },
  { index: '/audit-logs', label: '行为日志', icon: Tickets, platformStaff: true },
  { index: '/feedback-admin', label: '反馈管理', icon: ChatLineRound, platformStaff: true },
  { index: '/system-other-settings', label: '系统配置', icon: Setting, superOnly: true },
]

const isPlatformStaff = computed(
  () => !!(userInfo.value?.is_superuser || userInfo.value?.is_platform_admin)
)

const trafficPeriod = ref<'day' | 'week' | 'month'>('day')
const trafficLoading = ref(false)
const trafficRows = ref<ToolTrafficRow[]>([])
const trafficRange = ref<{ start: string; end: string } | null>(null)
const trafficMax = computed(() => Math.max(1, ...trafficRows.value.map((r) => r.request_count)))
const trafficBarPercent = (n: number) => Math.min(100, Math.round((n / trafficMax.value) * 100))
const trafficSummaryText = computed(() => {
  if (!trafficRange.value) return ''
  return `统计区间：${formatDate(trafficRange.value.start)} — ${formatDate(trafficRange.value.end)}（UTC）`
})

const loadTraffic = async () => {
  trafficLoading.value = true
  try {
    const res = await adminApi.getToolTrafficDashboard(trafficPeriod.value)
    trafficRows.value = res.rows || []
    trafficRange.value = { start: res.range_start, end: res.range_end }
  } catch (error: any) {
    ElMessage.error(error?.message || '加载访问量失败')
  } finally {
    trafficLoading.value = false
  }
}

const visibleMenuEntries = computed(() =>
  menuEntries.filter((item) => {
    if (item.superOnly) return !!userInfo.value?.is_superuser
    if (item.platformStaff) return isPlatformStaff.value
    return true
  })
)
const updateViewportState = () => {
  const mobile = window.innerWidth <= 768
  isMobile.value = mobile
  if (!mobile) mobileNavVisible.value = false
}
const handleMenuSelect = () => {
  if (isMobile.value) mobileNavVisible.value = false
}

const currentDate = ref('')
const userCount = ref(0)
const myToolsCount = ref(0)
const notificationUnreadCount = ref(0)
const feedbackAdminTotal = ref(0)
const systemFeedbackVisible = ref(false)
const adminDashboardTab = ref<'overview' | 'traffic' | 'announcement'>('overview')
const loadingAdminAnnouncements = ref(false)
const savingAdminAnnouncement = ref(false)
const adminAnnouncementRows = ref<ToolAnnouncementInDB[]>([])
const adminAnnouncementPage = ref(1)
const adminAnnouncementPageSize = ref(20)
const adminAnnouncementTotal = ref(0)
const editingAdminAnnouncementId = ref<number | null>(null)
const adminAnnouncementRange = ref<[string, string] | null>(null)
const adminAnnouncementForm = reactive({
  title: '',
  content: '',
  is_enabled: true,
  priority: 'notice' as 'urgent' | 'notice' | 'reminder',
  scroll_speed_seconds: 45,
  font_family: '',
  font_size_px: 14,
})

const onSystemFeedbackSubmitted = async () => {
  if (isPlatformStaff.value) {
    try {
      const c = await adminApi.getFeedbackCounts()
      feedbackAdminTotal.value = getFeedbackAdminBadgeCount(c.total, userInfo.value?.id ?? 0)
    } catch {
      /* ignore */
    }
  }
}

const goMyTools = () => {
  router.push('/my-tools')
}

const goNotifications = () => {
  router.push('/notifications')
}

const toPickerDateTime = (value?: string | null): string | null => {
  if (!value) return null
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return null
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

const resetAdminAnnouncementForm = () => {
  editingAdminAnnouncementId.value = null
  adminAnnouncementForm.title = ''
  adminAnnouncementForm.content = ''
  adminAnnouncementForm.is_enabled = true
  adminAnnouncementForm.priority = 'notice'
  adminAnnouncementForm.scroll_speed_seconds = 45
  adminAnnouncementForm.font_family = ''
  adminAnnouncementForm.font_size_px = 14
  adminAnnouncementRange.value = null
}

const loadAdminAnnouncements = async () => {
  if (!userInfo.value?.is_superuser) {
    adminAnnouncementRows.value = []
    adminAnnouncementTotal.value = 0
    return
  }
  loadingAdminAnnouncements.value = true
  try {
    const res = await adminApi.listGlobalAnnouncements({
      skip: (adminAnnouncementPage.value - 1) * adminAnnouncementPageSize.value,
      limit: adminAnnouncementPageSize.value,
      only_active: false,
    })
    adminAnnouncementRows.value = res.items || []
    adminAnnouncementTotal.value = Number(res.total || 0)
  } catch (error: any) {
    ElMessage.error(error?.message || '加载公告失败')
  } finally {
    loadingAdminAnnouncements.value = false
  }
}

const saveAdminAnnouncement = async () => {
  const title = adminAnnouncementForm.title.trim()
  const content = adminAnnouncementForm.content.trim()
  if (!title || !content) {
    ElMessage.warning('请填写公告标题和内容')
    return
  }
  savingAdminAnnouncement.value = true
  try {
    const payload = {
      title,
      content,
      is_enabled: adminAnnouncementForm.is_enabled,
      priority: adminAnnouncementForm.priority,
      scroll_speed_seconds: adminAnnouncementForm.scroll_speed_seconds,
      font_family: adminAnnouncementForm.font_family?.trim() || null,
      font_size_px: adminAnnouncementForm.font_size_px,
      start_at: adminAnnouncementRange.value?.[0] || null,
      end_at: adminAnnouncementRange.value?.[1] || null,
      disable_feature_slugs: [] as string[],
    }
    if (editingAdminAnnouncementId.value === null) {
      await adminApi.createGlobalAnnouncement(payload)
      ElMessage.success('公告发布成功')
    } else {
      await adminApi.updateGlobalAnnouncement(editingAdminAnnouncementId.value, payload)
      ElMessage.success('公告更新成功')
    }
    resetAdminAnnouncementForm()
    adminAnnouncementPage.value = 1
    await loadAdminAnnouncements()
  } catch (error: any) {
    ElMessage.error(error?.message || '公告保存失败')
  } finally {
    savingAdminAnnouncement.value = false
  }
}

const editAdminAnnouncement = (row: ToolAnnouncementInDB) => {
  editingAdminAnnouncementId.value = row.id
  adminAnnouncementForm.title = row.title || ''
  adminAnnouncementForm.content = row.content || ''
  adminAnnouncementForm.is_enabled = row.is_enabled
  adminAnnouncementForm.priority = row.priority || 'notice'
  adminAnnouncementForm.scroll_speed_seconds = Number(row.scroll_speed_seconds || 45)
  adminAnnouncementForm.font_family = row.font_family || ''
  adminAnnouncementForm.font_size_px = Number(row.font_size_px || 14)
  const start = toPickerDateTime(row.start_at)
  const end = toPickerDateTime(row.end_at)
  adminAnnouncementRange.value = start && end ? [start, end] : null
}

const toggleAdminAnnouncement = async (row: ToolAnnouncementInDB) => {
  try {
    await adminApi.updateGlobalAnnouncement(row.id, {
      is_enabled: !row.is_enabled,
    })
    ElMessage.success(!row.is_enabled ? '公告已启用' : '公告已停用')
    await loadAdminAnnouncements()
  } catch (error: any) {
    ElMessage.error(error?.message || '更新公告状态失败')
  }
}

const onAdminAnnouncementPageChange = async (page: number) => {
  adminAnnouncementPage.value = page
  await loadAdminAnnouncements()
}

const onAdminAnnouncementPageSizeChange = async (size: number) => {
  adminAnnouncementPageSize.value = size
  adminAnnouncementPage.value = 1
  await loadAdminAnnouncements()
}

const handleCommand = async (command: string) => {
  if (command === 'logout') {
    try {
      await ElMessageBox.confirm('确定要退出登录吗？', '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      })
      
      await authApi.logout()
      authStore.clearTokens()
      ElMessage.success('已退出登录')
      router.push('/login')
    } catch (error) {
      // 用户取消
    }
  } else if (command === 'profile') {
    router.push('/profile')
  }
}

const refreshWelcomeDate = () => {
  currentDate.value = formatShanghaiCalendarHeader()
}

const fetchDashboardData = async () => {
  try {
    if (userInfo.value?.is_superuser || userInfo.value?.is_platform_admin) {
      const users = await usersApi.getUsers(0, 1)
      userCount.value = users.total
    } else {
      userCount.value = 0
    }

    const tools = await toolsApi.getTools(0, 500)
    if (userInfo.value?.is_superuser) {
      myToolsCount.value = tools.length
    } else if (userInfo.value?.is_platform_admin) {
      const myPerms = await permissionsApi.getMyPermissions()
      const approved = new Set(
        myPerms.filter((p) => p.status === 'approved').map((p) => p.tool_id)
      )
      const owned = await adminApi.getMyOwnerTools()
      const ownedSet = new Set(owned)
      myToolsCount.value = tools.filter(
        (t) => approved.has(t.id) || ownedSet.has(t.id)
      ).length
    } else {
      const myPerms = await permissionsApi.getMyPermissions()
      const approved = new Set(
        myPerms.filter((p) => p.status === 'approved').map((p) => p.tool_id)
      )
      const owned = await adminApi.getMyOwnerTools()
      const ownedSet = new Set(owned)
      myToolsCount.value = tools.filter(
        (t) => approved.has(t.id) || ownedSet.has(t.id)
      ).length
    }

    const notifications = await notificationsApi.list()
    notificationUnreadCount.value = notifications.filter((n) => !n.is_read).length

    if (userInfo.value?.is_superuser || userInfo.value?.is_platform_admin) {
      try {
        const fc = await adminApi.getFeedbackCounts()
        feedbackAdminTotal.value = getFeedbackAdminBadgeCount(fc.total, userInfo.value?.id ?? 0)
      } catch {
        feedbackAdminTotal.value = 0
      }
    } else {
      feedbackAdminTotal.value = 0
    }
  } catch (error) {
    console.error('获取仪表板数据失败:', error)
  }
}

watch(adminDashboardTab, async (value) => {
  if (value === 'announcement') {
    await loadAdminAnnouncements()
  }
  if (value === 'traffic') {
    await loadTraffic()
  }
})

onMounted(() => {
  updateViewportState()
  window.addEventListener('resize', updateViewportState)
  refreshWelcomeDate()

  // 如果没有用户信息，尝试获取
  if (!authStore.userInfo && authStore.accessToken) {
    authApi.getCurrentUser().then(user => {
      authStore.setUserInfo(user)
      fetchDashboardData()
    }).catch(() => {
      // 获取失败，可能是token失效
      authStore.clearTokens()
      router.push('/login')
    })
  } else if (authStore.userInfo) {
    fetchDashboardData()
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', updateViewportState)
})
</script>

<style scoped>
.dashboard-container {
  width: 100%;
  height: 100vh;
}

.layout {
  height: 100%;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background-color: #fff;
  border-bottom: 1px solid #e4e7ed;
  padding: 0 20px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.mobile-menu-btn {
  display: none;
}

.header-left h2 {
  margin: 0;
  color: #333;
}

.welcome-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 16px;
  margin-bottom: 8px;
}

.welcome-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}

.welcome-feedback-badge :deep(.el-badge__content) {
  top: 4px;
  right: 2px;
}

.user-info {
  display: flex;
  align-items: center;
  cursor: pointer;
  padding: 8px 12px;
  border-radius: 6px;
  transition: background-color 0.3s;
  border: none;
  background: transparent;
}

.user-info:hover {
  background-color: #f5f7fa;
}

.user-info:focus-visible {
  outline: 2px solid #409eff;
  outline-offset: 2px;
}

.username {
  margin: 0 8px;
  font-size: 14px;
  color: #333;
}

.sidebar {
  background-color: #fff;
  border-right: 1px solid #e4e7ed;
}

.sidebar-menu {
  border-right: none;
  height: 100%;
}

.mobile-nav-menu {
  border-right: none;
  height: 100%;
}

.mobile-nav-drawer :deep(.el-drawer__body) {
  padding: 0;
}

.main-content {
  padding: 20px;
  background-color: #f5f7fa;
}

.welcome-card {
  background: white;
  border-radius: 8px;
  padding: 30px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.admin-dashboard-tabs {
  width: 100%;
}

.welcome-card h1 {
  margin-bottom: 10px;
  color: #333;
}

.welcome-card p {
  color: #606266;
  margin-bottom: 30px;
}

.dashboard-announcement-banner {
  margin-bottom: 18px;
}

.announcement-slide {
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 8px;
  padding: 14px 20px;
  border-radius: 8px;
  background: linear-gradient(90deg, #ecf5ff 0%, #f0f9eb 100%);
  border: 1px solid #d9ecff;
  cursor: pointer;
}

.announcement-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.announcement-content {
  font-size: 14px;
  color: #606266;
  white-space: pre-wrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.announcement-meta {
  font-size: 12px;
  color: #606266;
}

.table-pagination {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}

.traffic-toolbar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 8px;
}

.traffic-label {
  font-size: 14px;
  color: #606266;
}

.traffic-range {
  font-size: 13px;
  color: #606266;
  margin: 0 0 12px;
}

.stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
  margin-top: 20px;
}

.stat-card {
  border-radius: 8px;
}

.stat-card-clickable {
  cursor: pointer;
  transition: box-shadow 0.2s;
}

.stat-card-clickable:hover {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
}

.stat-card-clickable:focus-visible {
  outline: 2px solid #409eff;
  outline-offset: 2px;
}

.stat-content {
  display: flex;
  align-items: center;
}

.stat-icon {
  font-size: 36px;
  margin-right: 15px;
}

.stat-value {
  font-size: 24px;
  font-weight: bold;
  color: #333;
}

.stat-label {
  font-size: 14px;
  color: #606266;
  margin-top: 4px;
}

@media (max-width: 768px) {
  .dashboard-container {
    height: auto;
    min-height: 100vh;
  }

  .header {
    height: auto;
    min-height: 56px;
    padding: 8px 12px;
    gap: 8px;
  }

  .header-left h2 {
    font-size: 18px;
  }

  .mobile-menu-btn {
    display: inline-flex;
  }

  .user-info {
    padding: 4px 0;
  }

  .username {
    display: none;
  }

  .body-shell {
    display: flex;
    flex-direction: column;
  }

  .sidebar {
    width: 100% !important;
    border-right: none;
    border-bottom: 1px solid #e4e7ed;
  }

  .sidebar-menu {
    height: auto;
  }

  .main-content {
    padding: 12px;
  }

  .welcome-card {
    padding: 16px;
  }

  .welcome-card p {
    margin-bottom: 16px;
  }

  .stats {
    grid-template-columns: 1fr;
    gap: 12px;
  }

  .table-pagination {
    justify-content: flex-start;
  }
}
</style>
