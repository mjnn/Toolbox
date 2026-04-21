<template>
  <div class="app-root" :class="{ 'with-ticker': showGlobalTicker && globalAnnouncements.length > 0 }">
    <div v-if="showGlobalTicker && globalAnnouncements.length > 0" class="global-announcement-bar">
      <div class="global-announcement-track" :style="trackStyle">
        <span
          v-for="item in duplicatedAnnouncements"
          :key="`ticker-${item.id}-${item._idx}`"
          class="global-announcement-item"
          :style="announcementItemStyle(item)"
        >
          【{{ priorityLabelMap[item.priority] || '通知' }}】{{ item.title }}：{{ item.content }}
        </span>
      </div>
    </div>
    <router-view />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { usersApi } from '@/api/users'
import type { ToolAnnouncementInDB } from '@/api/types'

const route = useRoute()
const authStore = useAuthStore()
const globalAnnouncements = ref<ToolAnnouncementInDB[]>([])

const showGlobalTicker = computed(() => {
  if (!authStore.accessToken) return false
  return route.path !== '/login' && route.path !== '/register'
})

const duplicatedAnnouncements = computed(() => {
  const rows = globalAnnouncements.value
  if (rows.length === 0) return []
  return [...rows, ...rows].map((item, idx) => ({ ...item, _idx: idx }))
})

const priorityLabelMap: Record<string, string> = {
  urgent: '紧急维护',
  notice: '通知',
  reminder: '提醒',
}

const priorityStyleMap: Record<string, { text: string; bg: string }> = {
  urgent: { text: '#ffffff', bg: '#c62828' },
  notice: { text: '#102a43', bg: '#e8f4fd' },
  reminder: { text: '#5f370e', bg: '#fff4e5' },
}

const tickerDurationSeconds = computed(() => {
  const rows = globalAnnouncements.value
  if (!rows.length) return 45
  const minSpeed = Math.min(...rows.map((item) => Number(item.scroll_speed_seconds || 45)))
  return Math.min(300, Math.max(10, minSpeed))
})

const trackStyle = computed(() => ({
  animationDuration: `${tickerDurationSeconds.value}s`,
}))

const announcementItemStyle = (item: ToolAnnouncementInDB) => {
  const p = priorityStyleMap[item.priority] || priorityStyleMap.notice
  return {
    color: p.text,
    backgroundColor: p.bg,
    fontSize: `${Number(item.font_size_px || 14)}px`,
    fontFamily: item.font_family || 'inherit',
  }
}

const loadGlobalAnnouncements = async () => {
  if (!showGlobalTicker.value) {
    globalAnnouncements.value = []
    return
  }
  try {
    const res = await usersApi.getMyAnnouncements(0, 20)
    globalAnnouncements.value = res.items || []
  } catch {
    globalAnnouncements.value = []
  }
}

watch(
  () => route.fullPath,
  async () => {
    await loadGlobalAnnouncements()
  }
)

onMounted(async () => {
  await loadGlobalAnnouncements()
})
</script>

<style scoped>
.app-root {
  width: 100%;
  min-height: 100vh;
}

.app-root.with-ticker {
  padding-top: 38px;
}

.global-announcement-bar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 3000;
  height: 38px;
  display: flex;
  align-items: center;
  overflow: hidden;
  background: linear-gradient(90deg, #fff7e6 0%, #fff1f0 100%);
  border-bottom: 1px solid #ffd8bf;
}

.global-announcement-track {
  display: inline-flex;
  white-space: nowrap;
  animation: ticker-scroll 45s linear infinite;
}

.global-announcement-item {
  margin-right: 22px;
  padding: 4px 10px;
  border-radius: 4px;
}

@keyframes ticker-scroll {
  0% {
    transform: translateX(0);
  }
  100% {
    transform: translateX(-50%);
  }
}
</style>
