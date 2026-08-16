<template>
  <div class="history-page">
    <div class="page-header">
      <div class="header-left">
        <el-breadcrumb separator="/" class="breadcrumb-sm">
          <el-breadcrumb-item style="color: #94A3B8;">{{ t('schemaHistory.breadcrumb.project') }}</el-breadcrumb-item>
          <el-breadcrumb-item style="color: #94A3B8; cursor: pointer;" @click="$router.push('/projects')">{{ projectName }}</el-breadcrumb-item>
          <el-breadcrumb-item><span class="current-crumb">{{ t('schemaHistory.breadcrumb.title') }}</span></el-breadcrumb-item>
        </el-breadcrumb>
        <div class="subtitle">{{ t('schemaHistory.subtitle') }}</div>
      </div>
      <div class="header-actions">
        <el-button :icon="Download" :loading="exporting" @click="exportMarkdown">
          {{ t('schemaHistory.exportReport') }}
        </el-button>
        <el-button :icon="Back" @click="$router.push(`/projects/${projectId}/er-model`)">
          {{ t('schemaHistory.backToEr') }}
        </el-button>
      </div>
    </div>

    <div class="history-body" v-loading="loading">
      <aside class="timeline-panel">
        <div class="panel-title">{{ t('schemaHistory.timeline') }}</div>
        <el-scrollbar class="timeline-scroll">
          <div
            v-for="s in snapshots"
            :key="s.id"
            class="snapshot-item"
            :class="{ selected: selected.has(s.version) }"
            @click="toggleSelect(s.version)"
          >
            <div class="snapshot-dot" :class="{ from: fromVersion === s.version, to: toVersion === s.version }"></div>
            <div class="snapshot-info">
              <div class="snapshot-version">v{{ s.version }} <el-tag size="small" type="info" effect="plain" round>{{ s.table_count }} {{ t('schemaHistory.tables') }}</el-tag></div>
              <div class="snapshot-time">{{ formatTime(s.created_at) }}</div>
            </div>
          </div>
        </el-scrollbar>
        <div class="select-tip">{{ t('schemaHistory.selectTip') }}</div>
      </aside>

      <main class="diff-panel">
        <el-alert
          v-if="snapshots.length < 2"
          type="info"
          :closable="false"
          show-icon
          style="margin-bottom: 12px;"
          :title="t('schemaHistory.onlyOneHint')"
        />
        <div v-if="!diff" class="empty-state">
          <el-empty :description="t('schemaHistory.selectTwo')" :image-size="120" />
        </div>
        <template v-else>
          <div class="diff-meta">
            <span class="meta-chip">
              {{ t('schemaHistory.from') }}: <strong>v{{ diff.from_version }}</strong>
            </span>
            <el-icon color="#64748B"><Right /></el-icon>
            <span class="meta-chip">
              {{ t('schemaHistory.to') }}: <strong>v{{ diff.to_version }}</strong>
            </span>
          </div>

          <div class="summary-cards">
            <div class="sum-card added">
              <span class="sum-num">{{ diff.summary.tables_added }}</span>
              <span class="sum-label">{{ t('schemaHistory.tablesAdded') }}</span>
            </div>
            <div class="sum-card removed">
              <span class="sum-num">{{ diff.summary.tables_removed }}</span>
              <span class="sum-label">{{ t('schemaHistory.tablesRemoved') }}</span>
            </div>
            <div class="sum-card changed">
              <span class="sum-num">{{ diff.summary.tables_changed }}</span>
              <span class="sum-label">{{ t('schemaHistory.tablesChanged') }}</span>
            </div>
            <div class="sum-card fields">
              <span class="sum-num">{{ diff.summary.columns_added + diff.summary.columns_removed + diff.summary.columns_changed }}</span>
              <span class="sum-label">{{ t('schemaHistory.columnsAffected') }}</span>
            </div>
          </div>

          <div v-if="diff.tables_added.length" class="diff-section">
            <div class="section-title add">{{ t('schemaHistory.addedTables') }}</div>
            <div class="tag-list">
              <el-tag v-for="name in diff.tables_added" :key="name" type="success" effect="light" round>{{ name }}</el-tag>
            </div>
          </div>

          <div v-if="diff.tables_removed.length" class="diff-section">
            <div class="section-title remove">{{ t('schemaHistory.removedTables') }}</div>
            <div class="tag-list">
              <el-tag v-for="name in diff.tables_removed" :key="name" type="danger" effect="light" round>{{ name }}</el-tag>
            </div>
          </div>

          <div v-if="diff.tables_changed.length" class="diff-section">
            <div class="section-title change">{{ t('schemaHistory.changedTables') }}</div>
            <el-collapse>
              <el-collapse-item v-for="tc in diff.tables_changed" :key="tc.table" :name="tc.table">
                <template #title>
                  <span class="table-name">{{ tc.table }}</span>
                  <el-tag v-if="tc.comment" size="small" type="warning" effect="plain" round style="margin-left: 8px;">
                    {{ tc.comment.old || '-' }} → {{ tc.comment.new || '-' }}
                  </el-tag>
                </template>

                <div v-if="tc.columns_added.length" class="change-block">
                  <div class="change-label add">+ {{ t('schemaHistory.columnsAdded') }}</div>
                  <div v-for="c in tc.columns_added" :key="c.name" class="change-row add">
                    <code>{{ c.name }}</code> {{ c.data_type }}{{ c.length ? `(${c.length})` : '' }}
                    <el-tag v-if="c.is_primary_key" size="small" type="warning" effect="plain">PK</el-tag>
                    <span v-if="c.comment" class="muted">{{ c.comment }}</span>
                  </div>
                </div>
                <div v-if="tc.columns_removed.length" class="change-block">
                  <div class="change-label remove">- {{ t('schemaHistory.columnsRemoved') }}</div>
                  <div v-for="name in tc.columns_removed" :key="name" class="change-row remove"><code>{{ name }}</code></div>
                </div>
                <div v-if="tc.columns_changed.length" class="change-block">
                  <div class="change-label change">~ {{ t('schemaHistory.columnsChanged') }}</div>
                  <div v-for="c in tc.columns_changed" :key="c.name" class="change-row change">
                    <code>{{ c.name }}</code>
                    <ul class="change-list">
                      <li v-for="(ch, i) in c.changes" :key="i">{{ ch }}</li>
                    </ul>
                  </div>
                </div>
                <div v-if="tc.indexes_added.length || tc.indexes_removed.length" class="change-block">
                  <div class="change-label">@ {{ t('schemaHistory.indexes') }}</div>
                  <div v-for="idx in tc.indexes_added" :key="'a' + (idx.name || idx.columns)" class="change-row add">
                    + {{ idx.name || idx.columns.join(',') }} ({{ idx.columns.join(',') }}){{ idx.unique ? ' UNIQUE' : '' }}
                  </div>
                  <div v-for="idx in tc.indexes_removed" :key="'r' + (idx.name || idx.columns)" class="change-row remove">
                    - {{ idx.name || idx.columns.join(',') }} ({{ idx.columns.join(',') }}){{ idx.unique ? ' UNIQUE' : '' }}
                  </div>
                </div>
                <div v-if="tc.fks_added.length || tc.fks_removed.length" class="change-block">
                  <div class="change-label">🔗 {{ t('schemaHistory.fks') }}</div>
                  <div v-for="fk in tc.fks_added" :key="'a' + fk.source_column" class="change-row add">
                    + {{ tc.table }}.{{ fk.source_column }} → {{ fk.target_table }}.{{ fk.target_column }}
                  </div>
                  <div v-for="fk in tc.fks_removed" :key="'r' + fk.source_column" class="change-row remove">
                    - {{ tc.table }}.{{ fk.source_column }} → {{ fk.target_table }}.{{ fk.target_column }}
                  </div>
                </div>
              </el-collapse-item>
            </el-collapse>
          </div>
        </template>
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import dayjs from 'dayjs'
import utc from 'dayjs/plugin/utc'
import { getSnapshots, getSchemaDiff } from '@/api/schema'
import { getProject } from '@/api/project'

