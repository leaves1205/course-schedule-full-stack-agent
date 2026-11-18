<template>
  <div class="sidebar" :class="{ collapsed }">
    <div class="brand-row">
      <RouterLink
        to="/manager/home"
        class="brand"
        aria-label="CourseFlow overview"
        @click="$emit('navigate')"
      >
        <span class="brand-mark" aria-hidden="true"
          ><el-icon><Reading /></el-icon
        ></span>
        <span v-if="!collapsed" class="brand-copy">CourseFlow</span>
      </RouterLink>
      <button
        v-if="mobile"
        class="close-navigation"
        aria-label="Close navigation"
        type="button"
        @click="$emit('close')"
      >
        <el-icon><Close /></el-icon>
      </button>
    </div>
    <nav class="navigation" aria-label="Workspace">
      <p class="nav-label">{{ collapsed ? '···' : 'Workspace' }}</p>
      <RouterLink
        v-for="item in workspaceLinks"
        :key="item.to"
        :to="item.to"
        class="nav-link"
        :title="collapsed ? item.label : undefined"
        :aria-label="item.label"
        @click="$emit('navigate')"
      >
        <el-icon aria-hidden="true"><component :is="item.icon" /></el-icon
        ><span v-if="!collapsed">{{ item.label }}</span>
      </RouterLink>
      <p class="nav-label account-label">{{ collapsed ? '···' : 'Account' }}</p>
      <RouterLink
        v-for="item in accountLinks"
        :key="item.to"
        :to="item.to"
        class="nav-link"
        :title="collapsed ? item.label : undefined"
        :aria-label="item.label"
        @click="$emit('navigate')"
      >
        <el-icon aria-hidden="true"><component :is="item.icon" /></el-icon
        ><span v-if="!collapsed">{{ item.label }}</span>
      </RouterLink>
    </nav>
    <div class="sidebar-footer">
      <el-icon aria-hidden="true"><User /></el-icon
      ><span v-if="!collapsed">{{
        isAdmin ? 'Administrator workspace' : 'Student workspace'
      }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import {
  Calendar,
  ChatDotRound,
  Close,
  Document,
  Grid,
  Lock,
  Notebook,
  Reading,
  User,
  UserFilled
} from '@element-plus/icons-vue'
import { useUser } from '@/utils/user'

defineProps({ collapsed: Boolean, mobile: Boolean })
defineEmits(['navigate', 'close'])
const { userInfo } = useUser()
const isAdmin = computed(() => userInfo.value?.role === 'admin')
const workspaceLinks = computed(() => [
  { to: '/manager/home', label: 'Overview', icon: Grid },
  ...(isAdmin.value
    ? [
        { to: '/manager/course', label: 'Courses', icon: Reading },
        { to: '/manager/semesters', label: 'Semesters', icon: Calendar },
        { to: '/manager/scheduleManage', label: 'Schedules', icon: Calendar },
        { to: '/manager/user', label: 'Users', icon: UserFilled },
        { to: '/manager/documents', label: 'Documents', icon: Document }
      ]
    : [
        { to: '/manager/schedule', label: 'My schedule', icon: Calendar },
        { to: '/manager/study-plan', label: 'Study plans', icon: Notebook }
      ]),
  { to: '/manager/chat', label: 'Course assistant', icon: ChatDotRound }
])
const accountLinks = [
  { to: '/manager/profile', label: 'My profile', icon: User },
  { to: '/manager/password', label: 'Account security', icon: Lock }
]
</script>

<style scoped>
.sidebar {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  overflow-x: hidden;
  background: #fff;
  border-right: 1px solid var(--workspace-border);
  color: #4b5563;
}
.brand-row {
  min-height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 0 24px;
  border-bottom: 1px solid var(--workspace-border);
}
.brand {
  display: flex;
  align-items: center;
  gap: 10px;
}
.brand-mark {
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border-radius: 5px;
  background: #1668dc;
  color: #fff;
  font-size: 20px;
  flex-shrink: 0;
}
.brand-copy {
  color: #182230;
  font-size: 18px;
  font-weight: 600;
  letter-spacing: -0.4px;
  white-space: nowrap;
}
.navigation {
  padding: 24px 12px;
}
.nav-label {
  color: #697586;
  font-size: 12px;
  font-weight: 500;
  margin: 0 12px 10px;
}
.account-label {
  border-top: 1px solid #edf0f3;
  padding-top: 24px;
  margin-top: 24px;
}
.nav-link {
  position: relative;
  height: 40px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 12px;
  margin: 4px 0;
  border-radius: 5px;
  font-size: 14px;
  white-space: nowrap;
}
.nav-link .el-icon {
  font-size: 18px;
  color: #6b7787;
  flex-shrink: 0;
}
.nav-link:hover {
  color: #155bd4;
  background: #f5f7fa;
}
.nav-link.router-link-exact-active {
  color: #155bd4;
  background: #edf4ff;
  font-weight: 500;
}
.nav-link.router-link-exact-active .el-icon {
  color: #1668dc;
}
.nav-link.router-link-exact-active::before {
  content: '';
  position: absolute;
  left: -12px;
  width: 3px;
  height: 24px;
  border-radius: 0 2px 2px 0;
  background: #1668dc;
}
.sidebar-footer {
  margin-top: auto;
  border-top: 1px solid var(--workspace-border);
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 18px 24px;
  color: #697586;
  font-size: 12px;
  white-space: nowrap;
}
.sidebar-footer .el-icon {
  font-size: 16px;
  flex-shrink: 0;
}
.collapsed .brand-row {
  padding-inline: 18px;
}
.collapsed .navigation {
  padding-inline: 8px;
}
.collapsed .nav-label {
  text-align: center;
  margin-inline: 0;
}
.collapsed .nav-link {
  justify-content: center;
  padding-inline: 0;
}
.collapsed .nav-link.router-link-exact-active::before {
  left: -8px;
}
.collapsed .sidebar-footer {
  justify-content: center;
  padding-inline: 0;
}
.close-navigation {
  display: grid;
  place-items: center;
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  background: transparent;
  border: 0;
  border-radius: 4px;
  color: #697586;
  font-size: 18px;
  cursor: pointer;
}
.close-navigation:hover {
  background: #f0f3f7;
}
</style>
