<template>
  <div>
    <el-card>
      <template #header
        ><div class="schedule-header">
          <span>Semester scheduling</span>
          <div class="schedule-actions">
            <el-button :icon="Plus" :disabled="optionsLoading" @click="handleCreate"
              >Add one-off class</el-button
            ><el-button type="primary" :disabled="optionsLoading" @click="generateVisible = true"
              >Generate semester schedule</el-button
            >
          </div>
        </div></template
      >
      <div class="table-toolbar">
        <el-select
          v-model="params.semesterId"
          placeholder="All semesters"
          aria-label="Filter by semester"
          clearable
          style="width: 220px"
          @change="handleSearch"
          ><el-option
            v-for="item in semesterOptions"
            :key="item.id"
            :label="item.name"
            :value="item.id"
        /></el-select>
        <el-select
          v-model="params.userId"
          placeholder="All students"
          aria-label="Filter by user"
          clearable
          filterable
          style="width: 220px"
          @change="handleSearch"
          ><el-option
            v-for="item in studentOptions"
            :key="item.id"
            :label="`${item.name} (${item.username})`"
            :value="item.id"
        /></el-select>
        <el-date-picker
          v-if="activeTab === 'sessions'"
          v-model="params.date"
          type="date"
          value-format="YYYY-MM-DD"
          placeholder="Filter by date"
          aria-label="Filter by date"
          clearable
          @change="handleSearch"
        />
        <el-button :icon="Search" @click="handleSearch">Search</el-button>
        <RouterLink class="semester-link" to="/manager/semesters">Manage semesters</RouterLink>
      </div>
      <el-tabs v-model="activeTab" @tab-change="handleSearch"
        ><el-tab-pane label="Class sessions" name="sessions" /><el-tab-pane
          label="Weekly rules"
          name="rules"
      /></el-tabs>
      <template v-if="activeTab === 'sessions'">
        <el-checkbox v-model="showCancelled" @change="handleSearch" class="cancelled-filter"
          >Show cancelled classes</el-checkbox
        >
        <el-table :data="tableData" v-loading="loading">
          <el-table-column label="Student" min-width="170" show-overflow-tooltip
            ><template #default="{ row }"
              >{{ row.user_name }} ({{ row.username }})</template
            ></el-table-column
          >
          <el-table-column prop="class_date" label="Date" width="120" />
          <el-table-column prop="period" label="Period" width="90" />
          <el-table-column
            prop="course_name"
            label="Course"
            min-width="180"
            show-overflow-tooltip
          />
          <el-table-column prop="location" label="Location" min-width="130" show-overflow-tooltip />
          <el-table-column label="Source" min-width="180" show-overflow-tooltip
            ><template #default="{ row }"
              >{{ row.semester_name || 'One-off class'
              }}<span v-if="row.rule_id"> · Rule #{{ row.rule_id }}</span></template
            ></el-table-column
          >
          <el-table-column label="Status" width="120"
            ><template #default="{ row }"
              ><el-tag
                :type="row.is_cancelled ? 'info' : row.is_exception ? 'warning' : 'success'"
                >{{
                  row.is_cancelled ? 'Cancelled' : row.is_exception ? 'Adjusted' : 'Scheduled'
                }}</el-tag
              ></template
            ></el-table-column
          >
          <el-table-column label="Actions" width="200" fixed="right"
            ><template #default="{ row }"
              ><el-button
                v-if="row.is_cancelled"
                type="primary"
                link
                :loading="busyId === row.id"
                @click="restore(row)"
                >Restore</el-button
              ><template v-else
                ><el-button type="primary" link @click="handleEdit(row)">{{
                  row.rule_id ? 'Edit this class' : 'Edit'
                }}</el-button
                ><el-button type="danger" link @click="handleDelete(row)">{{
                  row.rule_id ? 'Cancel class' : 'Delete'
                }}</el-button></template
              ></template
            ></el-table-column
          >
          <template #empty
            >No classes match these filters. Generate a semester schedule or add a one-off
            class.</template
          >
        </el-table>
      </template>
      <el-table v-else :data="tableData" v-loading="loading">
        <el-table-column
          prop="semester_name"
          label="Semester"
          min-width="160"
          show-overflow-tooltip
        />
        <el-table-column prop="user_name" label="Student" min-width="140" />
        <el-table-column prop="course_name" label="Course" min-width="180" show-overflow-tooltip />
        <el-table-column label="Day" width="120"
          ><template #default="{ row }">{{ weekdays[row.weekday - 1] }}</template></el-table-column
        >
        <el-table-column label="Weeks" width="90"
          ><template #default="{ row }"
            >{{ row.start_week }}–{{ row.end_week }}</template
          ></el-table-column
        >
        <el-table-column label="Periods" width="90"
          ><template #default="{ row }"
            >{{ row.start_period }}–{{ row.end_period }}</template
          ></el-table-column
        >
        <el-table-column prop="location" label="Location" min-width="120" />
        <el-table-column prop="session_count" label="Classes" width="90" />
        <el-table-column prop="exception_count" label="Adjusted / cancelled" width="170" />
        <el-table-column label="Actions" width="200" fixed="right"
          ><template #default="{ row }"
            ><el-button type="primary" link :loading="busyId === row.id" @click="regenerate(row)"
              >Generate missing classes</el-button
            ></template
          ></el-table-column
        >
        <template #empty
          >No weekly rules yet. Save a semester schedule to create the rules and classes
          together.</template
        >
      </el-table>
      <div class="table-pagination">
        <el-pagination
          v-model:current-page="params.page"
          :page-size="params.pageSize"
          :total="total"
          background
          layout="total, prev, pager, next"
          @current-change="load"
        />
      </div>
    </el-card>

    <GenerateScheduleDialog
      v-model="generateVisible"
      :semesters="semesterOptions"
      :students="studentOptions"
      :courses="courseOptions"
      :semester-id="params.semesterId"
      :user-id="params.userId"
      @generated="afterGeneration"
    />

    <el-dialog
      v-model="dialogVisible"
      :title="
        form.rule_id ? 'Edit this class only' : form.id ? 'Edit one-off class' : 'Add one-off class'
      "
      width="500px"
      destroy-on-close
      :close-on-click-modal="!formLoading"
    >
      <el-alert
        v-if="form.rule_id"
        :closable="false"
        type="info"
        :title="`This change applies to one class only. Original date: ${form.source_date}. The weekly rule and other classes are preserved.`"
        class="edit-notice"
      />
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <el-form-item label="Student" prop="user_id"
          ><el-select
            v-model="form.user_id"
            :disabled="!!form.rule_id"
            filterable
            placeholder="Select student"
            ><el-option
              v-for="item in studentOptions"
              :key="item.id"
              :label="`${item.name} (${item.username})`"
              :value="item.id" /></el-select
        ></el-form-item>
        <el-form-item label="Course" prop="course_id"
          ><el-select
            v-model="form.course_id"
            :disabled="!!form.rule_id"
            filterable
            placeholder="Select course"
            ><el-option
              v-for="item in courseOptions"
              :key="item.id"
              :label="item.name"
              :value="item.id" /></el-select
        ></el-form-item>
        <el-form-item label="Class date" prop="class_date"
          ><el-date-picker
            v-model="form.class_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="Select date"
            style="width: 100%"
        /></el-form-item>
        <div class="period-fields">
          <el-form-item label="First period" prop="start_period"
            ><el-input-number
              v-model="form.start_period"
              :min="1"
              :max="30"
              controls-position="right" /></el-form-item
          ><el-form-item label="Last period" prop="end_period"
            ><el-input-number
              v-model="form.end_period"
              :min="form.start_period || 1"
              :max="30"
              controls-position="right"
          /></el-form-item>
        </div>
        <el-form-item label="Location"
          ><el-input v-model="form.location" maxlength="100" placeholder="For example: A201"
        /></el-form-item>
      </el-form>
      <template #footer
        ><el-button :disabled="formLoading" @click="dialogVisible = false">Cancel</el-button
        ><el-button type="primary" :loading="formLoading" @click="handleSave"
          >Save class</el-button
        ></template
      >
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { Plus, Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  createScheduleApi,
  deleteScheduleApi,
  listSchedulesApi,
  updateScheduleApi,
  listScheduleRulesApi,
  regenerateScheduleRuleApi,
  restoreScheduleApi
} from '@/api/schedule'
import { listSemestersApi } from '@/api/semester'
import { listCoursesApi } from '@/api/course'
import { getUserPageList } from '@/api/user'
import GenerateScheduleDialog from '@/components/GenerateScheduleDialog.vue'

