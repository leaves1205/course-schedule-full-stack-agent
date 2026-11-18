import request from '@/utils/request'

/** course schedule */
export function listSchedulesApi(params = {}) {
  return request({
    url: '/api/schedules',
    method: 'get',
    params
  })
}

export function createScheduleApi(data) {
  return request({
    url: '/api/schedules',
    method: 'post',
    data
  })
}

export function updateScheduleApi(id, data) {
  return request({
    url: `/api/schedules/${id}`,
    method: 'put',
    data
  })
}

export function deleteScheduleApi(id) {
  return request({
    url: `/api/schedules/${id}`,
    method: 'delete'
  })
}

export const generateSchedulesApi = (data) =>
  request({ url: '/api/schedules/generate', method: 'post', data })
export const listScheduleRulesApi = (params) =>
  request({ url: '/api/schedule-rules', method: 'get', params })
export const regenerateScheduleRuleApi = (id) =>
  request({ url: `/api/schedule-rules/${id}/generate`, method: 'post' })
export const restoreScheduleApi = (id) =>
  request({ url: `/api/schedules/${id}/restore`, method: 'post' })
