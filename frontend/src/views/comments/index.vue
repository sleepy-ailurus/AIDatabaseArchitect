<template>
  <div class="comments-page">
    <div class="page-header">
      <div class="header-left">
        <el-breadcrumb separator="/" class="breadcrumb-sm">
          <el-breadcrumb-item style="color: #94A3B8;">{{ t('comments.breadcrumb.project') }}</el-breadcrumb-item>
          <el-breadcrumb-item style="color: #94A3B8; cursor: pointer;" @click="$router.push('/projects')">{{ projectName }}</el-breadcrumb-item>
          <el-breadcrumb-item><span class="current-crumb">{{ t('comments.breadcrumb.title') }}</span></el-breadcrumb-item>
        </el-breadcrumb>
        <div class="subtitle">{{ t('comments.subtitle') }}</div>
      </div>
      <div class="header-actions">
        <el-button type="primary" :icon="MagicStick" :loading="generating" @click="handleGenerate">
          {{ t('comments.generate') }}
        </el-button>
        <el-dropdown @command="handleExport" :disabled="!hasAccepted">
          <el-button :icon="Download" :loading="exporting">
            {{ t('comments.exportDictionary') }}<el-icon class="el-icon--right"><ArrowDown /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="excel">Excel (.xlsx)</el-dropdown-item>
              <el-dropdown-item command="word">Word (.docx)</el-dropdown-item>
              <el-dropdown-item command="markdown">Markdown</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <el-button :icon="Document" :loading="applying" :disabled="!hasAccepted" @click="handleApply(false)">
          {{ t('comments.generateSql') }}
        </el-button>
        <el-button type="danger" plain :icon="Promotion" :loading="applying" :disabled="!hasAccepted" @click="handleApply(true)">
          {{ t('comments.executeWriteback') }}
        </el-button>
        <el-button :icon="Back" @click="$router.push(`/projects/${projectId}/er-model`)">
          {{ t('comments.backToEr') }}
        </el-button>
      </div>
    </div>

    <div class="comments-body">
      <div class="summary-cards">
        <div class="sum-card"><span class="sum-num">{{ counts.suggested }}</span><span class="sum-label">{{ t('comments.pending') }}</span></div>
        <div class="sum-card ok"><span class="sum-num">{{ counts.accepted }}</span><span class="sum-label">{{ t('comments.accepted') }}</span></div>
        <div class="sum-card no"><span class="sum-num">{{ counts.rejected }}</span><span class="sum-label">{{ t('comments.rejected') }}</span></div>
        <div class="sum-card applied"><span class="sum-num">{{ counts.applied }}</span><span class="sum-label">{{ t('comments.applied') }}</span></div>
      </div>

      <div class="toolbar">
        <el-radio-group v-model="statusFilter" size="small">
          <el-radio-button value="all">{{ t('comments.filterAll') }}</el-radio-button>
          <el-radio-button value="suggested">{{ t('comments.pending') }}</el-radio-button>
          <el-radio-button value="accepted">{{ t('comments.accepted') }}</el-radio-button>
          <el-radio-button value="rejected">{{ t('comments.rejected') }}</el-radio-button>
          <el-radio-button value="applied">{{ t('comments.applied') }}</el-radio-button>
        </el-radio-group>
        <div class="toolbar-actions">
          <el-button size="small" type="success" plain :disabled="pendingIds.length === 0" @click="batch('accepted')">
            {{ t('comments.acceptAll') }}
          </el-button>
          <el-button size="small" type="danger" plain :disabled="pendingIds.length === 0" @click="batch('rejected')">
            {{ t('comments.rejectAll') }}
          </el-button>
        </div>
      </div>

      <div class="suggestion-list" v-loading="loading">
        <div v-for="s in filtered" :key="s.id" class="suggestion-row" :class="s.status">
          <el-checkbox v-model="selectedIds" :value="s.id" :disabled="s.status !== 'suggested'" />
          <div class="target">
            <code>{{ s.table_name }}</code>
            <template v-if="s.column_name">.<code>{{ s.column_name }}</code></template>
            <el-tag size="small" effect="plain" :type="s.target_type === 'table' ? 'primary' : 'info'" round style="margin-left: 6px;">
              {{ s.target_type === 'table' ? t('comments.tableType') : t('comments.columnType') }}
            </el-tag>
          </div>
          <div class="comment">{{ s.suggested_comment }}</div>
          <el-tag size="small" :type="statusTag(s.status)" effect="light" class="status-tag">{{ statusLabel(s.status) }}</el-tag>
          <div class="row-actions" v-if="s.status === 'suggested'">
            <el-button size="small" type="success" link :icon="Check" @click="setStatus(s, 'accepted')">{{ t('common.confirm') }}</el-button>
            <el-button size="small" type="danger" link :icon="Close" @click="setStatus(s, 'rejected')">{{ t('common.reject') }}</el-button>
          </div>
        </div>
        <el-empty v-if="!loading && filtered.length === 0" :description="t('comments.empty')" :image-size="90" />
      </div>
    </div>

    <el-dialog v-model="showSqlDialog" :title="t('comments.sqlTitle')" width="760px" destroy-on-close>
      <pre class="sql-block">{{ applyResult?.sql?.join('\n') || t('comments.noSql') }}</pre>
      <template #footer>
        <el-button @click="showSqlDialog = false">{{ t('common.close') }}</el-button>
        <el-button type="primary" :icon="CopyDocument" @click="copySql">{{ t('comments.copySql') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  generateSuggestions,
  listSuggestions,
  updateSuggestion,
  batchUpdateSuggestions,
  applySuggestions,
  exportDictionary
} from '@/api/comments'
import { getProject } from '@/api/project'

const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const projectId = computed(() => route.params.id)

const projectName = ref('')
const items = ref([])
const loading = ref(false)
const generating = ref(false)
const applying = ref(false)
const exporting = ref(false)
const statusFilter = ref('all')
const selectedIds = ref([])
const applyResult = ref(null)
const showSqlDialog = ref(false)

const statusLabel = (s) => t(`comments.status.${s}`)
const statusTag = (s) => (s === 'accepted' ? 'success' : s === 'rejected' ? 'danger' : s === 'applied' ? 'primary' : 'info')

const counts = computed(() => {
  const c = { suggested: 0, accepted: 0, rejected: 0, applied: 0 }
  for (const s of items.value) c[s.status] = (c[s.status] || 0) + 1
  return c
})

const filtered = computed(() => {
  if (statusFilter.value === 'all') return items.value
  return items.value.filter((s) => s.status === statusFilter.value)
})

const pendingIds = computed(() => items.value.filter((s) => s.status === 'suggested').map((s) => s.id))
const hasAccepted = computed(() => items.value.some((s) => s.status === 'accepted'))

const load = async () => {
  loading.value = true
  try {
    items.value = await listSuggestions(projectId.value)
    selectedIds.value = []
  } catch {
    items.value = []
  } finally {
    loading.value = false
  }
}

const handleGenerate = async () => {
  try {
    await ElMessageBox.confirm(t('comments.generateConfirm'), t('comments.generate'), {
      confirmButtonText: t('common.confirm'),
      cancelButtonText: t('common.cancel'),
      type: 'info'
    })
  } catch {
    return
  }
  generating.value = true
  try {
    const res = await generateSuggestions(projectId.value, {})
    ElMessage.success(
      t('comments.generated', { tables: res.table_count, columns: res.column_count })
    )
    await load()
  } catch {
    // interceptor shows error
  } finally {
    generating.value = false
  }
}

const setStatus = async (s, status) => {
  try {
    await updateSuggestion(s.id, status)
    s.status = status
    selectedIds.value = selectedIds.value.filter((id) => id !== s.id)
  } catch {
    // ignore
  }
}

const batch = async (status) => {
  const ids = status === 'accepted' ? pendingIds.value : selectedIds.value.filter((id) => id !== null)
  if (!ids.length) return
  try {
    await batchUpdateSuggestions(projectId.value, ids, status)
    await load()
  } catch {
    // ignore
  }
}

const handleApply = async (execute) => {
  if (execute) {
    try {
      await ElMessageBox.confirm(t('comments.executeConfirm'), t('comments.executeWriteback'), {
        confirmButtonText: t('common.confirm'),
        cancelButtonText: t('common.cancel'),
        type: 'warning'
      })
    } catch {
      return
    }
  }
  applying.value = true
  try {
    applyResult.value = await applySuggestions(projectId.value, execute)
    if (!execute) {
      showSqlDialog.value = true
    } else {
      ElMessage.success(
        t('comments.executed', { count: applyResult.value.executed })
      )
    }
    await load()
  } catch {
    // interceptor shows error
  } finally {
    applying.value = false
  }
}

const copySql = () => {
  navigator.clipboard?.writeText(applyResult.value?.sql?.join('\n') || '')
  ElMessage.success(t('comments.copied'))
}

const handleExport = async (format) => {
  exporting.value = true
  try {
    const blob = await exportDictionary(projectId.value, format)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `data-dictionary.${format === 'markdown' ? 'md' : format}`
    a.click()
    URL.revokeObjectURL(url)
  } catch {
    // interceptor shows error
  } finally {
    exporting.value = false
  }
}

onMounted(async () => {
  try {
    const data = await getProject(projectId.value)
    if (data) projectName.value = data.name
  } catch {
    // ignore
  }
  await load()
})
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.comments-page { width: 100%; height: 100%; display: flex; flex-direction: column; background: $bg-color; }
.page-header {
  min-height: 64px; background: $bg-white; border-bottom: 1px solid $border-light;
  padding: 12px 20px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px;
}
.header-left { display: flex; flex-direction: column; gap: 4px; }
.subtitle { font-size: 12px; color: #94A3B8; }
.current-crumb { color: #1E293B; font-weight: 600; }
.header-actions { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.comments-body { flex: 1; overflow: auto; padding: 20px; }
.summary-cards { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 16px; }
.sum-card {
  background: $bg-white; border: 1px solid $border-light; border-radius: 12px; padding: 14px;
  display: flex; flex-direction: column; gap: 4px;
  .sum-num { font-size: 22px; font-weight: 700; color: #3b82f6; }
  &.ok .sum-num { color: #10b981; }
  &.no .sum-num { color: #ef4444; }
  &.applied .sum-num { color: #8b5cf6; }
}
.sum-label { font-size: 12px; color: #64748b; }
.toolbar { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; flex-wrap: wrap; gap: 10px; }
.suggestion-list { display: flex; flex-direction: column; gap: 8px; }
.suggestion-row {
  background: $bg-white; border: 1px solid $border-light; border-radius: 10px; padding: 10px 14px;
  display: flex; align-items: center; gap: 12px;
  &.accepted { border-left: 3px solid #10b981; }
  &.rejected { border-left: 3px solid #ef4444; opacity: 0.65; }
  &.applied { border-left: 3px solid #8b5cf6; }
}
.target { min-width: 200px; font-size: 13px; color: $text-primary; }
.comment { flex: 1; font-size: 13px; color: $text-regular; line-height: 1.5; }
.status-tag { flex-shrink: 0; }
.row-actions { flex-shrink: 0; display: flex; gap: 4px; }
.sql-block {
  max-height: 420px; overflow: auto; background: #0f172a; color: #e2e8f0;
  border-radius: 8px; padding: 14px; font-family: 'SF Mono', Consolas, monospace; font-size: 12px; line-height: 1.6; white-space: pre-wrap;
}
html.dark {
  .page-header { background: #252526 !important; border-bottom-color: #3c3c3c !important; }
  .current-crumb { color: #f8fafc !important; }
  .sum-card, .suggestion-row { background: #252526 !important; border-color: #3c3c3c !important; }
  .target { color: #e2e8f0 !important; }
}
</style>
