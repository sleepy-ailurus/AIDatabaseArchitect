<template>
  <div class="er-editor-page">
    <div class="editor-header">
      <div class="header-left">
        <el-breadcrumb separator="/" class="breadcrumb-sm">
          <el-breadcrumb-item style="color: #94A3B8;">项目</el-breadcrumb-item>
          <el-breadcrumb-item style="color: #94A3B8;">{{ projectName }}</el-breadcrumb-item>
          <el-breadcrumb-item>
            <span style="color: #1E293B; font-weight: 600;">ER 模型编辑器</span>
          </el-breadcrumb-item>
        </el-breadcrumb>

        <div class="header-stats">
          <div class="stat-pill">
            <el-icon :size="12"><Grid /></el-icon>
            <span>{{ nodes.length }} 张表</span>
          </div>
          <div class="stat-pill">
            <el-icon :size="12"><Share /></el-icon>
            <span>{{ edges.length }} 条关系</span>
          </div>
        </div>
      </div>

      <div class="header-right">
        <div class="search-box">
          <el-input v-model="searchTable" placeholder="搜索表名..." size="small" clearable style="width: 160px;">
            <template #prefix><el-icon :size="14"><Search /></el-icon></template>
          </el-input>
        </div>

        <el-divider direction="vertical" />

        <el-button-group>
          <el-tooltip content="自动布局" placement="bottom">
            <el-button size="small" @click="autoLayout"><el-icon><SetUp /></el-icon></el-button>
          </el-tooltip>
          <el-tooltip content="适配视图" placement="bottom">
            <el-button size="small" @click="fitView"><el-icon><Aim /></el-icon></el-button>
          </el-tooltip>
          <el-tooltip content="添加虚拟实体" placement="bottom">
            <el-button size="small" @click="addVirtualNode"><el-icon><Plus /></el-icon></el-button>
          </el-tooltip>
        </el-button-group>

        <el-divider direction="vertical" />

        <el-button size="small" :icon="MagicStick" type="primary" plain @click="goToSuggestions">
          AI 建议
        </el-button>
        <el-button size="small" :icon="Download" @click="goToExport">
          导出
        </el-button>
        <el-button size="small" :icon="Document" type="success" :loading="erModelStore.saving" @click="handleSave">
          保存
        </el-button>
        <el-button size="small" :icon="Promotion" @click="handleSaveVersion">
          存版本
        </el-button>
      </div>
    </div>

    <div class="editor-body">
      <aside class="tables-sidebar">
        <div class="sidebar-tabs">
          <div class="tab" :class="{ active: sidebarTab === 'tables' }" @click="sidebarTab = 'tables'">
            <el-icon><Grid /></el-icon> 表列表
          </div>
        </div>

        <div class="sidebar-search">
          <el-input v-model="searchTable" placeholder="筛选表..." size="small" clearable>
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
              <div class="table-sub">{{ node.data.columns?.length || 0 }} 字段 · {{ node.data.comment || '无注释' }}</div>
            </div>
          </div>
          <el-empty v-if="filteredNodes.length === 0" description="暂无表" :image-size="60" />
        </el-scrollbar>
      </aside>

      <main class="canvas-area">
        <VueFlow
          v-model:nodes="nodes"
          v-model:edges="edges"
          :node-types="nodeTypes"
          :edge-types="edgeTypes"
          :default-viewport="{ zoom: 1 }"
          :min-zoom="0.2"
          :max-zoom="2"
          fit-view-on-init
          class="vue-flow-canvas"
          @node-click="onNodeClick"
          @edge-click="onEdgeClick"
          @connect="onConnect"
          @pane-click="onPaneClick"
        >
          <Background :gap="20" :size="1" pattern="dots" />
          <Controls />
          <MiniMap pannable zoomable />
        </VueFlow>

        <div class="legend-bar">
          <div class="legend-item"><span class="legend-dot confirmed"></span> 数据库关系</div>
          <div class="legend-item"><span class="legend-dot ai"></span> AI 建议关系</div>
          <div class="legend-item"><span class="legend-dot manual"></span> 手动关系</div>
          <div class="legend-item"><span class="legend-key">🔑</span> 主键</div>
          <div class="legend-item"><span class="legend-key">🔗</span> 外键</div>
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
            <span style="color: #94A3B8; font-size: 12px;">{{ selectedNode.data.columns?.length || 0 }} 字段</span>
          </div>
          <p class="table-comment" v-if="selectedNode.data.comment">{{ selectedNode.data.comment }}</p>
        </div>

        <el-tabs v-model="detailTab" class="detail-tabs">
          <el-tab-pane label="字段" name="columns">
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
                  <span v-else style="font-size: 11px; color: #94A3B8;">可空</span>
                  <span v-if="c.default" class="col-d-default">默认: {{ c.default }}</span>
                </div>
                <div class="col-d-comment" v-if="c.comment">{{ c.comment }}</div>

                <div class="col-d-edit">
                  <el-button text size="small" type="primary" @click="editColumn(idx)">
                    <el-icon><Edit /></el-icon> 编辑
                  </el-button>
                </div>
              </div>
            </div>
          </el-tab-pane>

          <el-tab-pane label="关系" name="relations">
            <div class="rel-list">
              <div v-for="r in nodeRelations" :key="r.id" class="rel-card" :class="r.data?.sourceType">
                <div class="rel-head">
                  <span class="rel-type">{{ r.data?.cardinality || '1:N' }}</span>
                  <el-tag
                    v-if="r.data?.confidence !== undefined && r.data.confidence < 1"
                    size="small"
                    :class="getConfidenceClass(r.data.confidence)"
                    effect="light"
                  >
                    置信度 {{ (r.data.confidence * 100).toFixed(0) }}%
                  </el-tag>
                </div>
                <div class="rel-cols">
                  <code>{{ r.source === selectedNode.id ? (r.data?.fromColumn || '?') : (r.data?.toColumn || '?') }}</code>
                  →
                  <code>{{ r.source === selectedNode.id ? getTargetName(r.target) : getSourceName(r.source) }}</code>
                </div>
                <div class="rel-tag-row" v-if="r.data?.sourceType === 'ai_suggestion' || r.data?.sourceType === 'ai'">
                  <el-tag size="small" type="warning" effect="light"><el-icon><MagicStick /></el-icon> AI 推断</el-tag>
                </div>
                <div class="rel-tag-row" v-else-if="r.data?.sourceType === 'manual'">
                  <el-tag size="small" type="success" effect="light">手动创建</el-tag>
                </div>
              </div>
              <el-empty v-if="nodeRelations.length === 0" description="该表暂无关系" :image-size="60" />
            </div>
          </el-tab-pane>
        </el-tabs>
      </aside>

      <aside class="edge-sidebar" v-else-if="selectedEdge">
        <div class="detail-header">
          <div class="detail-title-row">
            <h3 class="detail-title">关系详情</h3>
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
          <el-form label-width="90px" size="small">
            <el-form-item label="基数">
              <el-select v-model="selectedEdge.data.cardinality" style="width: 100%;">
                <el-option label="一对一 (1:1)" value="1:1" />
                <el-option label="一对多 (1:N)" value="1:N" />
                <el-option label="多对多 (N:N)" value="N:N" />
              </el-select>
            </el-form-item>
            <el-form-item label="来源">
              <el-tag size="small" :type="getSourceTagType(selectedEdge.data.sourceType)">
                {{ getSourceLabel(selectedEdge.data.sourceType) }}
              </el-tag>
            </el-form-item>
            <el-form-item label="源字段">
              <code>{{ selectedEdge.data.fromColumn || '-' }}</code>
            </el-form-item>
            <el-form-item label="目标字段">
              <code>{{ selectedEdge.data.toColumn || '-' }}</code>
            </el-form-item>
            <el-form-item v-if="selectedEdge.data.reason && selectedEdge.data.reason.length" label="推断依据">
              <div class="reason-list">
                <div v-for="(r, i) in selectedEdge.data.reason" :key="i" class="reason-item">
                  <el-icon color="#10B981"><CircleCheckFilled /></el-icon>
                  <span>{{ r }}</span>
                </div>
              </div>
            </el-form-item>
          </el-form>

          <el-button type="danger" plain :icon="Delete" style="width: 100%;" @click="deleteEdge(selectedEdge.id)">
            删除该关系
          </el-button>
        </div>
      </aside>
    </div>

    <el-dialog v-model="showEditColumn" title="编辑字段" width="480px">
      <el-form :model="editColForm" label-width="90px" v-if="editColForm">
        <el-form-item label="字段名">
          <el-input v-model="editColForm.name" />
        </el-form-item>
        <el-form-item label="类型">
          <el-input v-model="editColForm.type" />
        </el-form-item>
        <el-form-item label="主键">
          <el-switch v-model="editColForm.isPK" />
        </el-form-item>
        <el-form-item label="唯一">
          <el-switch v-model="editColForm.isUnique" />
        </el-form-item>
        <el-form-item label="可空">
          <el-switch v-model="editColForm.nullable" />
        </el-form-item>
        <el-form-item label="注释">
          <el-input v-model="editColForm.comment" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditColumn = false">取消</el-button>
        <el-button type="primary" @click="saveColumnEdit">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showVersionDialog" title="保存版本" width="440px">
      <el-form :model="versionForm" label-width="80px">
        <el-form-item label="版本备注">
          <el-input v-model="versionForm.note" type="textarea" :rows="3" placeholder="描述本次版本变更..." />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showVersionDialog = false">取消</el-button>
        <el-button type="primary" :loading="savingVersion" @click="confirmSaveVersion">保存版本</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showVirtualDialog" title="添加虚拟实体" width="440px">
      <el-form :model="virtualForm" label-width="80px">
        <el-form-item label="实体名">
          <el-input v-model="virtualForm.name" placeholder="例如：external_api" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="virtualForm.comment" type="textarea" :rows="2" placeholder="该实体的用途说明..." />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showVirtualDialog = false">取消</el-button>
        <el-button type="primary" @click="confirmAddVirtual">添加</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showCardinalityDialog" title="选择关系基数" width="360px" :close-on-click-modal="false">
      <p style="font-size: 13px; color: #64748B; margin: 0 0 16px;">
        正在连接表 <strong>{{ getSourceName(pendingConnection?.source) }}</strong> → <strong>{{ getTargetName(pendingConnection?.target) }}</strong>
      </p>
      <el-radio-group v-model="pendingCardinality" style="display: flex; flex-direction: column; gap: 10px;">
        <el-radio value="1:1" class="cardinality-opt">
          <div>
            <div class="cardinality-label">一对一 (1:1)</div>
            <div class="cardinality-desc">一个源表记录对应一个目标表记录</div>
          </div>
        </el-radio>
        <el-radio value="1:N" class="cardinality-opt">
          <div>
            <div class="cardinality-label">一对多 (1:N)</div>
            <div class="cardinality-desc">一个源表记录对应多个目标表记录</div>
          </div>
        </el-radio>
        <el-radio value="N:N" class="cardinality-opt">
          <div>
            <div class="cardinality-label">多对多 (N:N)</div>
            <div class="cardinality-desc">双方记录互相可以对应多条</div>
          </div>
        </el-radio>
      </el-radio-group>
      <template #footer>
        <el-button @click="cancelTableConnection">取消</el-button>
        <el-button type="primary" @click="confirmTableConnection">创建关系</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, markRaw, provide } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { VueFlow, useVueFlow } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
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
import { getRelationships, createRelationship, deleteRelationship } from '@/api/relationship'

