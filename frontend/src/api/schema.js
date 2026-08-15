import request from './request'

export function syncSchema(projectId) {
  return request.post(`/projects/${projectId}/schema/sync`)
}

export function getSnapshots(projectId) {
  return request.get(`/projects/${projectId}/schema/snapshots`)
}

export function getSchemaDiff(projectId, params) {
  return request.get(`/projects/${projectId}/schema/diff`, { params })
}

export function getTables(projectId, params) {
  return request.get(`/projects/${projectId}/schema/tables`, { params })
}

export function getTableDetail(projectId, tableName) {
  return request.get(`/projects/${projectId}/schema/tables/${tableName}`)
}
