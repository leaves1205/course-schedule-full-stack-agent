<template>
  <div class="app-shell" :class="{ 'sidebar-collapsed': collapsed }">
    <a class="skip-link" href="#main-content">Skip to content</a>
    <aside class="desktop-sidebar" aria-label="Main navigation">
      <AppSidebar :collapsed="collapsed" />
    </aside>
    <el-drawer
      v-model="mobileOpen"
      direction="ltr"
      size="280px"
      :with-header="false"
      class="navigation-drawer"
      aria-label="Main navigation"
    >
      <AppSidebar mobile @navigate="mobileOpen = false" @close="mobileOpen = false" />
    </el-drawer>
    <div class="workspace">
      <header class="workspace-header">
        <div class="header-start">
          <button
            class="icon-button desktop-toggle"
            type="button"
            :aria-label="collapsed ? 'Expand sidebar' : 'Collapse sidebar'"
            :aria-expanded="!collapsed"
            @click="collapsed = !collapsed"
          >
            <el-icon><Expand v-if="collapsed" /><Fold v-else /></el-icon>
          </button>
          <button
            class="icon-button mobile-toggle"
            type="button"
            aria-label="Open navigation"
            :aria-expanded="mobileOpen"
            @click="mobileOpen = true"
          >
            <el-icon><Menu /></el-icon>
          </button>
          <div class="breadcrumb">
            <span>Workspace</span><span aria-hidden="true">/</span><strong>{{ page.title }}</strong>
          </div>
        </div>
        <div class="header-actions">
          <span class="header-date"
            ><el-icon><Calendar /></el-icon>{{ dateLabel }}</span
          >
          <span class="header-divider" aria-hidden="true"></span>
          <el-dropdown trigger="click" @command="handleCommand">
            <button class="account-trigger" type="button" aria-label="Account menu">
              <el-avatar :size="34" :src="userInfo?.avatar || undefined">{{ initial }}</el-avatar>
              <span class="account-copy"
                ><strong>{{ displayName }}</strong
                ><span>{{ isAdmin ? 'Administrator' : 'Student' }}</span></span
              >
              <el-icon class="account-chevron"><ArrowDown /></el-icon>
            </button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile" :icon="User">Profile</el-dropdown-item>
                <el-dropdown-item command="password" :icon="Lock">Change password</el-dropdown-item>
                <el-dropdown-item command="logout" :icon="SwitchButton" divided
                  >Sign out</el-dropdown-item
                >
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>
      <main id="main-content" class="workspace-main" tabindex="-1">
        <div class="page-heading">
          <div>
            <h1>{{ page.title }}</h1>
            <p class="page-description">{{ page.description }}</p>
          </div>
        </div>
        <RouterView />
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ArrowDown,
  Calendar,
  Expand,
  Fold,
  Lock,
  Menu,
  SwitchButton,
  User
} from '@element-plus/icons-vue'
import AppSidebar from './AppSidebar.vue'
import { logout } from '@/utils/auth'
import { useUser } from '@/utils/user'

const router = useRouter()
const route = useRoute()
const { userInfo } = useUser()
const collapsed = ref(false)
const mobileOpen = ref(false)
const now = ref(new Date())
let clock
let desktopMedia
const isAdmin = computed(() => userInfo.value?.role === 'admin')
const displayName = computed(() => userInfo.value?.name || userInfo.value?.username || 'Student')
const initial = computed(() => displayName.value.slice(0, 1).toUpperCase())
const dateLabel = computed(() =>
  now.value.toLocaleDateString('en', { weekday: 'short', month: 'short', day: 'numeric' })
)
const pages = {
  '/manager/home': {
    title: 'Overview',
    description: 'Your courses, schedules, and study plans.'
  },
  '/manager/schedule': {
    title: 'My schedule',
    description: 'View class dates, periods, and locations.'
  },
  '/manager/study-plan': {
    title: 'Study plans',
    description: 'Create and review your study plans.'
  },
  '/manager/chat': {
    title: 'Course assistant',
    description: 'Ask questions about your courses and schedule.'
  },
  '/manager/course': {
    title: 'Courses',
    description: 'Manage your course catalog.'
  },
  '/manager/semesters': {
    title: 'Semesters',
    description: 'Set the first teaching Monday and number of weeks for each semester.'
  },
  '/manager/documents': {
    title: 'Documents',
    description: 'Upload and manage course materials.'
  },
  '/manager/user': { title: 'Users', description: 'Manage student and administrator accounts.' },
  '/manager/scheduleManage': {
    title: 'Schedules',
    description: 'Set weekly rules once, generate class sessions, and manage single-class changes.'
  },
  '/manager/profile': {
    title: 'My profile',
    description: 'Manage your account details.'
  },
  '/manager/password': {
    title: 'Account security',
    description: 'Update your account password.'
  }
}
const page = computed(() => pages[route.path] || pages['/manager/home'])
watch(
  () => route.path,
  () => {
    mobileOpen.value = false
  }
)
function closeMobileOnDesktop(event) {
  if (event.matches) mobileOpen.value = false
}
onMounted(() => {
  clock = window.setInterval(() => {
    now.value = new Date()
  }, 60000)
  desktopMedia = window.matchMedia('(min-width: 901px)')
  desktopMedia.addEventListener('change', closeMobileOnDesktop)
})
onUnmounted(() => {
  window.clearInterval(clock)
  desktopMedia?.removeEventListener('change', closeMobileOnDesktop)
})
function handleCommand(command) {
  if (command === 'logout') {
    logout()
    router.push('/login')
  } else if (command === 'profile' || command === 'password') {
    router.push(`/manager/${command}`)
  }
}
</script>

