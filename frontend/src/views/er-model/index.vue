<template>
  <div class="er-editor-page">
    <div class="editor-header" :class="{ collapsed: topHeaderCollapsed }">
      <div class="header-left">
        <el-breadcrumb separator="/" class="breadcrumb-sm">
          <el-breadcrumb-item style="color: #94A3B8;">{{ t('erModel.breadcrumb.project') }}</el-breadcrumb-item>
          <el-breadcrumb-item style="color: #94A3B8; cursor: pointer;" @click="goToProject">{{ projectName }}</el-breadcrumb-item>
          <el-breadcrumb-item>
            <span class="current-crumb">{{ t('erModel.breadcrumb.erEditor') }}</span>
          </el-breadcrumb-item>
        </el-breadcrumb>

        <div class="header-stats">
          <div class="stat-pill">
            <el-icon :size="12"><Grid /></el-icon>
            <span>{{ t('erModel.tablesCount', { count: nodes.length }) }}</span>
          </div>
          <div class="stat-pill">
            <el-icon :size="12"><Share /></el-icon>
            <span>{{ t('erModel.relationsCount', { count: edges.length }) }}</span>
          </div>
        </div>
      </div>

      <div class="header-right">
        <div class="search-box">
          <el-input
            v-model="searchTable"
            :placeholder="t('erModel.searchTablePlaceholder')"
            size="small"
            clearable
            style="width: 160px;"
            @keyup.enter="onSearchEnter"
          >
            <template #prefix><el-icon :size="14"><Search /></el-icon></template>
          </el-input>
        </div>

        <el-divider direction="vertical" />

        <el-button-group>
          <el-tooltip :content="t('erModel.autoLayout')" placement="bottom" popper-class="er-tip">
            <el-button size="small" @click="autoLayout"><el-icon><SetUp /></el-icon></el-button>
          </el-tooltip>
          <el-tooltip :content="t('erModel.fitView')" placement="bottom" popper-class="er-tip">
            <el-button size="small" @click="handleFitView"><el-icon><Aim /></el-icon></el-button>
          </el-tooltip>
          <el-tooltip :content="t('erModel.addVirtual')" placement="bottom" popper-class="er-tip">
            <el-button size="small" @click="addVirtualNode"><el-icon><Plus /></el-icon></el-button>
          </el-tooltip>
        </el-button-group>

        <el-divider direction="vertical" />

        <el-button size="small" :icon="MagicStick" type="primary" plain @click="goToSuggestions">
          {{ t('erModel.aiSuggest') }}
        </el-button>
        <el-button size="small" :icon="Download" @click="goToExport">
          {{ t('erModel.export') }}
        </el-button>
        <el-button size="small" :icon="Document" type="success" :loading="erModelStore.saving" @click="handleSave">
          {{ t('erModel.save') }}
        </el-button>
        <el-button size="small" :icon="Promotion" @click="handleSaveVersion">
          {{ t('erModel.saveVersion') }}
        </el-button>
      </div>
    </div>

    <button class="header-collapse-btn" :class="{ collapsed: topHeaderCollapsed }" @click="topHeaderCollapsed = !topHeaderCollapsed">
      <el-icon><ArrowUp v-if="!topHeaderCollapsed" /><ArrowDown v-else /></el-icon>
    </button>

    <div class="editor-body">
      <button class="sidebar-collapse-btn" :class="{ collapsed: leftSidebarCollapsed }" @click="leftSidebarCollapsed = !leftSidebarCollapsed">
        <el-icon><ArrowLeft v-if="!leftSidebarCollapsed" /><ArrowRight v-else /></el-icon>
      </button>
      <aside class="tables-sidebar" :class="{ collapsed: leftSidebarCollapsed }">
        <div class="sidebar-tabs">
          <div class="tab" :class="{ active: sidebarTab === 'tables' }" @click="sidebarTab = 'tables'">
            <el-icon><Grid /></el-icon> {{ t('erModel.tableList') }}
          </div>
        </div>

        <div class="sidebar-search">
          <el-input v-model="sidebarSearchTable" :placeholder="t('erModel.filterTable')" size="small" clearable>
            <template #prefix><el-icon :size="14"><Search /></el-icon></template>
          </el-input>
        </div>

        <el-scrollbar class="sidebar-list">
          <div
            v-for="node in filteredNodes"
            :key="node.id"
            class="table-item"
            :class="{ active: selectedNodeId === node.id }"
            @click="selectNode(node)"
          >
            <div class="table-dot"></div>
            <div class="table-info">
              <div class="table-name">{{ node.data.name }}</div>
              <div class="table-sub">{{ node.data.columns?.length || 0 }} {{ t('erModel.fields') }} · {{ node.data.comment || t('erModel.noComment') }}</div>
            </div>
          </div>
          <el-empty v-if="filteredNodes.length === 0" :description="t('erModel.noTables')" :image-size="60" />
        </el-scrollbar>
      </aside>

      <main class="canvas-area">
        <VueFlow
          v-model:nodes="nodes"
          v-model:edges="edges"
          v-model:viewport="viewport"
          :node-types="nodeTypes"
          :edge-types="edgeTypes"
          :default-viewport="{ zoom: 1 }"
          :min-zoom="0.2"
          :max-zoom="2"
          :snap-grid="{ x: 20, y: 20 }"
          :connection-mode="ConnectionMode.Loose"
          fit-view-on-init
          class="vue-flow-canvas"
          :edges-updatable="true"
          @node-click="onNodeClick"
          @edge-click="onEdgeClick"
          @connect="onConnect"
          @edge-update-start="onEdgeUpdateStart"
          @edge-update="onEdgeUpdate"
          @edge-update-end="onEdgeUpdateEnd"
          @nodes-initialized="onNodesInitialized"
          @pane-click="onPaneClick"
        >
          <Background :gap="20" :size="1" pattern="dots" />
          <Controls :show-zoom="false" :show-fit-view="false" :show-interactive="false">
            <ControlButton @click="zoomIn">
              <el-tooltip :content="t('erModel.zoomIn')" placement="right" popper-class="er-tip">
                <el-icon><ZoomIn /></el-icon>
              </el-tooltip>
            </ControlButton>
            <ControlButton @click="zoomOut">
              <el-tooltip :content="t('erModel.zoomOut')" placement="right" popper-class="er-tip">
                <el-icon><ZoomOut /></el-icon>
              </el-tooltip>
            </ControlButton>
            <ControlButton :class="{ 'is-active': mode === 'pointer' }" @click="setMode('pointer')">
              <el-tooltip :content="t('erModel.pointerMode')" placement="right" popper-class="er-tip">
                <svg class="mode-icon pointer-icon" viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                  <path d="M5.5 2.5L6 18l3-3 3 6 2-1-3-6 4 .5z" />
                </svg>
              </el-tooltip>
            </ControlButton>
            <ControlButton :class="{ 'is-active': mode === 'hand' }" @click="setMode('hand')">
              <el-tooltip :content="t('erModel.handMode')" placement="right" popper-class="er-tip">
                <svg class="mode-icon hand-icon" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M18 11V6a2 2 0 00-2-2 2 2 0 00-2 2" />
                  <path d="M14 10V4a2 2 0 00-2-2 2 2 0 00-2 2" />
                  <path d="M10 10.5V6a2 2 0 00-2-2 2 2 0 00-2 2v8" />
                  <path d="M18 8a2 2 0 012 2v4a6 6 0 01-6 6h-2a6 6 0 01-6-6v-1" />
                </svg>
              </el-tooltip>
            </ControlButton>
          </Controls>
          <MiniMap pannable zoomable />
        </VueFlow>

        <div class="legend-bar">
          <div class="legend-item"><span class="legend-dot confirmed"></span> {{ t('erModel.legend.confirmed') }}</div>
          <div class="legend-item"><span class="legend-dot manual"></span> {{ t('erModel.legend.manual') }}</div>
          <div class="legend-item"><span class="legend-key">🔑</span> {{ t('erModel.legend.pk') }}</div>
          <div class="legend-item"><span class="legend-key">🔗</span> {{ t('erModel.legend.fk') }}</div>
        </div>
      </main>

      <aside class="detail-sidebar" v-if="selectedNode">
        <div class="detail-header">
          <div class="detail-title-row">
            <h3 class="detail-title">{{ selectedNode.data.name }}</h3>
            <el-button text circle size="small" @click="selectedNodeId = null">
              <el-icon><Close /></el-icon>
            </el-button>
          </div>
          <div class="detail-sub">
            <el-tag size="small" effect="plain" type="primary">{{ selectedNode.data.engine || 'InnoDB' }}</el-tag>
            <span style="color: #94A3B8; font-size: 12px;">{{ t('erModel.detail.fieldCount', { count: selectedNode.data.columns?.length || 0 }) }}</span>
          </div>
          <p class="table-comment" v-if="selectedNode.data.comment">{{ selectedNode.data.comment }}</p>
        </div>

        <el-tabs v-model="detailTab" class="detail-tabs">
          <el-tab-pane :label="t('erModel.detail.fields')" name="columns">
            <div style="padding: 12px 16px 0;">
              <el-button type="primary" size="small" :icon="Plus" @click="startAddColumn">
                {{ t('erModel.detail.addField') }}
              </el-button>
            </div>
            <div class="column-list">
              <div v-for="(c, idx) in selectedNode.data.columns" :key="idx" class="col-detail">
                <div class="col-d-head">
                  <div class="col-d-name">
                    <span v-if="c.isPK" class="badge pk">PK</span>
                    <span v-if="c.isFK" class="badge fk">FK</span>
                    <span v-if="c.isUnique" class="badge uk">UK</span>
                    <span>{{ c.name }}</span>
                  </div>
                  <span class="col-d-type">{{ c.type }}</span>
                </div>
                <div class="col-d-meta">
                  <el-tag v-if="!c.nullable" size="small" type="danger" effect="plain" round>NOT NULL</el-tag>
                  <span v-else style="font-size: 11px; color: #94A3B8;">{{ t('erModel.detail.nullable') }}</span>
                  <span v-if="c.default" class="col-d-default">{{ t('erModel.detail.defaultValue') }}: {{ c.default }}</span>
                </div>
                <div class="col-d-comment" v-if="c.comment">{{ c.comment }}</div>

                <div class="col-d-edit">
                  <el-button text size="small" type="primary" @click="editColumn(idx)">
                    <el-icon><Edit /></el-icon> {{ t('erModel.detail.editField') }}
                  </el-button>
                </div>
              </div>
            </div>
          </el-tab-pane>

          <el-tab-pane :label="t('erModel.detail.relations')" name="relations">
            <div class="rel-list">
              <div v-for="r in nodeRelations" :key="r.id" class="rel-card" :class="r.data?.sourceType">
                <div class="rel-head">
                  <span class="rel-type">{{ r.data?.cardinality || '1:N' }}</span>
                </div>
                <div class="rel-cols">
                  <code>{{ r.source === selectedNode.id ? (r.data?.fromColumn || '?') : (r.data?.toColumn || '?') }}</code>
                  →
                  <code>{{ r.source === selectedNode.id ? getTargetName(r.target) : getSourceName(r.source) }}</code>
                </div>
                <div class="rel-tag-row" v-if="r.data?.sourceType === 'ai_suggestion' || r.data?.sourceType === 'ai' || r.data?.sourceType === 'ai_confirmed'">
                  <el-tag size="small" type="success" effect="light"><el-icon><MagicStick /></el-icon> AI 建议</el-tag>
                </div>
                <div class="rel-tag-row" v-else-if="r.data?.sourceType === 'manual'">
                  <el-tag size="small" type="success" effect="light">{{ t('erModel.detail.manualCreated') }}</el-tag>
                </div>
                <div class="rel-tag-row" v-else-if="r.data?.sourceType === 'database' || r.data?.sourceType === 'database_constraint'">
                  <el-tag size="small" type="primary" effect="light">{{ t('erModel.sourceTypes.database_constraint') || t('erModel.sourceTypes.database') }}</el-tag>
                </div>
              </div>
              <el-empty v-if="nodeRelations.length === 0" :description="t('erModel.detail.noRelations')" :image-size="60" />
            </div>
          </el-tab-pane>
        </el-tabs>
      </aside>

      <aside class="edge-sidebar" v-else-if="selectedEdge" :style="{ width: edgeSidebarWidth }">
        <div class="detail-header">
          <div class="detail-title-row">
            <h3 class="detail-title">{{ t('erModel.detail.relationDetail') }}</h3>
            <el-button text circle size="small" @click="selectedEdgeId = null">
              <el-icon><Close /></el-icon>
            </el-button>
          </div>
          <div class="rel-path">
            <span class="table-chip">{{ getSourceName(selectedEdge.source) }}</span>
            <el-icon color="#3B82F6"><Right /></el-icon>
            <span class="table-chip target">{{ getTargetName(selectedEdge.target) }}</span>
          </div>
        </div>

        <div class="edge-detail-body">
          <el-form :label-width="edgeLabelWidth" size="small">
            <el-form-item :label="t('erModel.detail.cardinality')">
              <el-select
                v-model="selectedEdge.data.cardinality"
                style="width: 100%;"
                @change="onCardinalityChange"
              >
                <el-option :label="t('erModel.cardinalityOptions.oneToOne')" value="1:1" />
                <el-option :label="t('erModel.cardinalityOptions.oneToMany')" value="1:N" />
                <el-option :label="t('erModel.cardinalityOptions.manyToMany')" value="N:N" />
              </el-select>
            </el-form-item>
            <el-form-item :label="t('erModel.detail.source')">
              <el-tag size="small" :type="getSourceTagType(selectedEdge.data.sourceType)">
                {{ t(`erModel.sourceTypes.${selectedEdge.data.sourceType}`) || selectedEdge.data.sourceType }}
              </el-tag>
            </el-form-item>
            <el-form-item :label="t('erModel.detail.fromColumn')">
              <code>{{ selectedEdge.data.fromColumn || '-' }}</code>
            </el-form-item>
            <el-form-item :label="t('erModel.detail.toColumn')">
              <code>{{ selectedEdge.data.toColumn || '-' }}</code>
            </el-form-item>
            <el-form-item v-if="selectedEdge.data.reason && selectedEdge.data.reason.length" :label="t('erModel.detail.reason')">
              <div class="reason-list">
                <div v-for="(r, i) in selectedEdge.data.reason" :key="i" class="reason-item">
                  <el-icon color="#10B981"><CircleCheckFilled /></el-icon>
                  <span>{{ tData('reasons', r) }}</span>
                </div>
              </div>
            </el-form-item>
          </el-form>

          <el-button type="danger" plain :icon="Delete" style="width: 100%;" @click="deleteEdge(selectedEdge.id)">
            {{ t('erModel.detail.deleteRelation') }}
          </el-button>
        </div>
      </aside>
    </div>

    <el-dialog v-model="showEditColumn" :title="t('erModel.dialogs.editField')" width="480px">
      <el-form :model="editColForm" label-width="90px" v-if="editColForm">
        <el-form-item :label="t('erModel.dialogs.fieldName')">
          <el-input v-model="editColForm.name" />
        </el-form-item>
        <el-form-item :label="t('erModel.dialogs.type')">
          <el-input v-model="editColForm.type" />
        </el-form-item>
        <el-form-item :label="t('erModel.dialogs.primaryKey')">
          <el-switch v-model="editColForm.isPK" />
        </el-form-item>
        <el-form-item :label="t('erModel.dialogs.unique')">
          <el-switch v-model="editColForm.isUnique" />
        </el-form-item>
        <el-form-item :label="t('erModel.dialogs.nullable')">
          <el-switch v-model="editColForm.nullable" />
        </el-form-item>
        <el-form-item :label="t('erModel.dialogs.comment')">
          <el-input v-model="editColForm.comment" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditColumn = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" @click="saveColumnEdit">{{ t('common.save') }}</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showAddColumn" :title="t('erModel.dialogs.addField')" width="480px">
      <el-form :model="addColForm" label-width="90px">
        <el-form-item :label="t('erModel.dialogs.fieldName')">
          <el-input v-model="addColForm.name" :placeholder="t('erModel.dialogs.fieldNamePlaceholder')" />
        </el-form-item>
        <el-form-item :label="t('erModel.dialogs.type')">
          <el-select v-model="addColForm.type" :placeholder="t('erModel.dialogs.typePlaceholder')" filterable allow-create style="width: 100%;">
            <el-option label="INT" value="INT" />
            <el-option label="INTEGER" value="INTEGER" />
            <el-option label="BIGINT" value="BIGINT" />
            <el-option label="VARCHAR" value="VARCHAR" />
            <el-option label="CHAR" value="CHAR" />
            <el-option label="TEXT" value="TEXT" />
            <el-option label="DATETIME" value="DATETIME" />
            <el-option label="DATE" value="DATE" />
            <el-option label="TIMESTAMP" value="TIMESTAMP" />
            <el-option label="DECIMAL" value="DECIMAL" />
            <el-option label="FLOAT" value="FLOAT" />
            <el-option label="DOUBLE" value="DOUBLE" />
            <el-option label="BOOLEAN" value="BOOLEAN" />
            <el-option label="TINYINT" value="TINYINT" />
            <el-option label="JSON" value="JSON" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('erModel.dialogs.primaryKey')">
          <el-switch v-model="addColForm.isPK" />
        </el-form-item>
        <el-form-item :label="t('erModel.dialogs.unique')">
          <el-switch v-model="addColForm.isUnique" />
        </el-form-item>
        <el-form-item :label="t('erModel.dialogs.nullable')">
          <el-switch v-model="addColForm.nullable" />
        </el-form-item>
        <el-form-item :label="t('erModel.dialogs.defaultValue')">
          <el-input v-model="addColForm.default" :placeholder="t('common.optional')" />
        </el-form-item>
        <el-form-item :label="t('erModel.dialogs.comment')">
          <el-input v-model="addColForm.comment" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddColumn = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" @click="saveNewColumn">{{ t('common.save') }}</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showVersionDialog" :title="t('erModel.dialogs.saveVersion')" width="440px">
      <el-form :model="versionForm" label-width="80px">
        <el-form-item :label="t('erModel.dialogs.versionNote')">
          <el-input v-model="versionForm.note" type="textarea" :rows="3" :placeholder="t('erModel.dialogs.versionNotePlaceholder')" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showVersionDialog = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="savingVersion" @click="confirmSaveVersion">{{ t('erModel.dialogs.saveVersion') }}</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showVirtualDialog" :title="t('erModel.dialogs.addVirtual')" width="440px">
      <el-form :model="virtualForm" label-width="80px">
        <el-form-item :label="t('erModel.dialogs.entityName')">
          <el-input v-model="virtualForm.name" :placeholder="t('erModel.dialogs.entityNamePlaceholder')" />
        </el-form-item>
        <el-form-item :label="t('erModel.dialogs.remark')">
          <el-input v-model="virtualForm.comment" type="textarea" :rows="2" :placeholder="t('erModel.dialogs.entityRemarkPlaceholder')" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showVirtualDialog = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" @click="confirmAddVirtual">{{ t('common.add') }}</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showCardinalityDialog" :title="t('erModel.dialogs.selectCardinality')" width="360px" :close-on-click-modal="false">
      <p style="font-size: 13px; color: #64748B; margin: 0 0 16px;">
        {{ t('erModel.dialogs.connectingTables', { source: getSourceName(pendingConnection?.source), target: getTargetName(pendingConnection?.target) }) }}
      </p>
      <el-radio-group v-model="pendingCardinality" style="display: flex; flex-direction: column; gap: 10px; align-items: stretch;">
        <el-radio value="1:1" class="cardinality-opt">
          <div class="cardinality-text">
            <div class="cardinality-label">{{ t('erModel.cardinalityOptions.oneToOne') }}</div>
            <div class="cardinality-desc">{{ t('erModel.dialogs.oneToOneDesc') }}</div>
          </div>
        </el-radio>
        <el-radio value="1:N" class="cardinality-opt">
          <div class="cardinality-text">
            <div class="cardinality-label">{{ t('erModel.cardinalityOptions.oneToMany') }}</div>
            <div class="cardinality-desc">{{ t('erModel.dialogs.oneToManyDesc') }}</div>
          </div>
        </el-radio>
        <el-radio value="N:N" class="cardinality-opt">
          <div class="cardinality-text">
            <div class="cardinality-label">{{ t('erModel.cardinalityOptions.manyToMany') }}</div>
            <div class="cardinality-desc">{{ t('erModel.dialogs.manyToManyDesc') }}</div>
          </div>
        </el-radio>
      </el-radio-group>
      <template #footer>
        <el-button @click="cancelTableConnection">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" @click="confirmTableConnection">{{ t('erModel.dialogs.createRelation') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount, markRaw, provide, nextTick, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { VueFlow, useVueFlow, ConnectionMode } from '@vue-flow/core'
