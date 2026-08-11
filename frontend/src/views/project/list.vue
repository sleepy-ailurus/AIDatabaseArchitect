<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <div class="page-title">{{ t('project.list.title') }}</div>
        <div class="page-subtitle">{{ t('project.list.subtitle') }}</div>
      </div>
      <div class="header-actions">
        <el-input v-model="searchKey" :placeholder="t('project.list.searchPlaceholder')" style="width: 260px; margin-right: 12px;" clearable>
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-select v-model="statusFilter" :placeholder="t('project.list.status')" style="width: 120px; margin-right: 12px;" clearable>
          <el-option :label="t('dashboard.status.analyzing')" value="analyzing" />
          <el-option :label="t('dashboard.status.completed')" value="completed" />
          <el-option :label="t('dashboard.status.pending')" value="pending" />
          <el-option :label="t('dashboard.status.draft')" value="draft" />
        </el-select>
        <el-button type="primary" :icon="Plus" @click="openCreate">
          {{ t('project.list.newProject') }}
        </el-button>
      </div>
    </div>

    <div v-loading="loading">
      <div v-if="!loading && filteredProjects.length === 0" class="empty-state">
        <el-empty :description="t('project.list.emptyDesc')">
          <el-button type="primary" :icon="Plus" @click="openCreate">{{ t('project.list.newProject') }}</el-button>
        </el-empty>
      </div>

      <div v-else class="projects-grid">
        <div v-for="p in filteredProjects" :key="p.id" class="project-card" @click="openProject(p)">
          <div class="card-header">
            <div class="project-badge" :style="{ background: getProjectColor(p.id) + '15' }">
              <el-icon :size="22" :color="getProjectColor(p.id)"><DataBase /></el-icon>
            </div>
            <el-dropdown trigger="click" @click.stop>
              <el-button text circle size="small" @click.stop>
                <el-icon><MoreFilled /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item @click.stop="openProject(p)"><el-icon><Share /></el-icon> {{ t('project.list.actions.openER') }}</el-dropdown-item>
                  <el-dropdown-item @click.stop="goConnection(p)"><el-icon><Connection /></el-icon> {{ t('project.list.actions.connection') }}</el-dropdown-item>
                  <el-dropdown-item @click.stop="openVersions(p)"><el-icon><Clock /></el-icon> {{ t('project.list.actions.versions') }}</el-dropdown-item>
                  <el-dropdown-item divided style="color: #EF4444;" @click.stop="handleDelete(p)">
                    <el-icon><Delete /></el-icon> {{ t('project.list.actions.delete') }}
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>

          <div class="card-body">
            <div class="project-title">{{ tData('projectNames', p.name) }}</div>
            <div class="project-desc" v-if="p.description">{{ p.description }}</div>
            <div class="project-desc empty" v-else>{{ t('project.list.noDescription') }}</div>
          </div>

          <div class="card-stats">
            <div class="stat">
              <el-icon :size="14" color="#64748B"><Grid /></el-icon>
              <span>{{ p.table_count || p.tables || 0 }} {{ t('dashboard.tables') }}</span>
            </div>
            <div class="stat">
              <el-icon :size="14" color="#64748B"><Share /></el-icon>
              <span>{{ p.relation_count || p.relations || 0 }} {{ t('dashboard.relations') }}</span>
            </div>
            <div class="stat">
              <el-icon :size="14" color="#64748B"><MagicStick /></el-icon>
              <span>{{ p.suggestion_count || p.suggestions || 0 }} {{ t('project.list.suggestions') }}</span>
            </div>
          </div>

          <div class="card-footer">
            <div class="footer-left">
              <el-tag size="small" effect="plain" :type="getDbTypeTag(p.db_type || p.dbType)">
                {{ getDbTypeLabel(p.db_type || p.dbType) }}
              </el-tag>
              <el-tag size="small" :type="getStatusTag(p.status)" effect="light">
                {{ getStatusLabel(p.status) }}
              </el-tag>
            </div>
            <div class="footer-right">
              <span style="font-size: 12px; color: #94A3B8;">{{ formatTime(p.updated_at || p.updatedAt) }}</span>
            </div>
          </div>
        </div>

        <div class="project-card add-card" @click="openCreate">
          <div class="add-icon">
            <el-icon :size="40" color="#CBD5E1"><Plus /></el-icon>
          </div>
          <div style="font-size: 14px; color: #94A3B8; margin-top: 12px; font-weight: 500;">{{ t('project.list.newProject') }}</div>
          <div style="font-size: 12px; color: #CBD5E1; margin-top: 4px;">{{ t('project.list.newProjectDesc') }}</div>
        </div>
      </div>
    </div>

    <el-dialog v-model="showCreate" :title="t('project.form.title')" width="560px" :close-on-click-modal="false">
      <el-form :model="createForm" :rules="createRules" ref="createFormRef" label-width="100px" style="margin-top: 8px;">
        <el-form-item :label="t('project.form.name')" prop="name">
          <el-input v-model="createForm.name" :placeholder="t('project.form.namePlaceholder')" />
        </el-form-item>
        <el-form-item :label="t('project.form.description')">
          <el-input v-model="createForm.description" type="textarea" :rows="3" :placeholder="t('project.form.descriptionPlaceholder')" />
        </el-form-item>
        <el-form-item :label="t('project.form.dbType')" prop="db_type">
          <el-select v-model="createForm.db_type" style="width: 100%;" :placeholder="t('project.form.selectDbType')">
            <el-option label="MySQL 8.x" value="mysql" />
            <el-option label="PostgreSQL 14+" value="postgresql" disabled />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">{{ t('project.form.cancel') }}</el-button>
        <el-button type="primary" :loading="creating" @click="handleCreate">{{ t('project.form.create') }}</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showVersions" :title="`${t('project.list.versionHistory')} - ${tData('projectNames', versionProject?.name) || ''}`" width="640px" :close-on-click-modal="false">
      <div v-loading="versionLoading" class="version-list">
        <div v-if="!versions.length" class="version-empty">
          <el-empty :description="t('project.list.noVersions')" :image-size="80" />
        </div>
        <div v-else>
          <div v-for="v in versions" :key="v.id" class="version-item">
            <div class="version-info">
              <div class="version-header">
                <el-tag size="small" type="primary" effect="light">V{{ v.version_number }}</el-tag>
                <span class="version-time">{{ formatTime(v.created_at) }}</span>
              </div>
              <div class="version-note">{{ v.note || t('project.list.noNote') }}</div>
            </div>
            <div class="version-actions">
              <el-button type="danger" link size="small" :loading="deleteId === v.id" @click="deleteVersionItem(v)">
                {{ t('project.list.deleteVersion') }}
              </el-button>
              <el-button type="primary" link size="small" :loading="restoreId === v.id" @click="restoreVersion(v)">
                {{ t('project.list.restoreVersion') }}
              </el-button>
            </div>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import dayjs from 'dayjs'
