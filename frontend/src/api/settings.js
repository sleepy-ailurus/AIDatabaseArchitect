import request from './request'

export function getUserSettings() {
  return request.get('/user-settings')
}

export function updateUserSettings(data) {
  return request.patch('/user-settings', data)
}
