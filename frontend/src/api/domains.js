import request from './request'

export function analyzeDomains(projectId, data) {
  return request.post(`/projects/${projectId}/domains/analyze`, data || {})
}

export function getDomains(projectId) {
  return request.get(`/projects/${projectId}/domains`)
}
