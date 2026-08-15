import request from './request'

export function analyzeLineage(projectId, sqlText) {
  return request.post(`/projects/${projectId}/lineage/analyze`, { sql_text: sqlText })
}
