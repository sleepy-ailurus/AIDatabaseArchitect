import request from './request'

export function getLLMConfigs() {
  return request.get('/llm-configs')
}

export function getLLMConfig(id) {
  return request.get(`/llm-configs/${id}`)
}

export function saveLLMConfig(data) {
  return request.post('/llm-configs', data)
}

export function updateLLMConfig(id, data) {
  return request.patch(`/llm-configs/${id}`, data)
}

export function deleteLLMConfig(id) {
  return request.delete(`/llm-configs/${id}`)
}

export function testLLMConfig(data) {
  return request.post('/llm-configs/test', data)
}