const params = reactive({ page: 1, pageSize: 10, userId: null, semesterId: null, date: null })
const activeTab = ref('sessions')
const showCancelled = ref(true)
const loading = ref(false)
const optionsLoading = ref(true)
const tableData = ref([])
const total = ref(0)
const studentOptions = ref([])
const courseOptions = ref([])
const semesterOptions = ref([])
const busyId = ref(null)
const generateVisible = ref(false)
const dialogVisible = ref(false)
const formRef = ref()
const formLoading = ref(false)
const weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
const defaults = () => ({
  id: null,
  user_id: params.userId || null,
  course_id: null,
  class_date: '',
  start_period: 1,
  end_period: 2,
  location: '',
  rule_id: null,
  source_date: null
})
const form = reactive(defaults())
const rules = {
  user_id: [{ required: true, message: 'Select a student', trigger: 'change' }],
  course_id: [{ required: true, message: 'Select a course', trigger: 'change' }],
  class_date: [{ required: true, message: 'Select a class date', trigger: 'change' }],
  start_period: [{ required: true, message: 'Enter the first period', trigger: 'change' }],
  end_period: [{ required: true, message: 'Enter the last period', trigger: 'change' }]
}
let requestId = 0
async function load() {
  const currentRequest = ++requestId
  loading.value = true
  try {
    const filter = {
      page: params.page,
      page_size: params.pageSize,
      user_id: params.userId || undefined,
      semester_id: params.semesterId || undefined
    }
    const result =
      activeTab.value === 'rules'
        ? await listScheduleRulesApi(filter)
        : await listSchedulesApi({
            ...filter,
            date: params.date || undefined,
            include_cancelled: showCancelled.value
          })
    if (currentRequest === requestId && result.code === 200) {
      tableData.value = result.data?.list || []
      total.value = result.data?.total || 0
    }
  } finally {
    if (currentRequest === requestId) loading.value = false
  }
}
function handleSearch() {
  params.page = 1
  tableData.value = []
  load()
}
function handleCreate() {
  Object.assign(form, defaults())
  dialogVisible.value = true
}
function handleEdit(row) {
  const periods = String(row.period).match(/^(\d+)(?:\s*[-–—]\s*(\d+))?$/)
  Object.assign(form, defaults(), row, {
    start_period: row.start_period || Number(periods?.[1]) || 1,
    end_period: row.end_period || Number(periods?.[2] || periods?.[1]) || 2
  })
  dialogVisible.value = true
}
async function handleSave() {
  if (formLoading.value || !(await formRef.value.validate().catch(() => false))) return
  if (form.end_period < form.start_period) {
    ElMessage.warning('Check the period range')
    return
  }
  formLoading.value = true
  try {
    const data = {
      user_id: form.user_id,
      course_id: form.course_id,
      class_date: form.class_date,
      period: `${form.start_period}-${form.end_period}`,
      location: form.location || ''
    }
    const result = form.id ? await updateScheduleApi(form.id, data) : await createScheduleApi(data)
    if (result.code === 200) {
      dialogVisible.value = false
      ElMessage.success('Class saved')
      await load()
    }
  } finally {
    formLoading.value = false
  }
}
async function handleDelete(row) {
  const confirmed = await ElMessageBox.confirm(
    row.rule_id
      ? `Cancel only this class on ${row.class_date}? The cancellation will be kept when the rule is generated again.`
      : `Delete this one-off class on ${row.class_date}?`,
    row.rule_id ? 'Cancel this class' : 'Delete class',
    {
      type: 'warning',
      confirmButtonText: row.rule_id ? 'Cancel class' : 'Delete',
      cancelButtonText: 'Keep class'
    }
  )
    .then(() => true)
    .catch(() => false)
  if (!confirmed) return
  const result = await deleteScheduleApi(row.id)
  if (result.code === 200) {
    ElMessage.success(row.rule_id ? 'Class cancelled' : 'Class deleted')
    await load()
  }
}
async function restore(row) {
  if (busyId.value !== null) return
  busyId.value = row.id
  try {
    const result = await restoreScheduleApi(row.id)
    if (result.code === 200) {
      ElMessage.success('Class restored')
      await load()
    }
  } finally {
    busyId.value = null
  }
}
async function regenerate(row) {
  if (busyId.value !== null) return
  busyId.value = row.id
  try {
    const result = await regenerateScheduleRuleApi(row.id)
    if (result.code === 200) {
      ElMessage.success(
        `Created ${result.data.created_count} classes; preserved ${result.data.preserved_count} existing classes`
      )
      await load()
    }
  } finally {
    busyId.value = null
  }
}
function afterGeneration(filter) {
  params.semesterId = filter.semesterId
  params.userId = filter.userId
  params.date = null
  activeTab.value = 'sessions'
  handleSearch()
}
async function loadOptions() {
  optionsLoading.value = true
  try {
    await Promise.allSettled([
      listSemestersApi().then((result) => {
        if (result.code === 200) semesterOptions.value = result.data || []
      }),
      listCoursesApi().then((result) => {
        if (result.code === 200) courseOptions.value = result.data || []
      }),
      (async () => {
        const users = []
        for (let page = 1; ; page++) {
          const result = await getUserPageList({ page, page_size: 100 })
          if (result.code !== 200) break
          const items = result.data?.list || []
          users.push(...items)
          if (!items.length || users.length >= (result.data?.total || 0)) break
        }
        studentOptions.value = users.filter((item) => item.role === 'student')
      })()
    ])
  } finally {
    optionsLoading.value = false
  }
}
onMounted(async () => {
  await Promise.allSettled([loadOptions(), load()])
})
</script>

<style scoped>
.schedule-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}
.schedule-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.schedule-actions .el-button + .el-button {
  margin-left: 0;
}
.semester-link {
  color: var(--el-color-primary);
  font-size: 13px;
  margin-left: auto;
}
.cancelled-filter {
  margin-bottom: 12px;
}
.edit-notice {
  margin-bottom: 20px;
}
.period-fields {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}
.period-fields .el-input-number {
  width: 100%;
}
@media (max-width: 600px) {
  .semester-link {
    margin-left: 0;
  }
}
</style>