import { useProjectStore } from '@/stores/project'
import { createProject as createProjectApi, deleteProject as deleteProjectApi } from '@/api/project'
import { getVersions, getVersion, saveERModel, deleteVersion } from '@/api/erModel'
import { useDataI18n } from '@/i18n'

const { t, locale } = useI18n()
const { tData } = useDataI18n()

const router = useRouter()
const projectStore = useProjectStore()
const searchKey = ref('')
const statusFilter = ref('')
const showCreate = ref(false)
const loading = ref(false)
const creating = ref(false)
const createFormRef = ref()

const showVersions = ref(false)
const versionLoading = ref(false)
const versionProject = ref(null)
const versions = ref([])
const restoreId = ref(null)
const deleteId = ref(null)

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

const getDbTypeTag = (type) => type === 'mysql' ? 'primary' : 'success'

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

const filteredProjects = computed(() => {
  return projectStore.projects.filter(p => {
    const matchSearch = !searchKey.value || (p.name || '').includes(searchKey.value)
    let matchStatus = true
    if (statusFilter.value) {
      matchStatus = p.status === statusFilter.value
    }
    return matchSearch && matchStatus
  })
})

const loadProjects = async () => {
  loading.value = true
  try {
    await projectStore.fetchProjects()
  } finally {
    loading.value = false
  }
}

