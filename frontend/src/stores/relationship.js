import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as relApi from '@/api/relationship'

export const useRelationshipStore = defineStore('relationship', () => {
  const relationships = ref([])
  const loading = ref(false)

  const fetchRelationships = async (projectId, params) => {
    loading.value = true
    try {
      const data = await relApi.getRelationships(projectId, params)
      const list = Array.isArray(data) ? data : (data?.items || data?.relationships || [])
      relationships.value = list
      return list
    } catch (e) {
      relationships.value = []
      return []
    } finally {
      loading.value = false
    }
  }

  const confirmSuggestion = async (projectId, id, payload) => {
    const data = await relApi.confirmSuggestion(projectId, id, payload)
    const idx = relationships.value.findIndex(r => r.id === id)
    if (idx > -1) {
      relationships.value[idx] = { ...relationships.value[idx], ...data, status: 'confirmed' }
    }
    return data
  }

  const rejectSuggestion = async (projectId, id, payload) => {
    const data = await relApi.rejectSuggestion(projectId, id, payload)
    const idx = relationships.value.findIndex(r => r.id === id)
    if (idx > -1) {
      relationships.value[idx] = { ...relationships.value[idx], ...data, status: 'rejected' }
    }
    return data
  }

  const createRelationship = async (projectId, payload) => {
    const data = await relApi.createRelationship(projectId, payload)
    relationships.value.push(data)
    return data
  }

  const updateRelationship = async (projectId, id, payload) => {
    const data = await relApi.updateRelationship(projectId, id, payload)
    const idx = relationships.value.findIndex(r => r.id === id)
    if (idx > -1) relationships.value[idx] = data
    return data
  }

  const deleteRelationship = async (projectId, id) => {
    await relApi.deleteRelationship(projectId, id)
    relationships.value = relationships.value.filter(r => r.id !== id)
  }

  const reset = () => {
    relationships.value = []
  }

  return {
    relationships,
    loading,
    fetchRelationships,
    confirmSuggestion,
    rejectSuggestion,
    createRelationship,
    updateRelationship,
    deleteRelationship,
    reset
  }
})
