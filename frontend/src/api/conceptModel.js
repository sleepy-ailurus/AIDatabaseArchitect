import request from './request'

export function getConceptModel(projectId) {
  return request.get(`/projects/${projectId}/concept-model`)
}

export function convertConceptModel(projectId, data) {
  return request.post(`/projects/${projectId}/concept-model/convert`, data || {})
}

export function saveConceptModel(projectId, data) {
  return request.put(`/projects/${projectId}/concept-model`, data)
}

export function saveConceptPositions(projectId, positions, viewport) {
  return request.post(`/projects/${projectId}/concept-model/positions`, {
    positions: positions || {},
    viewport: viewport || null
  })
}
