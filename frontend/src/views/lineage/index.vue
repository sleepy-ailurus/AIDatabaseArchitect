<template>
  <div class="lineage-page">
    <div class="page-header">
      <div class="header-left">
        <el-breadcrumb separator="/" class="breadcrumb-sm">
          <el-breadcrumb-item style="color: #94A3B8;">{{ t('lineage.breadcrumb.project') }}</el-breadcrumb-item>
          <el-breadcrumb-item style="color: #94A3B8; cursor: pointer;" @click="$router.push('/projects')">{{ projectName }}</el-breadcrumb-item>
          <el-breadcrumb-item><span class="current-crumb">{{ t('lineage.breadcrumb.title') }}</span></el-breadcrumb-item>
        </el-breadcrumb>
        <div class="subtitle">{{ t('lineage.subtitle') }}</div>
      </div>
      <div class="header-actions">
        <el-button type="primary" :icon="MagicStick" :loading="analyzing" @click="handleAnalyze">
          {{ t('lineage.analyze') }}
        </el-button>
        <el-button :icon="Back" @click="$router.push(`/projects/${projectId}/er-model`)">
          {{ t('lineage.backToEr') }}
        </el-button>
      </div>
    </div>

    <div class="lineage-body">
      <el-input
        v-model="sqlText"
        type="textarea"
        :rows="8"
        :placeholder="t('lineage.placeholder')"
        class="sql-input"
      />

      <div v-if="result" class="result-section">
        <el-alert v-if="result.error" type="error" :title="result.error" :closable="false" show-icon style="margin-bottom: 12px;" />
        <el-alert
          v-else-if="result.unresolved.length"
          type="warning"
          :title="t('lineage.unresolved', { tables: result.unresolved.join(', ') })"
          :closable="false"
          show-icon
          style="margin-bottom: 12px;"
        />

        <div class="summary-cards">
          <div class="sum-card"><span class="sum-num">{{ result.queries.length }}</span><span class="sum-label">{{ t('lineage.queries') }}</span></div>
          <div class="sum-card"><span class="sum-num">{{ result.edges.length }}</span><span class="sum-label">{{ t('lineage.edges') }}</span></div>
          <div class="sum-card"><span class="sum-num">{{ result.known_tables.length }}</span><span class="sum-label">{{ t('lineage.knownTables') }}</span></div>
        </div>

        <div class="split">
          <div class="panel">
            <div class="panel-title">{{ t('lineage.queryList') }}</div>
            <el-table :data="result.queries" size="small" max-height="300">
              <el-table-column prop="index" label="#" width="46" />
              <el-table-column :label="t('lineage.type')" width="80">
                <template #default="{ row }"><el-tag size="small" effect="plain" type="info">{{ row.type }}</el-tag></template>
              </el-table-column>
              <el-table-column :label="t('lineage.target')" width="130">
                <template #default="{ row }"><code>{{ row.target_table || '-' }}</code></template>
              </el-table-column>
              <el-table-column :label="t('lineage.sources')">
                <template #default="{ row }">
                  <el-tag v-for="s in row.source_tables" :key="s" size="small" effect="plain" type="primary" round style="margin-right: 4px;">{{ s }}</el-tag>
                  <span v-if="!row.source_tables.length">-</span>
                </template>
              </el-table-column>
            </el-table>
          </div>

          <div class="panel">
            <div class="panel-title">{{ t('lineage.impactTitle') }}</div>
            <el-select v-model="impactTable" filterable clearable :placeholder="t('lineage.selectTable')" style="width: 100%; margin-bottom: 10px;">
              <el-option v-for="t in result.known_tables" :key="t" :label="t" :value="t" />
            </el-select>
            <div v-if="impact">
              <div class="impact-label">{{ t('lineage.downstream') }}</div>
              <div class="tag-list">
                <el-tag v-for="t in impact.downstream_tables" :key="t" type="danger" effect="light" round>{{ t }}</el-tag>
                <span v-if="!impact.downstream_tables.length" class="muted">{{ t('lineage.none') }}</span>
              </div>
              <div class="impact-label">{{ t('lineage.dependentQueries') }}</div>
              <div v-for="q in impact.dependent_queries" :key="q.index" class="query-chip">
                #{{ q.index }} {{ q.type }} <code>{{ q.target_table || q.source_tables.join(', ') }}</code>
              </div>
              <span v-if="!impact.dependent_queries.length" class="muted">{{ t('lineage.none') }}</span>
            </div>
            <el-button
              v-if="impactTable"
              size="small"
              type="warning"
              plain
              :icon="Share"
              style="margin-top: 12px;"
              @click="highlightInEr"
            >
              {{ t('lineage.highlightInEr') }}
            </el-button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { analyzeLineage } from '@/api/lineage'
