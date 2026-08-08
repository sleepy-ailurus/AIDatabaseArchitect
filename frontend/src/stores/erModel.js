import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as erModelApi from '@/api/erModel'

export const useErModelStore = defineStore('erModel', () => {
  const nodes = ref([])
  const edges = ref([])
  const viewport = ref({ x: 0, y: 0, zoom: 1 })
  const loading = ref(false)
  const saving = ref(false)

  const buildNodes = (tables) => {
    if (!Array.isArray(tables)) return []
    const cols = 4
    const colWidth = 280
    const rowHeight = 320
    return tables.map((t, idx) => {
      const col = idx % cols
      const row = Math.floor(idx / cols)
      const table = t.table_name || t.name || ('table_' + idx)
      const position = t.position || { x: 40 + col * colWidth, y: 40 + row * rowHeight }
      const columns = t.columns || []
      return {
        id: String(t.id ?? table),
        type: 'tableNode',
        position,
        data: {
          name: table,
          comment: t.comment || t.table_comment || '',
          engine: t.engine,
          rows: t.rows,
          columns: columns.map(c => ({
            name: c.name || c.column_name,
            type: c.type || c.column_type || c.data_type,
            isPK: c.is_pk || c.isPK || c.column_key === 'PRI',
            isFK: c.is_fk || c.isFK || c.column_key === 'MUL',
            isUnique: c.is_unique || c.isUnique || c.column_key === 'UNI',
            nullable: c.nullable !== false && c.is_nullable !== 'NO',
            default: c.default ?? c.column_default,
            comment: c.comment ?? c.column_comment ?? ''
          }))
        }
      }
    })
  }

  const buildEdges = (relationships) => {
    if (!Array.isArray(relationships)) return []
    return relationships.map((r, idx) => {
      const sourceCol = r.source_column || r.from_column
      const targetCol = r.target_column || r.to_column
      return {
        id: String(r.id ?? `e${idx}`),
        source: String(r.source_table || r.from_table),
        target: String(r.target_table || r.to_table),
        sourceHandle: sourceCol ? `s-${sourceCol}` : undefined,
        targetHandle: targetCol ? `t-${targetCol}` : undefined,
        type: 'relationEdge',
        data: {
          cardinality: r.cardinality || '1:N',
          sourceType: r.source_type || r.type || 'database',
          confidence: r.confidence ?? 1,
          fromColumn: sourceCol,
          toColumn: targetCol,
          reason: r.reason || []
        }
      }
    })
  }

  const loadModel = async (projectId) => {
    loading.value = true
    try {
      const data = await erModelApi.getERModel(projectId)
      if (data) {
        nodes.value = data.nodes?.length ? data.nodes : buildNodes(data.tables || [])
        edges.value = data.edges?.length ? data.edges : buildEdges(data.relationships || [])
        if (data.viewport) viewport.value = data.viewport
      }
      return data
    } catch (e) {
      return null
    } finally {
      loading.value = false
    }
  }

  const saveModel = async (projectId) => {
    saving.value = true
    try {
      const payload = {
        nodes: nodes.value,
        edges: edges.value,
        viewport: viewport.value
      }
      const data = await erModelApi.saveERModel(projectId, payload)
      return data
    } finally {
      saving.value = false
    }
  }

  const saveVersion = async (projectId, note) => {
    const payload = {
      nodes: nodes.value,
      edges: edges.value,
      viewport: viewport.value,
      note
    }
    return await erModelApi.saveVersion(projectId, payload)
  }

  const addNode = (node) => {
    nodes.value.push(node)
  }

  const addEdge = (edge) => {
    const exists = edges.value.find(e => e.id === edge.id)
    if (!exists) edges.value.push(edge)
  }

  const removeEdge = (id) => {
    edges.value = edges.value.filter(e => e.id !== id)
  }

  const removeNode = (id) => {
    nodes.value = nodes.value.filter(n => n.id !== id)
    edges.value = edges.value.filter(e => e.source !== id && e.target !== id)
  }

  const reset = () => {
    nodes.value = []
    edges.value = []
    viewport.value = { x: 0, y: 0, zoom: 1 }
  }

  return {
    nodes,
    edges,
    viewport,
    loading,
    saving,
    buildNodes,
    buildEdges,
    loadModel,
    saveModel,
    saveVersion,
    addNode,
    addEdge,
    removeEdge,
    removeNode,
    reset
  }
})