import dagre from 'dagre'
import { Background } from '@vue-flow/background'
import { Controls, ControlButton } from '@vue-flow/controls'
import { MiniMap } from '@vue-flow/minimap'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import '@vue-flow/controls/dist/style.css'
import '@vue-flow/minimap/dist/style.css'

import TableNode from '@/components/er/TableNode.vue'
import RelationEdge from '@/components/er/RelationEdge.vue'
import { useErModelStore } from '@/stores/erModel'
import { useProjectStore } from '@/stores/project'
import { getTables } from '@/api/schema'
import { getRelationships, createRelationship, deleteRelationship, updateRelationship } from '@/api/relationship'
import { useDataI18n } from '@/i18n'
import { registerShortcut, unregisterShortcut } from '@/utils/shortcuts'

const { t, locale } = useI18n()
const { tData } = useDataI18n()
const edgeLabelWidth = computed(() => (locale.value === 'en-US' ? '95px' : '70px'))
const edgeSidebarWidth = computed(() => (locale.value === 'en-US' ? '380px' : '320px'))
const route = useRoute()
const router = useRouter()
const erModelStore = useErModelStore()
const projectStore = useProjectStore()
const projectId = computed(() => route.params.id)

const nodeTypes = { tableNode: markRaw(TableNode) }
const edgeTypes = { relationEdge: markRaw(RelationEdge) }

