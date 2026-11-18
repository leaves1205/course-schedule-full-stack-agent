<template>
  <div>
    <el-container style="min-height: 100vh">
      <el-header
        style="
          display: flex;
          align-items: center;
          border-bottom: 1px solid #ddd;
          background-color: #fff;
        "
      >
        <div
          style="flex: 1; display: flex; align-items: center; font-size: 24px; font-weight: bold"
        >
          <img style="width: 40px" src="@/assets/imgs/logo.png" alt="" />
          <div style="margin-left: 5px">Intelligent System</div>
        </div>
        <div>
          <el-dropdown @command="handleCommand">
            <div style="display: flex; align-items: center; cursor: pointer">
              <img :src="userInfo?.avatar" alt="" style="width: 30px; border-radius: 50%" />
              <div style="margin-left: 3px">{{ userInfo?.name }}</div>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">Profile</el-dropdown-item>
                <el-dropdown-item command="password">Change password</el-dropdown-item>
                <el-dropdown-item divided command="logout">Sign out</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      <el-container>
        <el-aside width="220px">
          <el-menu
            router
            :default-active="router.currentRoute.value.path"
            style="height: 100%"
            default-active="/manager/home"
          >
            <el-menu-item index="/manager/home">
              <el-icon><icon-menu /></el-icon>
              <span>Home</span>
            </el-menu-item>
            <el-menu-item index="/manager/course" v-if="userInfo?.role === 'admin'">
              <el-icon><Reading /></el-icon>
              <span>Course management</span>
            </el-menu-item>
            <el-menu-item index="/manager/user" v-if="userInfo?.role === 'admin'">
              <el-icon><User /></el-icon>
              <span>User management</span>
            </el-menu-item>
            <el-menu-item v-if="userInfo?.role !== 'admin'" index="/manager/schedule">
              <el-icon><Calendar /></el-icon>
              My schedule
            </el-menu-item>
            <el-menu-item index="/manager/scheduleManage" v-if="userInfo?.role === 'admin'">
              <el-icon><Calendar /></el-icon>
              Schedule management
            </el-menu-item>
            <el-menu-item v-if="userInfo?.role !== 'admin'" index="/manager/study-plan">
              <el-icon><Notebook /></el-icon>
              Study plans
            </el-menu-item>
            <el-menu-item index="/manager/chat">
              <el-icon><ChatDotRound /></el-icon>
              Course assistant
            </el-menu-item>
          </el-menu>
        </el-aside>
        <el-main>
          <router-view />
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<script setup>
import router from '@/router'
import { logout } from '@/utils/auth'
import { useUser } from '@/utils/user'
import {
  Menu as IconMenu,
  User,
  Reading,
  Calendar,
  Notebook,
  ChatDotRound
} from '@element-plus/icons-vue'

const { userInfo } = useUser()

const handleCommand = (command) => {
  if (command === 'profile') {
    router.push('/manager/profile')
  } else if (command === 'password') {
    router.push('/manager/password')
  } else if (command === 'logout') {
    logout()
    router.push('/login')
  }
}
</script>