const route = useRoute()
const router = useRouter()
const erModelStore = useErModelStore()
const projectStore = useProjectStore()
const projectId = route.params.id

const nodeTypes = { tableNode: markRaw(TableNode) }
const edgeTypes = { relationEdge: markRaw(RelationEdge) }

const showCardinalityDialog = ref(false)
const pendingConnection = ref(null)
const pendingCardinality = ref('1:N')

const projectName = ref('')
const searchTable = ref('')
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

const nodes = ref(erModelStore.nodes)
const edges = ref(erModelStore.edges)

const { fitView } = useVueFlow()

const selectedNode = computed(() => {
  if (!selectedNodeId.value) return null
  return nodes.value.find(n => n.id === selectedNodeId.value) || null
})

const selectedEdge = computed(() => {
  if (!selectedEdgeId.value) return null
  return edges.value.find(e => e.id === selectedEdgeId.value) || null
})

const filteredNodes = computed(() => {
  if (!searchTable.value) return nodes.value
  return nodes.value.filter(n => (n.data.name || '').toLowerCase().includes(searchTable.value.toLowerCase()))
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
    ai: 'warning',
    ai_suggestion: 'warning',
    ai_confirmed: 'success',
    manual: 'success'
  }
  return map[t] || 'info'
}

const getSourceLabel = (t) => {
  const map = {
    database: '数据库外键',
    database_constraint: '数据库约束',
    ai: 'AI 推断',
    ai_suggestion: 'AI 建议',
    ai_confirmed: 'AI 已确认',
    manual: '手动创建'
  }
  return map[t] || t || '未知'
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
    ElMessage.warning('不能连接到自身节点')
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
    data: {
      cardinality: '1:N',
      sourceType: 'manual',
      confidence: 1,
      fromColumn: connection.sourceHandle?.replace('s-', ''),
      toColumn: connection.targetHandle?.replace('t-', ''),
      reason: []
    }
  }
  edges.value.push(newEdge)
  try {
    const data = await createRelationship(projectId, {
      source_table: connection.source,
      target_table: connection.target,
      source_column: newEdge.data.fromColumn,
      target_column: newEdge.data.toColumn,
      cardinality: '1:N',
      source_type: 'manual'
    })
    if (data?.id) newEdge.id = String(data.id)
    ElMessage.success('关系已创建')
  } catch {
    // keep local edge even if API fails
  }
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
  try {
    await createRelationship(projectId, {
      source_table: connection.source,
      target_table: connection.target,
      source_column: null,
      target_column: null,
      cardinality,
      source_type: 'manual'
    })
    ElMessage.success(`关系已创建 (${cardinality})`)
  } catch {
    // keep local edge even if API fails
  }

  showCardinalityDialog.value = false
  pendingConnection.value = null
}

