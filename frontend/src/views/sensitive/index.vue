<template>
  <div class="sensitive-page">
    <div class="page-header">
      <div class="header-left">
        <el-breadcrumb separator="/" class="breadcrumb-sm">
          <el-breadcrumb-item style="color: #94A3B8;">{{ t('sensitive.breadcrumb.project') }}</el-breadcrumb-item>
          <el-breadcrumb-item style="color: #94A3B8; cursor: pointer;" @click="$router.push('/projects')">{{ projectName }}</el-breadcrumb-item>
          <el-breadcrumb-item><span class="current-crumb">{{ t('sensitive.breadcrumb.title') }}</span></el-breadcrumb-item>
        </el-breadcrumb>
        <div class="subtitle">{{ t('sensitive.subtitle') }}</div>
      </div>
      <div class="header-actions">
        <el-checkbox v-model="includeSampling">{{ t('sensitive.sampling') }}</el-checkbox>
        <el-button type="primary" :icon="Search" :loading="scanning" @click="handleScan">
          {{ t('sensitive.scan') }}
        </el-button>
        <el-button :icon="Download" :loading="exporting" :disabled="items.length === 0" @click="handleExport">
          {{ t('sensitive.exportReport') }}
        </el-button>
        <el-button :icon="Back" @click="$router.push(`/projects/${projectId}/er-model`)">
          {{ t('sensitive.backToEr') }}
        </el-button>
      </div>
    </div>

    <div class="sensitive-body">
      <div class="summary-cards">
        <div class="sum-card high"><span class="sum-num">{{ counts.high }}</span><span class="sum-label">{{ t('sensitive.high') }}</span></div>
        <div class="sum-card medium"><span class="sum-num">{{ counts.medium }}</span><span class="sum-label">{{ t('sensitive.medium') }}</span></div>
        <div class="sum-card low"><span class="sum-num">{{ counts.low }}</span><span class="sum-label">{{ t('sensitive.low') }}</span></div>
        <div class="sum-card total"><span class="sum-num">{{ items.length }}</span><span class="sum-label">{{ t('sensitive.total') }}</span></div>
      </div>

      <div class="filter-row">
        <el-radio-group v-model="riskFilter" size="small">
          <el-radio-button value="all">{{ t('sensitive.filterAll') }}</el-radio-button>
          <el-radio-button value="high">{{ t('sensitive.high') }}</el-radio-button>
          <el-radio-button value="medium">{{ t('sensitive.medium') }}</el-radio-button>
          <el-radio-button value="low">{{ t('sensitive.low') }}</el-radio-button>
        </el-radio-group>
      </div>

      <div class="field-list" v-loading="loading">
        <div v-for="f in filtered" :key="f.id" class="field-row" :class="[f.risk_level, f.status]">
          <div class="field-target">
            <code>{{ f.table_name }}.{{ f.column_name }}</code>
          </div>
          <el-tag size="small" effect="light" type="warning" round>{{ f.category_label }}</el-tag>
          <el-tag size="small" :type="riskTag(f.risk_level)" effect="light" round>{{ riskLabel(f.risk_level) }}</el-tag>
          <div class="confidence">{{ (f.confidence * 100).toFixed(0) }}%</div>
          <div class="reason">{{ f.matched_reason }}</div>
          <div class="sample" v-if="f.sample_total">抽样 {{ f.sample_hits }}/{{ f.sample_total }}</div>
          <el-tag size="small" :type="statusTag(f.status)" effect="plain" class="status-tag">{{ statusLabel(f.status) }}</el-tag>
          <div class="row-actions" v-if="f.status === 'detected'">
            <el-button size="small" link type="danger" @click="setStatus(f, 'confirmed')">{{ t('sensitive.confirm') }}</el-button>
            <el-button size="small" link type="info" @click="setStatus(f, 'false_positive')">{{ t('sensitive.falsePositive') }}</el-button>
          </div>
          <el-button v-else-if="f.status === 'confirmed'" size="small" link type="success" @click="setStatus(f, 'mitigated')">
            {{ t('sensitive.mitigated') }}
          </el-button>
        </div>
        <el-empty v-if="!loading && items.length === 0" :description="t('sensitive.empty')" :image-size="120" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  scanSensitive,
  listSensitiveFields,
  updateSensitiveField,
  exportSensitiveReport
} from '@/api/sensitive'
import { getProject } from '@/api/project'

const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const projectId = computed(() => route.params.id)

