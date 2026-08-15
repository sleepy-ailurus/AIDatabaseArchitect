import request from './request'

export function previewImport(projectId, data) {
  return request.post(`/projects/${projectId}/schema/import-preview`, data)
}

export function importSchema(projectId, data) {
  return request.post(`/projects/${projectId}/schema/import`, data)
}
