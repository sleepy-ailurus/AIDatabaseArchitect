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
            <template v-if="suggestions.length > 0">
              模型已分析出 {{ suggestions.length }} 条潜在逻辑外键，请确认或拒绝这些建议
            </template>
            <template v-else-if="existingFks.length > 0">
              本次 AI 分析未发现新建议，数据库已存在 {{ existingFks.length }} 条显式外键关系
            </template>
            <template v-else>
              尚未分析，点击下方按钮启动 AI 关系分析
            </template>
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

    <el-alert
      v-if="fkCoverageFullBanner"
      type="success"
      :closable="true"
      show-icon
      class="coverage-banner"
      @close="fkCoverageFullBanner = false"
    >
      <template #title>🎉 数据库显式外键覆盖度很高</template>
      <div style="line-height: 1.6;">
        基于字段名匹配的规则法未发现新的候选关系，为避免浪费 Token 和耗时，已自动跳过 LLM 调用。
        当前数据库的物理外键已覆盖 AI 常规可识别的全部逻辑关联。
        若你仍认为存在未被识别的隐式关系（如多对多桥接表、1:1 扩展表等），可直接在 ER 编辑器中手动拖拽连线创建。
      </div>
    </el-alert>

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
          <div class="confidence-ring" :class="'level-' + getConfidenceLevel(s.confidence)" v-if="settingsStore.showConfidence">
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
          <div class="confidence-ring confidence-placeholder" v-else>
            <el-icon :size="24" color="#94A3B8"><MagicStick /></el-icon>
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

      <el-empty v-if="!loading && filteredSuggestions.length === 0 && existingFks.length === 0" description="当前筛选条件下无建议">
        <el-button type="primary" :icon="MagicStick" :loading="analyzing" @click="runAnalysis">
          启动 AI 关系分析
        </el-button>
      </el-empty>

      <!-- When AI produces no new suggestions but the database has explicit FKs,
           show them as reference. This happens when the schema already defines
           every discoverable relationship — the AI correctly found nothing new. -->
      <div v-if="!loading && filteredSuggestions.length === 0 && existingFks.length > 0" class="existing-fk-section">
        <el-alert
          type="info"
          show-icon
          :closable="false"
          class="fk-info-alert"
        >
          <template #title>
            本次 AI 分析未发现新的逻辑外键，但检测到数据库中已存在 {{ existingFks.length }} 条显式外键关系
          </template>
          <div style="line-height: 1.6;">
            这些外键由数据库 Schema 同步时自动解析，已在 ER 编辑器中以实线显示。
            AI 跳过分析是因为基于字段名匹配的规则法未发现新的候选关系，说明现有外键可能已经覆盖了主要的逻辑关联。
            如需在 ER 图中补充隐式关系（如缩写命名、多对多桥接表等），可在 ER 编辑器中手动拖拽连线创建。
          </div>
        </el-alert>

        <div class="existing-fk-list">
          <div class="existing-fk-header">
            <span class="section-title">已有的数据库外键（只读参考）</span>
            <span class="section-count">{{ existingFks.length }} 条</span>
          </div>
          <div v-for="fk in existingFks" :key="fk.id" class="existing-fk-card">
            <div class="fk-path">
              <div class="table-block source">
                <span class="tbl-icon" style="background: #FEF3C7;"><el-icon :size="14" color="#92400E"><Key /></el-icon></span>
                <div class="tbl-info">
                  <span class="tbl-name">{{ fk.source_table }}</span>
                  <span class="col-name">{{ fk.source_column }}</span>
                </div>
              </div>
              <div class="rel-arrow">
                <div class="rel-type-badge">{{ fk.cardinality_display || fk.cardinality || '1:N' }}</div>
                <div class="arrow-line">
                  <div class="line"></div>
                  <el-icon :size="18" color="#64748B"><Right /></el-icon>
                </div>
                <el-tag size="small" effect="plain" type="info" class="fk-tag">
                  <el-icon :size="11"><Connection /></el-icon> 数据库 FK
                </el-tag>
              </div>
              <div class="table-block target">
                <span class="tbl-icon" style="background: #DBEAFE;"><el-icon :size="14" color="#1E40AF"><Box /></el-icon></span>
                <div class="tbl-info">
                  <span class="tbl-name">{{ fk.target_table }}</span>
                  <span class="col-name">{{ fk.target_column }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="empty-actions">
          <el-button type="primary" :icon="MagicStick" :loading="analyzing" @click="runAnalysis">
            重新启动 AI 分析
          </el-button>
        </div>
      </div>
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

    <!-- 全屏加载遮罩 -->
    <div v-if="analyzing" class="loading-overlay">
      <div class="loading-box">
        <button class="loading-close-btn" @click="cancelAnalysis" title="取消分析">
          <el-icon :size="16"><Close /></el-icon>
        </button>
        <div class="loading-spinner"></div>
        <div class="loading-text">{{ loadingText }}</div>
        <div class="loading-progress">
          <el-progress
            :percentage="analyzeProgress"
            :stroke-width="8"
            :show-text="true"
            :text-inside="false"
            color="#3B82F6"
            style="width: 240px;"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ArrowLeft,
  Box,
  ChatDotRound,
  Check,
  CircleCheck,
  CircleCheckFilled,
  CircleClose,
  Close,
  Collection,
  Connection,
  Finished,
  Key,
  MagicStick,
  Refresh,
  Right,
} from '@element-plus/icons-vue'
import { createAnalysisTask, getAnalysisTask, cancelAnalysisTask } from '@/api/analysis'
import {
  getRelationships,
  confirmSuggestion as apiConfirm,
  rejectSuggestion as apiReject,
  resetSuggestion as apiReset,
  batchConfirmSuggestions as apiBatchConfirm,
  batchRejectSuggestions as apiBatchReject
} from '@/api/relationship'
import { useSettingsStore } from '@/stores/settings'