const showCardinalityDialog = ref(false)
const pendingConnection = ref(null)
const pendingCardinality = ref('1:N')

const projectName = ref('')
const searchTable = ref('')
const sidebarSearchTable = ref('')
const sidebarTab = ref('tables')
const selectedNodeId = ref(null)
const selectedEdgeId = ref(null)
const detailTab = ref('columns')
const showEditColumn = ref(false)
const showVersionDialog = ref(false)
const showVirtualDialog = ref(false)
const savingVersion = ref(false)
const editColForm = ref(null)
const editColIndex = ref(null)
const versionForm = reactive({ note: '' })
const virtualForm = reactive({ name: '', comment: '' })

const showAddColumn = ref(false)
const addColTargetNodeId = ref(null)
const addColForm = reactive({
  name: '',
  type: '',
  isPK: false,
  isUnique: false,
  nullable: true,
  default: '',
  comment: ''
})

const nodes = ref(erModelStore.nodes)
const edges = ref(erModelStore.edges)
const viewport = ref(erModelStore.viewport)

const searchMatches = ref([])
const searchIdx = ref(0)
const leftSidebarCollapsed = ref(false)
const topHeaderCollapsed = ref(false)

const { fitView, getNodes, nodesDraggable, panOnDrag, zoomIn, zoomOut, updateNodeInternals } = useVueFlow()

const mode = ref('hand')
const setMode = (m) => {
  mode.value = m
  if (m === 'hand') {
    // 手模式：画布和表都可以移动
    nodesDraggable.value = true
    panOnDrag.value = true
  } else {
    // 指针模式：只能移动表，画布不随拖拽偏移
    nodesDraggable.value = true
    panOnDrag.value = false
  }
}

const selectedNode = computed(() => {
  if (!selectedNodeId.value) return null
  return nodes.value.find(n => n.id === selectedNodeId.value) || null
})

const selectedEdge = computed(() => {
  if (!selectedEdgeId.value) return null
  return edges.value.find(e => e.id === selectedEdgeId.value) || null
})

const filteredNodes = computed(() => {
  if (!sidebarSearchTable.value) return nodes.value
  return nodes.value.filter(n => (n.data.name || '').toLowerCase().includes(sidebarSearchTable.value.toLowerCase()))
})

const onSearchEnter = () => {
  const q = searchTable.value.trim()
  if (!q) return
  const matches = nodes.value.filter(n => (n.data.name || '').toLowerCase().includes(q.toLowerCase()))
  if (matches.length === 0) {
    ElMessage.warning(t('erModel.messages.tableNotFound'))
    return
  }
  searchMatches.value = matches
  if (searchIdx.value >= matches.length) searchIdx.value = 0
  focusSearchNode(searchIdx.value)
  searchIdx.value = (searchIdx.value + 1) % matches.length
}

const focusSearchNode = (idx) => {
  const match = searchMatches.value[idx]
  if (!match) return
  nodes.value.forEach(n => { n.selected = false })
  const node = nodes.value.find(n => String(n.id) === String(match.id))
  if (node) node.selected = true
  selectedNodeId.value = match.id
  selectedEdgeId.value = null
  fitView({
    nodes: [{ id: match.id }],
    duration: 400,
    padding: 0.35,
    maxZoom: 1.2
  })
}

watch(searchTable, (val) => {
  if (!val) {
    searchMatches.value = []
    searchIdx.value = 0
    nodes.value.forEach(n => { n.selected = false })
  }
})

const nodeRelations = computed(() => {
  if (!selectedNode.value) return []
  const id = selectedNode.value.id
  return edges.value.filter(e => e.source === id || e.target === id)
})

const getSourceName = (id) => {
  const n = nodes.value.find(x => x.id === id)
  return n?.data.name || id
}

const getTargetName = (id) => {
  const n = nodes.value.find(x => x.id === id)
  return n?.data.name || id
}

const getConfidenceClass = (c) => c >= 0.85 ? 'confidence-tag high' : c >= 0.6 ? 'confidence-tag medium' : 'confidence-tag low'

const getSourceTagType = (t) => {
  const map = {
    database: 'primary',
    database_constraint: 'primary',
    ai: 'success',
    ai_suggestion: 'success',
    ai_confirmed: 'success',
    manual: 'success'
  }
  return map[t] || 'info'
}

const selectNode = (node) => {
  selectedNodeId.value = node.id
  selectedEdgeId.value = null
}

const onNodeClick = ({ node }) => {
  selectedNodeId.value = node.id
  selectedEdgeId.value = null
}

const onEdgeClick = ({ edge }) => {
  selectedEdgeId.value = edge.id
  selectedNodeId.value = null
}

const onPaneClick = () => {
  selectedNodeId.value = null
  selectedEdgeId.value = null
}

const onConnect = async (connection) => {
  // Prevent self-loop connections
  if (connection.source === connection.target) {
    ElMessage.warning(t('erModel.messages.cannotConnectSelf'))
    return
  }

  if (
    connection.sourceHandle?.startsWith('top-source') ||
    connection.sourceHandle?.startsWith('bottom-source')
  ) {
    pendingConnection.value = connection
    pendingCardinality.value = '1:N'
    showCardinalityDialog.value = true
    return
  }

  const newEdge = {
    id: `e-${Date.now()}`,
    source: connection.source,
    target: connection.target,
    sourceHandle: connection.sourceHandle,
    targetHandle: connection.targetHandle,
    type: 'relationEdge',
    updatable: true,
    data: {
      cardinality: '1:N',
      sourceType: 'manual',
      confidence: 1,
      fromColumn: connection.sourceHandle?.startsWith('s-')
        ? connection.sourceHandle.replace('s-', '')
        : null,
      toColumn: connection.targetHandle?.startsWith('t-')
        ? connection.targetHandle.replace('t-', '')
        : null,
      reason: []
    }
  }
  edges.value.push(newEdge)
  try {
    const data = await createRelationship(projectId.value, {
      source_table: getSourceName(connection.source),
      target_table: getSourceName(connection.target),
      source_column: newEdge.data.fromColumn,
      target_column: newEdge.data.toColumn,
      cardinality: '1:N',
      source_type: 'manual'
    })
    if (data?.id) newEdge.id = String(data.id)
    ElMessage.success(t('erModel.messages.relationCreated'))
  } catch {
    // keep local edge even if API fails
  }
  refreshHandleBounds()
}

