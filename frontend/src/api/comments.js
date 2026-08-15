import request from './request'

export function generateSuggestions(projectId, data) {
  return request.post(`/projects/${projectId}/comment-suggestions/generate`, data || {})
}

export function listSuggestions(projectId, params) {
  return request.get(`/projects/${projectId}/comment-suggestions`, { params })
}

export function updateSuggestion(id, status) {
  return request.patch(`/comment-suggestions/${id}`, { status })
}

export function batchUpdateSuggestions(projectId, ids, status) {
  return request.post(`/projects/${projectId}/comment-suggestions/batch`, {
    ids: Array.isArray(ids) ? ids : [],
    status
  })
}

export function applySuggestions(projectId, execute = false) {
  return request.post(`/projects/${projectId}/comment-suggestions/apply`, { execute })
}

export function exportDictionary(projectId, format) {
  return request.get(`/projects/${projectId}/dictionary/export`, {
    params: { format },
    responseType: 'blob'
  })
}