const route = useRoute()
const projectId = computed(() => route.params.id)
const settingsStore = useSettingsStore()

// Map canonical backend status strings → audit-page UI status words.
// Backend persist suggestions as `suggested`; once approved/rejected they become
// `confirmed` / `rejected`. Audit UI uses `pending` for "not yet decided" because
// that is the word used throughout filter tabs, checkboxes, and summary counts.
const SERVER_STATUS_TO_UI = {
  suggested: 'pending',
  pending: 'pending',
  confirmed: 'confirmed',
  rejected: 'rejected',
  manual: 'confirmed'
}
const UI_STATUS_TO_SERVER = {
  pending: 'suggested',
  confirmed: 'confirmed',
  rejected: 'rejected'
}

const filter = ref('all')
const tableFilter = ref('')
const allSelected = ref(false)
const loading = ref(false)
const analyzing = ref(false)
const analyzeProgress = ref(0)
const loadingText = ref('准备中...')
let pollTimer = null
let currentTaskId = null
const cancelled = ref(false)
const fkCoverageFullBanner = ref(false)

const suggestions = reactive([])

const normalizeSuggestion = (raw) => {
  const confidence = Number(raw.confidence ?? raw.confidence_score ?? 0)
  // Prefer the canonical server status when present. `suggested` is the real server
  // enum for AI items still in review; the legacy raw.confirmed booleans fall back
  // only when raw.status is not available (old payloads / mocked data).
  const rawStatus = typeof raw.status === 'string' && raw.status.trim() !== ''
    ? raw.status.trim()
    : null
  const status = rawStatus
    ? (SERVER_STATUS_TO_UI[rawStatus.toLowerCase()] ?? 'pending')
    : (raw.confirmed === true ? 'confirmed' : raw.confirmed === false ? 'rejected' : 'pending')
  const reason = Array.isArray(raw.reason) ? raw.reason
    : Array.isArray(raw.reasons) ? raw.reasons
    : (raw.reason ? [raw.reason] : [])
  const cardinality = raw.cardinality || 'one-to-many'
  const cardinalityMap = {
    'one-to-one': '1:1',
    'one-to-many': '1:N',
    'many-to-one': 'N:1',
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

const existingFks = ref([])

const fetchSuggestions = async () => {
  loading.value = true
  try {
    const data = await getRelationships(projectId.value, { source_type: 'ai_suggestion' })
    const list = Array.isArray(data) ? data : (data?.items || data?.relationships || data?.suggestions || [])
    suggestions.splice(0, suggestions.length, ...list.map(normalizeSuggestion))

    // Also load database explicit FKs so we can show them as a reference when
    // the AI produces no new suggestions. This handles the case where the user's
    // database already has all its logical relationships defined as explicit FKs
    // — the AI correctly returns 0 (nothing new to suggest) — but the user still
    // wants to see what their database already covers.
    if (suggestions.length === 0) {
      try {
        const fkData = await getRelationships(projectId.value, { source_type: 'database_constraint' })
        const fkList = Array.isArray(fkData) ? fkData : (fkData?.items || fkData?.relationships || [])
        existingFks.value = fkList.map(normalizeSuggestion)
      } catch {
        existingFks.value = []
      }
    } else {
      existingFks.value = []
    }
  } catch (e) {
    suggestions.splice(0, suggestions.length)
    existingFks.value = []
    ElMessage.error('加载 AI 建议失败')
  } finally {
    loading.value = false
  }
}

const STATUS_TEXT = {
  pending: '等待开始...',
  parsing: '正在解析 Schema 结构...',
  analyzing: '正在生成候选关系...',
  validating: 'AI 正在分析关系中...',
  completed: '分析完成',
  failed: '分析失败',
  cancelled: '已取消',
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
  analyzeProgress.value = 5
  loadingText.value = '正在提交分析任务...'
  cancelled.value = false
  currentTaskId = null

  try {
    const task = await createAnalysisTask(projectId.value, { analysis_type: 'relationship' })
    const taskId = task?.id
    currentTaskId = taskId
    if (!taskId) {
      throw new Error('未获取到任务 ID')
    }

    loadingText.value = STATUS_TEXT.parsing || '解析中...'

    // 轮询任务状态
    const completedTask = await new Promise((resolve, reject) => {
      const startTs = Date.now()
      const MAX_WAIT = 180_000 // 3 分钟超时

      pollTimer = setInterval(async () => {
        try {
          if (cancelled.value) {
            clearInterval(pollTimer)
            pollTimer = null
            reject(new Error('已取消'))
            return
          }
          const t = await getAnalysisTask(taskId)
          if (!t) return
          analyzeProgress.value = t.progress || analyzeProgress.value
          loadingText.value = STATUS_TEXT[t.status] || t.status

          if (t.status === 'completed') {
            clearInterval(pollTimer)
            pollTimer = null
            resolve(t)
          } else if (t.status === 'failed') {
            clearInterval(pollTimer)
            pollTimer = null
            reject(new Error(t.error || '分析失败'))
          } else if (t.status === 'cancelled') {
            clearInterval(pollTimer)
            pollTimer = null
            reject(new Error('已取消'))
          } else if (Date.now() - startTs > MAX_WAIT) {
            clearInterval(pollTimer)
            pollTimer = null
            reject(new Error('分析超时，请稍后重试'))
          }
        } catch (err) {
          if (err.message === '已取消') {
            clearInterval(pollTimer)
            pollTimer = null
            reject(err)
            return
          }
          // 忽略轮询中的单次网络错误
          console.warn('Poll error:', err)
        }
      }, 1500)
    })

    const skipped = completedTask?.result?.skipped_reason
    if (skipped === 'fk_coverage_full') {
      // Explicit FKs already cover every rule-discoverable relation. No LLM was
      // called, no tokens were burned, and there's nothing new to audit.
      fkCoverageFullBanner.value = true
      ElMessage.success({
        message: '数据库显式外键覆盖度很高，已自动跳过 LLM 调用，节省 Token 与时间。',
        duration: 5000,
      })
    } else {
      fkCoverageFullBanner.value = false
      ElMessage.success('AI 关系分析已完成')
    }
    await fetchSuggestions()

    // 高置信度默认勾选功能：如果开启，自动确认置信度 >= 85% 的建议
    if (settingsStore.autoCheckHigh && skipped !== 'fk_coverage_full') {
      autoConfirmHighConfidence()
    }
  } catch (e) {
    if (e?.message === '已取消') {
      ElMessage.info('已取消 AI 分析')
    } else {
      ElMessage.error(e?.message || '启动分析失败')
    }
  } finally {
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
    analyzing.value = false
    analyzeProgress.value = 0
    currentTaskId = null
    cancelled.value = false
  }
}

const cancelAnalysis = async () => {
  if (!currentTaskId || cancelled.value) return
  cancelled.value = true
  loadingText.value = '正在取消...'
  try {
    await cancelAnalysisTask(currentTaskId)
  } catch (e) {
    // 忽略错误，可能任务已完成
  }
}

// 组件卸载时清理定时器
onUnmounted(() => {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
})

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
    const updated = await apiConfirm(s.id)
    // Always trust server truth. PATCH promoted source_type to manual and set
    // status=confirmed. Translate that status back into the audit-page word.
    const uiStatus = updated?.status
      ? (SERVER_STATUS_TO_UI[String(updated.status).toLowerCase()] ?? 'confirmed')
      : 'confirmed'
    s.status = uiStatus
    ElMessage.success('已确认该关系建议（返回ER编辑器即可看到连线）')
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '确认失败，请稍后重试')
  } finally {
    s._loading = false
  }
}