const confirmTableConnection = async () => {
  if (!pendingConnection.value) return
  const connection = pendingConnection.value
  const cardinality = pendingCardinality.value

  const newEdge = {
    id: `e-${Date.now()}`,
    source: connection.source,
    target: connection.target,
    sourceHandle: connection.sourceHandle,
    targetHandle: connection.targetHandle,
    type: 'relationEdge',
    updatable: true,
    data: {
      cardinality,
      sourceType: 'manual',
      confidence: 1,
      fromColumn: null,
      toColumn: null,
      reason: []
    }
  }
  edges.value.push(newEdge)
  erModelStore.addEdge(newEdge)
  try {
    const data = await createRelationship(projectId.value, {
      source_table: getSourceName(connection.source),
      target_table: getSourceName(connection.target),
      source_column: null,
      target_column: null,
      cardinality,
      source_type: 'manual'
    })
    if (data?.id) newEdge.id = String(data.id)
    ElMessage.success(t('erModel.messages.relationCreatedWithCardinality', { cardinality }))
  } catch {
    // keep local edge even if API fails
  }
  refreshHandleBounds()

  showCardinalityDialog.value = false
  pendingConnection.value = null
}

const cancelTableConnection = () => {
  showCardinalityDialog.value = false
  pendingConnection.value = null
}

// ---------------------------------------------------------------------------
// Edge reconnect via Vue Flow's built-in updater.
//
// Pressing an edge endpoint hides the original edge and draws a temporary
// connection line from the fixed end to the cursor; on release the new
// connection is applied (or the edge snaps back). Vue Flow emits
// @edge-update during the drag and @edge-update-end on release.
// ---------------------------------------------------------------------------

// If Vue Flow cannot resolve the fixed-end handle it never attaches its own
// pointer-up listener, so the edge would stay hidden forever. Track every
// update-start and recover the edge when its end event never arrives:
//  - immediately on the next mouseup (covers normal releases), and
//  - via a timeout (covers releases outside the window, where no mouseup
//    event is ever delivered).
const pendingEdgeUpdates = new Map() // edgeId -> timeout id

const recoverEdge = (id) => {
  const idx = edges.value.findIndex(e => String(e.id) === id)
  if (idx < 0) return
  const snapshot = { ...edges.value[idx] }
  // Remove for one tick so Vue Flow unmounts the EdgeWrapper (resetting its
  // internal `updating` flag), then re-add the edge to bring the line back.
  edges.value = edges.value.filter(e => String(e.id) !== id)
  erModelStore.edges = edges.value
  nextTick(() => {
    edges.value.push(snapshot)
    erModelStore.edges = edges.value
  })
}

const onEdgeUpdateStart = ({ edge }) => {
  if (!edge) return
  const id = String(edge.id)
  clearTimeout(pendingEdgeUpdates.get(id))
  pendingEdgeUpdates.set(id, setTimeout(() => {
    if (!pendingEdgeUpdates.has(id)) return
    pendingEdgeUpdates.delete(id)
    recoverEdge(id)
  }, 3000))
}

const onWindowMouseUp = () => {
  if (pendingEdgeUpdates.size === 0) return
  for (const [id, timer] of [...pendingEdgeUpdates]) {
    clearTimeout(timer)
    pendingEdgeUpdates.delete(id)
    recoverEdge(id)
  }
}

// Tracks the latest valid connection while the user drags an edge endpoint.
let pendingReconnect = null

const onEdgeUpdate = ({ edge, connection }) => {
  if (!edge || !connection) {
    pendingReconnect = null
    return
  }
  if (String(connection.source) === String(connection.target)) {
    pendingReconnect = null
    return
  }
  pendingReconnect = {
    edgeId: String(edge.id),
    source: String(connection.source),
    target: String(connection.target),
    sourceHandle: connection.sourceHandle,
    targetHandle: connection.targetHandle
  }
}

const onEdgeUpdateEnd = async ({ edge }) => {
  if (edge) {
    const id = String(edge.id)
    clearTimeout(pendingEdgeUpdates.get(id))
    pendingEdgeUpdates.delete(id)
  }
  const conn = pendingReconnect
  pendingReconnect = null

  if (!edge || !conn) {
    // Update aborted (dropped on invalid area / same node) - force a shallow
    // copy so Vue Flow re-renders the edge and the line comes back.
    if (edge) {
      const idx = edges.value.findIndex(e => String(e.id) === String(edge.id))
      if (idx >= 0) {
        edges.value[idx] = { ...edges.value[idx] }
        edges.value = [...edges.value]
      }
    }
    return
  }

  if (conn.edgeId !== String(edge.id)) return
  if (conn.source === conn.target) return

  const idx = edges.value.findIndex(e => String(e.id) === conn.edgeId)
  if (idx < 0) return
  const before = edges.value[idx]

  const updated = {
    ...before,
    source: conn.source,
    target: conn.target,
    sourceHandle: conn.sourceHandle ?? before.sourceHandle,
    targetHandle: conn.targetHandle ?? before.targetHandle
  }
  edges.value[idx] = updated
  edges.value = [...edges.value]
  erModelStore.updateEdge(updated)
  refreshHandleBounds()

  const sourceNodeChanged = String(before.source) !== conn.source
  const targetNodeChanged = String(before.target) !== conn.target
  if (sourceNodeChanged || targetNodeChanged) {
    const relId = Number(edge.id)
    if (!relId || Number.isNaN(relId)) return
    try {
      await updateRelationship(relId, {
        source_table: getSourceName(conn.source),
        target_table: getTargetName(conn.target),
        source_column: sourceNodeChanged ? null : undefined,
        target_column: targetNodeChanged ? null : undefined
      })
      if (updated.data) {
        if (sourceNodeChanged) updated.data.fromColumn = null
        if (targetNodeChanged) updated.data.toColumn = null
      }
    } catch {
      edges.value[idx] = before
      edges.value = [...edges.value]
      erModelStore.updateEdge(before)
    }
  }
}

const refreshHandleBounds = () => {
  nextTick(() => {
    updateNodeInternals(nodes.value.map(n => String(n.id)))
  })
}

const copyNode = (nodeId) => {
  const node = nodes.value.find(n => n.id === nodeId)
  if (!node) return
  const newNode = {
    id: `copy-${Date.now()}`,
    type: node.type,
    position: {
      x: node.position.x + 60,
      y: node.position.y + 60
    },
    data: JSON.parse(JSON.stringify(node.data))
  }
  newNode.data.name = `${node.data.name}_copy`
  nodes.value.push(newNode)
  erModelStore.addNode(newNode)
  ElMessage.success(t('erModel.messages.tableDuplicated'))
}

const deleteNode = (nodeId) => {
  const node = nodes.value.find(n => n.id === nodeId)
  if (!node) return

  edges.value = edges.value.filter(e => e.source !== nodeId && e.target !== nodeId)
  nodes.value = nodes.value.filter(n => n.id !== nodeId)
  erModelStore.removeNode(nodeId)

  if (selectedNodeId.value === nodeId) {
    selectedNodeId.value = null
  }

  ElMessage.success(t('erModel.messages.tableDeleted'))
}

const deleteEdge = async (id) => {
  const numericId = Number(id)
  const isPersisted = Number.isInteger(numericId) && numericId > 0
  if (isPersisted) {
    try {
      await deleteRelationship(numericId)
      ElMessage.success(t('erModel.messages.relationDeleted'))
    } catch {
      // keep local edge even if API fails
    }
  }
  // Local-only edges (the create response never confirmed a server id, e.g.
  // `e-<timestamp>`) have no relationship row to delete. Calling the API with
  // such an id would fail with 422 (path expects an int), so skip it and just
  // drop the edge from the canvas.
  edges.value = edges.value.filter(e => e.id !== id)
  erModelStore.removeEdge(id)
  selectedEdgeId.value = null
}

// Map UI cardinality values (used in v-model and RelationEdge) to backend canonical enum.
// Pull-down dropdown only ever produces 1:1 / 1:N / N:N — never N:1, which the backend
// normalizer would otherwise flip endpoints for. So source/target endpoints are stable
// across every change the user makes in the drawer; we only need to mutate the cardinality
// string on the existing edge to keep crow-feet markers, node handles and anchor positions stable.
const UI_TO_BACKEND_CARD = {
  '1:1': 'one-to-one',
  '1:N': 'one-to-many',
  'N:N': 'many-to-many'
}
const BACKEND_TO_UI_CARD = {
  'one-to-one': '1:1',
  'one-to-many': '1:N',
  'many-to-many': 'N:N',
  'many-to-one': '1:N'
}

