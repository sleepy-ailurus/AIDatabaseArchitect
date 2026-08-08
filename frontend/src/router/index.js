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
        meta: { title: '项目总览', icon: 'DataAnalysis' }
      },
      {
        path: 'projects',
        name: 'Projects',
        component: () => import('@/views/project/list.vue'),
        meta: { title: '项目列表', icon: 'FolderOpened' }
      },
      {
        path: 'projects/:id/connection',
        name: 'ConnectionConfig',
        component: () => import('@/views/project/connection.vue'),
        meta: { title: '数据库连接', icon: 'Connection', hidden: true }
      },
      {
        path: 'projects/:id/er-model',
        name: 'ERModel',
        component: () => import('@/views/er-model/index.vue'),
        meta: { title: 'ER模型编辑器', icon: 'Share', hidden: true }
      },
      {
        path: 'projects/:id/ai-suggestions',
        name: 'AISuggestions',
        component: () => import('@/views/ai-suggestions/index.vue'),
        meta: { title: 'AI关系建议', icon: 'MagicStick', hidden: true }
      },
      {
        path: 'projects/:id/export',
        name: 'DocumentExport',
        component: () => import('@/views/export/index.vue'),
        meta: { title: '文档导出', icon: 'Download', hidden: true }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
