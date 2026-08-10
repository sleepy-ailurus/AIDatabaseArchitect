<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <div class="page-title">{{ t('dashboard.title') }}</div>
        <div class="page-subtitle">{{ t('dashboard.subtitle') }}</div>
      </div>
      <div>
        <el-button type="primary" :icon="Plus" @click="showCreateDialog = true">
          {{ t('dashboard.newProject') }}
        </el-button>
      </div>
    </div>

    <el-row :gutter="16" class="stat-cards" v-loading="loading">
      <el-col :span="6">
        <div class="stat-card">
          <div class="stat-icon" style="background: linear-gradient(135deg, rgba(59, 130, 246, 0.15), rgba(59, 130, 246, 0.05));">
            <el-icon :size="24" color="#3B82F6"><FolderOpened /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.totalProjects }}</div>
            <div class="stat-label">{{ t('dashboard.totalProjects') }}</div>
          </div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card">
          <div class="stat-icon" style="background: linear-gradient(135deg, rgba(16, 185, 129, 0.15), rgba(16, 185, 129, 0.05));">
            <el-icon :size="24" color="#10B981"><Grid /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.totalTables }}</div>
            <div class="stat-label">{{ t('dashboard.totalTables') }}</div>
          </div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card">
          <div class="stat-icon" style="background: linear-gradient(135deg, rgba(99, 102, 241, 0.15), rgba(99, 102, 241, 0.05));">
            <el-icon :size="24" color="#6366F1"><Share /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.totalRelations }}</div>
            <div class="stat-label">{{ t('dashboard.totalRelations') }}</div>
          </div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card">
          <div class="stat-icon" style="background: linear-gradient(135deg, rgba(245, 158, 11, 0.15), rgba(245, 158, 11, 0.05));">
            <el-icon :size="24" color="#F59E0B"><MagicStick /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.aiSuggestions }}</div>
            <div class="stat-label">{{ t('dashboard.aiSuggestionsPending') }}</div>
          </div>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top: 16px;">
      <el-col :span="16">
        <div class="card">
          <div class="flex-between mb-16">
            <div>
              <div style="font-size: 16px; font-weight: 600;">{{ t('dashboard.recentProjects') }}</div>
              <div style="font-size: 12px; color: #94A3B8; margin-top: 2px;">{{ t('dashboard.recentProjectsDesc') }}</div>
            </div>
            <el-button text type="primary" @click="$router.push('/projects')">
              {{ t('dashboard.viewAll') }} <el-icon style="margin-left: 2px;"><ArrowRight /></el-icon>
            </el-button>
          </div>

          <el-empty v-if="!loading && recentProjects.length === 0" :description="t('dashboard.noProjects')" />
          <el-table v-else :data="recentProjects" style="width: 100%" :show-header="false">
            <el-table-column>
              <template #default="{ row }">
                <div class="project-row" @click="goToProject(row)">
                  <div class="project-icon" :style="{ background: getProjectColor(row.id) + '20' }">
                    <el-icon :size="20" :color="getProjectColor(row.id)"><DataBase /></el-icon>
                  </div>
                  <div class="project-info">
                    <div class="project-name">{{ tData('projectNames', row.name) }}</div>
                    <div class="project-meta">
                      <el-tag size="small" effect="plain" :type="getDbTypeTag(row.db_type || row.dbType)">
                        {{ getDbTypeLabel(row.db_type || row.dbType) }}
                      </el-tag>
                      <span style="color: #94A3B8; margin-left: 8px;">
                        {{ row.table_count || row.tables || 0 }} {{ t('dashboard.tables') }} · {{ row.relation_count || row.relations || 0 }} {{ t('dashboard.relations') }}
                      </span>
                    </div>
                  </div>
                  <div class="project-status">
                    <el-tag :type="getStatusTag(row.status)" effect="light" size="small">
                      {{ getStatusLabel(row.status) }}
                    </el-tag>
                  </div>
                  <div class="project-time">
                    <div style="font-size: 12px; color: #94A3B8;">{{ t('dashboard.updatedAt') }}</div>
                    <div style="font-size: 13px; color: #64748B; margin-top: 2px;">{{ formatTime(row.updated_at || row.updatedAt) }}</div>
                  </div>
                  <el-icon :size="18" color="#CBD5E1" class="arrow-icon"><ArrowRight /></el-icon>
                </div>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-col>

      <el-col :span="8">
        <div class="card">
          <div class="mb-16">
            <div style="font-size: 16px; font-weight: 600;">{{ t('dashboard.quickStart') }}</div>
            <div style="font-size: 12px; color: #94A3B8; margin-top: 2px;">{{ t('dashboard.quickStartDesc') }}</div>
          </div>

          <div class="step-list">
            <div class="step-item" :class="{ done: recentProjects.length > 0 }">
              <div class="step-number done"><el-icon><Check /></el-icon></div>
              <div class="step-content">
                <div class="step-title">{{ t('dashboard.step1') }}</div>
                <div class="step-desc">{{ t('dashboard.step1Desc') }}</div>
              </div>
            </div>
            <div class="step-item">
              <div class="step-number">2</div>
              <div class="step-content">
                <div class="step-title">{{ t('dashboard.step2') }}</div>
                <div class="step-desc">{{ t('dashboard.step2Desc') }}</div>
              </div>
            </div>
            <div class="step-item">
              <div class="step-number">3</div>
              <div class="step-content">
                <div class="step-title">{{ t('dashboard.step3') }}</div>
                <div class="step-desc">{{ t('dashboard.step3Desc') }}</div>
              </div>
            </div>
            <div class="step-item">
              <div class="step-number">4</div>
              <div class="step-content">
                <div class="step-title">{{ t('dashboard.step4') }}</div>
                <div class="step-desc">{{ t('dashboard.step4Desc') }}</div>
              </div>
            </div>
            <div class="step-item">
              <div class="step-number">5</div>
              <div class="step-content">
                <div class="step-title">{{ t('dashboard.step5') }}</div>
                <div class="step-desc">{{ t('dashboard.step5Desc') }}</div>
              </div>
            </div>
          </div>
        </div>

        <div class="card mt-16">
          <div class="mb-16">
            <div style="font-size: 16px; font-weight: 600;">{{ t('dashboard.taskStatus') }}</div>
          </div>
          <div class="task-list" v-if="recentProjects.length > 0">
            <div class="task-item" v-for="p in recentProjects.slice(0, 3)" :key="p.id">
              <div class="flex-between">
                <div class="task-name">{{ tData('projectNames', p.name) }}</div>
                <el-tag size="small" :type="getStatusTag(p.status)">{{ getStatusLabel(p.status) }}</el-tag>
              </div>
              <div style="font-size: 12px; color: #94A3B8; margin-top: 4px;">
                {{ p.table_count || p.tables || 0 }} {{ t('dashboard.tables') }} · {{ p.relation_count || p.relations || 0 }} {{ t('dashboard.relations') }}
              </div>
            </div>
          </div>
          <el-empty v-else :description="t('dashboard.noTasks')" :image-size="60" />
        </div>
      </el-col>
    </el-row>

    <el-dialog v-model="showCreateDialog" :title="t('project.form.titleNew')" width="560px" :close-on-click-modal="false">
      <el-form :model="createForm" :rules="createRules" ref="createFormRef" label-width="100px" style="margin-top: 8px;">
        <el-form-item :label="t('project.form.name')" prop="name">
          <el-input v-model="createForm.name" :placeholder="t('project.form.namePlaceholder')" />
        </el-form-item>
        <el-form-item :label="t('project.form.description')">
          <el-input v-model="createForm.description" type="textarea" :rows="3" :placeholder="t('project.form.descriptionPlaceholder')" />
        </el-form-item>
        <el-form-item :label="t('project.form.dbType')" prop="db_type">
          <el-select v-model="createForm.db_type" style="width: 100%;" :placeholder="t('project.form.selectDbType')">
            <el-option label="MySQL 8.x" value="mysql">
              <div class="db-option">
                <el-icon color="#4479A1"><Coin /></el-icon>
                <span>MySQL 8.x</span>
                <el-tag size="small" type="success">{{ t('project.form.recommended') }}</el-tag>
              </div>
            </el-option>
            <el-option label="PostgreSQL 14+" value="postgresql" disabled>
              <div class="db-option">
                <el-icon color="#336791"><Coin /></el-icon>
                <span>PostgreSQL 14+</span>
                <el-tag size="small" type="info">{{ t('connection.soonSupported') }}</el-tag>
              </div>
            </el-option>
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">{{ t('project.form.cancel') }}</el-button>
        <el-button type="primary" :loading="creating" @click="handleCreate">{{ t('project.form.create') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import { useProjectStore } from '@/stores/project'
import { createProject } from '@/api/project'
import { useDataI18n } from '@/i18n'

const { t, locale } = useI18n()
const { tData } = useDataI18n()
dayjs.extend(relativeTime)

const router = useRouter()
const projectStore = useProjectStore()
const showCreateDialog = ref(false)
const loading = ref(false)
const creating = ref(false)
const createFormRef = ref()

const stats = reactive({
  totalProjects: 0,
  totalTables: 0,
  totalRelations: 0,
  aiSuggestions: 0
})

const recentProjects = ref([])

const createForm = reactive({
  name: '',
  description: '',
  db_type: 'mysql'
})

const createRules = {
  name: [{ required: true, message: () => t('project.form.nameRequired'), trigger: 'blur' }],
  db_type: [{ required: true, message: () => t('project.form.dbTypeRequired'), trigger: 'change' }]
}

const projectColors = ['#3B82F6', '#10B981', '#F59E0B', '#6366F1', '#EC4899', '#8B5CF6']

const getProjectColor = (id) => {
  const num = Number(id) || 0
  return projectColors[num % projectColors.length]
}

const getDbTypeTag = (type) => {
  return type === 'mysql' ? 'primary' : 'success'
}

const getDbTypeLabel = (type) => {
  const map = { mysql: 'MySQL', postgresql: 'PostgreSQL' }
  return map[type] || type || 'MySQL'
}

const getStatusTag = (status) => {
  const map = {
    analyzing: 'warning',
    completed: 'success',
    pending: 'info',
    draft: 'info',
    connected: 'primary'
  }
  return map[status] || 'info'
}

const getStatusLabel = (status) => {
  const keyMap = {
    analyzing: 'dashboard.status.analyzing',
    completed: 'dashboard.status.completed',
    pending: 'dashboard.status.pending',
    draft: 'dashboard.status.draft',
    connected: 'dashboard.status.connected'
  }
  return t(keyMap[status] || 'dashboard.status.draft')
}

const formatTime = (time) => {
  if (!time) return '-'
  try {
    dayjs.locale(locale.value === 'zh-CN' ? 'zh-cn' : 'en')
    return dayjs(time).fromNow()
  } catch {
    return String(time)
  }
}

const loadData = async () => {
  loading.value = true
  try {
    await projectStore.fetchProjects()
    recentProjects.value = projectStore.projects.slice(0, 5)
    stats.totalProjects = projectStore.projects.length
    let totalTables = 0
    let totalRelations = 0
    projectStore.projects.forEach(p => {
      totalTables += (p.table_count || p.tables || 0)
      totalRelations += (p.relation_count || p.relations || 0)
    })
    stats.totalTables = totalTables
    stats.totalRelations = totalRelations
    stats.aiSuggestions = projectStore.projects.reduce((sum, p) => sum + (p.suggestion_count || p.suggestions || 0), 0)

    try {
      const apiStats = await projectStore.fetchStats()
      if (apiStats) {
        stats.totalProjects = apiStats.total_projects ?? stats.totalProjects
        stats.totalTables = apiStats.total_tables ?? stats.totalTables
        stats.totalRelations = apiStats.total_relations ?? stats.totalRelations
        stats.aiSuggestions = apiStats.ai_suggestions ?? stats.aiSuggestions
      }
    } catch {
      // stats API optional
    }
  } finally {
    loading.value = false
  }
}

const goToProject = (row) => {
  const id = row.id
  if (row.status === 'draft' || !row.status) {
    router.push(`/projects/${id}/connection`)
  } else {
    router.push(`/projects/${id}/er-model`)
  }
}

const handleCreate = async () => {
  try {
    await createFormRef.value.validate()
  } catch {
    return
  }
  creating.value = true
  try {
    const data = await createProject({
      name: createForm.name,
      description: createForm.description,
      db_type: createForm.db_type
    })
    ElMessage.success(t('project.list.projectCreated'))
    showCreateDialog.value = false
    createForm.name = ''
    createForm.description = ''
    createForm.db_type = 'mysql'
    const newId = data?.id || data?.project_id
    if (newId) {
      router.push(`/projects/${newId}/connection`)
    } else {
      loadData()
    }
  } catch (e) {
    // error handled by interceptor
  } finally {
    creating.value = false
  }
}

onMounted(() => {
  loadData()
})
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;
.stat-cards {
  .stat-card {
    background: $bg-white;
    border-radius: $radius-lg;
    padding: 20px;
    display: flex;
    align-items: center;
    gap: 16px;
    box-shadow: $shadow-sm;
    transition: $transition-base;

    &:hover {
      box-shadow: $shadow-md;
      transform: translateY(-1px);
    }

    .stat-icon {
      width: 52px;
      height: 52px;
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }

    .stat-info {
      flex: 1;
      min-width: 0;
    }

    .stat-value {
      font-size: 24px;
      font-weight: 700;
      color: $text-primary;
      line-height: 1.2;
    }

    .stat-label {
      font-size: 12px;
      color: $text-secondary;
      margin-top: 4px;
    }
  }
}

.project-row {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 8px;
  cursor: pointer;
  border-radius: $radius-md;
  transition: $transition-base;

  &:hover {
    background: $bg-light;

    .arrow-icon {
      color: $primary-color;
      transform: translateX(2px);
    }
  }

  .project-icon {
    width: 44px;
    height: 44px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }

  .project-info {
    flex: 1;
    min-width: 0;
  }

  .project-name {
    font-size: 14px;
    font-weight: 600;
    color: $text-primary;
  }

  .project-meta {
    display: flex;
    align-items: center;
    margin-top: 6px;
  }

  .project-status {
    width: 80px;
  }

  .project-time {
    width: 100px;
    text-align: right;
  }

  .arrow-icon {
    transition: $transition-base;
  }
}

.step-list {
  .step-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px 0;

    & + & {
      border-top: 1px dashed $border-light;
    }

    .step-number {
      width: 28px;
      height: 28px;
      border-radius: 50%;
      background: $bg-light;
      color: $text-secondary;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 12px;
      font-weight: 600;
      flex-shrink: 0;

      &.done {
        background: rgba(16, 185, 129, 0.15);
        color: $success-color;
      }
    }

    .step-content {
      flex: 1;
      min-width: 0;
    }

    .step-title {
      font-size: 13px;
      font-weight: 600;
      color: $text-primary;
    }

    .step-desc {
      font-size: 11px;
      color: $text-secondary;
      margin-top: 2px;
    }
  }
}

.task-list {
  .task-item {
    padding: 14px 0;

    & + & {
      border-top: 1px dashed $border-light;
    }

    .task-name {
      font-size: 13px;
      font-weight: 500;
      color: $text-primary;
    }
  }
}

.db-option {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>

<style lang="scss">
html.dark {
  .stat-cards .stat-card {
    background: #252526 !important;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.2) !important;

    &:hover {
      box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3) !important;
    }

    .stat-value {
      color: #f8fafc !important;
    }

    .stat-label {
      color: #94a3b8 !important;
    }
  }

  .project-row {
    &:hover {
      background: #3c3c3c !important;
    }

    .project-name {
      color: #f8fafc !important;
    }
  }

  .step-list .step-item {
    & + .step-item {
      border-color: #3c3c3c !important;
    }

    .step-number {
      background: #3c3c3c !important;
      color: #94a3b8 !important;

      &.done {
        background: rgba(16, 185, 129, 0.15) !important;
        color: #34d399 !important;
      }
    }

    .step-title {
      color: #f8fafc !important;
    }

    .step-desc {
      color: #94a3b8 !important;
    }
  }

  .task-list .task-item {
    & + .task-item {
      border-color: #3c3c3c !important;
    }

    .task-name {
      color: #f8fafc !important;
    }
  }
}
</style>
