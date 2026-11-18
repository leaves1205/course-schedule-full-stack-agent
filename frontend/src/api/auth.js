import request from '@/utils/request'

/**
 * Sign-in request.
 */
export function loginApi(data) {
  return request({
    url: '/api/auth/login',
    method: 'post',
    data
  })
}

/**
 * Registration request.
 */
export function registerApi(data) {
  return request({
    url: '/api/auth/register',
    method: 'post',
    data
  })
}
