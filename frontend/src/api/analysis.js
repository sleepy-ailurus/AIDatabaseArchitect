import request from './request'

export function createAnalysisTask(projectId, data) {
  return request.post(`/projects/${projectId}/analysis-tasks`, data || {})
}

export function getAnalysisTask(taskId) {
  return request.get(`/analysis-tasks/${taskId}`)
}

export function getAnalysisList(projectId, params) {
  return request.get(`/projects/${projectId}/analysis-tasks`, { params })
}

export function getLatestAnalysis(projectId) {
  return request.get(`/projects/${projectId}/analysis-tasks/latest`)
}

export function cancelAnalysisTask(taskId) {
  return request.post(`/analysis-tasks/${taskId}/cancel`)
}