dayjs.extend(utc)

const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const projectId = computed(() => route.params.id)

const projectName = ref('')
const snapshots = ref([])
const selected = ref(new Set())
const diff = ref(null)
const loading = ref(false)
const exporting = ref(false)

const fromVersion = computed(() => [...selected.value].sort((a, b) => a - b)[0])
const toVersion = computed(() => [...selected.value].sort((a, b) => a - b)[1])

const formatTime = (v) => (v ? dayjs.utc(v).local().format('YYYY-MM-DD HH:mm') : '-')

const toggleSelect = (version) => {
  const set = new Set(selected.value)
  if (set.has(version)) {
    set.delete(version)
  } else {
    if (set.size >= 2) {
      ElMessage.info(t('schemaHistory.maxTwo'))
      return
    }
    set.add(version)
  }
  selected.value = set
  if (set.size === 2) loadDiff()
  else diff.value = null
}

const loadDiff = async () => {
  if (fromVersion.value === undefined || toVersion.value === undefined) return
  loading.value = true
  try {
    diff.value = await getSchemaDiff(projectId.value, {
      from_version: fromVersion.value,
      to_version: toVersion.value
    })
  } catch {
    diff.value = null
  } finally {
    loading.value = false
  }
}

const markdown = computed(() => {
  if (!diff.value) return ''
  const d = diff.value
  const lines = []
  lines.push(`# Schema 变更对比 v${d.from_version} → v${d.to_version}`)
  lines.push('')
  lines.push(`- 新增表：${d.summary.tables_added} 张`)
  lines.push(`- 删除表：${d.summary.tables_removed} 张`)
  lines.push(`- 变更表：${d.summary.tables_changed} 张`)
  lines.push(`- 字段影响：新增 ${d.summary.columns_added} / 删除 ${d.summary.columns_removed} / 修改 ${d.summary.columns_changed}`)
  lines.push('')
  if (d.tables_added.length) {
    lines.push('## 新增表')
    d.tables_added.forEach((n) => lines.push(`- \`${n}\``))
    lines.push('')
  }
  if (d.tables_removed.length) {
    lines.push('## 删除表')
    d.tables_removed.forEach((n) => lines.push(`- \`${n}\``))
    lines.push('')
  }
  if (d.tables_changed.length) {
    lines.push('## 变更明细')
    for (const tc of d.tables_changed) {
      lines.push(`### ${tc.table}`)
      if (tc.comment) lines.push(`- 表注释：${tc.comment.old || '无'} → ${tc.comment.new || '无'}`)
      tc.columns_added.forEach((c) => lines.push(`- [新增字段] \`${c.name}\` ${c.data_type}${c.is_primary_key ? ' PK' : ''}${c.comment ? ' — ' + c.comment : ''}`))
      tc.columns_removed.forEach((n) => lines.push(`- [删除字段] \`${n}\``))
      tc.columns_changed.forEach((c) => c.changes.forEach((ch) => lines.push(`- [修改字段] \`${c.name}\`：${ch}`)))
      tc.indexes_added.forEach((idx) => lines.push(`- [新增索引] ${idx.name || idx.columns.join(',')} (${idx.columns.join(',')})${idx.unique ? ' UNIQUE' : ''}`))
      tc.indexes_removed.forEach((idx) => lines.push(`- [删除索引] ${idx.name || idx.columns.join(',')} (${idx.columns.join(',')})${idx.unique ? ' UNIQUE' : ''}`))
      tc.fks_added.forEach((fk) => lines.push(`- [新增外键] ${tc.table}.${fk.source_column} → ${fk.target_table}.${fk.target_column}`))
      tc.fks_removed.forEach((fk) => lines.push(`- [删除外键] ${tc.table}.${fk.source_column} → ${fk.target_table}.${fk.target_column}`))
      lines.push('')
    }
  }
  return lines.join('\n')
})