const onCardinalityChange = async (newUiCard) => {
  // Called when user picks a different cardinality from the edge-detail drawer select.
  // Persists via PATCH /relationships/{id}; on success, rewrites the canonical server-
  // truth cardinality (UI form) back onto the SAME edge object so Vue reactivity triggers
  // RelationEdge marker re-computation, WITHOUT rebuilding endpoints / handles (which
  // would assign wrong bucket indices when only a single edge is re-normalized).
  const edge = selectedEdge.value
  if (!edge) return
  const relId = edge.id
  const backendCard = UI_TO_BACKEND_CARD[newUiCard]
  if (!backendCard) {
    ElMessage.warning(`Unknown cardinality: ${newUiCard}`)
    return
  }
  try {
    const updated = await updateRelationship(relId, { cardinality: backendCard })
    // Translate server's canonical enum back into the 1:1/1:N/N:N format that every
    // RelationEdge computed uses to split start/end markers.
    const serverUiCard = BACKEND_TO_UI_CARD[String(updated.cardinality || '').toLowerCase()] || newUiCard

    // Update the edge IN PLACE, preserving source/target/handles/id so anchors and
    // TableNode handle counts don't desync. Mutating a nested property still triggers
    // RelationEdge because its `cardinality` computed tracks props.data.cardinality.
    // We also fully replace the edges.value[i] element to guarantee reactivity for any
    // consumer that compares edge objects by identity.
    const idx = edges.value.findIndex(e => String(e.id) === String(relId))
    if (idx >= 0) {
      const cur = edges.value[idx]
      edges.value[idx] = {
        ...cur,
        data: {
          ...(cur.data || {}),
          cardinality: serverUiCard
        }
      }
      // Vue Flow keeps internal identity caches keyed on the array reference as well
      // as on per-item identity; replacing just the element at index N is often not
      // enough after the 2nd+ change (the shallow cache returns the stale vnode).
      // Swapping the entire edges array for a fresh shallow copy forces VueFlow's
      // v-for to diff against a new array identity so every affected edge re-renders
      // and crow-foot markers flip correctly regardless of change count.
      edges.value = [...edges.value]
    }
    // If v-model wrote a "best-effort" value before the server round-trip, force it to
    // exactly the server value so the select shows canonical choice.
    if (selectedEdge.value?.data) {
      selectedEdge.value.data.cardinality = serverUiCard
    }
    ElMessage.success(t('erModel.messages.relationUpdated'))
  } catch (err) {
    // Revert the optimistic v-model change by re-reading current truth from the server
    // and writing it back to the edge object so the UI matches what is actually stored.
    try {
      const rels = await getRelationships(projectId.value)
      const list = Array.isArray(rels) ? rels : (rels?.items || rels?.relationships || [])
      const latest = list.find(r => String(r.id) === String(relId))
      if (latest && edge?.data) {
        const revertUi = BACKEND_TO_UI_CARD[String(latest.cardinality || '').toLowerCase()] || '1:N'
        const idx = edges.value.findIndex(e => String(e.id) === String(relId))
        if (idx >= 0) {
          const cur = edges.value[idx]
          edges.value[idx] = {
            ...cur,
            data: { ...(cur.data || {}), cardinality: revertUi }
          }
          // Same reasoning as success path — force a new array identity so Vue Flow
          // invalidates its cached edge vnodes on rollback too.
          edges.value = [...edges.value]
        }
        if (selectedEdge.value?.data) {
          selectedEdge.value.data.cardinality = revertUi
        }
      }
    } catch {
      /* ignore revert error */
    }
  }
}

const editColumn = (idx) => {
  if (!selectedNode.value) return
  const col = selectedNode.value.data.columns[idx]
  editColForm.value = JSON.parse(JSON.stringify(col))
  editColIndex.value = idx
  showEditColumn.value = true
}

const resetAddColForm = () => {
  addColForm.name = ''
  addColForm.type = ''
  addColForm.isPK = false
  addColForm.isUnique = false
  addColForm.nullable = true
  addColForm.default = ''
  addColForm.comment = ''
}

const startAddColumn = () => {
  if (!selectedNode.value) return
  addColTargetNodeId.value = selectedNode.value.id
  resetAddColForm()
  showAddColumn.value = true
}

const openAddColumn = (nodeId) => {
  const node = nodes.value.find(n => String(n.id) === String(nodeId))
  if (!node) return
  selectedNodeId.value = node.id
  selectedEdgeId.value = null
  addColTargetNodeId.value = node.id
  resetAddColForm()
  showAddColumn.value = true
}

provide('nodeActions', {
  copyNode,
  deleteNode,
  openAddColumn
})
// Set of `${nodeId}|${handleId}` anchors already used by an edge, provided to
// TableNode so occupied anchors show a move cursor and reconnect their edge on
// press instead of starting a brand-new connection.
const occupiedHandleKeys = computed(() => {
  const set = new Set()
  for (const e of edges.value) {
    if (e.sourceHandle) set.add(`${String(e.source)}|${e.sourceHandle}`)
    if (e.targetHandle) set.add(`${String(e.target)}|${e.targetHandle}`)
  }
  return set
})
provide('occupiedHandleKeys', occupiedHandleKeys)

const saveNewColumn = () => {
  if (!addColForm.name.trim()) {
    ElMessage.warning(t('erModel.messages.enterFieldName'))
    return
  }
  if (!addColForm.type.trim()) {
    ElMessage.warning(t('erModel.messages.enterFieldType'))
    return
  }
  const target = nodes.value.find(n => String(n.id) === String(addColTargetNodeId.value))
  if (!target) return
  if (!Array.isArray(target.data.columns)) {
    target.data.columns = []
  }
  target.data.columns.push({
    name: addColForm.name.trim(),
    type: addColForm.type.trim(),
    isPK: addColForm.isPK,
    isFK: false,
    isUnique: addColForm.isUnique,
    nullable: addColForm.nullable,
    default: addColForm.default,
    comment: addColForm.comment,
    aiSuggested: false
  })
  showAddColumn.value = false
  ElMessage.success(t('erModel.messages.fieldAdded'))
}

const saveColumnEdit = () => {
  if (selectedNode.value && editColForm.value) {
    const idx = editColIndex.value
    selectedNode.value.data.columns[idx] = { ...editColForm.value }
  }
  showEditColumn.value = false
  ElMessage.success(t('erModel.messages.fieldUpdated'))
}

// Saved ER models can carry stale `handleBounds` (e.g. an edge pointing at
// `right-target-1` while the node's saved bounds only contain `right-target-0`).
// Vue Flow only re-measures handle positions when node dimensions change, so on
// load it keeps using the stale bounds: edges render at fallback positions and
// their reconnection handles fail the internal handle lookup. Re-measure all
// handles from the DOM once nodes are initialized.
const onNodesInitialized = () => {
  nextTick(() => {
    updateNodeInternals(nodes.value.map(n => String(n.id)))
  })
}

const handleFitView = () => {
  nextTick(() => {
    setTimeout(() => {
      fitView({ padding: 0.15, includeHiddenNodes: false, duration: 300 })
    }, 50)
  })
}

const autoLayout = () => {
  const g = new dagre.graphlib.Graph()
  g.setGraph({
    rankdir: 'LR',
    align: 'UL',
    nodesep: 120,
    ranksep: 220,
    edgesep: 50,
    marginx: 60,
    marginy: 60
  })
  g.setDefaultEdgeLabel(() => ({}))

  const vueNodes = getNodes.value
  vueNodes.forEach(node => {
    const w = node.dimensions?.width || node.width || 240
    const h = node.dimensions?.height || node.height || 200
    g.setNode(String(node.id), { width: w, height: h })
  })

  edges.value.forEach(edge => {
    // Target = parent (referenced), Source = child (foreign key holder)
    // Edge direction target -> source makes parent sit to the left of child in LR layout.
    g.setEdge(String(edge.target), String(edge.source))
  })

  dagre.layout(g)

  vueNodes.forEach(node => {
    const dagreNode = g.node(String(node.id))
    if (dagreNode) {
      node.position = {
        x: dagreNode.x - dagreNode.width / 2,
        y: dagreNode.y - dagreNode.height / 2
      }
    }
  })

  // Every table has exactly four anchors (one per side). Multiple edges between
  // the same pair of tables rotate through the sides so they do not all pile up
  // on the same anchor: the first edge takes the geometrically best side, the
  // next one takes the next free side, etc.
  const SIDE_CYCLE = [
    ['right', 'left'],
    ['bottom', 'top'],
    ['left', 'right'],
    ['top', 'bottom']
  ]
  const pairCounter = new Map()
  const firstPass = []
  edges.value.forEach(edge => {
    const sourceNode = vueNodes.find(n => String(n.id) === String(edge.source))
    const targetNode = vueNodes.find(n => String(n.id) === String(edge.target))
    if (!sourceNode || !targetNode) {
      firstPass.push({ edge, srcSide: null, tgtSide: null })
      return
    }
    const sx = sourceNode.position.x + (sourceNode.dimensions?.width || sourceNode.width || 240) / 2
    const sy = sourceNode.position.y + (sourceNode.dimensions?.height || sourceNode.height || 200) / 2
    const tx = targetNode.position.x + (targetNode.dimensions?.width || targetNode.width || 240) / 2
    const ty = targetNode.position.y + (targetNode.dimensions?.height || targetNode.height || 200) / 2
    const dx = tx - sx
    const dy = ty - sy
    let geo
    if (Math.abs(dy) > Math.abs(dx)) {
      geo = dy > 0 ? ['bottom', 'top'] : ['top', 'bottom']
    } else {
      geo = dx > 0 ? ['right', 'left'] : ['left', 'right']
    }
    const pairKey = `${String(edge.source)}|${String(edge.target)}`
    const pairIdx = pairCounter.get(pairKey) ?? 0
    pairCounter.set(pairKey, pairIdx + 1)
    const ordered = [geo, ...SIDE_CYCLE.filter(s => s[0] !== geo[0])]
    const [srcSide, tgtSide] = ordered[pairIdx % ordered.length]
    firstPass.push({ edge, srcSide, tgtSide })
  })

  edges.value = firstPass.map(({ edge, srcSide, tgtSide }) => {
    if (!srcSide || !tgtSide) return edge
    return {
      ...edge,
      sourceHandle: `${srcSide}-source-0`,
      targetHandle: `${tgtSide}-source-0`
    }
  })
  refreshHandleBounds()

  ElMessage.success(t('erModel.messages.autoLayoutDone'))
  handleFitView()
}

const addVirtualNode = () => {
  virtualForm.name = ''
  virtualForm.comment = ''
  showVirtualDialog.value = true
}

const confirmAddVirtual = () => {
  if (!virtualForm.name) {
    ElMessage.warning(t('erModel.messages.enterEntityName'))
    return
  }
  const id = `virtual-${Date.now()}`
  const node = {
    id,
    type: 'tableNode',
    position: { x: 100 + Math.random() * 200, y: 100 + Math.random() * 200 },
    data: {
      name: virtualForm.name,
      comment: virtualForm.comment || t('erModel.defaults.virtualEntity'),
      engine: 'VIRTUAL',
      columns: [
        { name: 'id', type: 'BIGINT', isPK: true, nullable: false, comment: t('erModel.defaults.virtualPK') }
      ]
    }
  }
  nodes.value.push(node)
  erModelStore.addNode(node)
  showVirtualDialog.value = false
  ElMessage.success(t('erModel.messages.virtualAdded'))
}

