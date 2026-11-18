<template>
  <div>
    <el-card>
      <template #header>
        <div style="font-size: 16px; font-weight: bold">Course list</div>
      </template>
      <div class="table-toolbar">
        <el-input
          v-model="keywords"
          placeholder="Search by name, code or description"
          aria-label="Search courses"
          style="width: 300px"
          clearable
          @keyup.enter="handleSearch"
          @clear="handleSearch"
        />
        <el-button :icon="Search" @click="handleSearch">Search</el-button>
        <el-button class="toolbar-create" type="primary" :icon="Plus" @click="handleCreate"
          >Add course</el-button
        >
      </div>
      <el-table
        v-loading="loading"
        :header-cell-style="{ backgroundColor: '#f5f7fa', color: '#333' }"
        :data="allData"
        style="width: 100%"
      >
        <el-table-column prop="name" label="Course name" min-width="140" />
        <el-table-column prop="code" label="Course code" width="120" />
        <el-table-column
          prop="description"
          label="Description"
          min-width="200"
          show-overflow-tooltip
        />
        <el-table-column prop="status" label="Status" width="90">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'info'">
              {{ row.status === 1 ? 'Active' : 'Inactive' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="Actions" width="180" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="handleEdit(row)">Edit</el-button>
            <el-button type="danger" link @click="handleDelete(row)">Delete</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
    <el-dialog v-model="dialogVisible" :title="form.id ? 'Edit course' : 'Add course'" width="480">
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        style="padding-top: 8px"
      >
        <el-form-item label="Course name" prop="name">
          <el-input v-model="form.name" placeholder="For example: Data Structures" />
        </el-form-item>
        <el-form-item label="Course code" prop="code">
          <el-input v-model="form.code" placeholder="Optional, unique" />
        </el-form-item>
        <el-form-item label="Description" prop="description">
          <el-input v-model="form.description" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="Status">
          <el-radio-group v-model="form.status">
            <el-radio :value="1">Active</el-radio>
            <el-radio :value="0">Inactive</el-radio>
          </el-radio-group>
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
defineOptions({ name: 'Course' })
import { Search, Plus } from '@element-plus/icons-vue'
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { createCourseApi, deleteCourseApi, listCoursesApi, updateCourseApi } from '@/api/course'

const keywords = ref('')
const loading = ref(false)
const allData = ref([])

const dialogVisible = ref(false)
const formRef = ref()
const formLoading = ref(false)
const form = reactive({
  id: null,
  name: '',
  code: '',
  description: '',
  status: 1
})
const rules = {
  name: [{ required: true, message: 'Please enter a course name', trigger: 'blur' }],
  code: [{ required: true, message: 'Please enter a course code', trigger: 'blur' }]
}

const resetForm = () => {
  Object.assign(form, {
    id: null,
    name: '',
    code: '',
    description: '',
    status: 1
  })
}

const load = async () => {
  loading.value = true
  try {
    const res = await listCoursesApi({ keywords: keywords.value || undefined })
    if (res.code === 200) {
      allData.value = res.data || []
    }
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
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
    name: row.name,
    code: row.code || '',
    description: row.description || '',
    status: row.status
  })
  dialogVisible.value = true
}

const handleSave = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  formLoading.value = true
  try {
    const payload = {
      name: form.name,
      code: form.code || null,
      description: form.description || null,
      status: form.status
    }
    const res = form.id ? await updateCourseApi(form.id, payload) : await createCourseApi(payload)
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
  ElMessageBox.confirm(`Delete course [${row.name}]?`, 'Confirm deletion', {
    type: 'warning'
  }).then(async () => {
    const res = await deleteCourseApi(row.id)
    if (res.code === 200) {
      ElMessage.success('Deleted')
      load()
    }
  })
}

onMounted(() => {
  load()
})
</script>
