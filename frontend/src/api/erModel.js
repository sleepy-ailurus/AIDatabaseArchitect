import request from './request'

export function getERModel(projectId) {
  return request.get(`/projects/${projectId}/er-models`)
}

export function saveERModel(projectId, data) {
  return request.put(`/projects/${projectId}/er-models`, data)
}

export function saveVersion(projectId, data) {
  return request.post(`/projects/${projectId}/er-models/versions`, data)
}

export function getVersions(projectId) {
  return request.get(`/projects/${projectId}/er-models/versions`)
}

export function getVersion(versionId) {
  return request.get(`/er-models/versions/${versionId}`)
}

export function deleteVersion(versionId) {
  return request.delete(`/er-models/versions/${versionId}`)
}