const openProject = (p) => {
  const needsConnection = !p.db_type || p.status === 'created' || p.status === 'draft'
  if (needsConnection) {
    router.push(`/projects/${p.id}/connection`)
  } else {
    router.push(`/projects/${p.id}/er-model`)
  }
}

const goConnection = (p) => {
  router.push(`/projects/${p.id}/connection`)
}

const openCreate = () => {
  createForm.name = ''
  createForm.description = ''
  createForm.db_type = 'mysql'
  showCreate.value = true
}

const handleCreate = async () => {
  try {
    await createFormRef.value.validate()
  } catch {
    return
  }
  creating.value = true
  try {
    const data = await createProjectApi({
      name: createForm.name,
      description: createForm.description,
      db_type: createForm.db_type
    })
    ElMessage.success(t('project.list.projectCreated'))
    showCreate.value = false
    const newId = data?.id || data?.project_id
    if (newId) {
      router.push(`/projects/${newId}/connection`)
    } else {
      loadProjects()
    }
  } catch {
    // handled by interceptor
  } finally {
    creating.value = false
  }
}

const handleDelete = async (p) => {
  try {
    await ElMessageBox.confirm(
      t('project.list.deleteConfirm', { name: tData('projectNames', p.name) }),
      t('project.list.deleteTitle'),
      { type: 'warning', confirmButtonText: t('project.list.confirmDelete'), cancelButtonText: t('project.form.cancel') }
    )
  } catch {
    return
  }
  try {
    await deleteProjectApi(p.id)
    ElMessage.success(t('project.list.projectDeleted'))
    loadProjects()
  } catch {
    // handled by interceptor
  }
}

const openVersions = (p) => {
  versionProject.value = p
  showVersions.value = true
  loadVersions(p.id)
}

const loadVersions = async (projectId) => {
  versionLoading.value = true
  try {
    const data = await getVersions(projectId)
    versions.value = Array.isArray(data) ? data : (data?.items || [])
  } catch {
    versions.value = []
  } finally {
    versionLoading.value = false
  }
}

const restoreVersion = async (v) => {
  try {
    await ElMessageBox.confirm(
      t('project.list.restoreConfirm', { name: versionProject.value.name, version: v.version_number }),
      t('project.list.restoreTitle'),
      { type: 'warning', confirmButtonText: t('project.list.confirmRestore'), cancelButtonText: t('project.form.cancel') }
    )
  } catch {
    return
  }
  restoreId.value = v.id
  try {
    const versionData = await getVersion(v.id)
    await saveERModel(versionProject.value.id, versionData.version_data)
    ElMessage.success(t('project.list.restoredTo', { version: v.version_number }))
    loadProjects()
  } catch {
    // handled by interceptor
  } finally {
    restoreId.value = null
  }
}

const deleteVersionItem = async (v) => {
  try {
    await ElMessageBox.confirm(
      t('project.list.deleteVersionConfirm', { version: v.version_number }),
      t('project.list.deleteVersionTitle'),
      { type: 'warning', confirmButtonText: t('project.list.confirmDelete'), cancelButtonText: t('project.form.cancel') }
    )
  } catch {
    return
  }
  deleteId.value = v.id
  try {
    await deleteVersion(v.id)
    ElMessage.success(t('project.list.versionDeleted', { version: v.version_number }))
    versions.value = versions.value.filter(item => item.id !== v.id)
  } catch {
    // handled by interceptor
  } finally {
    deleteId.value = null
  }
}

onMounted(() => {
  loadProjects()
})
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;
.header-actions {
  display: flex;
  align-items: center;
}