const cancelTableConnection = () => {
  showCardinalityDialog.value = false
  pendingConnection.value = null
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
  ElMessage.success('表已复制')
}

const deleteNode = (nodeId) => {
  const node = nodes.value.find(n => n.id === nodeId)
  if (!node) return

  edges.value = edges.value.filter(e => e.source !== nodeId && e.target !== nodeId)
  nodes.value = nodes.value.filter(n => n.id !== nodeId)

  if (selectedNodeId.value === nodeId) {
    selectedNodeId.value = null
  }

  ElMessage.success('表已删除')
}

provide('nodeActions', {
  copyNode,
  deleteNode
})

const deleteEdge = async (id) => {
  try {
    await deleteRelationship(id)
    ElMessage.success('关系已删除')
  } catch {
    // ignore
  }
  edges.value = edges.value.filter(e => e.id !== id)
  selectedEdgeId.value = null
}

const editColumn = (idx) => {
  if (!selectedNode.value) return
  const col = selectedNode.value.data.columns[idx]
  editColForm.value = JSON.parse(JSON.stringify(col))
  editColIndex.value = idx
  showEditColumn.value = true
}

const saveColumnEdit = () => {
  if (!selectedNode.value || editColForm.value) {
    const idx = editColIndex.value
    selectedNode.value.data.columns[idx] = { ...editColForm.value }
  }
  showEditColumn.value = false
  ElMessage.success('字段已更新（请点击保存按钮持久化）')
}