const handleSave = async () => {
  erModelStore.nodes = nodes.value
  erModelStore.edges = edges.value
  try {
    await erModelStore.saveModel(projectId.value)
    ElMessage.success(t('erModel.messages.modelSaved'))
  } catch {
    // handled by interceptor
  }
}

const handleSaveVersion = () => {
  versionForm.note = ''
  showVersionDialog.value = true
}

const confirmSaveVersion = async () => {
  savingVersion.value = true
  erModelStore.nodes = nodes.value
  erModelStore.edges = edges.value
  try {
    await erModelStore.saveVersion(projectId.value, versionForm.note)
    ElMessage.success(t('erModel.messages.versionSaved'))
    showVersionDialog.value = false
  } catch {
    // handled by interceptor
  } finally {
    savingVersion.value = false
  }
}

const goToSuggestions = () => router.push(`/projects/${projectId.value}/ai-suggestions`)
const goToExport = () => router.push(`/projects/${projectId.value}/export`)
const goToProject = () => router.push('/projects')

const buildFromSchema = (tables, relationships) => {
  // Build nodes into the store first so buildEdges can resolve table names -> node ids.
  const builtNodes = erModelStore.buildNodes(tables, relationships)
  erModelStore.nodes = builtNodes
  nodes.value = builtNodes
  edges.value = erModelStore.buildEdges(relationships)
}

const normalizeList = (d) => Array.isArray(d) ? d : (d?.items || d?.relationships || d?.tables || [])

// Every table has exactly four anchors (top/right/bottom/left, one per side),
// so every edge handle is normalized to the fixed `-0` id of that side. Old
// models with indexed ids (`right-source-1`) are folded back to `-0`.
// Every table has exactly four anchors (top/right/bottom/left, one per side,
// type=source). Loose connection mode lets every anchor act as both source and
// target, so edge source/target handles both use the fixed `${side}-source-0` id.
const normalizeHandleId = (handleId, fallback) => {
  const m = /^(top|right|bottom|left)-(source|target)(?:-(\d+))?$/.exec(handleId || '')
  if (!m) return fallback
  return `${m[1]}-source-0`
}

const normalizeEdge = (edge) => {
  const data = edge.data || {}
  return {
    ...edge,
    type: 'relationEdge',
    updatable: true,
    sourceHandle: normalizeHandleId(edge.sourceHandle, 'right-source-0'),
    targetHandle: normalizeHandleId(edge.targetHandle, 'left-source-0'),
    data: {
      cardinality: data.cardinality || '1:N',
      sourceType: data.sourceType || 'database',
      confidence: data.confidence ?? 1,
      fromColumn: data.fromColumn || null,
      toColumn: data.toColumn || null,
      constraintName: data.constraintName || null,
      reason: data.reason || []
    }
  }
}

const loadModel = async () => {
  // Snapshot the project id: if the user navigates away while this
  // async load is still running, route.params.id becomes undefined and later
  // requests would hit /api/projects/undefined/... (422).
  const pid = projectId.value
  if (!pid) return
  // 1) 优先加载已保存的 ER 模型（含节点位置、视口）
  let usedSaved = false
  try {
    const data = await erModelStore.loadModel(pid)
    if (data?.model_data?.nodes?.length) {
      nodes.value = erModelStore.nodes.map(n => ({ ...n }))
      edges.value = (erModelStore.edges || []).map(normalizeEdge)
      if (data.model_data.viewport) {
        viewport.value = data.model_data.viewport
      }
      usedSaved = true
    }
  } catch {
    // 继续走 schema 兜底
  }

  // 2) 没有已保存模型时，从 schema 表 + 关系重建节点与边
  if (!usedSaved) {
    try {
      const [tablesData, relsData] = await Promise.all([
        getTables(pid),
        getRelationships(pid)
      ])
      const tables = normalizeList(tablesData)
      // Only visualize relationships the user has committed (confirmed/manual) —
      // AI suggestions with status=suggested are intentionally hidden until the
      // user approves them in the AI review drawer (router /ai-suggestions).
      // Explicit database foreign keys always land with status=confirmed (see
      // schema.py relationship persistence) so they are always drawn.
      const rels = normalizeList(relsData).filter(r => r.status === 'confirmed')
      buildFromSchema(tables, rels)
    } catch {
      // 还没有 schema 数据
    }
  }

  // 3) 始终用最新的关系数据补齐边：
  //    - 显式外键(database_constraint status=confirmed)、已确认(confirmed)、手动创建(manual) 显示；
  //    - 被用户“拒绝/删除”的关系和未确认的AI建议(suggested)不在画布上出现，
  //      前者被彻底排除，后者留在审核页等待用户批准后再进入画布；
  //    - 已存在的边（含用户在编辑器中的修改）优先保留，避免覆盖；
  //    - 对已有边合并最新关系元数据（如 constraintName），避免已保存模型里缺少字段。
  try {
    const relsData = await getRelationships(pid)
    const rels = normalizeList(relsData).filter(r => r.status === 'confirmed')
    const confirmedIds = new Set(rels.map(r => String(r.id)))
    const relEdges = erModelStore.buildEdges(rels).map(normalizeEdge)
    const edgeMap = new Map()
    const norm = (v) => (v == null ? '' : String(v))
    const edgeKey = (e) => {
      const d = e.data || {}
      return `${e.source}|${e.target}|${norm(d.fromColumn)}|${norm(d.toColumn)}`
    }
    const pairKey = (e) => `${e.source}|${e.target}`
    const edgeByKey = new Map()
    const edgeByPair = new Map()
    for (const e of edges.value.map(normalizeEdge)) {
      edgeMap.set(e.id, e)
      edgeByKey.set(edgeKey(e), e)
      const pk = pairKey(e)
      if (!edgeByPair.has(pk)) edgeByPair.set(pk, [])
      edgeByPair.get(pk).push(e)
    }
    for (const e of relEdges) {
      let existing = edgeMap.get(e.id) || edgeByKey.get(edgeKey(e))
      if (!existing) {
        const candidates = edgeByPair.get(pairKey(e)) || []
        existing = candidates.find(c => !c.data?.constraintName)
      }
      if (existing) {
        // If the existing edge is a local-only temp edge (the create response
        // was lost before the id was applied), adopt the real DB relationship id
        // so delete/update hit the correct API and the edge doesn't stay an
        // orphan that reappears after reload.
        const existingId = String(existing.id)
        const finalId = existingId.startsWith('e-') && String(e.id) !== existingId
          ? e.id
          : existing.id
        edgeMap.set(finalId, normalizeEdge({
          ...existing,
          id: finalId,
          data: {
            ...(existing.data || {}),
            constraintName: e.data?.constraintName || existing.data?.constraintName || null,
            sourceType: e.data?.sourceType || existing.data?.sourceType || 'database',
            cardinality: e.data?.cardinality || existing.data?.cardinality || '1:N',
            fromColumn: e.data?.fromColumn || existing.data?.fromColumn || null,
            toColumn: e.data?.toColumn || existing.data?.toColumn || null
          }
        }))
      } else {
        edgeMap.set(e.id, e)
        edgeByKey.set(edgeKey(e), e)
        const pk = pairKey(e)
        if (!edgeByPair.has(pk)) edgeByPair.set(pk, [])
        edgeByPair.get(pk).push(e)
      }
    }
    edges.value = [...edgeMap.values()].filter(e => {
      const id = String(e.id)
      return confirmedIds.has(id) || id.startsWith('e-')
    })
  } catch (err) {
    console.error('补齐关系边失败', err)
  }

  // 4) 用最新 schema + relationships 修复已保存节点的 PK/FK/Unique 标志
  try {
    const [tablesData, relsData] = await Promise.all([
      getTables(pid),
      getRelationships(pid)
    ])
    const tables = normalizeList(tablesData)
    // Confirmed + manual relationships are enough to correctly light up the
    // FK flags on columns; suggested (unapproved AI) relationships are omitted
    // from the canvas so their columns should not get the blue FK badge either.
    const rels = normalizeList(relsData).filter(r => r.status === 'confirmed')
    const repaired = erModelStore.repairNodeKeyFlags(nodes.value, tables, rels)
    nodes.value = repaired
  } catch {
    // ignore
  }

  erModelStore.nodes = nodes.value
  erModelStore.edges = edges.value
  refreshHandleBounds()
}

const loadProject = async () => {
  const pid = projectId.value
  if (!pid) return
  try {
    const data = await projectStore.fetchProject(pid)
    if (data) projectName.value = data.name
  } catch {
    // ignore
  }
}

// 左侧表列表面板折叠/展开后，画布宽度变化，等 0.25s transition 结束再 fitView
watch(leftSidebarCollapsed, () => {
  setTimeout(() => handleFitView(), 300)
})

// 切换项目时（组件被复用，仅 route.params.id 变化），清空画布状态后重新加载
watch(projectId, async (newId, oldId) => {
  if (!newId || newId === oldId) return
  nodes.value = []
  edges.value = []
  viewport.value = { x: 0, y: 0, zoom: 1 }
  selectedNode.value = null
  selectedEdge.value = null
  erModelStore.nodes = []
  erModelStore.edges = []
  setMode(mode.value)
  await Promise.all([loadProject(), loadModel()])
})

onMounted(() => {
  setMode(mode.value)
  loadProject()
  loadModel()
  window.addEventListener('mouseup', onWindowMouseUp)

  registerShortcut('Ctrl+s', handleSave)
  registerShortcut('Ctrl+l', autoLayout)
  registerShortcut('Ctrl+e', goToExport)
})

onBeforeUnmount(() => {
  window.removeEventListener('mouseup', onWindowMouseUp)
  unregisterShortcut('Ctrl+s')
  unregisterShortcut('Ctrl+l')
  unregisterShortcut('Ctrl+e')
})
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;
.er-editor-page {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: $bg-color;
  position: relative;
}

