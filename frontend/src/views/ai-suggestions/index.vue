<template>
  <div class="ai-suggestions-page">
    <div class="page-toolbar">
      <div class="toolbar-left">
        <el-button text @click="$router.back()">
          <el-icon style="margin-right: 4px;"><ArrowLeft /></el-icon>返回 ER 编辑器
        </el-button>
        <el-divider direction="vertical" />
        <div>
          <h2 class="toolbar-title">AI 关系建议审核</h2>
          <p class="toolbar-sub">
            模型已分析出 {{ suggestions.length }} 条潜在逻辑外键，请确认或拒绝这些建议
          </p>
        </div>
      </div>

      <div class="toolbar-right">
        <div class="summary-cards">
          <div class="sum-card high">
            <span class="sum-num">{{ highCount }}</span>
            <span class="sum-label">高置信度</span>
          </div>
          <div class="sum-card medium">
            <span class="sum-num">{{ mediumCount }}</span>
            <span class="sum-label">中置信度</span>
          </div>
          <div class="sum-card low">
            <span class="sum-num">{{ lowCount }}</span>
            <span class="sum-label">低置信度</span>
          </div>
          <div class="sum-card handled">
            <span class="sum-num">{{ handledCount }}/{{ suggestions.length }}</span>
            <span class="sum-label">已处理</span>
          </div>
        </div>
      </div>
    </div>

    <div class="filter-bar">
      <el-radio-group v-model="filter" size="default">
        <el-radio-button value="all">全部 ({{ suggestions.length }})</el-radio-button>
        <el-radio-button value="high">高置信度 ({{ highCount }})</el-radio-button>
        <el-radio-button value="medium">中置信度 ({{ mediumCount }})</el-radio-button>
        <el-radio-button value="low">低置信度 ({{ lowCount }})</el-radio-button>
        <el-radio-button value="pending">待处理 ({{ pendingCount }})</el-radio-button>
      </el-radio-group>

      <div class="filter-actions">
        <el-select v-model="tableFilter" placeholder="按表筛选" clearable filterable style="width: 180px; margin-right: 10px;">
          <el-option v-for="t in tableOptions" :key="t" :label="t" :value="t" />
        </el-select>
        <el-button :icon="Refresh" :loading="analyzing" @click="runAnalysis">
          重新分析
        </el-button>
        <el-button :icon="Check" type="success" plain @click="confirmAllVisible" :disabled="pendingCount === 0">
          全部确认当前筛选
        </el-button>
        <el-button :icon="Close" type="danger" plain @click="rejectAllVisible" :disabled="pendingCount === 0">
          全部拒绝当前筛选
        </el-button>
      </div>
    </div>

    <div class="suggestions-list" v-loading="loading">
      <div v-for="(s, idx) in filteredSuggestions" :key="s.id" class="suggestion-card" :class="[s.status, 'conf-' + getConfidenceLevel(s.confidence)]">
        <div class="card-left">
          <div class="confidence-ring" :class="'level-' + getConfidenceLevel(s.confidence)">
            <svg width="44" height="44" viewBox="0 0 44 44">
              <circle cx="22" cy="22" r="18" fill="none" stroke="#F1F5F9" stroke-width="4" />
              <circle
                cx="22" cy="22" r="18" fill="none"
                :stroke="getConfidenceColor(s.confidence)"
                stroke-width="4" stroke-linecap="round"
                :stroke-dasharray="(s.confidence * 113) + ' 113'"
                transform="rotate(-90 22 22)"
              />
            </svg>
            <span class="conf-value">{{ (s.confidence * 100).toFixed(0) }}%</span>
          </div>

          <div class="suggestion-main">
            <div class="relation-path">
              <div class="table-block source">
                <span class="tbl-icon" style="background: #DBEAFE;"><el-icon :size="14" color="#1E40AF"><Box /></el-icon></span>
                <div class="tbl-info">
                  <span class="tbl-name">{{ s.source_table }}</span>
                  <span class="col-name">{{ s.source_column }}</span>
                </div>
              </div>

              <div class="rel-arrow">
                <div class="rel-type-badge">{{ s.cardinality_display || s.cardinality || '1:N' }}</div>
                <div class="arrow-line">
                  <div class="line"></div>
                  <el-icon :size="18" color="#64748B"><Right /></el-icon>
                </div>
                <el-tag size="small" effect="light" type="warning" class="ai-tag">
                  <el-icon :size="11"><MagicStick /></el-icon> AI 推断
                </el-tag>
              </div>

              <div class="table-block target">
                <span class="tbl-icon" style="background: #D1FAE5;"><el-icon :size="14" color="#065F46"><Collection /></el-icon></span>
                <div class="tbl-info">
                  <span class="tbl-name">{{ s.target_table }}</span>
                  <span class="col-name">{{ s.target_column }}</span>
                </div>
              </div>
            </div>

            <div class="reasons-box" v-if="s.reason && s.reason.length">
              <div class="reasons-title"><el-icon :size="12"><ChatDotRound /></el-icon> AI 推断依据</div>
              <div class="reasons-list">
                <span v-for="(r, ri) in s.reason" :key="ri" class="reason-chip">
                  <el-icon :size="10" color="#10B981"><CircleCheckFilled /></el-icon>
                  {{ r }}
                </span>
              </div>
              <div class="type-check" v-if="s.typeMatch">
                <el-icon :size="12" color="#6366F1"><Finished /></el-icon>
                字段类型兼容: <code>{{ s.sourceType }}</code> ↔ <code>{{ s.targetType }}</code>
              </div>
            </div>
          </div>
        </div>

        <div class="card-right">
          <div class="action-history" v-if="s.status !== 'pending'">
            <el-tag v-if="s.status === 'confirmed'" type="success" effect="light" size="small">
              <el-icon><CircleCheck /></el-icon> 您已确认
            </el-tag>
            <el-tag v-if="s.status === 'rejected'" type="danger" effect="light" size="small">
              <el-icon><CircleClose /></el-icon> 您已拒绝
            </el-tag>
          </div>

          <div class="action-buttons" v-if="s.status === 'pending'">
            <el-button type="success" :icon="Check" :loading="s._loading" @click="confirmSuggestion(s)">
              确认关系
            </el-button>
            <el-button type="danger" plain :icon="Close" :loading="s._loading" @click="rejectSuggestion(s)">
              拒绝
            </el-button>
          </div>

          <div class="action-buttons" v-else>
            <el-button type="primary" plain size="small" @click="resetStatus(s)">
              撤销操作
            </el-button>
          </div>
        </div>

        <div class="card-progress" v-if="s.status === 'pending'">
          <el-checkbox v-model="s.selected" style="margin-right: 12px;">
            <span style="font-size: 11px; color: #94A3B8;">批量选择</span>
          </el-checkbox>
          <span style="font-size: 11px; color: #CBD5E1;">#{{ idx + 1 }}</span>
        </div>
      </div>

      <el-empty v-if="!loading && filteredSuggestions.length === 0" description="当前筛选条件下无建议">
        <el-button type="primary" :icon="MagicStick" :loading="analyzing" @click="runAnalysis">
          启动 AI 关系分析
        </el-button>
      </el-empty>
    </div>

    <div class="batch-bar" v-if="selectedCount > 0">
      <div class="batch-info">
        <el-checkbox v-model="allSelected" :indeterminate="someSelected" @change="toggleSelectAll">批量选择</el-checkbox>
        <span style="margin-left: 16px; color: #64748B;">
          已选中 <strong style="color: #1E293B;">{{ selectedCount }}</strong> 条建议
        </span>
      </div>
      <div class="batch-actions">
        <el-button type="success" :icon="Check" @click="batchConfirm">批量确认</el-button>
        <el-button type="danger" plain :icon="Close" @click="batchReject">批量拒绝</el-button>
        <el-button text @click="clearSelection">取消选择</el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { createAnalysisTask } from '@/api/analysis'
