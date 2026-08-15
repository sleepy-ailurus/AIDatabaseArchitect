import request from './request'

export function scanSensitive(projectId, data) {
  return request.post(`/projects/${projectId}/sensitive-scan`, data || {})
}

export function listSensitiveFields(projectId, params) {
  return request.get(`/projects/${projectId}/sensitive-fields`, { params })
}

export function updateSensitiveField(id, status) {
  return request.patch(`/sensitive-fields/${id}`, { status })
}

export function exportSensitiveReport(projectId) {
  return request.get(`/projects/${projectId}/sensitive-report`, { responseType: 'blob' })
}