<style scoped>
.app-shell {
  --sidebar-width: 224px;
  min-height: 100vh;
}
.sidebar-collapsed {
  --sidebar-width: 64px;
}
.desktop-sidebar {
  position: fixed;
  inset: 0 auto 0 0;
  width: var(--sidebar-width);
  z-index: 30;
}
.workspace {
  min-width: 0;
  margin-left: var(--sidebar-width);
}
.workspace-header {
  height: 64px;
  padding: 0 32px;
  border-bottom: 1px solid var(--workspace-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  background: #fff;
}
.header-start,
.header-actions,
.header-date,
.breadcrumb {
  display: flex;
  align-items: center;
}
.header-start {
  gap: 16px;
  min-width: 0;
}
.breadcrumb {
  gap: 12px;
  font-size: 13px;
  color: var(--workspace-muted);
  white-space: nowrap;
}
.breadcrumb strong {
  font-weight: 400;
  color: var(--workspace-ink);
}
.header-actions {
  gap: 24px;
}
.header-date {
  gap: 8px;
  font-size: 13px;
  color: var(--workspace-muted);
  white-space: nowrap;
}
.header-date .el-icon {
  font-size: 16px;
}
.header-divider {
  width: 1px;
  height: 24px;
  background: var(--workspace-border);
}
.icon-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  flex-shrink: 0;
  border: 0;
  border-radius: 4px;
  background: transparent;
  color: #57606a;
  cursor: pointer;
  font-size: 18px;
}
.icon-button:hover {
  background: #f0f3f7;
  color: var(--el-color-primary);
}
.mobile-toggle {
  display: none;
}
.account-trigger {
  border: 0;
  padding: 4px 0;
  background: transparent;
  display: flex;
  align-items: center;
  gap: 10px;
  text-align: left;
  cursor: pointer;
  color: var(--workspace-ink);
}
.account-trigger .el-avatar {
  background: #eaf2ff;
  color: #155bd4;
  font-weight: 600;
}
.account-copy {
  display: grid;
  gap: 2px;
  max-width: 145px;
}
.account-copy strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
  font-weight: 500;
}
.account-copy > span {
  color: var(--workspace-muted);
  font-size: 12px;
}
.account-chevron {
  margin-left: 4px;
  font-size: 12px;
  color: var(--workspace-muted);
}
.workspace-main {
  max-width: 1600px;
  margin: 0 auto;
  padding: 28px 32px 40px;
  min-width: 0;
  outline: none;
}
.page-heading {
  margin-bottom: 24px;
}
h1 {
  font-size: 24px;
  font-weight: 600;
  line-height: 1.35;
  letter-spacing: -0.4px;
}
.page-description {
  color: var(--workspace-muted);
  font-size: 14px;
  line-height: 1.6;
  margin-top: 6px;
}
.skip-link {
  position: fixed;
  top: -100px;
  left: 16px;
  z-index: 3000;
  padding: 12px 20px;
  border-radius: 4px;
  background: white;
  color: var(--workspace-ink);
}
.skip-link:focus {
  top: 12px;
}
@media (max-width: 1100px) {
  .workspace-header {
    padding-inline: 24px;
  }
  .workspace-main {
    padding-inline: 24px;
  }
  .header-date,
  .header-divider {
    display: none;
  }
}
@media (max-width: 900px) {
  .desktop-sidebar,
  .desktop-toggle {
    display: none;
  }
  .mobile-toggle {
    display: inline-flex;
  }
  .workspace {
    margin-left: 0;
  }
}
@media (max-width: 600px) {
  .workspace-header {
    height: 56px;
    padding-inline: 16px;
  }
  .header-start {
    gap: 8px;
  }
  .breadcrumb > span:first-child,
  .breadcrumb > span:nth-child(2),
  .account-copy,
  .account-chevron {
    display: none;
  }
  .workspace-main {
    padding: 20px 16px 32px;
  }
  .page-heading {
    margin-bottom: 20px;
  }
  h1 {
    font-size: 22px;
  }
  .page-description {
    font-size: 13px;
  }
}
</style>
