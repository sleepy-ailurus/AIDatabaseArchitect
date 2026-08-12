import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as projectApi from '@/api/project'

export const useProjectStore = defineStore('project', () => {
  const currentProject = ref(null)
  const projects = ref([])
  const loading = ref(false)
  const stats = ref({
    totalProjects: 0,
    totalTables: 0,
    totalRelations: 0,
    aiSuggestions: 0
  })

  const fetchProjects = async (params) => {
    loading.value = true
    try {
      const data = await projectApi.getProjects(params)
      const list = Array.isArray(data) ? data : (data?.items || data?.list || [])
      projects.value = list
      return list
    } catch (e) {
      projects.value = []
      return []
    } finally {
      loading.value = false
    }
  }

  const fetchProject = async (id) => {
    try {
      const data = await projectApi.getProject(id)
      currentProject.value = data
      return data
    } catch (e) {
      currentProject.value = null
      return null
    }
  }

  const createProject = async (payload) => {
    const data = await projectApi.createProject(payload)
    projects.value.unshift(data)
    return data
  }

  const updateProject = async (id, payload) => {
    const data = await projectApi.updateProject(id, payload)
    const idx = projects.value.findIndex(p => p.id === id)
    if (idx > -1) projects.value[idx] = data
    if (currentProject.value?.id === id) currentProject.value = data
    return data
  }

  const deleteProject = async (id) => {
    await projectApi.deleteProject(id)
    projects.value = projects.value.filter(p => p.id !== id)
  }

  const fetchStats = async () => {
    try {
      const data = await projectApi.getProjectStats()
      stats.value = { ...stats.value, ...data }
      return data
    } catch (e) {
      return null
    }
  }

  const clearCurrent = () => {
    currentProject.value = null
  }

  return {
    currentProject,
    projects,
    loading,
    stats,
    fetchProjects,
    fetchProject,
    createProject,
    updateProject,
    deleteProject,
    fetchStats,
    clearCurrent
  }
})
