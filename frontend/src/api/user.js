import request from '@/utils/request'

/**
 * Get the current user.
 */
export function getUserInfo() {
  return request({
    url: '/api/user/me',
    method: 'get'
  })
}

/**
 * Update the current user profile.
 */
export function updateUserInfo(data) {
  return request({
    url: '/api/user/me',
    method: 'put',
    data
  })
}

/**
 * Change password
 */
export function updatePassword(data) {
  return request({
    url: '/api/user/password',
    method: 'put',
    data
  })
}

/**
 * List users with pagination and fuzzy search.
 */
export function getUserPageList(params) {
  return request({
    url: '/api/user/list',
    method: 'get',
    params
  })
}

/**
 * Add user
 */
export function createUserApi(data) {
  return request({
    url: '/api/user',
    method: 'post',
    data
  })
}

/**
 * Update user
 */
export function updateUserApi(userId, data) {
  return request({
    url: `/api/user/${userId}`,
    method: 'put',
    data
  })
}

/**
 * Delete user
 */
export function deleteUserApi(userId) {
  return request({
    url: `/api/user/${userId}`,
    method: 'delete'
  })
}