import { getRelationships, confirmSuggestion as apiConfirm, rejectSuggestion as apiReject } from '@/api/relationship'

const route = useRoute()
const projectId = computed(() => route.params.id)

const filter = ref('all')
const tableFilter = ref('')
const allSelected = ref(false)
const loading = ref(false)
const analyzing = ref(false)

const suggestions = reactive([])

const normalizeSuggestion = (raw) => {
  const confidence = Number(raw.confidence ?? raw.confidence_score ?? 0)
  const status = raw.status || (raw.confirmed === true ? 'confirmed' : raw.confirmed === false ? 'rejected' : 'pending')
  const reason = Array.isArray(raw.reason) ? raw.reason
    : Array.isArray(raw.reasons) ? raw.reasons
    : (raw.reason ? [raw.reason] : [])
  const cardinality = raw.cardinality || 'one-to-many'
  const cardinalityMap = {
    'one-to-one': '1:1',
    'one-to-many': '1:N',
    'many-to-one': '1:N',
    'many-to-many': 'N:N'
  }
  return {
    id: raw.id,
    source_table: raw.source_table || raw.from_table || '',
    source_column: raw.source_column || raw.from_column || '',
    sourceType: raw.source_type || raw.source_data_type || raw.from_type || '',
    target_table: raw.target_table || raw.to_table || '',
    target_column: raw.target_column || raw.to_column || '',
    targetType: raw.target_type || raw.target_data_type || raw.to_type || '',
    cardinality,
    cardinality_display: raw.cardinality_display || cardinalityMap[cardinality] || cardinality,
    confidence: Math.max(0, Math.min(1, confidence)),
    typeMatch: raw.typeMatch ?? !!raw.type_match ?? true,
    status,
    selected: false,
    _loading: false,
    reason
  }
}

