import axios from 'axios'
import { getToken, logout } from './auth'
import { settleFailedRequest } from './apiError'
import { ElMessage } from 'element-plus'
import router from '@/router'

const service = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '',
  timeout: 30000 //30s
})

// Configure the request interceptor.
service.interceptors.request.use(
  (config) => {
    const token = getToken()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (err) => Promise.reject(err)
)

// Configure the response interceptor.
service.interceptors.response.use(
  (res) => {
    const data = res.data
    if (data.code !== 200) {
      ElMessage.error(data.message || 'Request failed')
      if (data.code === 401) {
        logout()
        router.push('/login')
        return Promise.reject(data)
      }
    }
    return data
  },
  (err) => {
    const outcome = settleFailedRequest(err, {
      notify: (message) => ElMessage.error(message),
      onSessionExpired: () => {
        logout()
        router.push('/login')
      }
    })
    return 'resolve' in outcome ? outcome.resolve : Promise.reject(outcome.reject)
  }
)

export default service
