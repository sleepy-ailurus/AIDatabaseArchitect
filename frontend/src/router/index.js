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
        path: 'projects/:id/concept-model',
        name: 'ConceptModel',
        component: () => import('@/views/concept-model/index.vue'),
        meta: { title: 'menu.conceptModel', icon: 'DataAnalysis', hidden: true }
      },
      {
        path: 'projects/:id/ai-suggestions',
        name: 'AISuggestions',
        component: () => import('@/views/ai-suggestions/index.vue'),
        meta: { title: 'menu.aiSuggestions', icon: 'MagicStick', hidden: true }
      },
      {
        path: 'projects/:id/schema-history',
        name: 'SchemaHistory',
        component: () => import('@/views/schema-history/index.vue'),
        meta: { title: 'menu.schemaHistory', icon: 'Clock', hidden: true }
      },
      {
        path: 'projects/:id/review',
        name: 'SchemaReview',
        component: () => import('@/views/review/index.vue'),
        meta: { title: 'menu.review', icon: 'DocumentChecked', hidden: true }
      },
      {
        path: 'projects/:id/comments',
        name: 'Comments',
        component: () => import('@/views/comments/index.vue'),
        meta: { title: 'menu.comments', icon: 'ChatLineRound', hidden: true }
      },
      {
        path: 'projects/:id/sensitive',
        name: 'Sensitive',
        component: () => import('@/views/sensitive/index.vue'),
        meta: { title: 'menu.sensitive', icon: 'Lock', hidden: true }
      },
      {
        path: 'projects/:id/data-gen',
        name: 'DataGen',
        component: () => import('@/views/data-gen/index.vue'),
        meta: { title: 'menu.dataGen', icon: 'DataLine', hidden: true }
      },
      {
        path: 'projects/:id/domains',
        name: 'Domains',
        component: () => import('@/views/domains/index.vue'),
        meta: { title: 'menu.domains', icon: 'Collection', hidden: true }
      },
      {
        path: 'projects/:id/lineage',
        name: 'Lineage',
        component: () => import('@/views/lineage/index.vue'),
        meta: { title: 'menu.lineage', icon: 'Share', hidden: true }
      },
      {
        path: 'projects/:id/design-doc',
        name: 'DesignDoc',
        component: () => import('@/views/design-doc/index.vue'),
        meta: { title: 'menu.designDoc', icon: 'Document', hidden: true }
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
