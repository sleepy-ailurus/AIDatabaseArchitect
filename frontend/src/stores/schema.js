import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as schemaApi from '@/api/schema'

export const useSchemaStore = defineStore('schema', () => {
  const tables = ref([])
  const currentSnapshot = ref(null)
  const snapshots = ref([])
  const loading = ref(false)

  const fetchTables = async (projectId, params) => {
    loading.value = true
    try {
      const data = await schemaApi.getTables(projectId, params)
      const list = Array.isArray(data) ? data : (data?.items || data?.tables || [])
      tables.value = list
      return list
    } catch (e) {
      tables.value = []
      return []
    } finally {
      loading.value = false
    }
  }

  const syncSchema = async (projectId) => {
    const data = await schemaApi.syncSchema(projectId)
    if (data?.snapshot) currentSnapshot.value = data.snapshot
    return data
  }

  const fetchSnapshots = async (projectId) => {
    try {
      const data = await schemaApi.getSnapshots(projectId)
      const list = Array.isArray(data) ? data : (data?.items || [])
      snapshots.value = list
      return list
    } catch (e) {
      snapshots.value = []
      return []
    }
  }

  const getTableByName = (name) => {
    return tables.value.find(t => t.name === name || t.table_name === name)
  }

  const reset = () => {
    tables.value = []
    currentSnapshot.value = null
    snapshots.value = []
  }

  return {
    tables,
    currentSnapshot,
    snapshots,
    loading,
    fetchTables,
    syncSchema,
    fetchSnapshots,
    getTableByName,
    reset
  }
})
