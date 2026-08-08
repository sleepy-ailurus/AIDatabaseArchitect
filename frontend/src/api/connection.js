import request from './request'

export function testConnection(data) {
  return request.post('/database-connections/test', data)
}

export function saveConnection(data) {
  return request.post('/database-connections', data)
}

export function getConnection(projectId) {
  return request.get(`/projects/${projectId}/database-connection`)
}

export function deleteConnection(connectionId) {
  return request.delete(`/database-connections/${connectionId}`)
}