.editor-header {
  height: 64px;
  background: $bg-white;
  border-bottom: 1px solid $border-light;
  padding: 0 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
  overflow: hidden;
  transition: height 0.25s ease, padding 0.25s ease, opacity 0.25s ease, border-width 0.25s ease;

  &.collapsed {
    height: 0;
    padding: 0 20px;
    opacity: 0;
    border-bottom-width: 0;
  }
}

  .header-collapse-btn {
    position: absolute;
    top: 18px;
    right: 8px;
    z-index: 30;
    width: 28px;
    height: 28px;
    border-radius: 50%;
    border: 1px solid $border-light;
    background: $bg-white;
    color: $text-secondary;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    box-shadow: $shadow-sm;
    transition: top 0.25s ease, background 0.15s, color 0.15s;

    &.collapsed {
      top: 8px;
      right: 8px;
    }

    &:hover {
      background: $bg-light;
      color: $primary-color;
    }
  }

.header-left {
  display: flex;
  align-items: center;
  gap: 20px;
}

.breadcrumb-sm {
  :deep(.el-breadcrumb__inner) { font-size: 13px; }

  .current-crumb {
    color: #1E293B;
    font-weight: 600;
  }

  .el-breadcrumb__item[style*="cursor: pointer"] :deep(.el-breadcrumb__inner) {
    cursor: pointer;
    transition: color .15s;
  }
  .el-breadcrumb__item[style*="cursor: pointer"] :deep(.el-breadcrumb__inner):hover {
    color: #2563eb !important;
  }
}

.header-stats {
  display: flex;
  gap: 8px;
}

.stat-pill {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 4px 10px;
  background: $bg-light;
  border-radius: 14px;
  font-size: 12px;
  color: $text-regular;
  font-weight: 500;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-right: 32px;
}

.editor-body {
  flex: 1;
  display: flex;
  overflow: hidden;
  position: relative;
}

.tables-sidebar {
  width: 260px;
  background: $bg-white;
  border-right: 1px solid $border-light;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  transition: width 0.25s ease;
  position: relative;

  &.collapsed {
    width: 0;
    overflow: hidden;
    border-right: none;
  }
}

.sidebar-collapse-btn {
  position: absolute;
  left: 246px;
  top: 50%;
  transform: translateY(-50%);
  z-index: 20;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: 1px solid $border-light;
  background: $bg-white;
  color: $text-secondary;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: $shadow-sm;
  transition: left 0.25s ease;

  &.collapsed {
    left: 14px;
  }

  &:hover {
    background: $bg-light;
    color: $primary-color;
  }
}

.sidebar-tabs {
  display: flex;
  padding: 12px;
  gap: 4px;
  border-bottom: 1px solid $border-light;

  .tab {
    flex: 1;
    padding: 8px 10px;
    font-size: 12px;
    font-weight: 500;
    color: $text-secondary;
    border-radius: $radius-md;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 5px;
    transition: $transition-base;

    &:hover { background: $bg-light; }
    &.active { background: rgba(59, 130, 246, 0.1); color: $primary-color; }
  }
}

.sidebar-search {
  padding: 12px;
  border-bottom: 1px solid $border-light;
}

.sidebar-list {
  flex: 1;
  padding: 4px 8px 12px;
}

