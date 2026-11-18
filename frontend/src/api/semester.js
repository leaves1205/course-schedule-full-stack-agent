import request from '@/utils/request'

export const listSemestersApi = () => request({ url: '/api/semesters', method: 'get' })
export const createSemesterApi = (data) => request({ url: '/api/semesters', method: 'post', data })
export const updateSemesterApi = (id, data) =>
  request({ url: `/api/semesters/${id}`, method: 'put', data })
export const deleteSemesterApi = (id) => request({ url: `/api/semesters/${id}`, method: 'delete' })
