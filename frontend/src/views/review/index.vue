<template>
  <div class="review-page">
    <div class="page-header">
      <div class="header-left">
        <el-breadcrumb separator="/" class="breadcrumb-sm">
          <el-breadcrumb-item style="color: #94A3B8;">{{ t('review.breadcrumb.project') }}</el-breadcrumb-item>
          <el-breadcrumb-item style="color: #94A3B8; cursor: pointer;" @click="$router.push('/projects')">{{ projectName }}</el-breadcrumb-item>
          <el-breadcrumb-item><span class="current-crumb">{{ t('review.breadcrumb.title') }}</span></el-breadcrumb-item>
        </el-breadcrumb>
        <div class="subtitle">{{ t('review.subtitle') }}</div>
      </div>
      <div class="header-actions">
        <el-checkbox v-model="runAi">{{ t('review.runAi') }}</el-checkbox>
        <el-button type="primary" :icon="MagicStick" :loading="running" @click="runReview">
          {{ t('review.runReview') }}
        </el-button>
        <el-button :icon="Download" :loading="exporting" :disabled="!report" @click="exportMarkdown">
          {{ t('review.exportReport') }}
        </el-button>
        <el-button :icon="Back" @click="$router.push(`/projects/${projectId}/er-model`)">
          {{ t('review.backToEr') }}
        </el-button>
      </div>
    </div>

    <div class="review-body" v-loading="running">
      <div v-if="!report" class="empty-state">
        <el-empty :description="t('review.empty')" :image-size="140" />
      </div>
      <template v-else>
        <div class="summary-cards">
          <div class="sum-card fatal">
            <span class="sum-num">{{ report.summary?.fatal || 0 }}</span>
            <span class="sum-label">{{ t('review.fatal') }}</span>
          </div>
          <div class="sum-card warning">
            <span class="sum-num">{{ report.summary?.warning || 0 }}</span>
            <span class="sum-label">{{ t('review.warning') }}</span>
          </div>
          <div class="sum-card suggestion">
            <span class="sum-num">{{ report.summary?.suggestion || 0 }}</span>
            <span class="sum-label">{{ t('review.suggestion') }}</span>
          </div>
          <div class="sum-card ai">
            <span class="sum-num">{{ report.summary?.ai_findings || 0 }}</span>
            <span class="sum-label">{{ t('review.aiFindings') }}</span>
          </div>
        </div>

        <div class="report-time">{{ t('review.generatedAt') }}: {{ formatTime(report.created_at) }}</div>

        <div v-if="report.ai_findings?.length" class="ai-section">
          <div class="section-title ai">{{ t('review.aiTitle') }}</div>
          <div v-for="(f, i) in report.ai_findings" :key="i" class="ai-card" :class="f.severity">
            <div class="ai-head">
              <el-tag size="small" :type="severityTag(f.severity)" effect="light">{{ severityLabel(f.severity) }}</el-tag>
              <span class="ai-category">{{ f.category }}</span>
              <span class="ai-target" v-if="f.target">{{ f.target }}</span>
            </div>
            <div class="ai-message">{{ f.message }}</div>
            <div class="ai-suggestion" v-if="f.suggestion">💡 {{ f.suggestion }}</div>
          </div>
        </div>

        <div class="lint-section">
          <div class="section-title">{{ t('review.lintTitle') }}</div>
          <div class="filter-row">
            <el-radio-group v-model="severityFilter" size="small">
              <el-radio-button value="all">{{ t('review.filterAll') }}</el-radio-button>
              <el-radio-button value="fatal">{{ t('review.fatal') }}</el-radio-button>
              <el-radio-button value="warning">{{ t('review.warning') }}</el-radio-button>
              <el-radio-button value="suggestion">{{ t('review.suggestion') }}</el-radio-button>
            </el-radio-group>
          </div>
          <div v-for="f in filteredFindings" :key="f.id + f.table + f.column + f.message" class="lint-card" :class="f.severity">
            <div class="lint-head">
              <el-tag size="small" :type="severityTag(f.severity)" effect="light">{{ severityLabel(f.severity) }}</el-tag>
              <span class="lint-category">{{ f.category }}</span>
              <span class="lint-target">{{ f.table }}<template v-if="f.column">.{{ f.column }}</template></span>
            </div>
            <div class="lint-message">{{ f.message }}</div>
            <div class="lint-fix" v-if="f.fix">🔧 {{ f.fix }}</div>
          </div>
          <el-empty v-if="filteredFindings.length === 0" :description="t('review.noFindings')" :image-size="80" />
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import dayjs from 'dayjs'
import { createReview, getLatestReview } from '@/api/review'
import { getProject } from '@/api/project'

const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const projectId = computed(() => route.params.id)

const projectName = ref('')
const report = ref(null)
const running = ref(false)
const exporting = ref(false)
const runAi = ref(false)
const severityFilter = ref('all')

const formatTime = (v) => (v ? dayjs(v).format('YYYY-MM-DD HH:mm') : '-')
const severityTag = (s) => (s === 'fatal' ? 'danger' : s === 'warning' ? 'warning' : 'info')
const severityLabel = (s) => (s === 'fatal' ? t('review.fatal') : s === 'warning' ? t('review.warning') : t('review.suggestion'))

