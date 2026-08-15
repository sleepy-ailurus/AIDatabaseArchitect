import request from './request'

export function exportDesignDoc(projectId, format, data) {
  return request.post(`/projects/${projectId}/design-doc/export`, data || {}, {
    params: { format },
    responseType: 'blob'
  })
}
