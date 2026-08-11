import request from './request'

export function getRelationships(projectId, params) {
  return request.get(`/projects/${projectId}/relationships`, { params })
}

export function updateRelationship(id, data) {
  return request.patch(`/relationships/${id}`, data)
}

export function createRelationship(projectId, data) {
  return request.post(`/projects/${projectId}/relationships`, data)
}

export function deleteRelationship(id) {
  return request.delete(`/relationships/${id}`)
}

export function confirmSuggestion(id) {
  return request.post(`/relationships/${id}/confirm`)
}

export function rejectSuggestion(id) {
  return request.post(`/relationships/${id}/reject`)
}

export function resetSuggestion(id) {
  return request.post(`/relationships/${id}/reset`)
}

export function batchConfirmSuggestions(projectId, ids) {
  return request.post(`/projects/${projectId}/relationships/batch-confirm`, {
    relationship_ids: Array.isArray(ids) ? ids : []
  })
}

export function batchRejectSuggestions(projectId, ids) {
  return request.post(`/projects/${projectId}/relationships/batch-reject`, {
    relationship_ids: Array.isArray(ids) ? ids : []
  })
}
