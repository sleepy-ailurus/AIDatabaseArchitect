import axios from 'axios'
import { ElMessage } from 'element-plus'

const request = axios.create({
  baseURL: '/api',
  timeout: 120000,
  headers: {
    'Content-Type': 'application/json'
  }
})

request.interceptors.request.use(
  (config) => {
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

request.interceptors.response.use(
  (response) => {
    const res = response.data
    if (res && typeof res === 'object' && 'code' in res) {
      if (res.code === 0 || res.code === 200) {
        return res.data !== undefined ? res.data : res
      }
      ElMessage.error(res.message || '请求失败')
      return Promise.reject(new Error(res.message || '请求失败'))
    }
    return res
  },
  (error) => {
    let message = '网络异常，请稍后重试'
    if (error.response) {
      const status = error.response.status
      const data = error.response.data
      if (data && data.message) {
        message = data.message
      } else {
        const statusMap = {
          400: '请求参数错误',
          401: '未授权，请重新登录',
          403: '拒绝访问',
          404: '请求资源不存在',
          500: '服务器内部错误',
          502: '网关错误',
          503: '服务不可用',
          504: '网关超时'
        }
        message = statusMap[status] || `请求错误 (${status})`
      }
    } else if (error.code === 'ECONNABORTED') {
      message = '请求超时，请检查网络或稍后重试'
    } else if (error.message && error.message.includes('Network')) {
      message = '网络连接失败，请检查后端服务是否启动'
    }
    ElMessage.error(message)
    return Promise.reject(error)
  }
)

export default request