const exportMarkdown = () => {
  if (!diff.value) return
  exporting.value = true
  try {
    const blob = new Blob([markdown.value], { type: 'text/markdown;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `schema-diff-v${diff.value.from_version}-v${diff.value.to_version}.md`
    a.click()
    URL.revokeObjectURL(url)
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
  try {
    snapshots.value = await getSnapshots(projectId.value)
    // pre-select the latest two
    const versions = snapshots.value.map((s) => s.version).sort((a, b) => b - a)
    if (versions.length >= 2) {
      selected.value = new Set([versions[1], versions[0]])
      loadDiff()
    }
  } catch {
    // interceptor shows error
  }
})
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.history-page {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: $bg-color;
}

.page-header {
  min-height: 48px;
  background: $bg-white;
  border-bottom: 1px solid $border-light;
  padding: 10px 20px 4px;
  margin-bottom: 0;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 10px;
}

.header-left { display: flex; flex-direction: column; gap: 4px; }
.subtitle { font-size: 12px; color: #94A3B8; }
.current-crumb { color: #1E293B; font-weight: 600; }

.history-body {
  flex: 1;
  display: flex;
  overflow: hidden;
  min-height: 0;
}

.timeline-panel {
  width: 280px;
  background: $bg-white;
  border-right: 1px solid $border-light;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.panel-title {
  padding: 8px 16px 8px;
  font-size: 13px;
  font-weight: 600;
  color: $text-primary;
}

.timeline-scroll { flex: 1; padding: 4px 8px 8px; }

.snapshot-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 9px 10px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s;
  &:hover { background: $bg-light; }
  &.selected { background: rgba(59, 130, 246, 0.08); }
}

.snapshot-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #cbd5e1;
  margin-top: 4px;
  flex-shrink: 0;
  &.from { background: #10b981; }
  &.to { background: #3b82f6; }
}

.snapshot-info { min-width: 0; }
.snapshot-version {
  font-size: 13px;
  font-weight: 600;
  color: $text-primary;
  display: flex;
  align-items: center;
  gap: 6px;
}
.snapshot-time { font-size: 11px; color: #94a3b8; margin-top: 2px; }
.select-tip { padding: 8px 16px; font-size: 11px; color: #94a3b8; border-top: 1px solid $border-light; }

.diff-panel {
  flex: 1;
  overflow: auto;
  padding: 20px;
  min-width: 0;
}

.empty-state { display: flex; align-items: center; justify-content: center; height: 100%; }

.diff-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
}
.meta-chip {
  background: $bg-white;
  border: 1px solid $border-light;
  border-radius: 8px;
  padding: 6px 12px;
  font-size: 13px;
  color: $text-regular;
}

.summary-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 20px;
}
.sum-card {
  background: $bg-white;
  border: 1px solid $border-light;
  border-radius: 12px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  &.added .sum-num { color: #10b981; }
  &.removed .sum-num { color: #ef4444; }
  &.changed .sum-num { color: #f59e0b; }
  &.fields .sum-num { color: #3b82f6; }
}
.sum-num { font-size: 22px; font-weight: 700; }
.sum-label { font-size: 12px; color: #64748b; }

.diff-section { margin-bottom: 18px; }
.section-title {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 10px;
  padding-left: 10px;
  border-left: 3px solid #cbd5e1;
  &.add { border-color: #10b981; color: #047857; }
  &.remove { border-color: #ef4444; color: #b91c1c; }
  &.change { border-color: #f59e0b; color: #b45309; }
}
.tag-list { display: flex; flex-wrap: wrap; gap: 8px; }

.table-name { font-weight: 600; color: $text-primary; }
.change-block { margin: 8px 0 12px 12px; }
.change-label { font-size: 12px; font-weight: 600; margin-bottom: 6px; color: #64748b; &.add { color: #059669; } &.remove { color: #dc2626; } &.change { color: #d97706; } }
.change-row {
  font-size: 12px;
  padding: 4px 8px;
  border-radius: 6px;
  margin-bottom: 4px;
  color: $text-regular;
  &.add { background: rgba(16, 185, 129, 0.08); }
  &.remove { background: rgba(239, 68, 68, 0.08); text-decoration: line-through; }
  &.change { background: rgba(245, 158, 11, 0.08); }
}
.change-list { margin: 4px 0 0 16px; padding: 0; }
.muted { color: #94a3b8; margin-left: 8px; }

html.dark {
  .page-header { background: #252526 !important; border-bottom-color: #3c3c3c !important; }
  .current-crumb { color: #f8fafc !important; }
  .timeline-panel { background: #252526 !important; border-right-color: #3c3c3c !important; }
  .snapshot-item:hover { background: #3c3c3c !important; }
  .snapshot-item.selected { background: rgba(59, 130, 246, 0.18) !important; }
  .snapshot-version { color: #f8fafc !important; }
  .sum-card { background: #252526 !important; border-color: #3c3c3c !important; }
  .meta-chip { background: #252526 !important; border-color: #3c3c3c !important; color: #94a3b8 !important; }
  .table-name { color: #f8fafc !important; }
  .history-page { background: #1e1e1e !important; }
  .panel-title { color: #e2e8f0 !important; }
  .snapshot-time { color: #94a3b8 !important; }
  .select-tip { color: #94a3b8 !important; border-top-color: #3c3c3c !important; }
  .sum-label { color: #94a3b8 !important; }
  .change-row { color: #cbd5e1 !important; }
  .muted { color: #94a3b8 !important; }
}
</style>