const rejectSuggestion = async (s) => {
  s._loading = true
  try {
    const updated = await apiReject(s.id)
    const uiStatus = updated?.status
      ? (SERVER_STATUS_TO_UI[String(updated.status).toLowerCase()] ?? 'rejected')
      : 'rejected'
    s.status = uiStatus
    ElMessage.success('已拒绝该关系建议')
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '拒绝失败，请稍后重试')
  } finally {
    s._loading = false
  }
}

const resetStatus = async (s) => {
  // User clicked "撤销操作" — call reset endpoint which writes status=suggested
  // server-side, then reflect pending back on the audit row so counters & tabs
  // recompute without a full fetch.
  s._loading = true
  try {
    const updated = await apiReset(s.id)
    const uiStatus = updated?.status
      ? (SERVER_STATUS_TO_UI[String(updated.status).toLowerCase()] ?? 'pending')
      : 'pending'
    s.status = uiStatus
    ElMessage.success('已撤销，可继续审核')
  } catch (e) {
    ElMessage.warning(e?.response?.data?.detail || '无法撤销该关系')
  } finally {
    s._loading = false
  }
}

const confirmAllVisible = async () => {
  const targets = filteredSuggestions.value.filter(s => s.status === 'pending')
  if (targets.length === 0) return
  try {
    const updated = await apiBatchConfirm(projectId.value, targets.map(s => s.id))
    const byId = new Map((updated || []).map(r => [String(r.id), r]))
    for (const s of targets) {
      const r = byId.get(String(s.id))
      const uiStatus = r?.status
        ? (SERVER_STATUS_TO_UI[String(r.status).toLowerCase()] ?? 'confirmed')
        : 'confirmed'
      s.status = uiStatus
    }
    ElMessage.success(`已确认 ${targets.length} 条建议（返回ER编辑器即可看到连线）`)
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || `批量确认失败`)
  }
}

