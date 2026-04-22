import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { authApi } from '@/api/auth'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/Register.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    name: 'Dashboard',
    component: () => import('@/views/Dashboard.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/welcome',
    name: 'Welcome',
    component: () => import('@/views/Tools.vue'),
    meta: { requiresAuth: false, publicTools: true }
  },
  {
    path: '/users',
    name: 'Users',
    component: () => import('@/views/Users.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/tools',
    name: 'Tools',
    component: () => import('@/views/Tools.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/my-tools',
    name: 'MyTools',
    component: () => import('@/views/Tools.vue'),
    meta: { requiresAuth: true, toolsView: 'my' }
  },
  {
    path: '/notifications',
    name: 'Notifications',
    component: () => import('@/views/Notifications.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/profile',
    name: 'Profile',
    component: () => import('@/views/Profile.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/tools/:toolId/usage-logs',
    redirect: (to) => ({ path: `/tools/${to.params.toolId}/manage` })
  },
  {
    path: '/tools/:toolId/manage',
    name: 'ToolManage',
    component: () => import('@/views/ToolManage.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/tools/:toolId',
    name: 'ToolDetail',
    component: () => import('@/views/ToolDetail.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/permissions',
    name: 'Permissions',
    component: () => import('@/views/Permissions.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/audit-logs',
    name: 'AuditLogs',
    component: () => import('@/views/AuditLogs.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/feedback-admin',
    name: 'FeedbackAdmin',
    component: () => import('@/views/FeedbackAdmin.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/system-db-optimization',
    name: 'SystemDbOptimization',
    component: () => import('@/views/DatabaseOptimization.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()
  const isAuthenticated = authStore.isAuthenticated

  if (to.meta.requiresAuth && !isAuthenticated) {
    next('/welcome')
    return
  }
  if ((to.path === '/login' || to.path === '/register') && isAuthenticated) {
    next('/')
    return
  }

  if (to.meta.requiresAdmin && isAuthenticated) {
    if (!authStore.userInfo) {
      try {
        const user = await authApi.getCurrentUser()
        authStore.setUserInfo(user)
      } catch {
        next('/login')
        return
      }
    }
    if (!authStore.userInfo?.is_superuser) {
      next('/')
      return
    }
  }

  next()
})

export default router