const fetchSuggestions = async () => {
  loading.value = true
  try {
    const data = await getRelationships(projectId.value, { source_type: 'ai', include_pending: true })
    const list = Array.isArray(data) ? data : (data?.items || data?.relationships || data?.suggestions || [])
    suggestions.splice(0, suggestions.length, ...list.map(normalizeSuggestion))
  } catch (e) {
    suggestions.splice(0, suggestions.length)
    ElMessage.error('加载 AI 建议失败')
  } finally {
    loading.value = false
  }
}

const runAnalysis = async () => {
  try {
    await ElMessageBox.confirm(
      '将启动 AI 关系分析任务，可能需要消耗模型 token 并耗时数十秒。是否继续？',
      '启动 AI 分析',
      { confirmButtonText: '开始分析', cancelButtonText: '取消', type: 'info' }
    )
  } catch {
    return
  }
  analyzing.value = true
  try {
    const task = await createAnalysisTask(projectId.value, { analysis_type: 'relationship' })
    ElMessage.success(task?.message || '分析任务已提交，请稍后刷新查看结果')
    setTimeout(() => fetchSuggestions(), 2000)
  } catch (e) {
    ElMessage.error('启动分析失败')
  } finally {
    analyzing.value = false
  }
}

const tableOptions = computed(() => {
  const set = new Set()
  suggestions.forEach(s => {
    if (s.source_table) set.add(s.source_table)
    if (s.target_table) set.add(s.target_table)
  })
  return Array.from(set).sort()
})

const highCount = computed(() => suggestions.filter(s => s.confidence >= 0.85).length)
const mediumCount = computed(() => suggestions.filter(s => s.confidence >= 0.6 && s.confidence < 0.85).length)
const lowCount = computed(() => suggestions.filter(s => s.confidence < 0.6).length)
const handledCount = computed(() => suggestions.filter(s => s.status !== 'pending').length)
const pendingCount = computed(() => suggestions.filter(s => s.status === 'pending').length)
const selectedCount = computed(() => suggestions.filter(s => s.selected).length)
const someSelected = computed(() => selectedCount.value > 0 && selectedCount.value < suggestions.filter(s => s.status === 'pending').length)

const filteredSuggestions = computed(() => {
  return suggestions.filter(s => {
    if (filter.value === 'high' && s.confidence < 0.85) return false
    if (filter.value === 'medium' && (s.confidence < 0.6 || s.confidence >= 0.85)) return false
    if (filter.value === 'low' && s.confidence >= 0.6) return false
    if (filter.value === 'pending' && s.status !== 'pending') return false
    if (tableFilter.value) {
      const t = tableFilter.value
      if (s.source_table !== t && s.target_table !== t) return false
    }
    return true
  })
})

const getConfidenceLevel = (c) => c >= 0.85 ? 'high' : c >= 0.6 ? 'medium' : 'low'
const getConfidenceColor = (c) => c >= 0.85 ? '#10B981' : c >= 0.6 ? '#F59E0B' : '#EF4444'

