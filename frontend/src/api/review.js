import request from './request'

export function createReview(projectId, data) {
  return request.post(`/projects/${projectId}/reviews`, data || {})
}

export function getLatestReview(projectId) {
  return request.get(`/projects/${projectId}/reviews/latest`)
}
