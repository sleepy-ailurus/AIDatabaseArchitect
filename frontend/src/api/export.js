import request from './request'

export function exportDocument(projectId, data) {
  return request.post(`/projects/${projectId}/exports`, data)
}

export function getExport(projectId, params) {
  return request.get(`/projects/${projectId}/exports`, { params })
}

export function getExportDetail(exportId) {
  return request.get(`/exports/${exportId}`)
}

export function getExportDownloadUrl(exportId) {
  return `/api/exports/${exportId}/download`
}

export function previewDocument(projectId, data) {
  return request.post(`/projects/${projectId}/exports/preview`, data)
}