import { getProject } from '@/api/project'

const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const projectId = computed(() => route.params.id)

const projectName = ref('')
const sqlText = ref('')
const analyzing = ref(false)
const result = ref(null)
const impactTable = ref('')
const SESSION_KEY = () => `lineage:${projectId.value}`

const persistState = () => {
  try {
    sessionStorage.setItem(SESSION_KEY(), JSON.stringify({ sql: sqlText.value, result: result.value }))
  } catch {
    // ignore
  }
}

const restoreState = () => {
  try {
    const raw = sessionStorage.getItem(SESSION_KEY())
    if (raw) {
      const data = JSON.parse(raw)
      if (data.sql) sqlText.value = data.sql
      if (data.result) result.value = data.result
    }
  } catch {
    // ignore
  }
}

const impact = computed(() => {
  if (!result.value || !impactTable.value) return null
  const key = impactTable.value.toLowerCase()
  const dependent_queries = result.value.queries.filter(
    (q) =>
      q.source_tables.some((s) => s.toLowerCase() === key) ||
      (q.target_table || '').toLowerCase() === key
  )
  const downstream_tables = []
  for (const e of result.value.edges) {
    if (e.from.toLowerCase() === key && e.to) downstream_tables.push(e.to)
  }
  return {
    dependent_queries,
    downstream_tables: [...new Set(downstream_tables)]
  }
})

const handleAnalyze = async () => {
  if (!sqlText.value.trim()) {
    ElMessage.warning(t('lineage.enterSql'))
    return
  }
  analyzing.value = true
  try {
    result.value = await analyzeLineage(projectId.value, sqlText.value)
    impactTable.value = ''
    persistState()
  } catch {
    // interceptor shows error
  } finally {
    analyzing.value = false
  }
}

const highlightInEr = () => {
  router.push(`/projects/${projectId.value}/er-model?tables=${impactTable.value}&from=lineage`)
}

onMounted(async () => {
  restoreState()
  try {
    const data = await getProject(projectId.value)
    if (data) projectName.value = data.name
  } catch {
    // ignore
  }
})
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.lineage-page { width: 100%; height: 100%; display: flex; flex-direction: column; background: $bg-color; }
.page-header {
  min-height: 64px; background: $bg-white; border-bottom: 1px solid $border-light;
  padding: 12px 20px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px;
}
.header-left { display: flex; flex-direction: column; gap: 4px; }
.subtitle { font-size: 12px; color: #94A3B8; }
.current-crumb { color: #1E293B; font-weight: 600; }
.header-actions { display: flex; align-items: center; gap: 10px; }
.lineage-body { flex: 1; overflow: auto; padding: 20px; }
.sql-input { font-family: 'SF Mono', Consolas, monospace; font-size: 12px; margin-bottom: 16px; }
.result-section { min-width: 0; }
.summary-cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 16px; }
.sum-card { background: $bg-white; border: 1px solid $border-light; border-radius: 12px; padding: 14px; display: flex; flex-direction: column; gap: 4px; }
.sum-num { font-size: 22px; font-weight: 700; color: #3b82f6; }
.sum-label { font-size: 12px; color: #64748b; }
.split { display: grid; grid-template-columns: 1.4fr 1fr; gap: 14px; }
.panel { background: $bg-white; border: 1px solid $border-light; border-radius: 12px; padding: 14px; min-width: 0; }
.panel-title { font-size: 14px; font-weight: 600; color: $text-primary; margin-bottom: 10px; }
.impact-label { font-size: 12px; font-weight: 600; color: #64748b; margin: 10px 0 6px; }
.tag-list { display: flex; flex-wrap: wrap; gap: 6px; }
.query-chip { font-size: 12px; color: $text-regular; padding: 5px 8px; background: $bg-light; border-radius: 6px; margin-bottom: 4px; }
.muted { font-size: 12px; color: #94a3b8; }

html.dark {
  .page-header { background: #252526 !important; border-bottom-color: #3c3c3c !important; }
  .current-crumb { color: #f8fafc !important; }
  .sum-card, .panel { background: #252526 !important; border-color: #3c3c3c !important; }
  .panel-title { color: #e2e8f0 !important; }
  .query-chip { background: #1e1e1e !important; color: #94a3b8 !important; }
}
</style>
