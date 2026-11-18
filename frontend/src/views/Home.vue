<template>
  <div class="overview">
    <section class="stats-grid" aria-label="Workspace statistics" :aria-busy="loading">
      <RouterLink v-for="stat in stats" :key="stat.label" :to="stat.to" class="stat-card">
        <div class="stat-heading">
          <span>{{ stat.label }}</span
          ><el-icon aria-hidden="true"><component :is="stat.icon" /></el-icon>
        </div>
        <strong>{{ loading ? '…' : (stat.value ?? '—') }}</strong>
        <p v-if="stat.value === null && !loading">Currently unavailable</p>
      </RouterLink>
    </section>

    <div class="overview-grid">
      <section class="dashboard-panel schedule-panel" :aria-busy="loading">
        <div class="panel-heading">
          <h2>Today's schedule</h2>
          <RouterLink :to="schedulePath" class="text-link"
            >View all<el-icon><ArrowRight /></el-icon
          ></RouterLink>
        </div>
        <div class="schedule-date">
          <el-icon><Calendar /></el-icon><span>{{ dateLabel }}</span
          ><span class="date-count" v-if="!loading && scheduleTotal !== null"
            >{{ scheduleTotal }}
            {{ isAdmin ? 'entries' : scheduleTotal === 1 ? 'class' : 'classes' }}</span
          >
        </div>
        <div v-if="scheduleError && !loading" class="panel-state" role="status">
          <p>Unable to load the schedule.</p>
          <el-button @click="loadOverview">Try again</el-button>
        </div>
        <el-table v-else :data="schedules" v-loading="loading" class="schedule-table">
          <el-table-column prop="period" label="Period" width="90" />
          <el-table-column
            prop="course_name"
            label="Course"
            min-width="180"
            show-overflow-tooltip
          />
          <el-table-column v-if="isAdmin" label="Student" min-width="130" show-overflow-tooltip
            ><template #default="{ row }">{{
              row.user_name || row.username || '—'
            }}</template></el-table-column
          >
          <el-table-column label="Location" min-width="140" show-overflow-tooltip
            ><template #default="{ row }">{{ row.location || '—' }}</template></el-table-column
          >
          <template #empty
            ><div class="table-empty">
              <el-icon aria-hidden="true"><Calendar /></el-icon>
              <p>{{ loading ? 'Loading schedules…' : 'No classes scheduled today.' }}</p>
              <RouterLink v-if="!loading" :to="schedulePath" class="text-link">{{
                isAdmin ? 'Manage schedules' : 'View full schedule'
              }}</RouterLink>
            </div></template
          >
        </el-table>
        <div class="panel-footer">
          <span v-if="scheduleTotal > schedules.length && !loading"
            >Showing {{ schedules.length }} of {{ scheduleTotal }} entries</span
          ><span v-else>Class periods follow the saved schedule.</span>
        </div>
      </section>

      <section class="dashboard-panel recent-panel" :aria-busy="loading">
        <div class="panel-heading">
          <h2>{{ isAdmin ? 'Course catalog' : 'Recent study plans' }}</h2>
          <RouterLink :to="isAdmin ? '/manager/course' : '/manager/study-plan'" class="text-link"
            >View all<el-icon><ArrowRight /></el-icon
          ></RouterLink>
        </div>
        <div v-if="loading" class="recent-loading"><el-skeleton :rows="4" animated /></div>
        <div v-else-if="recentUnavailable" class="panel-state" role="status">
          <p>{{ isAdmin ? 'Course data is unavailable.' : 'Study plans are unavailable.' }}</p>
          <el-button @click="loadOverview">Try again</el-button>
        </div>
        <ul v-else-if="recentItems.length" class="recent-list">
          <li v-for="item in recentItems" :key="item.id">
            <RouterLink
              :to="isAdmin ? '/manager/course' : '/manager/study-plan'"
              class="recent-item"
              ><span class="recent-icon"
                ><el-icon><Reading v-if="isAdmin" /><Notebook v-else /></el-icon></span
              ><span class="recent-copy"
                ><strong>{{ isAdmin ? item.name : previewText(item.content) }}</strong
                ><span>{{
                  isAdmin ? item.code || 'No course code' : formatDate(item.create_time)
                }}</span></span
              ><el-icon class="recent-arrow"><ArrowRight /></el-icon
            ></RouterLink>
          </li>
        </ul>
        <div v-else class="panel-state">
          <p>{{ isAdmin ? 'No courses added yet.' : 'No study plans saved yet.' }}</p>
          <RouterLink :to="isAdmin ? '/manager/course' : '/manager/study-plan'" class="text-link">{{
            isAdmin ? 'Manage courses' : 'Create a study plan'
          }}</RouterLink>
        </div>
      </section>
    </div>

    <section class="dashboard-panel">
      <div class="panel-heading"><h2>Quick links</h2></div>
      <div class="quick-links">
        <RouterLink
          v-for="action in quickActions"
          :key="action.to"
          :to="action.to"
          class="quick-link"
          ><el-icon><component :is="action.icon" /></el-icon><span>{{ action.label }}</span
          ><el-icon class="quick-arrow"><ArrowRight /></el-icon
        ></RouterLink>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import {
  ArrowRight,
  Calendar,
  ChatDotRound,
  Document,
  Notebook,
  Reading,
  User,
  UserFilled
} from '@element-plus/icons-vue'
import { listSchedulesApi } from '@/api/schedule'
import { listStudyPlans } from '@/api/studyPlan'
import { listCoursesApi } from '@/api/course'
import { getUserPageList } from '@/api/user'
import { useUser } from '@/utils/user'