const filteredFindings = computed(() => {
  const list = report.value?.lint_findings || []
  if (severityFilter.value === 'all') return list
  return list.filter((f) => f.severity === severityFilter.value)
})

const runReview = async () => {
  running.value = true
  try {
    report.value = await createReview(projectId.value, { run_ai: runAi.value })
  } catch {
    // interceptor shows error
  } finally {
    running.value = false
  }
}

const markdown = computed(() => {
  if (!report.value) return ''
  const r = report.value
  const lines = []
  lines.push(`# 数据库架构评审报告`)
  lines.push('')
  lines.push(`- 生成时间：${formatTime(r.created_at)}`)
  lines.push(`- 致命：${r.summary?.fatal || 0} / 警告：${r.summary?.warning || 0} / 建议：${r.summary?.suggestion || 0}`)
  lines.push('')
  if (r.ai_findings?.length) {
    lines.push('## AI 架构评审')
    r.ai_findings.forEach((f) => {
      lines.push(`### [${severityLabel(f.severity)}] ${f.category}${f.target ? ' — ' + f.target : ''}`)
      lines.push(`- ${f.message}`)
      if (f.suggestion) lines.push(`- 建议：${f.suggestion}`)
      lines.push('')
    })
  }
  lines.push('## 规则体检')
  ;(r.lint_findings || []).forEach((f) => {
    lines.push(`- [${severityLabel(f.severity)}] ${f.category} ${f.table}${f.column ? '.' + f.column : ''}：${f.message}`)
    if (f.fix) lines.push(`  - 修复：${f.fix}`)
  })
  return lines.join('\n')
})

const exportMarkdown = () => {
  exporting.value = true
  try {
    const blob = new Blob([markdown.value], { type: 'text/markdown;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'schema-review-report.md'
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
    report.value = await getLatestReview(projectId.value)
  } catch {
    report.value = null
  }
})
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.review-page {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: $bg-color;
}
.page-header {
  min-height: 64px;
  background: $bg-white;
  border-bottom: 1px solid $border-light;
  padding: 12px 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 10px;
}
.header-left { display: flex; flex-direction: column; gap: 4px; }
.subtitle { font-size: 12px; color: #94A3B8; }
.current-crumb { color: #1E293B; font-weight: 600; }
.header-actions { display: flex; align-items: center; gap: 10px; }
.review-body { flex: 1; overflow: auto; padding: 20px; }
.empty-state { display: flex; align-items: center; justify-content: center; height: 100%; }
.summary-cards { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 12px; }
.sum-card {
  background: $bg-white;
  border: 1px solid $border-light;
  border-radius: 12px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  &.fatal .sum-num { color: #ef4444; }
  &.warning .sum-num { color: #f59e0b; }
  &.suggestion .sum-num { color: #3b82f6; }
  &.ai .sum-num { color: #8b5cf6; }
}
.sum-num { font-size: 22px; font-weight: 700; }
.sum-label { font-size: 12px; color: #64748b; }
.report-time { font-size: 12px; color: #94a3b8; margin-bottom: 16px; }
.section-title {
  font-size: 15px;
  font-weight: 600;
  margin: 18px 0 12px;
  padding-left: 10px;
  border-left: 3px solid #cbd5e1;
  &.ai { border-color: #8b5cf6; color: #6d28d9; }
}
.ai-card, .lint-card {
  background: $bg-white;
  border: 1px solid $border-light;
  border-radius: 10px;
  padding: 12px 14px;
  margin-bottom: 10px;
  &.fatal { border-left: 3px solid #ef4444; }
  &.warning { border-left: 3px solid #f59e0b; }
  &.suggestion { border-left: 3px solid #3b82f6; }
}
.ai-head, .lint-head { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.ai-category, .lint-category { font-size: 12px; font-weight: 600; color: $text-regular; }
.ai-target, .lint-target { font-size: 12px; color: #3b82f6; font-family: 'SF Mono', Consolas, monospace; }
.ai-message, .lint-message { font-size: 13px; color: $text-primary; margin-top: 8px; line-height: 1.55; }
.ai-suggestion, .lint-fix { font-size: 12px; color: #047857; background: rgba(16, 185, 129, 0.07); border-radius: 6px; padding: 8px 10px; margin-top: 8px; line-height: 1.5; }
.filter-row { margin-bottom: 12px; }

html.dark {
  .page-header { background: #252526 !important; border-bottom-color: #3c3c3c !important; }
  .current-crumb { color: #f8fafc !important; }
  .sum-card, .ai-card, .lint-card { background: #252526 !important; border-color: #3c3c3c !important; }
  .ai-message, .lint-message { color: #e2e8f0 !important; }
  .review-page { background: #1e1e1e !important; }
  .sum-label { color: #94a3b8 !important; }
  .report-time { color: #94a3b8 !important; }
  .section-title { color: #e2e8f0 !important; }
  .section-title.ai { color: #a78bfa !important; }
  .ai-category, .lint-category { color: #cbd5e1 !important; }
}
</style>
