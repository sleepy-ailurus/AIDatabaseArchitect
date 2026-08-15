<template>
  <div class="concept-page">
    <div class="concept-header">
      <div class="header-left">
        <el-breadcrumb separator="/" class="breadcrumb-sm">
          <el-breadcrumb-item style="color: #94A3B8;">{{ t('conceptModel.breadcrumb.project') }}</el-breadcrumb-item>
          <el-breadcrumb-item style="color: #94A3B8; cursor: pointer;" @click="goBack">{{ projectName }}</el-breadcrumb-item>
          <el-breadcrumb-item>
            <span class="current-crumb">{{ t('conceptModel.breadcrumb.title') }}</span>
          </el-breadcrumb-item>
        </el-breadcrumb>

        <div class="header-stats">
          <div class="stat-pill">
            <el-icon :size="12"><Grid /></el-icon>
            <span>{{ t('conceptModel.stats.entities', { count: stats.entityCount }) }}</span>
          </div>
          <div class="stat-pill">
            <el-icon :size="12"><Share /></el-icon>
            <span>{{ t('conceptModel.stats.relations', { count: stats.relationCount }) }}</span>
          </div>
          <div class="stat-pill">
            <el-icon :size="12"><CircleCheck /></el-icon>
            <span>{{ t('conceptModel.stats.attributes', { count: stats.attributeCount }) }}</span>
          </div>
        </div>
      </div>

      <div class="header-right">
        <el-tooltip :content="t('conceptModel.reLayout')" placement="bottom" popper-class="er-tip">
          <el-button size="small" @click="reLayout"><el-icon><SetUp /></el-icon></el-button>
        </el-tooltip>
        <el-tooltip :content="t('conceptModel.fitView')" placement="bottom" popper-class="er-tip">
          <el-button size="small" @click="handleFitView"><el-icon><Aim /></el-icon></el-button>
        </el-tooltip>

        <el-divider direction="vertical" />

        <el-tooltip :content="t('conceptModel.aiName')" placement="bottom" popper-class="er-tip">
          <el-button
            size="small"
            :icon="MagicStick"
            :loading="converting"
            @click="handleAiName"
          >
            <span class="btn-text">{{ t('conceptModel.aiName') }}</span>
          </el-button>
        </el-tooltip>
        <el-tooltip :content="t('conceptModel.reconvert')" placement="bottom" popper-class="er-tip">
          <el-button size="small" :icon="Refresh" :loading="converting" @click="handleReconvert">
            <span class="btn-text">{{ t('conceptModel.reconvert') }}</span>
          </el-button>
        </el-tooltip>
        <el-button size="small" :icon="Download" @click="goToEr">
          <span class="btn-text">{{ t('conceptModel.backToEr') }}</span>
        </el-button>
        <el-button size="small" :icon="Document" type="success" @click="handleSave">
          <span class="btn-text">{{ t('common.save') }}</span>
        </el-button>
      </div>
    </div>

    <div class="concept-body" v-loading="loading || converting">
      <VueFlow
        v-model:nodes="nodes"
        v-model:edges="edges"
        v-model:viewport="viewport"
        :node-types="nodeTypes"
        :edge-types="edgeTypes"
        :min-zoom="0.15"
        :max-zoom="2.5"
        :snap-grid="{ x: 10, y: 10 }"
        fit-view-on-init
        class="concept-canvas"
        @node-drag="onNodeDrag"
        @node-drag-stop="onNodeDragStop"
        @pane-click="selectedRelId = null"
      >
        <Background :gap="20" :size="1" pattern="dots" />
        <Controls :show-zoom="false" :show-fit-view="false" :show-interactive="false">
          <ControlButton @click="zoomIn"><el-icon><ZoomIn /></el-icon></ControlButton>
          <ControlButton @click="zoomOut"><el-icon><ZoomOut /></el-icon></ControlButton>
        </Controls>
        <MiniMap pannable zoomable />
      </VueFlow>

      <div class="legend-bar">
        <div class="legend-item"><span class="legend-box entity"></span> {{ t('conceptModel.legend.entity') }}</div>
        <div class="legend-item"><span class="legend-box relation"></span> {{ t('conceptModel.legend.relation') }}</div>
        <div class="legend-item"><span class="legend-attr pk"></span> {{ t('conceptModel.legend.pk') }}</div>
        <div class="legend-item"><span class="legend-attr fk"></span> {{ t('conceptModel.legend.fk') }}</div>
        <div class="legend-item"><span class="legend-attr uk"></span> {{ t('conceptModel.legend.uk') }}</div>
        <div class="legend-item"><span class="legend-attr plain"></span> {{ t('conceptModel.legend.attr') }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, markRaw, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { VueFlow, useVueFlow } from '@vue-flow/core'
import dagre from 'dagre'
import { Background } from '@vue-flow/background'
import { Controls, ControlButton } from '@vue-flow/controls'
import { MiniMap } from '@vue-flow/minimap'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import '@vue-flow/controls/dist/style.css'
import '@vue-flow/minimap/dist/style.css'

import EntityNode from '@/components/concept/EntityNode.vue'
import AttributeNode from '@/components/concept/AttributeNode.vue'
import RelationNode from '@/components/concept/RelationNode.vue'
import ChenEdge from '@/components/concept/ChenEdge.vue'
import {
  getConceptModel,
  convertConceptModel,
  saveConceptModel,
  saveConceptPositions
} from '@/api/conceptModel'
import { getProject } from '@/api/project'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const projectId = computed(() => route.params.id)

const projectName = ref('')
const loading = ref(false)
const converting = ref(false)
const modelData = ref(null)
const nodes = ref([])
const edges = ref([])
const viewport = ref({ x: 0, y: 0, zoom: 1 })
const selectedRelId = ref(null)

const nodeTypes = {
  entityNode: markRaw(EntityNode),
  attributeNode: markRaw(AttributeNode),
  relationNode: markRaw(RelationNode)
}
const edgeTypes = { chenEdge: markRaw(ChenEdge) }

const { fitView, zoomIn, zoomOut, screenToFlowCoordinate } = useVueFlow()

// Layout bookkeeping: base positions + follower attribute nodes per parent.
const layoutState = ref(null)

const stats = computed(() => {
  const data = modelData.value
  if (!data) return { entityCount: 0, relationCount: 0, attributeCount: 0 }
  const entities = data.entities || []
  const relations = data.relations || []
  const attrCount = entities.reduce((s, e) => s + (e.attributes?.length || 0), 0)
    + relations.reduce((s, r) => s + (r.attributes?.length || 0), 0)
  return {
    entityCount: entities.length,
    relationCount: relations.length,
    attributeCount: attrCount
  }
})

const applyLayout = (data) => {
  const entities = data.entities || []
  const relations = data.relations || []
  const g = new dagre.graphlib.Graph()
  g.setGraph({ rankdir: 'TB', nodesep: 110, ranksep: 150, marginx: 80, marginy: 80 })
  g.setDefaultEdgeLabel(() => ({}))
  for (const e of entities) g.setNode(e.id, { width: 170, height: 54 })
  for (const r of relations) g.setNode(r.id, { width: 150, height: 76 })
  for (const r of relations) {
    g.setEdge(r.source_entity, r.id)
    g.setEdge(r.target_entity, r.id)
  }
  dagre.layout(g)

  const nodeList = []
  const edgeList = []
  const base = new Map()
  const followers = new Map()

  for (const e of entities) {
    const dn = g.node(e.id)
    const pos = e.position || { x: dn.x - dn.width / 2, y: dn.y - dn.height / 2 }
    base.set(e.id, { x: pos.x, y: pos.y })
    nodeList.push({
      id: e.id,
      type: 'entityNode',
      position: { ...pos },
      data: { label: e.name, table: e.table, comment: e.comment }
    })

    const attrs = e.attributes || []
    const radius = 90 + Math.min(attrs.length, 14) * 15
    attrs.forEach((a, i) => {
      const angle = (2 * Math.PI * i) / Math.max(attrs.length, 1) - Math.PI / 2
      const ax = pos.x + 85 + radius * Math.cos(angle) - 54
      const ay = pos.y + 27 + radius * Math.sin(angle) - 17
      base.set(a.id, { x: ax, y: ay })
      nodeList.push({
        id: a.id,
        type: 'attributeNode',
        position: { x: ax, y: ay },
        data: {
          label: a.name,
          column: a.column,
          isPk: !!a.is_pk,
          isFk: !!a.is_fk,
          isUnique: !!a.is_unique
        }
      })
      edgeList.push({
        id: `${e.id}-${a.id}`,
        source: e.id,
        target: a.id,
        type: 'chenEdge',
        data: {},
        style: { stroke: '#cbd5e1', strokeWidth: 1 }
      })
      if (!followers.has(e.id)) followers.set(e.id, [])
      followers.get(e.id).push(a.id)
    })
  }

  for (const r of relations) {
    const dn = g.node(r.id)
    const pos = r.position || { x: dn.x - dn.width / 2, y: dn.y - dn.height / 2 }
    const junction = r.source_type === 'junction'
    base.set(r.id, { x: pos.x, y: pos.y })
    nodeList.push({
      id: r.id,
      type: 'relationNode',
      position: { ...pos },
      data: { label: r.name, junction, reason: r.reason || [] }
    })
    edgeList.push({
      id: `${r.source_entity}-${r.id}`,
      source: r.source_entity,
      target: r.id,
      type: 'chenEdge',
      data: { sourceCard: r.source_card, targetCard: null, junction }
    })
    edgeList.push({
      id: `${r.id}-${r.target_entity}`,
      source: r.id,
      target: r.target_entity,
      type: 'chenEdge',
      data: { sourceCard: null, targetCard: r.target_card, junction }
    })

    const attrs = r.attributes || []
    attrs.forEach((a, i) => {
      const angle = (2 * Math.PI * i) / Math.max(attrs.length, 1)
      const ax = pos.x + 75 + 78 * Math.cos(angle) - 54
      const ay = pos.y + 38 + 78 * Math.sin(angle) - 17
      base.set(a.id, { x: ax, y: ay })
      nodeList.push({
        id: a.id,
        type: 'attributeNode',
        position: { x: ax, y: ay },
        data: {
          label: a.name,
          column: a.column,
          isPk: !!a.is_pk,
          isFk: !!a.is_fk,
          isUnique: !!a.is_unique
        }
      })
      edgeList.push({
        id: `${r.id}-${a.id}`,
        source: r.id,
        target: a.id,
        type: 'chenEdge',
        data: {},
        style: { stroke: '#cbd5e1', strokeWidth: 1 }
      })
      if (!followers.has(r.id)) followers.set(r.id, [])
      followers.get(r.id).push(a.id)
    })
  }

  nodes.value = nodeList
  edges.value = edgeList
  layoutState.value = { base, followers }
  nextTick(() => {
    setTimeout(() => fitView({ padding: 0.2, duration: 300 }), 50)
  })
}

const onNodeDrag = ({ node }) => {
  const ls = layoutState.value
  if (!ls) return
  const base = ls.base.get(String(node.id))
  if (!base) return
  const dx = node.position.x - base.x
  const dy = node.position.y - base.y
  for (const fid of ls.followers.get(String(node.id)) || []) {
    const fb = ls.base.get(fid)
    const n = nodes.value.find(n => String(n.id) === String(fid))
    if (fb && n) n.position = { x: fb.x + dx, y: fb.y + dy }
  }
}

const onNodeDragStop = () => {
  persistPositions()
}

const persistPositions = async () => {
  try {
    const positions = {}
    for (const n of nodes.value) {
      positions[String(n.id)] = { x: n.position.x, y: n.position.y }
    }
    await saveConceptPositions(projectId.value, positions, viewport.value)
  } catch {
    // interceptor shows error; keep editing locally
  }
}

const syncPositionsToModel = () => {
  if (!modelData.value) return
  const posMap = new Map(nodes.value.map(n => [String(n.id), n.position]))
  for (const e of modelData.value.entities || []) {
    if (posMap.has(e.id)) e.position = { x: posMap.get(e.id).x, y: posMap.get(e.id).y }
  }
  for (const r of modelData.value.relations || []) {
    if (posMap.has(r.id)) r.position = { x: posMap.get(r.id).x, y: posMap.get(r.id).y }
  }
}

const handleSave = async () => {
  syncPositionsToModel()
  if (!modelData.value) return
  try {
    await saveConceptModel(projectId.value, {
      entities: modelData.value.entities,
      relations: modelData.value.relations,
      viewport: viewport.value
    })
    ElMessage.success(t('conceptModel.saved'))
  } catch {
    // interceptor shows error
  }
}

const load = async (forceConvert = false, useAi = false) => {
  loading.value = true
  try {
    let data = null
    if (forceConvert) {
      converting.value = true
      data = await convertConceptModel(projectId.value, { use_ai_names: useAi })
    } else {
      const stored = await getConceptModel(projectId.value)
      if (stored?.model_data?.entities?.length) {
        data = stored.model_data
      } else {
        converting.value = true
        data = await convertConceptModel(projectId.value, { use_ai_names: false })
      }
    }
    if (data) {
      modelData.value = data
      applyLayout(data)
    }
  } catch {
    // interceptor shows error
  } finally {
    loading.value = false
    converting.value = false
  }
}

const handleReconvert = async () => {
  try {
    await ElMessageBox.confirm(t('conceptModel.reconvertConfirm'), t('conceptModel.reconvert'), {
      confirmButtonText: t('common.confirm'),
      cancelButtonText: t('common.cancel'),
      type: 'warning'
    })
  } catch {
    return
  }
  await load(true, false)
}

const handleAiName = async () => {
  try {
    await ElMessageBox.confirm(t('conceptModel.aiNameConfirm'), t('conceptModel.aiName'), {
      confirmButtonText: t('common.confirm'),
      cancelButtonText: t('common.cancel'),
      type: 'info'
    })
  } catch {
    return
  }
  await load(true, true)
}

const reLayout = () => {
  if (modelData.value) applyLayout(modelData.value)
}

const handleFitView = () => {
  nextTick(() => {
    setTimeout(() => fitView({ padding: 0.2, duration: 300 }), 50)
  })
}

const goBack = () => router.push('/projects')
const goToEr = () => router.push(`/projects/${projectId.value}/er-model`)

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

.concept-page {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: $bg-color;
  position: relative;
}

.concept-header {
  min-height: 64px;
  height: auto;
  background: $bg-white;
  border-bottom: 1px solid $border-light;
  padding: 10px 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
  flex-wrap: wrap;
  gap: 10px 20px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 20px;
  flex-wrap: wrap;
  min-width: 0;
}

.breadcrumb-sm {
  :deep(.el-breadcrumb__inner) { font-size: 13px; }
  .current-crumb { color: #1E293B; font-weight: 600; }
  .el-breadcrumb__item[style*="cursor: pointer"] :deep(.el-breadcrumb__inner) {
    cursor: pointer;
    &:hover { color: #2563eb !important; }
  }
}

.header-stats { display: flex; gap: 8px; }

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
  justify-content: flex-end;
  gap: 8px;
  flex-wrap: wrap;
  min-width: 0;
}

.btn-text { display: inline; margin-left: 4px; }

.concept-body {
  flex: 1;
  position: relative;
  overflow: hidden;
  min-height: 0;
}

.concept-canvas {
  width: 100%;
  height: 100%;
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

.legend-box {
  width: 18px;
  height: 14px;
  display: inline-block;
  &.entity { border: 2px solid #3b82f6; border-radius: 2px; }
  &.relation {
    width: 14px;
    height: 14px;
    border: 2px solid #10b981;
    transform: rotate(45deg);
  }
}

.legend-attr {
  width: 14px;
  height: 14px;
  border: 1.5px solid #94a3b8;
  border-radius: 50%;
  display: inline-block;
  &.pk { border-color: #d97706; background: #fffbeb; }
  &.fk { border-color: #2563eb; background: #eff6ff; }
  &.uk { border-color: #4f46e5; background: #eef2ff; }
  &.plain { background: #f8fafc; }
}

html.dark {
  .concept-header {
    background: #252526 !important;
    border-bottom-color: #3c3c3c !important;
  }
  .current-crumb { color: #f8fafc !important; }
  .stat-pill { background: #1e1e1e !important; color: #94a3b8 !important; }
  .concept-body { background: #1e1e1e !important; }
  .legend-bar {
    background: #252526 !important;
    border: 1px solid #3c3c3c !important;
    .legend-item { color: #94a3b8 !important; }
  }
}
</style>
