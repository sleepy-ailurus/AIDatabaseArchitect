import request from './request'

export function generateTestData(projectId, data) {
  return request.post(`/projects/${projectId}/test-data/generate`, data || {})
}