.table-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: $radius-sm;
  cursor: pointer;
  transition: $transition-base;

  &:hover { background: $bg-light; }
  &.active { background: rgba(59, 130, 246, 0.08); }

  .table-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: $primary-color;
    flex-shrink: 0;
  }

  .table-info {
    flex: 1;
    min-width: 0;
  }

  .table-name {
    font-size: 12px;
    font-weight: 500;
    color: $text-primary;
    font-family: 'SF Mono', Consolas, monospace;
  }

  .table-sub {
    font-size: 11px;
    color: $text-placeholder;
    margin-top: 1px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

.canvas-area {
  flex: 1;
  position: relative;
  background: $bg-color;
  overflow: hidden;
  min-width: 0;
}

.vue-flow-canvas {
  width: 100%;
  height: 100%;
}

.marker-defs {
  position: absolute;
  width: 0;
  height: 0;
  overflow: hidden;
  pointer-events: none;
}

.legend-bar {
  position: absolute;
  left: 50px;
  bottom: 20px;
  background: $bg-white;
  padding: 10px 16px;
  border-radius: $radius-md;
  box-shadow: $shadow-md;
  display: flex;
  gap: 16px;
  z-index: 10;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: $text-regular;
}

.legend-dot {
  width: 24px;
  height: 2px;
  border-radius: 1px;

  &.confirmed { background: #3B82F6; }
  &.ai { background: #F59E0B; }
  &.manual { background: #10B981; }
}

.legend-key { font-size: 11px; }

.detail-sidebar,
.edge-sidebar {
  width: 320px;
  background: $bg-white;
  border-left: 1px solid $border-light;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  overflow: hidden;
}

.detail-header {
  padding: 20px;
  border-bottom: 1px solid $border-light;
}

.detail-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.detail-title {
  font-size: 18px;
  font-weight: 700;
  color: $text-primary;
  font-family: 'SF Mono', monospace;
  margin: 0;
}

.detail-sub {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 6px;
}

.table-comment {
  font-size: 12px;
  color: $text-secondary;
  line-height: 1.6;
  margin: 12px 0 0;
  padding: 10px 12px;
  background: $bg-light;
  border-radius: $radius-sm;
}

.rel-path {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 12px;
}

.table-chip {
  padding: 3px 8px;
  background: $bg-light;
  border-radius: 4px;
  font-family: 'SF Mono', monospace;
  font-size: 11px;
  color: $text-regular;
  font-weight: 500;

  &.target {
    background: rgba(59, 130, 246, 0.08);
    color: $primary-color;
  }
}

.detail-tabs {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;

  :deep(.el-tabs__header) {
    margin: 0;
    padding: 0 16px;
  }

  :deep(.el-tabs__nav-wrap) {
    padding-top: 12px;
  }

  :deep(.el-tabs__item) {
    font-size: 13px;
    font-weight: 500;
  }

  :deep(.el-tabs__content) {
    flex: 1;
    overflow: auto;
    padding: 12px 16px 20px;
  }
}

.column-list {
  .col-detail {
    padding: 12px;
    background: $bg-light;
    border-radius: $radius-md;
    margin-bottom: 8px;

    &:last-child { margin-bottom: 0; }
  }

  .col-d-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .col-d-name {
    display: flex;
    align-items: center;
    gap: 6px;
    font-family: 'SF Mono', monospace;
    font-size: 13px;
    font-weight: 600;
    color: $text-primary;
  }

  .badge {
    font-size: 9px;
    font-weight: 700;
    padding: 1px 4px;
    border-radius: 3px;

    &.pk { background: #FEF3C7; color: #B45309; }
    &.uk { background: #E0E7FF; color: #4338CA; }
    &.fk { background: #DBEAFE; color: #1E40AF; }
  }

  .col-d-type {
    font-size: 11px;
    color: $primary-color;
    font-family: 'SF Mono', monospace;
    font-weight: 500;
  }

  .col-d-meta {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-top: 6px;
  }

  .col-d-default {
    font-size: 11px;
    color: $text-placeholder;
    font-family: 'SF Mono', monospace;
  }

  .col-d-comment {
    margin-top: 8px;
    font-size: 11px;
    color: $text-secondary;
    line-height: 1.5;
    padding-top: 8px;
    border-top: 1px dashed $border-color;
  }

  .col-d-edit {
    margin-top: 8px;
    padding-top: 8px;
    border-top: 1px dashed $border-light;
  }
}

.rel-list {
  .rel-card {
    padding: 12px;
    border-radius: $radius-md;
    border: 1px solid $border-light;
    margin-bottom: 10px;

    &.ai_suggestion,
    &.ai,
    &.ai_confirmed,
    &.manual {
      border-color: rgba(16, 185, 129, 0.3);
      background: rgba(16, 185, 129, 0.03);
    }
  }

  .rel-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 8px;
  }

  .rel-type {
    font-size: 12px;
    font-weight: 700;
    color: $primary-color;
    background: rgba(59, 130, 246, 0.08);
    padding: 2px 8px;
    border-radius: 4px;
  }

  .rel-cols {
    font-size: 11px;
    color: $text-secondary;
    margin-top: 6px;

    code {
      font-family: 'SF Mono', monospace;
      background: $bg-light;
      padding: 1px 5px;
      border-radius: 3px;
      color: $text-regular;
    }
  }

  .rel-tag-row {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-top: 10px;
    padding-top: 10px;
    border-top: 1px dashed $border-light;
  }
}

.edge-detail-body {
  flex: 1;
  overflow: auto;
  padding: 20px;
  // Extra right padding so long wrapped reason text doesn't brush against the
  // drawer scroll-bar / right edge. Box-sizing ensures the padding is inside.
  padding-right: 28px;
  box-sizing: border-box;

  .reason-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
    // Guarantee the list shrinks so its children can honor the drawer width
    // and wrap to a second line instead of overflowing the right border.
    min-width: 0;
    width: 100%;
  }

  .reason-item {
    display: flex;
    // Icon stays pinned to the first line's top; wrapped text flows under.
    align-items: flex-start;
    justify-content: flex-start;
    gap: 8px;
    font-size: 12px;
    color: $text-regular;
    line-height: 1.55;
    flex-wrap: nowrap;
    width: 100%;
    min-width: 0;
    // Add its own small right breathing room as a belt-and-suspenders safety net.
    padding-right: 4px;
    box-sizing: border-box;

    .el-icon {
      // Keep the check icon aligned with the middle of the first line of text
      // even when the line wraps to a second row.
      flex-shrink: 0;
      // Was 2px; nudged down so the tick sits on the same optical baseline
      // as 12px reason text (font-size 12px + line-height 1.55 ≈ 18.6px row).
      margin-top: 5px;
    }

    span {
      // Allow the reason sentence to wrap anywhere (including mid-word for long
      // column/table names like teacher_course_semester_uk_idx) and fall back
      // to a second line instead of overflowing the drawer boundary.
      flex: 1 1 auto;
      min-width: 0;
      white-space: normal;
      word-break: break-word;
      overflow-wrap: anywhere;
      // Cap visual height at 2 lines as requested; user can still scroll the
      // outer drawer if an extremely long sentence needs more room.
      display: -webkit-box;
      -webkit-line-clamp: 2;
      line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
      text-overflow: ellipsis;
    }
  }
}

.cardinality-opt {
  width: 100%;
  box-sizing: border-box;
  padding: 10px 12px;
  border: 1px solid $border-light;
  border-radius: $radius-md;
  transition: all 0.2s;
  cursor: pointer;
  display: flex;
  align-items: center;
  overflow: visible;
  height: auto;
  min-height: 0;

  :deep(.el-radio) {
    display: flex;
    align-items: center;
    padding-top: 0;
    margin-right: 0;
    width: 100%;
    overflow: visible;
    height: auto;
    min-height: 0;
  }

  :deep(.el-radio__input) {
    padding-top: 0;
    margin-right: 8px;
    flex-shrink: 0;
  }

  :deep(.el-radio__label) {
    flex: 1;
    min-width: 0;
    padding-left: 0;
    overflow: visible;
  }

  :deep(.el-radio__inner) {
    border-color: #64748B;
    width: 14px;
    height: 14px;
  }

  :deep(.el-radio__original:checked + .el-radio__inner) {
    width: 14px;
    height: 14px;
  }

  :deep(.el-radio__inner::after) {
    width: 4px;
    height: 4px;
    border-radius: 50%;
    background-color: #fff;
    content: '';
    position: absolute;
    left: 50%;
    top: 50%;
    transform: translate(-50%, -50%) scale(0);
    transition: transform 0.15s ease-in;
  }

  &:hover {
    border-color: $primary-color;
    background: rgba(59, 130, 246, 0.03);
  }

  .cardinality-text {
    min-width: 0;
    white-space: normal;
  }

  .cardinality-label {
    font-size: 13px;
    font-weight: 600;
    color: $text-primary;
    line-height: 1.3;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .cardinality-desc {
    font-size: 11px;
    color: $text-secondary;
    margin-top: 2px;
    line-height: 1.3;
    word-break: break-word;
    overflow-wrap: break-word;
  }
}

html.dark {
  .er-editor-page { background: #252526; }

  .editor-header {
    background: #252526 !important;
    border-bottom-color: #3c3c3c !important;
  }

  .current-crumb { color: #f8fafc !important; }

  .breadcrumb-sm :deep(.el-breadcrumb__inner) { color: #94a3b8 !important; }
  .breadcrumb-sm :deep(.el-breadcrumb__inner.is-link:hover) { color: #60a5fa !important; }
  .breadcrumb-sm .el-breadcrumb__item[style*="cursor: pointer"] :deep(.el-breadcrumb__inner):hover { color: #60a5fa !important; }

  .stat-pill {
    background: #1e1e1e !important;
    color: #94a3b8 !important;
  }

  .search-box {
    .el-input__wrapper {
      background: #1e1e1e !important;
      box-shadow: 0 0 0 1px #3c3c3c !important;
    }
    .el-input__inner { color: #f8fafc; }
    .el-input__icon { color: #94a3b8; }
  }

  :deep(.el-divider--vertical) { border-left-color: #3c3c3c !important; }

  .tables-sidebar {
    background: #252526 !important;
    border-right-color: #3c3c3c !important;

    &.collapsed { border-right: none; }
  }

  .sidebar-collapse-btn {
    background: #252526 !important;
    border-color: #3c3c3c !important;
    color: #94a3b8 !important;

    &:hover { background: #3c3c3c !important; color: #60a5fa !important; }
  }

  .header-collapse-btn {
    background: #252526 !important;
    border-color: #3c3c3c !important;
    color: #94a3b8 !important;

    &:hover { background: #3c3c3c !important; color: #60a5fa !important; }
  }

  .sidebar-tabs {
    border-bottom-color: #3c3c3c !important;
    .tab {
      color: #94a3b8 !important;
      &:hover { background: #3c3c3c !important; }
      &.active { background: rgba(59, 130, 246, 0.15) !important; color: #60a5fa !important; }
    }
  }

  .sidebar-search {
    border-bottom-color: #3c3c3c !important;
    .el-input__wrapper {
      background: #1e1e1e !important;
      box-shadow: 0 0 0 1px #3c3c3c !important;
    }
    .el-input__inner { color: #f8fafc; }
  }

  .table-item {
    .table-name { color: #e2e8f0 !important; }
    .table-sub { color: #94a3b8 !important; }
    &:hover { background: #3c3c3c !important; }
    &.active { background: rgba(59, 130, 246, 0.15) !important; }
  }

  .canvas-area {
    background: #1e1e1e !important;
  }

  .legend-bar {
    background: #252526 !important;
    border: 1px solid #3c3c3c !important;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4) !important;

    .legend-item { color: #94a3b8 !important; }
  }

  .detail-sidebar,
  .edge-sidebar {
    background: #252526 !important;
    border-left-color: #3c3c3c !important;
  }

  .detail-header { border-bottom-color: #3c3c3c !important; }
  .detail-title { color: #f8fafc !important; }
  .table-comment {
    background: #1e1e1e !important;
    color: #94a3b8 !important;
  }

  .detail-tabs {
    :deep(.el-tabs__item) { color: #94a3b8 !important; }
    :deep(.el-tabs__item.is-active) { color: #60a5fa !important; }
    :deep(.el-tabs__active-bar) { background-color: #60a5fa !important; }
  }

  .column-list {
    .col-detail { background: #1e1e1e !important; }
    .col-d-name { color: #f8fafc !important; }
    .col-d-type { color: #60a5fa !important; }
    .col-d-comment { color: #94a3b8 !important; border-top-color: #3c3c3c !important; }
    .col-d-edit { border-top-color: #3c3c3c !important; }
  }

  .rel-list {
    .rel-card { border-color: #3c3c3c !important; }
    .rel-cols { color: #94a3b8 !important; }
  }

  .edge-detail-body {
    code { background: #1e1e1e !important; color: #e2e8f0 !important; }
  }

  .cardinality-opt {
    border-color: #3c3c3c !important;
    &:hover { border-color: #60a5fa !important; background: rgba(59, 130, 246, 0.08) !important; }
    .cardinality-label { color: #f8fafc !important; }
    .cardinality-desc { color: #94a3b8 !important; }
  }

  :deep(.vue-flow__controls-button) {
    background: #252526 !important;
    border-color: #3c3c3c !important;
    svg { color: #94a3b8 !important; }
    &:hover { background: #3c3c3c !important; svg { color: #60a5fa !important; } }

    &.is-active {
      background: rgba(96, 165, 250, 0.22) !important;
      border-color: #60a5fa !important;
      box-shadow: 0 0 0 1px rgba(96, 165, 250, 0.45), 0 0 8px rgba(96, 165, 250, 0.35) !important;
      svg { color: #93c5fd !important; }
    }
  }

  :deep(.vue-flow__controls-button) .mode-icon {
    display: block;
    margin: auto;
  }

  :deep(.vue-flow__minimap) {
    background: #252526 !important;
    border: 1px solid #3c3c3c !important;
  }
}
</style>

<style lang="scss">
/* 全局 tooltip：去掉默认黑色背景 */
.er-tip.el-popper {
  background: #ffffff !important;
  color: #1e293b !important;
  border: 1px solid #e2e8f0 !important;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.12) !important;
}
.er-tip.el-popper .el-popper__arrow::before {
  background: #ffffff !important;
  border: 1px solid #e2e8f0 !important;
}
html.dark .er-tip.el-popper {
  background: #252526 !important;
  color: #e5e7eb !important;
  border: 1px solid #3c3c3c !important;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.4) !important;
}
html.dark .er-tip.el-popper .el-popper__arrow::before {
  background: #252526 !important;
  border: 1px solid #3c3c3c !important;
}

/* 浅色模式：当前模式按钮高亮（淡蓝） */
.vue-flow__controls {
  .vue-flow__controls-button.is-active {
    background: rgba(96, 165, 250, 0.22) !important;
    border-color: #60a5fa !important;
    box-shadow: 0 0 0 1px rgba(96, 165, 250, 0.45), 0 0 8px rgba(96, 165, 250, 0.35) !important;
    svg { color: #2563eb !important; }
  }
}

html.dark .vue-flow__controls {
  .vue-flow__controls-button {
    background: #252526 !important;
    border-color: #3c3c3c !important;

    svg { color: #94a3b8 !important; }

    &:hover {
      background: #3c3c3c !important;
      svg { color: #60a5fa !important; }
    }

    &.is-active {
      background: rgba(96, 165, 250, 0.22) !important;
      border-color: #60a5fa !important;
      box-shadow: 0 0 0 1px rgba(96, 165, 250, 0.45), 0 0 8px rgba(96, 165, 250, 0.35) !important;
      svg { color: #2563eb !important; }
    }
  }
}

html.dark .vue-flow__minimap {
  background: #252526 !important;
  border: 1px solid #3c3c3c !important;

  .vue-flow__minimap-mask {
    fill: rgba(37, 37, 38, 0.7) !important;
  }
}

html.dark .vue-flow__edge-path {
  stroke: #94a3b8 !important;
}
</style>
