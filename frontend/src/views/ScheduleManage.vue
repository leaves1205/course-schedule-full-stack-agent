<template>
  <div>
    <el-card>
      <template #header>
        <div style="font-size: 16px; font-weight: bold">Schedule list</div>
      </template>
      <div class="table-toolbar">
        <el-select
          v-model="params.userId"
          placeholder="Filter by user"
          aria-label="Filter by user"
          clearable
          filterable
          style="width: 220px"
          @change="handleSearch"
          @clear="handleSearch"
        >
          <el-option
            v-for="u in studentOptions"
            :key="u.id"
            :label="`${u.name} (${u.username})`"
            :value="u.id"
          />
        </el-select>
        <el-date-picker
          v-model="params.date"
          type="date"
          value-format="YYYY-MM-DD"
          placeholder="Filter by date"
          aria-label="Filter by date"
          clearable
          @change="handleSearch"
          @clear="handleSearch"
        />
        <el-button :icon="Search" @click="handleSearch">Search</el-button>
        <el-button class="toolbar-create" type="primary" :icon="Plus" @click="handleCreate"
          >Add schedule</el-button
        >
      </div>
      <el-table
        v-loading="loading"
        :header-cell-style="{ backgroundColor: '#f5f7fa', color: '#333' }"
        :data="tableData"
        style="width: 100%"
      >
        <el-table-column label="Student" min-width="140">
          <template #default="{ row }"> {{ row.user_name }} ({{ row.username }}) </template>
        </el-table-column>
        <el-table-column prop="class_date" label="Date" width="120" />
        <el-table-column prop="period" label="Period" width="110" />
        <el-table-column prop="course_name" label="Course" min-width="140" />
        <el-table-column prop="location" label="Location" min-width="120" />
        <el-table-column label="Actions" width="180" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="handleEdit(row)">Edit</el-button>
            <el-button type="danger" link @click="handleDelete(row)">Delete</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="table-pagination">
        <el-pagination
          v-model:current-page="params.page"
          v-model:page-size="params.pageSize"
          :total="total"
          background
          layout="total, prev, pager, next"
          @current-change="load"
        />
      </div>
    </el-card>
    <el-dialog
      v-model="dialogVisible"
      :title="form.id ? 'Edit schedule' : 'Add schedule'"
      width="480"
      destroy-on-close
    >
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        style="padding-top: 8px"
      >
        <el-form-item label="Student" prop="user_id">
          <el-select
            v-model="form.user_id"
            placeholder="Select a student"
            filterable
            style="width: 100%"
          >
            <el-option
              v-for="u in studentOptions"
              :key="u.id"
              :label="`${u.name} (${u.username})`"
              :value="u.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="Course" prop="course_id">
          <el-select
            v-model="form.course_id"
            placeholder="Select a course"
            filterable
            style="width: 100%"
          >
            <el-option
              v-for="c in courseOptions"
              :key="c.id"
              :label="c.code ? `${c.name} (${c.code})` : c.name"
              :value="c.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="Class date" prop="class_date">
          <el-date-picker
            v-model="form.class_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="Select a date"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="Period" prop="period">
          <el-input v-model="form.period" placeholder="For example: periods 1-2" />
        </el-form-item>
        <el-form-item label="Location" prop="location">
          <el-input v-model="form.location" placeholder="For example: Building A, room A201" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">Cancel</el-button>
        <el-button type="primary" :loading="formLoading" @click="handleSave">Confirm</el-button>
      </template>
    </el-dialog>
  </div>
</template>
<script setup>
defineOptions({ name: 'ScheduleManage' })
import { Plus, Search } from '@element-plus/icons-vue'
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  createScheduleApi,
  deleteScheduleApi,
  listSchedulesApi,
  updateScheduleApi
} from '@/api/schedule'
import { listCoursesApi } from '@/api/course'
import { getUserPageList } from '@/api/user'

const params = reactive({
  page: 1,
  pageSize: 10,
  userId: null,
  date: null
})
const loading = ref(false)
const tableData = ref([])
const total = ref(0)

const studentOptions = ref([])
const courseOptions = ref([])

const dialogVisible = ref(false)
const formRef = ref()
const formLoading = ref(false)
const form = reactive({
  id: null,
  user_id: null,
  course_id: null,
  class_date: '',
  period: '',
  location: ''
})

const rules = {
  user_id: [{ required: true, message: 'Please select a student', trigger: 'change' }],
  course_id: [{ required: true, message: 'Please select a course', trigger: 'change' }],
  class_date: [{ required: true, message: 'Please select a class date', trigger: 'change' }],
  period: [{ required: true, message: 'Please enter a period', trigger: 'blur' }],
  location: [{ required: true, message: 'Please enter a location', trigger: 'blur' }]
}

const resetForm = () => {
  Object.assign(form, {
    id: null,
    user_id: params.userId || null,
    course_id: null,
    class_date: '',
    period: '',
    location: ''
  })
}

const loadStudents = async () => {
  const res = await getUserPageList({ page: 1, page_size: 200 })
  if (res.code === 200) {
    studentOptions.value = (res.data?.list || []).filter((u) => u.role === 'student')
  }
}

const loadCourses = async () => {
  const res = await listCoursesApi()
  if (res.code === 200) {
    courseOptions.value = (res.data || []).filter((c) => c.status === 1)
  }
}

const load = async () => {
  loading.value = true
  try {
    const res = await listSchedulesApi({
      page: params.page,
      page_size: params.pageSize,
      user_id: params.userId ?? undefined,
      date: params.date || undefined
    })
    if (res.code === 200) {
      tableData.value = res.data?.list || []
      total.value = res.data?.total || 0
    }
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  params.page = 1
  load()
}

const handleCreate = () => {
  resetForm()
  dialogVisible.value = true
}

const handleEdit = (row) => {
  resetForm()
  Object.assign(form, {
    id: row.id,
    user_id: row.user_id,
    course_id: row.course_id,
    class_date: row.class_date,
    period: row.period,
    location: row.location
  })
  dialogVisible.value = true
}

const handleSave = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  formLoading.value = true
  try {
    const payload = {
      user_id: form.user_id,
      course_id: form.course_id,
      class_date: form.class_date,
      period: form.period,
      location: form.location
    }
    const res = form.id
      ? await updateScheduleApi(form.id, payload)
      : await createScheduleApi(payload)
    if (res.code === 200) {
      dialogVisible.value = false
      ElMessage.success('Operation successful')
      load()
    }
  } finally {
    formLoading.value = false
  }
}

const handleDelete = (row) => {
  ElMessageBox.confirm(
    `Delete the schedule for [${row.user_name}] on ${row.class_date}: [${row.course_name}]?`,
    'Confirm deletion',
    { type: 'warning' }
  ).then(async () => {
    const res = await deleteScheduleApi(row.id)
    if (res.code === 200) {
      ElMessage.success('Deleted')
      load()
    }
  })
}

onMounted(async () => {
  await Promise.all([loadStudents(), loadCourses()])
  load()
})
</script>
