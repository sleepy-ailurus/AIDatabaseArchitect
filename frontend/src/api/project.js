import request from './request'

export function createProject(data) {
  return request.post('/projects', data)
}

export function getProjects(params) {
  return request.get('/projects', { params })
}

export function getProject(id) {
  return request.get(`/projects/${id}`)
}

export function updateProject(id, data) {
  return request.patch(`/projects/${id}`, data)
}

export function deleteProject(id) {
  return request.delete(`/projects/${id}`)
}

export function getProjectStats() {
  return request.get('/projects/stats')
}