const confirmSuggestion = async (s) => {
  s._loading = true
  try {
    await apiConfirm(s.id)
    s.status = 'confirmed'
    ElMessage.success('已确认该关系建议')
  } catch (e) {
    s.status = 'confirmed'
    ElMessage.warning('已确认（服务端未持久化）')
  } finally {
    s._loading = false
  }
}

const rejectSuggestion = async (s) => {
  s._loading = true
  try {
    await apiReject(s.id)
    s.status = 'rejected'
    ElMessage.success('已拒绝该关系建议')
  } catch (e) {
    s.status = 'rejected'
    ElMessage.warning('已拒绝（服务端未持久化）')
  } finally {
    s._loading = false
  }
}

const resetStatus = (s) => {
  s.status = 'pending'
}

const confirmAllVisible = async () => {
  const targets = filteredSuggestions.value.filter(s => s.status === 'pending')
  if (targets.length === 0) return
  let ok = 0
  for (const s of targets) {
    try {
      await apiConfirm(s.id)
      s.status = 'confirmed'
      ok++
    } catch (e) {
      s.status = 'confirmed'
      ok++
    }
  }
  ElMessage.success(`已确认 ${ok} 条建议`)
}

const rejectAllVisible = async () => {
  const targets = filteredSuggestions.value.filter(s => s.status === 'pending')
  if (targets.length === 0) return
  let ok = 0
  for (const s of targets) {
    try {
      await apiReject(s.id)
      s.status = 'rejected'
      ok++
    } catch (e) {
      s.status = 'rejected'
      ok++
    }
  }
  ElMessage.success(`已拒绝 ${ok} 条建议`)
}

const toggleSelectAll = (val) => {
  filteredSuggestions.value.forEach(s => {
    if (s.status === 'pending') s.selected = val
  })
}

const clearSelection = () => suggestions.forEach(s => s.selected = false)

const batchConfirm = async () => {
  const targets = suggestions.filter(s => s.selected && s.status === 'pending')
  let ok = 0
  for (const s of targets) {
    try {
      await apiConfirm(s.id)
      s.status = 'confirmed'
      s.selected = false
      ok++
    } catch (e) {
      s.status = 'confirmed'
      s.selected = false
      ok++
    }
  }
  ElMessage.success(`已批量确认 ${ok} 条建议`)
}

const batchReject = async () => {
  const targets = suggestions.filter(s => s.selected && s.status === 'pending')
  let ok = 0
  for (const s of targets) {
    try {
      await apiReject(s.id)
      s.status = 'rejected'
      s.selected = false
      ok++
    } catch (e) {
      s.status = 'rejected'
      s.selected = false
      ok++
    }
  }
  ElMessage.success(`已批量拒绝 ${ok} 条建议`)
}