.empty-state {
  padding: 60px 0;
  display: flex;
  justify-content: center;
}

.projects-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}

.project-card {
  background: $bg-white;
  border-radius: $radius-lg;
  padding: 20px;
  cursor: pointer;
  transition: $transition-base;
  display: flex;
  flex-direction: column;
  box-shadow: $shadow-sm;
  border: 1px solid transparent;

  &:hover {
    box-shadow: $shadow-lg;
    transform: translateY(-2px);
    border-color: rgba(59, 130, 246, 0.2);
  }

  &.add-card {
    display: flex;
    align-items: center;
    justify-content: center;
    text-align: center;
    min-height: 240px;
    border: 2px dashed #E2E8F0;
    background: transparent;

    &:hover {
      border-color: $primary-color;
      background: rgba(59, 130, 246, 0.03);

      .add-icon :deep(svg) {
        color: $primary-color !important;
      }
    }
  }
}

.card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 16px;
}

.project-badge {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.add-icon {
  width: 72px;
  height: 72px;
  border-radius: 18px;
  background: $bg-light;
  display: flex;
  align-items: center;
  justify-content: center;
}

.card-body {
  flex: 1;
  min-height: 60px;
}

.project-title {
  font-size: 15px;
  font-weight: 600;
  color: $text-primary;
  line-height: 1.4;
}

.project-desc {
  font-size: 12px;
  color: $text-secondary;
  margin-top: 6px;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;

  &.empty {
    color: #CBD5E1;
    font-style: italic;
  }
}

.card-stats {
  display: flex;
  gap: 16px;
  margin: 16px 0;
  padding: 12px 0;
  border-top: 1px solid $border-light;
  border-bottom: 1px solid $border-light;
}

.stat {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: $text-regular;
  font-weight: 500;
}

.card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.footer-left {
  display: flex;
  gap: 6px;
}

.version-list {
  max-height: 460px;
  overflow-y: auto;

  .version-empty {
    padding: 20px 0;
  }

  .version-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 14px 16px;
    border: 1px solid $border-light;
    border-radius: $radius-md;
    margin-bottom: 10px;
    background: $bg-white;
    transition: $transition-base;

    &:last-child {
      margin-bottom: 0;
    }

    &:hover {
      border-color: rgba(59, 130, 246, 0.25);
      background: rgba(59, 130, 246, 0.02);
    }
  }

  .version-info {
    flex: 1;
    min-width: 0;
  }

  .version-header {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 6px;
  }

  .version-time {
    font-size: 12px;
    color: $text-secondary;
  }

  .version-note {
    font-size: 13px;
    color: $text-regular;
    line-height: 1.5;
    word-break: break-all;
  }

  .version-actions {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    gap: 8px;
  }
}

html.dark {
  .project-card {
    background: #252526 !important;
    border-color: #3c3c3c !important;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.2) !important;

    &:hover {
      background: #252526 !important;
      border-color: rgba(59, 130, 246, 0.35) !important;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.35) !important;
    }
  }

  .project-title {
    color: #f8fafc !important;
  }

  .project-desc {
    color: #94a3b8 !important;

    &.empty {
      color: #64748b !important;
    }
  }

  .card-stats {
    border-color: #3c3c3c !important;
  }

  .stat {
    color: #94a3b8 !important;
  }

  .add-card {
    background: transparent !important;
    border-color: #3c3c3c !important;

    &:hover {
      border-color: #3b82f6 !important;
      background: rgba(59, 130, 246, 0.06) !important;
    }
  }

  .add-icon {
    background: #3c3c3c !important;
  }

  .version-list {
    .version-item {
      background: #252526 !important;
      border-color: #3c3c3c !important;

      &:hover {
        background: #252526 !important;
        border-color: rgba(59, 130, 246, 0.3) !important;
      }
    }

    .version-time,
    .version-note {
      color: #94a3b8 !important;
    }
  }
}
</style>
