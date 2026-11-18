import { getToken } from '@/utils/auth'
import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  scrollBehavior(to, from, savedPosition) {
    return savedPosition || { top: 0 }
  },
  routes: [
    { path: '/', redirect: '/manager/home' },
    {
      path: '/manager',
      name: 'Layout',
      component: () => import('@/layouts/Layout.vue'),
      children: [
        { path: 'home', name: 'Home', component: () => import('@/views/Home.vue') },
        { path: 'profile', name: 'Profile', component: () => import('@/views/Profile.vue') },
        { path: 'password', name: 'Password', component: () => import('@/views/Password.vue') },
        { path: 'user', name: 'User', component: () => import('@/views/User.vue') },
        { path: 'course', name: 'Course', component: () => import('@/views/Course.vue') },
        { path: 'semesters', name: 'Semesters', component: () => import('@/views/Semesters.vue') },
        { path: 'schedule', name: 'Schedule', component: () => import('@/views/Schedule.vue') },
        {
          path: 'scheduleManage',
          name: 'ScheduleManage',
          component: () => import('@/views/ScheduleManage.vue')
        },
        { path: 'study-plan', name: 'StudyPlan', component: () => import('@/views/studyPlan.vue') },
        { path: 'chat', name: 'Chat', component: () => import('@/views/Chat.vue') },
        { path: 'documents', name: 'Documents', component: () => import('@/views/Documents.vue') }
      ]
    },
    { path: '/login', name: 'Login', component: () => import('@/views/Login.vue') },
    { path: '/register', name: 'Register', component: () => import('@/views/Register.vue') }
  ]
})

// Route guard: validate the token.
router.beforeEach((to, from) => {
  const token = getToken()

  if (to.path === '/login' || to.path === '/register') {
    return true
  } else {
    return token ? true : '/login'
  }
})

export default router