const autoLayout = () => {
  const cols = 4
  const colWidth = 300
  const rowHeight = 360
  nodes.value.forEach((node, idx) => {
    const col = idx % cols
    const row = Math.floor(idx / cols)
    node.position = {
      x: 40 + col * colWidth,
      y: 40 + row * rowHeight
    }
  })
  ElMessage.success('已自动布局')
  setTimeout(() => fitView(), 100)
}

const addVirtualNode = () => {
  virtualForm.name = ''
  virtualForm.comment = ''
  showVirtualDialog.value = true
}

const confirmAddVirtual = () => {
  if (!virtualForm.name) {
    ElMessage.warning('请输入实体名')
    return
  }
  const id = `virtual-${Date.now()}`
  const node = {
    id,
    type: 'tableNode',
    position: { x: 100 + Math.random() * 200, y: 100 + Math.random() * 200 },
    data: {
      name: virtualForm.name,
      comment: virtualForm.comment || '虚拟实体',
      engine: 'VIRTUAL',
      columns: [
        { name: 'id', type: 'BIGINT', isPK: true, nullable: false, comment: '虚拟主键' }
      ]
    }
  }
  nodes.value.push(node)
  erModelStore.addNode(node)
  showVirtualDialog.value = false
  ElMessage.success('虚拟实体已添加')
}

