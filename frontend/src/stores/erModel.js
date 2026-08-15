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
        isUnique: schemaCol.is_unique || schemaCol.isUnique || schemaCol.column_key === 'UNI',
        comment: schemaCol.comment || schemaCol.column_comment || col.comment || ''
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
    const resolveNode = (name) => {
      if (!name) return null
      const byId = nodeById.get(String(name))
      if (byId) return byId
      const byName = nodeByName.get(name)
      return byName || null
    }

    // Parse cardinality into canonical form, flipping N:1 -> 1:N by swapping endpoints.
    // Never returns N:1 — the UI only ever shows 1:1, 1:N, N:N.
    const normalizeRelationship = (r) => {
      const raw = String(r.cardinality || '1:N').toLowerCase()
      let src = r.source_table || r.from_table
      let srcCol = r.source_column || r.from_column || ''
      let tgt = r.target_table || r.to_table
      let tgtCol = r.target_column || r.to_column || ''
      let card = '1:N'
      if (raw === 'one-to-one' || raw === '1:1') {
        card = '1:1'
      } else if (raw === 'many-to-many' || raw === 'n:n') {
        card = 'N:N'
      } else if (raw === 'many-to-one' || raw === 'n:1') {
        // N:1 → flip endpoints so cardinality becomes 1:N (one PK side → many FK side)
        const [tmp, tmpCol] = [src, srcCol]
        src = tgt; srcCol = tgtCol
        tgt = tmp; tgtCol = tmpCol
        card = '1:N'
      } else {
        // one-to-many / 1:n / unknown → 1:N
        card = '1:N'
      }
      return { src, srcCol, tgt, tgtCol, card }
    }

    // 1) Pre-normalize every relationship (swap endpoints for N:1)
    const normalized = relationships.map((r, idx) => {
      const { src, srcCol, tgt, tgtCol, card } = normalizeRelationship(r)
      return {
        rawRel: r,
        idx,
        src, srcCol, tgt, tgtCol, card
      }
    })

    // 2) Every table has twelve anchors (three per side). Multiple edges
    //    between the same pair of tables rotate through the sides and the
    //    0/1/2 anchor slots so they do not all pile up on the same spot: the
    //    first edge takes the geometrically best side/slot, the next one takes
    //    the next free side/slot, etc.
    const chooseGeo = (srcNode, tgtNode) => {
      if (!srcNode || !tgtNode) return ['right', 'left']
      const sx = srcNode.position?.x ?? 0
      const sy = srcNode.position?.y ?? 0
      const tx = tgtNode.position?.x ?? 0
      const ty = tgtNode.position?.y ?? 0
      const dx = tx - sx
      const dy = ty - sy
      if (Math.abs(dy) > Math.abs(dx)) {
        return dy > 0 ? ['bottom', 'top'] : ['top', 'bottom']
      }
      return dx > 0 ? ['right', 'left'] : ['left', 'right']
    }

    const SIDE_CYCLE = [
      ['right', 'left'],
      ['bottom', 'top'],
      ['left', 'right'],
      ['top', 'bottom']
    ]
    // Rotate sides per NODE (not per table pair) so a table with several
    // outgoing/incoming FKs spreads them over its twelve anchors instead of
    // stacking every line on the single geometrically-best side.
    const srcCounter = new Map()
    const tgtCounter = new Map()
    const edgeAssignments = []
    for (const item of normalized) {
      const srcNode = resolveNode(item.src)
      const tgtNode = resolveNode(item.tgt)
      const geo = chooseGeo(srcNode, tgtNode)
      const srcId = resolveNodeId(item.src)
      const tgtId = resolveNodeId(item.tgt)
      const srcIdx = srcCounter.get(String(srcId)) ?? 0
      const tgtIdx = tgtCounter.get(String(tgtId)) ?? 0
      srcCounter.set(String(srcId), srcIdx + 1)
      tgtCounter.set(String(tgtId), tgtIdx + 1)
      // Prefer the geometric side for the first line of a node, then rotate.
      const srcOrdered = [geo[0], ...SIDE_CYCLE.map(s => s[0]).filter(s => s !== geo[0])]
      const tgtOrdered = [geo[1], ...SIDE_CYCLE.map(s => s[1]).filter(s => s !== geo[1])]
      const srcSide = srcOrdered[srcIdx % srcOrdered.length]
      const tgtSide = tgtOrdered[tgtIdx % tgtOrdered.length]
      edgeAssignments.push({
        ...item,
        srcId, tgtId, srcSide, tgtSide,
        srcAnchor: srcIdx % 3,
        tgtAnchor: tgtIdx % 3
      })
    }

    // 3) Build final edges. Anchor ids are fixed slots (-0/-1/-2): three per side.
    return edgeAssignments.map((a) => {
      const r = a.rawRel
      return {
        id: String(r.id ?? `e${a.idx}`),
        source: a.srcId,
        target: a.tgtId,
        sourceHandle: `${a.srcSide}-source-${a.srcAnchor}`,
        targetHandle: `${a.tgtSide}-source-${a.tgtAnchor}`,
        type: 'relationEdge',
        data: {
          cardinality: a.card,
          sourceType: r.source_type || r.type || 'database',
          confidence: r.confidence ?? 1,
          fromColumn: a.srcCol || null,
          toColumn: a.tgtCol || null,
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

  const updateEdge = (edge) => {
    const idx = edges.value.findIndex(e => String(e.id) === String(edge.id))
    if (idx >= 0) {
      edges.value[idx] = { ...edges.value[idx], ...edge }
    } else {
      edges.value.push(edge)
    }
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
    updateEdge,
    removeEdge,
    removeNode,
    reset
  }
})