const rejectAllVisible = async () => {
  const targets = filteredSuggestions.value.filter(s => s.status === 'pending')
  if (targets.length === 0) return
  try {
    const updated = await apiBatchReject(projectId.value, targets.map(s => s.id))
    const byId = new Map((updated || []).map(r => [String(r.id), r]))
    for (const s of targets) {
      const r = byId.get(String(s.id))
      const uiStatus = r?.status
        ? (SERVER_STATUS_TO_UI[String(r.status).toLowerCase()] ?? 'rejected')
        : 'rejected'
      s.status = uiStatus
    }
    ElMessage.success(`已拒绝 ${targets.length} 条建议`)
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || `批量拒绝失败`)
  }
}

const toggleSelectAll = (val) => {
  filteredSuggestions.value.forEach(s => {
    if (s.status === 'pending') s.selected = val
  })
}

const clearSelection = () => suggestions.forEach(s => s.selected = false)

const batchConfirm = async () => {
  const targets = suggestions.filter(s => s.selected && s.status === 'pending')
  if (targets.length === 0) return
  try {
    const updated = await apiBatchConfirm(projectId.value, targets.map(s => s.id))
    const byId = new Map((updated || []).map(r => [String(r.id), r]))
    for (const s of targets) {
      const r = byId.get(String(s.id))
      const uiStatus = r?.status
        ? (SERVER_STATUS_TO_UI[String(r.status).toLowerCase()] ?? 'confirmed')
        : 'confirmed'
      s.status = uiStatus
      s.selected = false
    }
    ElMessage.success(`已批量确认 ${targets.length} 条建议（返回ER编辑器即可看到连线）`)
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || `批量确认失败`)
  }
}