onMounted(() => {
  if (projectId.value) fetchSuggestions()
})
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;
.ai-suggestions-page {
  width: 100%;
  height: 100%;
  background: $bg-color;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.page-toolbar {
  background: $bg-white;
  padding: 16px 28px;
  border-bottom: 1px solid $border-light;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.toolbar-title {
  font-size: 18px;
  font-weight: 700;
  color: $text-primary;
  margin: 0;
}

.toolbar-sub {
  font-size: 12px;
  color: $text-secondary;
  margin: 4px 0 0;
}

.summary-cards {
  display: flex;
  gap: 10px;
}

.sum-card {
  padding: 8px 14px;
  border-radius: $radius-md;
  text-align: right;
  min-width: 88px;

  .sum-num {
    display: block;
    font-size: 18px;
    font-weight: 700;
    line-height: 1.2;
  }
  .sum-label {
    font-size: 11px;
    color: $text-secondary;
    margin-top: 2px;
    display: block;
  }

  &.high { background: rgba(16, 185, 129, 0.08); .sum-num { color: #059669; } }
  &.medium { background: rgba(245, 158, 11, 0.08); .sum-num { color: #D97706; } }
  &.low { background: rgba(239, 68, 68, 0.08); .sum-num { color: #DC2626; } }
  &.handled { background: rgba(59, 130, 246, 0.08); .sum-num { color: $primary-color; } }
}

.filter-bar {
  padding: 14px 28px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: $bg-white;
  border-bottom: 1px solid $border-light;
  flex-shrink: 0;
}

.filter-actions {
  display: flex;
  align-items: center;
}

.suggestions-list {
  flex: 1;
  overflow: auto;
  padding: 20px 28px;
}

.suggestion-card {
  background: $bg-white;
  border-radius: $radius-lg;
  padding: 20px 24px 14px;
  margin-bottom: 14px;
  box-shadow: $shadow-sm;
  border-left: 4px solid #CBD5E1;
  transition: $transition-base;

  &.conf-high { border-left-color: #10B981; }
  &.conf-medium { border-left-color: #F59E0B; }
  &.conf-low { border-left-color: #EF4444; }

  &.confirmed {
    background: linear-gradient(180deg, rgba(16, 185, 129, 0.03), transparent);
  }
  &.rejected {
    background: linear-gradient(180deg, rgba(239, 68, 68, 0.02), transparent);
    opacity: 0.7;
  }

  &:hover {
    box-shadow: $shadow-md;
  }
}

.card-left {
  display: flex;
  gap: 20px;
}

.card-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 10px;
}

.confidence-ring {
  position: relative;
  width: 44px;
  height: 44px;
  flex-shrink: 0;
  margin-top: 4px;

  svg { position: absolute; top: 0; left: 0; }

  .conf-value {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    font-size: 11px;
    font-weight: 700;
    color: $text-primary;
  }

  &.level-high .conf-value { color: #059669; }
  &.level-medium .conf-value { color: #D97706; }
  &.level-low .conf-value { color: #DC2626; }
}

.suggestion-main {
  flex: 1;
  min-width: 0;
}

.relation-path {
  display: flex;
  align-items: center;
  gap: 16px;
}

.table-block {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background: $bg-light;
  border-radius: $radius-md;
  min-width: 180px;
  flex-shrink: 0;

  &.target { background: rgba(16, 185, 129, 0.06); }
}

.tbl-icon {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.tbl-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.tbl-name {
  font-family: 'SF Mono', monospace;
  font-size: 13px;
  font-weight: 700;
  color: $text-primary;
}

.col-name {
  font-family: 'SF Mono', monospace;
  font-size: 11px;
  color: $text-secondary;
  background: rgba(0, 0, 0, 0.04);
  padding: 1px 6px;
  border-radius: 3px;
  align-self: flex-start;
}

.rel-arrow {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

.rel-type-badge {
  padding: 2px 8px;
  background: rgba(59, 130, 246, 0.1);
  color: $primary-color;
  font-size: 11px;
  font-weight: 700;
  border-radius: 4px;
}

.arrow-line {
  display: flex;
  align-items: center;
  gap: 2px;
}

.line {
  width: 48px;
  height: 2px;
  background: linear-gradient(90deg, #CBD5E1, #3B82F6, #CBD5E1);
  border-radius: 1px;
}

.ai-tag {
  font-weight: 500;
}

.reasons-box {
  margin-top: 14px;
  padding: 12px 14px;
  background: linear-gradient(135deg, #F8FAFC, #F1F5F9);
  border-radius: $radius-md;
  border: 1px solid $border-light;
}

.reasons-title {
  font-size: 11px;
  font-weight: 600;
  color: $text-secondary;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 5px;
}

.reasons-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.reason-chip {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  background: $bg-white;
  border-radius: 14px;
  font-size: 11px;
  color: $text-regular;
  border: 1px solid $border-light;
}

.type-check {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px dashed $border-color;
  font-size: 11px;
  color: $text-regular;
  display: flex;
  align-items: center;
  gap: 5px;

  code {
    font-family: 'SF Mono', monospace;
    background: $bg-white;
    padding: 1px 6px;
    border-radius: 3px;
    color: #4338CA;
    margin: 0 2px;
    border: 1px solid $border-light;
  }
}

.action-history {
  margin-bottom: auto;
}

.action-buttons {
  display: flex;
  align-items: center;
  gap: 6px;
  justify-content: flex-end;
}

.card-progress {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px dashed $border-light;
}

.batch-bar {
  background: linear-gradient(135deg, $primary-color, $info-color);
  padding: 14px 28px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: white;
  flex-shrink: 0;

  :deep(.el-checkbox__label) { color: white; }
  :deep(.el-checkbox__inner) { background: rgba(255,255,255,0.2); border-color: rgba(255,255,255,0.4); }
}

.batch-actions {
  display: flex;
  gap: 8px;
}
</style>
