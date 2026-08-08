<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <div class="page-title">项目列表</div>
        <div class="page-subtitle">管理所有数据库分析项目</div>
      </div>
      <div class="header-actions">
        <el-input v-model="searchKey" placeholder="搜索项目名称..." style="width: 260px; margin-right: 12px;" clearable>
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-select v-model="statusFilter" placeholder="状态" style="width: 120px; margin-right: 12px;" clearable>
          <el-option label="分析中" value="analyzing" />
          <el-option label="已完成" value="completed" />
          <el-option label="待确认" value="pending" />
          <el-option label="草稿" value="draft" />
        </el-select>
        <el-button type="primary" :icon="Plus" @click="openCreate">
          新建项目
        </el-button>
      </div>
    </div>

    <div v-loading="loading">
      <div v-if="!loading && filteredProjects.length === 0" class="empty-state">
        <el-empty description="暂无项目，点击右上角新建一个数据库分析项目">
          <el-button type="primary" :icon="Plus" @click="openCreate">新建项目</el-button>
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
                  <el-dropdown-item @click.stop="openProject(p)"><el-icon><Share /></el-icon> 打开 ER 模型</el-dropdown-item>
                  <el-dropdown-item @click.stop="goConnection(p)"><el-icon><Connection /></el-icon> 连接配置</el-dropdown-item>
                  <el-dropdown-item divided style="color: #EF4444;" @click.stop="handleDelete(p)">
                    <el-icon><Delete /></el-icon> 删除
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>

          <div class="card-body">
            <div class="project-title">{{ p.name }}</div>
            <div class="project-desc" v-if="p.description">{{ p.description }}</div>
            <div class="project-desc empty" v-else>暂无描述</div>
          </div>

          <div class="card-stats">
            <div class="stat">
              <el-icon :size="14" color="#64748B"><Grid /></el-icon>
              <span>{{ p.table_count || p.tables || 0 }} 张表</span>
            </div>
            <div class="stat">
              <el-icon :size="14" color="#64748B"><Share /></el-icon>
              <span>{{ p.relation_count || p.relations || 0 }} 条关系</span>
            </div>
            <div class="stat">
              <el-icon :size="14" color="#64748B"><MagicStick /></el-icon>
              <span>{{ p.suggestion_count || p.suggestions || 0 }} 条建议</span>
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
          <div style="font-size: 14px; color: #94A3B8; margin-top: 12px; font-weight: 500;">新建项目</div>
          <div style="font-size: 12px; color: #CBD5E1; margin-top: 4px;">创建新的数据库分析任务</div>
        </div>
      </div>
    </div>

    <el-dialog v-model="showCreate" title="新建项目" width="560px" :close-on-click-modal="false">
      <el-form :model="createForm" :rules="createRules" ref="createFormRef" label-width="100px" style="margin-top: 8px;">
        <el-form-item label="项目名称" prop="name">
          <el-input v-model="createForm.name" placeholder="例如：电商核心数据库分析" />
        </el-form-item>
        <el-form-item label="项目描述">
          <el-input v-model="createForm.description" type="textarea" :rows="3" placeholder="简要描述项目用途和目标数据库..." />
        </el-form-item>
        <el-form-item label="数据库类型" prop="db_type">
          <el-select v-model="createForm.db_type" style="width: 100%;" placeholder="选择数据库类型">
            <el-option label="MySQL 8.x" value="mysql" />
            <el-option label="PostgreSQL 14+" value="postgresql" disabled />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="handleCreate">创建项目</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import 'dayjs/locale/zh-cn'
import { useProjectStore } from '@/stores/project'
import { createProject as createProjectApi, deleteProject as deleteProjectApi } from '@/api/project'

dayjs.extend(relativeTime)
dayjs.locale('zh-cn')

const router = useRouter()
const projectStore = useProjectStore()
const searchKey = ref('')
const statusFilter = ref('')
const showCreate = ref(false)
const loading = ref(false)
const creating = ref(false)
const createFormRef = ref()

const createForm = reactive({
  name: '',
  description: '',
  db_type: 'mysql'
})

const createRules = {
  name: [{ required: true, message: '请输入项目名称', trigger: 'blur' }],
  db_type: [{ required: true, message: '请选择数据库类型', trigger: 'change' }]
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
  const map = {
    analyzing: '分析中',
    completed: '已完成',
    pending: '待确认',
    draft: '草稿',
    connected: '已连接'
  }
  return map[status] || status || '草稿'
}

const formatTime = (time) => {
  if (!time) return '-'
  try {
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
    ElMessage.success('项目创建成功')
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
      `确定要删除项目 "${p.name}" 吗？该操作不可恢复，所有相关数据将被清除。`,
      '删除确认',
      { type: 'warning', confirmButtonText: '确认删除', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  try {
    await deleteProjectApi(p.id)
    ElMessage.success('项目已删除')
    loadProjects()
  } catch {
    // handled by interceptor
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
</style>