const batchReject = async () => {
  const targets = suggestions.filter(s => s.selected && s.status === 'pending')
  if (targets.length === 0) return
  try {
    const updated = await apiBatchReject(projectId.value, targets.map(s => s.id))
    const byId = new Map((updated || []).map(r => [String(r.id), r]))
    for (const s of targets) {
      const r = byId.get(String(s.id))
      const uiStatus = r?.status
        ? (SERVER_STATUS_TO_UI[String(r.status).toLowerCase()] ?? 'rejected')
        : 'rejected'
      s.status = uiStatus
      s.selected = false
    }
    ElMessage.success(`已批量拒绝 ${targets.length} 条建议`)
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || `批量拒绝失败`)
  }
}

// 自动确认高置信度建议
const autoConfirmHighConfidence = async () => {
  if (!settingsStore.autoCheckHigh) return
  const highConfSuggestions = suggestions.filter(s => s.confidence >= 0.85 && s.status === 'pending')
  if (highConfSuggestions.length > 0) {
    try {
      const ids = highConfSuggestions.map(s => s.id)
      await apiBatchConfirm(projectId.value, ids)
      highConfSuggestions.forEach(s => {
        s.status = 'confirmed'
      })
      ElMessage.success(`已自动确认 ${highConfSuggestions.length} 条高置信度建议`)
    } catch (e) {
      console.warn('批量确认高置信度建议失败:', e)
    }
  }
}

// 切换项目时（组件被复用，仅 route.params.id 变化），重置状态后重新加载数据
watch(projectId, async (newId, oldId) => {
  if (!newId || newId === oldId) return
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
  currentTaskId = null
  analyzing.value = false
  analyzeProgress.value = 0
  cancelled.value = false
  allSelected.value = false
  filter.value = 'all'
  tableFilter.value = ''
  fkCoverageFullBanner.value = false
  existingFks.value = []
  suggestions.splice(0, suggestions.length)
  await fetchSuggestions()
})

onMounted(async () => {
  if (projectId.value) {
    await fetchSuggestions()
  }
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

  &.confidence-placeholder {
    display: flex;
    align-items: center;
    justify-content: center;
    background: #F8FAFC;
    border-radius: 50%;
    border: 1px solid #E2E8F0;
  }
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

/* 全屏加载遮罩 */
.loading-overlay {
  position: fixed;
  inset: 0;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
}

.loading-box {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
  padding: 36px 48px;
  background: white;
  border-radius: 16px;
  box-shadow: 0 12px 48px rgba(0, 0, 0, 0.15);
}

.loading-close-btn {
  position: absolute;
  top: 12px;
  right: 12px;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  color: #94A3B8;
  transition: all 0.2s;
}

.loading-close-btn:hover {
  background: #F1F5F9;
  color: #EF4444;
}

.loading-spinner {
  width: 48px;
  height: 48px;
  border: 4px solid #E2E8F0;
  border-top-color: #3B82F6;
  border-radius: 50%;
  animation: spin 0.9s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-text {
  font-size: 15px;
  font-weight: 600;
  color: #1E293B;
  text-align: center;
}

.loading-progress {
  display: flex;
  align-items: center;
}

/* ==== 已有数据库外键参考区 ==== */
.existing-fk-section {
  padding: 24px 0;
  max-width: 960px;
  margin: 0 auto;
}

.fk-info-alert {
  margin-bottom: 20px;
}

.fk-info-alert :deep(.el-alert__title) {
  font-weight: 600;
  font-size: 14px;
}

.existing-fk-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.existing-fk-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  padding: 0 4px;
}

.existing-fk-header .section-title {
  font-size: 14px;
  font-weight: 600;
  color: #334155;
}

.existing-fk-header .section-count {
  font-size: 12px;
  color: #94A3B8;
}

.existing-fk-card {
  background: #fff;
  border: 1px solid #E2E8F0;
  border-radius: 10px;
  padding: 16px 20px;
  transition: box-shadow 0.2s, border-color 0.2s;
}

.existing-fk-card:hover {
  border-color: #CBD5E1;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
}

.fk-path {
  display: flex;
  align-items: center;
  gap: 12px;
}

.fk-tag {
  font-size: 10px;
}

.empty-actions {
  display: flex;
  justify-content: center;
  margin-top: 24px;
}

/* 覆盖 coverage-banner 以避免冲突 */
.coverage-banner {
  margin-bottom: 16px;
}
</style>