const projectName = ref('')
const items = ref([])
const loading = ref(false)
const scanning = ref(false)
const exporting = ref(false)
const includeSampling = ref(false)
const riskFilter = ref('all')

const riskTag = (r) => (r === 'high' ? 'danger' : r === 'medium' ? 'warning' : 'info')
const riskLabel = (r) => t(`sensitive.risk.${r}`)
const statusTag = (s) => (s === 'confirmed' ? 'danger' : s === 'mitigated' ? 'success' : s === 'false_positive' ? 'info' : 'warning')
const statusLabel = (s) => t(`sensitive.status.${s}`)

const counts = computed(() => {
  const c = { high: 0, medium: 0, low: 0 }
  for (const f of items.value) c[f.risk_level] = (c[f.risk_level] || 0) + 1
  return c
})

const filtered = computed(() => {
  if (riskFilter.value === 'all') return items.value
  return items.value.filter((f) => f.risk_level === riskFilter.value)
})

const load = async () => {
  loading.value = true
  try {
    items.value = await listSensitiveFields(projectId.value)
  } catch {
    items.value = []
  } finally {
    loading.value = false
  }
}

const handleScan = async () => {
  if (includeSampling.value) {
    try {
      await ElMessageBox.confirm(t('sensitive.samplingConfirm'), t('sensitive.scan'), {
        confirmButtonText: t('common.confirm'),
        cancelButtonText: t('common.cancel'),
        type: 'info'
      })
    } catch {
      return
    }
  }
  scanning.value = true
  try {
    const res = await scanSensitive(projectId.value, {
      include_sampling: includeSampling.value,
      sample_size: 100
    })
    ElMessage.success(t('sensitive.scanned', { count: res.field_count }))
    await load()
  } catch {
    // interceptor shows error
  } finally {
    scanning.value = false
  }
}

const setStatus = async (f, status) => {
  try {
    await updateSensitiveField(f.id, status)
    f.status = status
  } catch {
    // ignore
  }
}

const handleExport = async () => {
  exporting.value = true
  try {
    const blob = await exportSensitiveReport(projectId.value)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'sensitive-report.md'
    a.click()
    URL.revokeObjectURL(url)
  } catch {
    // ignore
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

.sensitive-page { width: 100%; height: 100%; display: flex; flex-direction: column; background: $bg-color; }
.page-header {
  min-height: 64px; background: $bg-white; border-bottom: 1px solid $border-light;
  padding: 12px 20px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px;
}
.header-left { display: flex; flex-direction: column; gap: 4px; }
.subtitle { font-size: 12px; color: #94A3B8; }
.current-crumb { color: #1E293B; font-weight: 600; }
.header-actions { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.sensitive-body { flex: 1; overflow: auto; padding: 20px; }
.summary-cards { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 16px; }
.sum-card {
  background: $bg-white; border: 1px solid $border-light; border-radius: 12px; padding: 14px;
  display: flex; flex-direction: column; gap: 4px;
  &.high .sum-num { color: #ef4444; }
  &.medium .sum-num { color: #f59e0b; }
  &.low .sum-num { color: #3b82f6; }
  &.total .sum-num { color: #64748b; }
}
.sum-num { font-size: 22px; font-weight: 700; }
.sum-label { font-size: 12px; color: #64748b; }
.filter-row { margin-bottom: 14px; }
.field-list { display: flex; flex-direction: column; gap: 8px; }
.field-row {
  background: $bg-white; border: 1px solid $border-light; border-radius: 10px; padding: 10px 14px;
  display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
  &.high { border-left: 3px solid #ef4444; }
  &.medium { border-left: 3px solid #f59e0b; }
  &.low { border-left: 3px solid #3b82f6; }
  &.false_positive { opacity: 0.6; }
  &.mitigated { opacity: 0.75; }
}
.field-target { min-width: 180px; font-size: 13px; color: $text-primary; }
.confidence { font-size: 13px; font-weight: 600; color: #334155; min-width: 42px; }
.reason { flex: 1; font-size: 12px; color: #64748b; min-width: 120px; }
.sample { font-size: 11px; color: #94a3b8; }
.status-tag { flex-shrink: 0; }
.row-actions { flex-shrink: 0; display: flex; gap: 4px; }

html.dark {
  .page-header { background: #252526 !important; border-bottom-color: #3c3c3c !important; }
  .current-crumb { color: #f8fafc !important; }
  .sum-card, .field-row { background: #252526 !important; border-color: #3c3c3c !important; }
  .field-target { color: #e2e8f0 !important; }
  .confidence { color: #e2e8f0 !important; }
}
</style>
