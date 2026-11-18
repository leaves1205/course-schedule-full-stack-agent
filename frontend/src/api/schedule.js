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
