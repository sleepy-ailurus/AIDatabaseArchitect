import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    component: () => import('@/layout/MainLayout.vue'),
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/dashboard/index.vue'),
        meta: { title: 'menu.dashboard', icon: 'DataAnalysis' }
      },
      {
        path: 'projects',
        name: 'Projects',
        component: () => import('@/views/project/list.vue'),
        meta: { title: 'menu.projects', icon: 'FolderOpened' }
      },
      {
        path: 'projects/:id/connection',
        name: 'ConnectionConfig',
        component: () => import('@/views/project/connection.vue'),
        meta: { title: 'menu.connection', icon: 'Connection', hidden: true }
      },
      {
        path: 'projects/:id/er-model',
        name: 'ERModel',
        component: () => import('@/views/er-model/index.vue'),
        meta: { title: 'menu.erModel', icon: 'Share', hidden: true }
      },
      {
        path: 'projects/:id/ai-suggestions',
        name: 'AISuggestions',
        component: () => import('@/views/ai-suggestions/index.vue'),
        meta: { title: 'menu.aiSuggestions', icon: 'MagicStick', hidden: true }
      },
      {
        path: 'projects/:id/export',
        name: 'DocumentExport',
        component: () => import('@/views/export/index.vue'),
        meta: { title: 'menu.export', icon: 'Download', hidden: true }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