const handleSave = async () => {
  try {
    await erModelStore.saveModel(projectId)
    ElMessage.success('ER 模型已保存')
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
  try {
    await erModelStore.saveVersion(projectId, versionForm.note)
    ElMessage.success('版本已保存')
    showVersionDialog.value = false
  } catch {
    // handled by interceptor
  } finally {
    savingVersion.value = false
  }
}

const goToSuggestions = () => router.push(`/projects/${projectId}/ai-suggestions`)
const goToExport = () => router.push(`/projects/${projectId}/export`)

const buildFromSchema = (tables, relationships) => {
  nodes.value = erModelStore.buildNodes(tables)
  edges.value = erModelStore.buildEdges(relationships)
}

const loadModel = async () => {
  try {
    const data = await erModelStore.loadModel(projectId)
    if (data && (data.nodes?.length || data.tables?.length)) {
      nodes.value = erModelStore.nodes
      edges.value = erModelStore.edges
      return
    }
  } catch {
    // fall through to schema
  }

  try {
    const [tablesData, relsData] = await Promise.all([
      getTables(projectId),
      getRelationships(projectId)
    ])
    const tables = Array.isArray(tablesData) ? tablesData : (tablesData?.items || tablesData?.tables || [])
    const rels = Array.isArray(relsData) ? relsData : (relsData?.items || relsData?.relationships || [])
    buildFromSchema(tables, rels)
    erModelStore.nodes = nodes.value
    erModelStore.edges = edges.value
  } catch {
    // no schema data yet
  }
}

const loadProject = async () => {
  try {
    const data = await projectStore.fetchProject(projectId)
    if (data) projectName.value = data.name
  } catch {
    // ignore
  }
}

onMounted(() => {
  loadProject()
  loadModel()
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
}

.header-left {
  display: flex;
  align-items: center;
  gap: 20px;
}

.breadcrumb-sm {
  :deep(.el-breadcrumb__inner) { font-size: 13px; }
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
}

.editor-body {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.tables-sidebar {
  width: 260px;
  background: $bg-white;
  border-right: 1px solid $border-light;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
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
    &.ai {
      border-color: rgba(245, 158, 11, 0.3);
      background: rgba(245, 158, 11, 0.03);
    }

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

  .reason-list {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .reason-item {
    display: flex;
    align-items: flex-start;
    gap: 6px;
    font-size: 12px;
    color: $text-regular;
    line-height: 1.5;
  }
}

.cardinality-opt {
  padding: 10px 12px;
  border: 1px solid $border-light;
  border-radius: $radius-md;
  transition: all 0.2s;
  cursor: pointer;
  align-items: center;

  :deep(.el-radio__inner) {
    border-color: #64748B;
  }

  :deep(.el-radio) {
    display: flex;
    align-items: flex-start;
    padding-top: 2px;
  }

  &:hover {
    border-color: $primary-color;
    background: rgba(59, 130, 246, 0.03);
  }

  .cardinality-label {
    font-size: 13px;
    font-weight: 600;
    color: $text-primary;
  }

  .cardinality-desc {
    font-size: 11px;
    color: $text-secondary;
    margin-top: 2px;
  }
}
</style>