const { userInfo } = useUser()
const isAdmin = computed(() => userInfo.value?.role === 'admin')
const today = ref(new Date())
const dateLabel = computed(() =>
  today.value.toLocaleDateString('en', {
    weekday: 'long',
    month: 'short',
    day: 'numeric',
    year: 'numeric'
  })
)
const schedulePath = computed(() =>
  isAdmin.value ? '/manager/scheduleManage' : '/manager/schedule'
)
const loading = ref(true)
const scheduleError = ref(false)
const schedules = ref([])
const scheduleTotal = ref(null)
const secondaryTotal = ref(null)
const tertiaryTotal = ref(null)
const recentItems = ref([])
const recentUnavailable = ref(false)
const stats = computed(() => [
  {
    label: isAdmin.value ? "Today's sessions" : "Today's classes",
    value: scheduleTotal.value,
    icon: Calendar,
    to: schedulePath.value
  },
  {
    label: isAdmin.value ? 'Courses' : 'Scheduled classes',
    value: secondaryTotal.value,
    icon: Reading,
    to: isAdmin.value ? '/manager/course' : schedulePath.value
  },
  {
    label: isAdmin.value ? 'Accounts' : 'Study plans',
    value: tertiaryTotal.value,
    icon: isAdmin.value ? UserFilled : Notebook,
    to: isAdmin.value ? '/manager/user' : '/manager/study-plan'
  }
])
const quickActions = computed(() => [
  ...(isAdmin.value
    ? [
        { label: 'Manage users', to: '/manager/user', icon: UserFilled },
        { label: 'Course documents', to: '/manager/documents', icon: Document }
      ]
    : [
        { label: 'My schedule', to: '/manager/schedule', icon: Calendar },
        { label: 'Study plans', to: '/manager/study-plan', icon: Notebook }
      ]),
  { label: 'Course assistant', to: '/manager/chat', icon: ChatDotRound },
  { label: 'My profile', to: '/manager/profile', icon: User }
])
function previewText(value) {
  return (
    String(value || '')
      .replace(/[#*_`>]/g, '')
      .replace(/\s+/g, ' ')
      .trim() || 'Untitled study plan'
  )
}
function formatDate(value) {
  return value ? String(value).replace('T', ' ').slice(0, 16) : 'Date unavailable'
}
function successfulData(result) {
  return result.status === 'fulfilled' && result.value.code === 200 ? result.value.data : null
}
async function loadOverview() {
  loading.value = true
  today.value = new Date()
  const date = `${today.value.getFullYear()}-${String(today.value.getMonth() + 1).padStart(2, '0')}-${String(today.value.getDate()).padStart(2, '0')}`
  const results = await Promise.allSettled([
    listSchedulesApi({ date, page: 1, page_size: 5 }),
    isAdmin.value ? listCoursesApi() : listSchedulesApi({ page: 1, page_size: 1 }),
    isAdmin.value
      ? getUserPageList({ page: 1, page_size: 1 })
      : listStudyPlans({ page: 1, page_size: 3 })
  ])
  const daily = successfulData(results[0])
  const secondary = successfulData(results[1])
  const tertiary = successfulData(results[2])
  scheduleError.value = !daily
  schedules.value = daily?.list || []
  scheduleTotal.value = daily?.total ?? null
  secondaryTotal.value = isAdmin.value
    ? Array.isArray(secondary)
      ? secondary.length
      : null
    : (secondary?.total ?? null)
  tertiaryTotal.value = tertiary?.total ?? null
  recentUnavailable.value = isAdmin.value ? !Array.isArray(secondary) : !tertiary
  recentItems.value = (
    isAdmin.value ? (Array.isArray(secondary) ? secondary : []) : tertiary?.list || []
  ).slice(0, 3)
  loading.value = false
}
onMounted(loadOverview)
</script>

<style scoped>
.overview {
  display: grid;
  gap: 24px;
}
.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 24px;
}
.stat-card {
  padding: 20px 24px;
  background: #fff;
  border: 1px solid var(--workspace-border);
  border-radius: 6px;
}
.stat-card:hover {
  border-color: #91baff;
}
.stat-heading {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  color: #4b5563;
  font-size: 14px;
}
.stat-heading .el-icon {
  font-size: 19px;
  color: #6483ab;
  flex-shrink: 0;
}
.stat-card > strong {
  display: block;
  font-size: 30px;
  font-weight: 600;
  line-height: 1.25;
  margin-top: 12px;
  font-variant-numeric: tabular-nums;
}
.stat-card > p {
  margin-top: 8px;
  color: var(--workspace-muted);
  font-size: 12px;
  line-height: 1.6;
}
.overview-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.8fr) minmax(300px, 1fr);
  gap: 24px;
  align-items: stretch;
}
.dashboard-panel {
  background: #fff;
  border: 1px solid var(--workspace-border);
  border-radius: 6px;
  min-width: 0;
  overflow: hidden;
}
.panel-heading {
  min-height: 60px;
  padding: 16px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  border-bottom: 1px solid var(--workspace-border);
}
.panel-heading h2 {
  font-size: 15px;
  line-height: 1.5;
  font-weight: 600;
}
.text-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--el-color-primary);
  flex-shrink: 0;
}
.text-link:hover {
  text-decoration: underline;
}
.text-link .el-icon {
  font-size: 12px;
}
.schedule-date {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 16px 24px;
  font-size: 13px;
  color: #4b5563;
}
.schedule-date > .el-icon {
  font-size: 16px;
  color: #697586;
}
.date-count {
  margin-left: auto;
  font-size: 12px;
  color: #697586;
}
.schedule-table {
  width: calc(100% - 48px);
  margin-inline: 24px;
}
.schedule-table :deep(.el-table__empty-text) {
  width: 100%;
  padding-inline: 12px;
}
.table-empty {
  min-height: 210px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 12px;
  line-height: 1.5;
}
.table-empty > .el-icon {
  font-size: 28px;
  color: #b7c3d4;
}
.table-empty p {
  font-size: 13px;
  color: #697586;
}
.panel-footer {
  display: flex;
  align-items: center;
  min-height: 48px;
  padding: 12px 24px;
  font-size: 12px;
  color: #697586;
}
.panel-state {
  min-height: 294px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  padding: 24px;
  gap: 16px;
  text-align: center;
  color: #697586;
  font-size: 13px;
}
.recent-loading {
  padding: 28px 24px;
}
.recent-list {
  padding: 4px 24px;
}
.recent-list li + li {
  border-top: 1px solid #edf0f4;
}
.recent-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 20px 0;
}
.recent-icon {
  display: grid;
  place-items: center;
  background: #f2f6fc;
  color: #5a7ca9;
  width: 32px;
  height: 36px;
  border-radius: 4px;
  font-size: 18px;
  flex-shrink: 0;
}
.recent-copy {
  min-width: 0;
}
.recent-copy strong {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  overflow-wrap: anywhere;
  font-weight: 400;
  font-size: 14px;
  line-height: 1.6;
}
.recent-copy > span {
  display: block;
  margin-top: 6px;
  font-size: 12px;
  color: #697586;
}
.recent-arrow {
  margin-left: auto;
  margin-top: 10px;
  color: #8d98a7;
  font-size: 12px;
  flex-shrink: 0;
}
.recent-item:hover strong {
  color: var(--el-color-primary);
}
.quick-links {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  padding: 20px 12px;
}
.quick-link {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 4px;
  font-size: 13px;
}
.quick-link > .el-icon:first-child {
  font-size: 18px;
  color: #697586;
}
.quick-link .quick-arrow {
  margin-left: auto;
  color: #98a2b3;
  font-size: 12px;
}
.quick-link:hover {
  background: #f4f8ff;
  color: #1668dc;
}
@media (max-width: 1200px) {
  .overview-grid {
    grid-template-columns: minmax(0, 1fr);
  }
  .quick-links {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .recent-panel .panel-state {
    min-height: 180px;
  }
}
@media (max-width: 600px) {
  .overview,
  .stats-grid {
    gap: 12px;
  }
  .stat-card {
    padding: 16px 12px;
  }
  .stat-heading {
    font-size: 12px;
    line-height: 1.5;
    min-height: 36px;
    align-items: flex-start;
  }
  .stat-heading .el-icon {
    display: none;
  }
  .stat-card > strong {
    font-size: 26px;
    margin-top: 8px;
  }
  .stat-card > p {
    font-size: 11px;
  }
  .overview-grid {
    gap: 16px;
  }
  .panel-heading {
    padding: 16px;
    gap: 10px;
  }
  .panel-heading h2 {
    font-size: 14px;
  }
  .schedule-date {
    padding: 16px;
    font-size: 12px;
    flex-wrap: wrap;
  }
  .date-count {
    display: none;
  }
  .schedule-table {
    width: calc(100% - 32px);
    margin-inline: 16px;
  }
  .panel-footer {
    padding-inline: 16px;
  }
  .recent-list {
    padding-inline: 16px;
  }
  .quick-links {
    padding: 12px 4px;
  }
  .quick-link {
    font-size: 12px;
    gap: 8px;
  }
  .quick-link .quick-arrow {
    display: none;
  }
}
</style>
