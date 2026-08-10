import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as erModelApi from '@/api/erModel'

export const useErModelStore = defineStore('erModel', () => {
  const nodes = ref([])
  const edges = ref([])
  const viewport = ref({ x: 0, y: 0, zoom: 1 })
  const loading = ref(false)
  const saving = ref(false)

  const buildNodes = (tables, relationships) => {
    if (!Array.isArray(tables)) return []
    const cols = 4
    const colWidth = 280
    const rowHeight = 320

    // Infer FK columns from relationships (schema API no longer returns table.foreign_keys).
    const fkColumnsByTable = new Map()
    if (Array.isArray(relationships)) {
      for (const r of relationships) {
        const table = r.source_table || r.from_table
        const col = r.source_column || r.from_column
        if (!table || !col) continue
        if (!fkColumnsByTable.has(table)) fkColumnsByTable.set(table, new Set())
        fkColumnsByTable.get(table).add(col)
      }
    }

    return tables.map((t, idx) => {
      const col = idx % cols
      const row = Math.floor(idx / cols)
      const table = t.table_name || t.name || ('table_' + idx)
      const position = t.position || { x: 40 + col * colWidth, y: 40 + row * rowHeight }
      const columns = t.columns || []
      const fkColumns = fkColumnsByTable.get(table) || new Set()
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
            isPK: c.is_primary_key || c.is_pk || c.isPK || c.column_key === 'PRI',
            isFK: fkColumns.has(c.name || c.column_name) || c.is_fk || c.isFK || c.column_key === 'MUL',
            isUnique: c.is_unique || c.isUnique || c.column_key === 'UNI',
            nullable: c.nullable !== false && c.is_nullable !== 'NO',
            default: c.default ?? c.column_default,
            comment: c.comment ?? c.column_comment ?? ''
          }))
        }
      }
    })
  }

  /**
   * Repair key flags (PK/FK/Unique) on existing nodes using the latest schema tables
   * and relationships. Preserves positions, sizes, and any user edits to column names.
   */
  const repairNodeKeyFlags = (existingNodes, tables, relationships) => {
    if (!Array.isArray(existingNodes) || !existingNodes.length) return existingNodes
    if (!Array.isArray(tables) || !tables.length) return existingNodes

    const schemaByTable = new Map()
    for (const t of tables) {
      const tableName = t.table_name || t.name
      if (!tableName) continue
      const colMap = new Map()
      for (const c of t.columns || []) {
        const colName = c.name || c.column_name
        if (colName) colMap.set(colName, c)
      }
      schemaByTable.set(tableName, colMap)
    }

    const fkColumnsByTable = new Map()
    if (Array.isArray(relationships)) {
      for (const r of relationships) {
        const table = r.source_table || r.from_table
        const col = r.source_column || r.from_column
        if (!table || !col) continue
        if (!fkColumnsByTable.has(table)) fkColumnsByTable.set(table, new Set())
        fkColumnsByTable.get(table).add(col)
      }
    }

    return existingNodes.map(node => {
      const tableName = node.data?.name
      const schemaCols = schemaByTable.get(tableName)
      if (!schemaCols || !Array.isArray(node.data?.columns)) return node

      const fkCols = fkColumnsByTable.get(tableName) || new Set()
      const newColumns = node.data.columns.map(col => {
        const schemaCol = schemaCols.get(col.name)
        if (!schemaCol) return col
        return {
          ...col,
          isPK: schemaCol.is_primary_key || schemaCol.is_pk || schemaCol.isPK || schemaCol.column_key === 'PRI',
          isFK: fkCols.has(col.name) || schemaCol.is_fk || schemaCol.isFK || schemaCol.column_key === 'MUL',
          isUnique: schemaCol.is_unique || schemaCol.isUnique || schemaCol.column_key === 'UNI'
        }
      })

      return {
        ...node,
        data: {
          ...node.data,
          columns: newColumns
        }
      }
    })
  }

  const buildEdges = (relationships) => {
    if (!Array.isArray(relationships)) return []

    // Map table names -> current node ids, because nodes may use numeric DB ids
    // while relationships use table names as source/target.
    const nodeById = new Map()
    const nodeByName = new Map()
    for (const n of nodes.value || []) {
      nodeById.set(String(n.id), n)
      if (n.data?.name) nodeByName.set(n.data.name, n)
    }
    const resolveNodeId = (name) => {
      if (!name) return ''
      const byId = nodeById.get(String(name))
      if (byId) return String(byId.id)
      const byName = nodeByName.get(name)
      if (byName) return String(byName.id)
      return String(name)
    }

    const normalizeCardinality = (card) => {
      const c = String(card || '1:N').toLowerCase()
      if (c === 'one-to-one' || c === '1:1') return '1:1'
      if (c === 'one-to-many' || c === '1:n') return '1:N'
      // Treat many-to-one (N:1) as one-to-many (1:N) since they are inverse relationships
      if (c === 'many-to-one' || c === 'n:1') return '1:N'
      if (c === 'many-to-many' || c === 'n:n') return 'N:N'
      return '1:N'
    }

    return relationships.map((r, idx) => {
      return {
        id: String(r.id ?? `e${idx}`),
        source: resolveNodeId(r.source_table || r.from_table),
        target: resolveNodeId(r.target_table || r.to_table),
        sourceHandle: 'right-source',
        targetHandle: 'left-target',
        type: 'relationEdge',
        data: {
          cardinality: normalizeCardinality(r.cardinality),
          sourceType: r.source_type || r.type || 'database',
          confidence: r.confidence ?? 1,
          fromColumn: r.source_column || r.from_column || null,
          toColumn: r.target_column || r.to_column || null,
          constraintName: r.constraint_name || null,
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
        const model = data.model_data || {}
        if (model.nodes?.length) {
          nodes.value = model.nodes
          edges.value = model.edges || []
          if (model.viewport) viewport.value = model.viewport
        }
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
    repairNodeKeyFlags,
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
